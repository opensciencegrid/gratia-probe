#!/usr/bin/python
__author__ = 'marcom'

#import sys, os, stat
#import time
#import calendar

import sys  # used for DebugPrint replacement
import os
#import logging
import stat
import tempfile
from datetime import datetime, timedelta
try:
    import cPickle
except ImportError:
    import pickle as cPickle

try:
    from gratia.common.debug import DebugPrint
except ImportError:
    # DebugPrint form debug prints on log file (which this function will not) and on stderr
    def DebugPrint(val, msg):
        sys.stderr.write("DEBUG LEVEL %s: %s\n" % (val, msg))

import gratia.common2.timeutil as timeutil  # for datetime_to_unix_time


class Checkpoint(object):
    """Checkpoint base class to enforce attributes
    should never be instantiated
    All sub-classes must have:
    - self._target
    - get_val()
    - set_val(val)
    - conditional_set(val)
    And if different form set_val
    - prepare(val)
    And if different from NOOP
    - commit()
    - sync()
    - close()

    """
    #def __init__(self):
    #    pass

    def get_target(self):
        # child classes must have _target element
        return self._target

    def get_val(self):
        """getter for the checkpoint value"""
        raise AttributeError

    def set_val(self, val):
        """setter for the checkpoint value"""
        raise AttributeError

    value = property(get_val, set_val)

    def conditional_set(self, val):
        """set only if a special condition is true, e.g. the value is more recent"""
        raise AttributeError

    def prepare(self, val):
        """If no two-stage commit is required this is the same as set_val"""
        self.set_val(val)

    def commit(self):
        """Noop if no transaction is required"""
        pass

    def sync(self):
        """Make sure that the checkpoint is committed after this call"""
        pass

    def close(self):
        """close the checkpoint if needed"""
        pass

    #@classmethod
    #def get_checkpoint(cls, target=None):
    #    if cls._single is None:
    #        cls._single = cls(target)
    #    return cls._single

    @staticmethod
    def get_tempfile(target, suffix='temp', makedir=False):
        """Return a temporary file in a thread safe manner

        :param target: full pathname (dir, basename) used as prefix for the temporary file name
        :return: file handle, file name
        """
        #dirname = os.path.dirname(target)
        #prefix = os.path.basename(target)
        dirname, prefix = os.path.split(target)
        if makedir and not os.path.exists(dir):
            try:
                os.makedirs(dirname)
            except IOError, (errno, strerror):
                raise IOError("Could not create checkpoint directory %s: %s" %
                              (dirname, strerror))
        try:
            fd, fname = tempfile.mkstemp(suffix, prefix, dirname)
            # returning a file obj open for write instead of a file descriptor
            return os.fdopen(fd, 'w'), fname
        except OSError:
            raise IOError("Could not open checkpoint file %sXXXX%s" % (os.path.join(dirname, prefix), suffix))


class SimpleCheckpoint(Checkpoint):
    """Read and write a checkpoint file
    This class is a singleton (only one checkpoint is allowed)
    Checkpoint value is number of seconds from epoch
    If class is instantiated without a filename, class works as expected but
    data is not stored to disk
    """

    _single = None

    def __init__(self, target=None, min_val=None, default_val=None):
        """
        Open or Create a checkpoint file
        target - checkpoint filename (optionally null)
        min_val - checkpoint cannot be less than it
        default_val - checkpoint will assume this value if no checkpoint value is available
        """
        self._val = default_val
        self._fp = None
        self._target = None
        if target:
            try:
                fd = os.open(target, os.O_RDWR | os.O_CREAT)
                self._fp = os.fdopen(fd, 'r+')
                self._val = long(self._fp.readline())
                if self._val < min_val:
                    self._val = min_val
                DebugPrint(3, "Resuming from checkpoint in %s" % target)
            except IOError:
                #raise IOError("Could not open checkpoint file %s" % target)
                DebugPrint(1, "Could not open checkpoint file %s" % target)
            except EOFError:
                DebugPrint(1, "Empty or truncated checkpoint file %s" % target)
            except ValueError:
                DebugPrint(1, "Failed to read checkpoint file %s" % target)
        if self._val < min_val:
            # None can be compared with integers (it is smaller)
            DebugPrint(3, "Checkpoint adjusted to %s" % min_val)
            self._val = min_val

    def get_val(self):
        """Get checkpoint value"""
        return self._val

    def set_val(self, val):
        """Set checkpoint value"""
        self._val = long(val)
        if self._fp:
            self._fp.seek(0)
            self._fp.write(str(self._val) + "\n")
            self._fp.truncate()

    value = property(get_val, set_val)

    def conditional_set(self, val):
        """Set only for greater values of val. Return True if setting a new value"""
        if val < self._val:
            return False
        self.set_val(val)
        return True

    @staticmethod
    def get_checkpoint(target=None, min_val=None, default_val=None):
        if SimpleCheckpoint._single is None:
            SimpleCheckpoint._single = SimpleCheckpoint(target, min_val, default_val)
        return SimpleCheckpoint._single


class DateTransactionCheckpoint(Checkpoint):
    """Checkpoint with date and transaction

    Must have a file to store the checkpoint, default is dtcheckpoint
    Write and move is used together with file syncing primitives
    to improve atomicity and durability

    The checkpoint value is a dictionary {'date': date, 'transaction': txn}
            date - datetime.datetime object (UTC or a timezone consistent within the use of the checkpoint)
            txn - integer (can be None)
    """
    #TODO: test and choose the following
    # - add also checksum to the checksum file (for consistency)?
    # - append multiple lines to the pending file and use the last one (better performance?)
    _single = None

    def __init__(self, target, max_age=-1, default_age=30, full_precision=True):
        """Initialize a checkpoint reading the value from the file (if it exists)

        :param target: can be the name of the table in the DB for which we are keeping
        a checkpoint. It is used to locate the file with the pickled record
        of the last checkpoint. Default: dtcheckpoint
        :param max_age: maximum age for records in days. -1, meas no limit. Default: -1
        :param default_age: default age in days, used if no checkpoint is provided. Default: 30
        :param full_precision: if True, checkpoints read from file are not truncated to the beginning
                         of the hour. Default: False
        :return:
        """
        if not target:
            target = 'dtcheckpoint'
        self._target = target  # both file name (abs path) and checkpoint ID
        self._tmp_fp = None
        self._tmp_filename = ''
        self._pending = False
        self._pending_dateStamp = datetime.min
        self._pending_transaction = None

        # None checking can be removed in py2 (None < any int), but None gives TypeError in py3 when compared to int
        if max_age is None:
            max_age = -1
        if default_age is None:
            default_age = -1
        min_day = datetime.min
        # Checkpoint date cannot be None (checkpoint has to be None)
        default_day = min_day

        if max_age >= 0 or default_age >= 0:
            # datetime.utcnow() is unbound
            # datetime.now(utc) , with utc=UTC(), a subclass of tzinfo would be better
            # https://docs.python.org/2/library/datetime.html
            now = datetime.utcnow()
            now = datetime(now.year, now.month, now.day, 0, 0, 0)

            if max_age >= 0:
                min_day = now - timedelta(max_age, 0)
                default_day = min_day

            if default_age >= 0:
                if default_age > max_age >= 0:
                    default_age = max_age
                else:
                    default_day = now - timedelta(default_age, 0)

        # setting the default values
        self._dateStamp = default_day
        self._transaction = None

        # loading from file
        try:
            self._load(target)
        except IOError, (errno, strerror):
            # This is not really an error, since it might be the first
            # time we try to make this checkpoint.
            # We log a warning, just in case some nice person has
            # deleted the checkpoint file.
            #log = logging.getLogger('checkpoint')
            msg = "Checkpoint: couldn't read the checkpoint file %s: %s." % \
                  (target, strerror)
            msg += "\nThis is okay the first time you run the probe."
            #log.warn(msg)
            DebugPrint(3, msg)
        except EOFError:
            msg = "Checkpoint: the checkpoint file %s is empty or has wrong data (EOFError)." % \
                  (target,)
            DebugPrint(3, msg)
        # checking constraints
        if max_age >= 0:
            if self._dateStamp < min_day:
                self._dateStamp = min_day

        if not full_precision:
            # restart from the beginning of the hour
            ds = self._dateStamp
            self._dateStamp = datetime(ds.year, ds.month, ds.day, ds.hour, 0, 0)

    def _load(self, target):
        pkl_file = open(target, 'rb')
        self._dateStamp, self._transaction = cPickle.load(pkl_file)
        pkl_file.close()

    def get_val(self):
        return {'date': self._dateStamp,
                'transaction': self._transaction}

    def set_date_transaction(self, date, transaction=None):
        """
        Save checkpoint using the provided date and transaction (if provided)
        :param date: datetime object saved as provided. Can be UTC, some local time zone or naive
            must be consistent across the use of the same checkpoint
        :param transaction: long int or other transaction object
        :return: no return (None)
        """
        self.set_val({'date': date, 'transaction': transaction})

    def set_date_seconds_transaction(self, date_epoch, transaction=None):
        """ convert epoch to datetime, assume UTC """
        date = datetime.utcfromtimestamp(date_epoch)
        self.set_val({'date': date, 'transaction': transaction})

    def set_val(self, val):
        """
        Save checkpoint using the provided value with date and transaction.
        :param val: checkpoint, i.e. dictionary with keys 'date' and 'transaction'. Date must be a datetime object.
            Can be UTC, some local time zone or naive must be consistent across the use of the same checkpoint.
            Transaction can be None or any object acting as transaction ID (e.g. long int)
        :return: no return (None)
        """
        self.prepare(val)
        self.commit()

    value = property(get_val, set_val)

    def conditional_set(self, val):
        """Set only for greater values of 'date'. Return True if setting a new value"""
        # _dateStamp is always a valid date, val must contain a date not None
        if val['date'] < self._dateStamp:
            return False
        if self._pending and val['date'] < self._pending_dateStamp:
            return False
        self.set_val(val)
        return True

    def conditional_set_transaction(self, val):
        """Set only for greater values of 'transaction'. Return True if setting a new value"""
        # _transaction could be None or a valid transaction
        if self._transaction is not None and val['transaction'] < self._transaction:
            return False
        if self._pending_transaction is not None and self._pending and val['transaction'] < self._pending_transaction:
            return False
        self.set_val(val)
        return True

    def prepare(self, val):
        """
        Saves the specified primary key string as the new checkpoint.
        The Checkpoint value is a dictionary {'date': date, 'transaction': txn}
            date - datetime.datetime object in UTC (or a consistent time zone)
            txn - integer (can be None)
        """
        #TODO: Verify best option. Be more strict and accept only datestamp values?
        datestamp = val['date']
        txn = val['transaction']
        # date must be defined, transaction can be None
        if datestamp is None:
            raise IOError("Checkpoint.createPending was passed null values for date")
        # Check timestamp validity
        if not type(datestamp) == datetime:
            # raise IOError("Checkpoint.createPending was passed invalid date (%s, %s)" % (type(datestamp), datestamp))
            # attempting to convert to datetime - interpreting as seconds form the Epoch (UTC)
            datestamp = datetime.utcfromtimestamp(datestamp)
        self._pending_dateStamp = datestamp
        self._pending_transaction = txn
        # Get rid of extant pending file, if any.
        # truncate and write should be faster and as safe as
        # unlink and close
        if not self._tmp_fp:
            self._tmp_fp, self._tmp_filename = self.get_tempfile(self._target, '.pending')

        if self._tmp_fp:
            self._tmp_fp.seek(0)
            cPickle.dump([datestamp, txn], self._tmp_fp, -1)
            self._tmp_fp.truncate()
            self._tmp_fp.flush()
            # make sure that the file is on disk
            try:
                os.fdatasync(self._tmp_fp)
            except AttributeError:
                # This is not available on MacOS
                pass
            self._pending = True

    def commit(self):
        """
        We created the tmp file. Now make it the actual file with an atomic
        rename.
        We make the file read-only, in the hope it will reduce the risk
        of accidental/stupid deletion by third parties.
        """
        if not self._pending:
            # raise a warning or print and return?
            raise IOError("Checkpoint.commit called with no transaction")
            #return

        try:
            # move the temp file
            if os.path.exists(self._target):
                os.chmod(self._target, stat.S_IWRITE)
            os.rename(self._tmp_filename, self._target)
            os.chmod(self._target, stat.S_IREAD)
            # opening the directory to make sure that the rename took effect
            # could be removed since it is not too critical
            # the old checkpoint value would mean only some extra work
            dirname = os.path.dirname(self._target)
            if not dirname:
                dirname = "."
            dirfd = os.open(dirname, os.O_DIRECTORY)
            os.fsync(dirfd)
            os.close(dirfd)

            self._dateStamp = self._pending_dateStamp
            self._transaction = self._pending_transaction

            # values committed
            self._pending = False
            self._tmp_filename = ''
            self._tmp_fp = None  # will trigger the creation of a new temp file

        except OSError, (errno, strerror):
            raise IOError("Checkpoint.commit could not rename %s to %s: %s" %
                          (self._tmp_filename, self._target, strerror))

    def sync(self):
        """commit a checkpoint if needed
        """
        if self._pending:
            self.commit()

    def close(self):
        if os.path.exists(self._tmp_filename):
            os.chmod(self._tmp_filename, stat.S_IWRITE)
            os.remove(self._tmp_filename)  # remove and unlink are the same

    def date_seconds(self):
        """
        Returns last stored dateStamp in seconds from Epoch. It returns the epoch (datetime.min),
        if there is no stored checkpoint.
        """
        retv = self._dateStamp
        if not retv:
            retv = datetime.min
        return timeutil.datetime_to_unix_time(retv)

    def date(self):
        """
        Returns last stored dateStamp. It returns the epoch, if there is no
        stored checkpoint.
        """
        return self._dateStamp

    def transaction(self):
        """
        Returns last stored transaction id. It returns the empty string if
        there is no stored checkpoint.
        """
        return self._transaction


class DateTransactionAuxCheckpoint(DateTransactionCheckpoint):
    """Checkpoint with date, transaction and auxiliary value

    Must have a file to store the checkpoint, default is dtacheckpoint
    Extension of @DateTransactionCheckpoint (see for more implementation info)

    The checkpoint value is a dictionary {'date': date, 'transaction': txn, 'aux': aux}
            date - datetime.datetime object in UTC (or a consistent time zone)
            txn - integer (can be None)
            aux - arbitrary pickable object or dictionary (can be None)
    """
    def __init__(self, target, max_age=-1, default_age=30, full_precision=False):
        if not target:
            target = 'dtacheckpoint'
        # set the default (the ones not set in DateTransactionCheckpoint)
        self._aux = None
        # __init__ invokes _load() to load the value from file
        DateTransactionCheckpoint.__init__(self, target, max_age, default_age, full_precision)
        self._pending_aux = None

    def _load(self, target):
        pkl_file = open(target, 'rb')
        self._dateStamp, self._transaction, self._aux = cPickle.load(pkl_file)
        pkl_file.close()

    def get_val(self):
        return {'date': self._dateStamp,
                'transaction': self._transaction,
                'aux': self._aux}

    def aux(self):
        return self._aux

    def prepare(self, val):
        """
        Saves the specified primary key string as the new checkpoint.
        The Checkpoint value is a dictionary {'date': date, 'transaction': txn}
            date - datetime.datetime object in UTC (or a consistent time zone)
            txn - integer (can be None)
            aux - arbitrary pickable object (dictionary? can be None)
        """
        #TODO: see DateTransactionCheckpoint - maybe merge the 2 functions (factor out common part)
        datestamp = val['date']
        txn = val['transaction']
        aux = val['aux']
        # date must be defined, transaction can be None
        if datestamp is None:
            raise IOError("Checkpoint.createPending was passed null values for date")
        # Check timestamp validity
        if not type(datestamp) == datetime:
            # raise IOError("Checkpoint.createPending was passed invalid date (%s, %s)" % (type(datestamp), datestamp))
            # attempting to convert to datetime - interpreting as seconds form the Epoch (UTC)
            datestamp = datetime.utcfromtimestamp(datestamp)
        self._pending_dateStamp = datestamp
        self._pending_transaction = txn
        self._pending_aux = aux
        # Get rid of extant pending file, if any.
        # truncate and write should be faster and as safe as
        # unlink and close
        if not self._tmp_fp:
            self._tmp_fp, self._tmp_filename = self.get_tempfile(self._target, '.pending')

        if self._tmp_fp:
            self._tmp_fp.seek(0)
            cPickle.dump([datestamp, txn, aux], self._tmp_fp, -1)
            self._tmp_fp.truncate()
            self._tmp_fp.flush()
            # make sure that the file is on disk
            try:
                os.fdatasync(self._tmp_fp)
            except AttributeError:
                # This is not available on MacOS
                pass
            self._pending = True

    def commit(self):
        """
        We created the tmp file. Now make it the actual file with an atomic
        rename.
        We make the file read-only, in the hope it will reduce the risk
        of accidental/stupid deletion by third parties.
        """
        if not self._pending:
            # raise a warning or print and return?
            raise IOError("Checkpoint.commit called with no transaction")
            #return

        try:
            # move the temp file
            if os.path.exists(self._target):
                os.chmod(self._target, stat.S_IWRITE)
            os.rename(self._tmp_filename, self._target)
            os.chmod(self._target, stat.S_IREAD)
            # opening the directory to make sure that the rename took effect
            # could be removed since it is not too critical
            # the old checkpoint value would mean only some extra work
            dirname = os.path.dirname(self._target)
            if not dirname:
                dirname = "."
            dirfd = os.open(dirname, os.O_DIRECTORY)
            os.fsync(dirfd)
            os.close(dirfd)

            self._dateStamp = self._pending_dateStamp
            self._transaction = self._pending_transaction
            self._aux = self._pending_aux

            # values committed
            self._pending = False
            self._tmp_filename = ''
            self._tmp_fp = None  # will trigger the creation of a new temp file

        except OSError, (errno, strerror):
            raise IOError("Checkpoint.commit could not rename %s to %s: %s" %
                          (self._tmp_filename, self._target, strerror))

    def conditional_set_aux(self, val, aux_key=None, reverse=False):
        """Set only for greater or equal values of 'aux' or aux[val_key]. Return True if setting a new value"""
        # initial value of _aux may be None, if not the structure must be consistent
        # but then no need to check for None aux in pending because checkpoints are supposed to be
        # consistent (The same checkpoint will either have aux or not)
        smaller = False
        if aux_key:
            if self._aux[aux_key] is None:
                smaller = not reverse
            elif val['aux'][aux_key] < self._aux[aux_key]:
                smaller = True
            if self._pending and val['aux'][aux_key] < self._pending_aux[aux_key]:
                smaller = True
        else:
            if self._aux is None:
                smaller = not reverse
            elif val['aux'] < self._aux:
                smaller = True
            if self._pending and val['aux'] < self._pending_aux:
                smaller = True
        if smaller == reverse:
            return False
        self.set_val(val)
        return True

    def set_date_transaction_aux(self, date, transaction=None, aux=None):
        self.set_val({'date': date, 'transaction': transaction, 'aux': aux})


get_checkpoint = SimpleCheckpoint.get_checkpoint

CHECKPOINTS = {
    'simple': SimpleCheckpoint,
    'dt': DateTransactionCheckpoint,
    'dta': DateTransactionAuxCheckpoint,
    'DateTransactionCheckpoint': DateTransactionCheckpoint,
    'DateTransactionAuxCheckpoint': DateTransactionAuxCheckpoint
}


def test():
    print "Checkpoint test"
    print "File list (in %s)" % os.curdir
    print "%s" % [i for i in os.listdir(os.curdir) if i.startswith('cptest')]
    c1 = SimpleCheckpoint()  # ('checkpoint-file')
    c1.value = '55'
    c2 = SimpleCheckpoint('cptestfile-simplecheckpoint')
    c2.value = '66'
    c3 = DateTransactionCheckpoint('cptestfile-dtcheckpoint')
    c3.value = {'date': datetime.now(),
                'transaction': 77}
    print "Before close"
    print "%s" % [i for i in os.listdir(os.curdir) if i.startswith('cptest')]
    c3.close()
    print "After close"
    print "%s" % [i for i in os.listdir(os.curdir) if i.startswith('cptest')]
    cc1 = SimpleCheckpoint()
    cc2 = SimpleCheckpoint('cptestfile-simplecheckpoint')
    cc3 = DateTransactionCheckpoint('cptestfile-dtcheckpoint')
    print "Checkpoint values: %s, %s, %s." % (cc1.value, cc2.value, cc3.value)
    print "Before final close"
    print "%s" % [i for i in os.listdir(os.curdir) if i.startswith('cptest')]
    cc3.close()
    print "At end"
    print "%s" % [i for i in os.listdir(os.curdir) if i.startswith('cptest')]


def usage(name):
    outstr = """%(name)s [options] [test|read|write]
%(name)s test - run a checksum test
%(name)s [options] read - read a  DateTransactionCheckpoint
%(name)s [options] write date [[transaction] aux] - write a checkpoint
     default: DateTransactionCheckpoint
Options:
 -f FNAME - checkpoint file name (default depends from the checkpoint type)
 -t CP_TYPE - checkpoint type [simple|dt(DateTransactionCheckpoint)|dta(DateTransactionAuxCheckpoint)]
              default:dt
    """
    print outstr % ({'name': name})

if __name__ == "__main__":
    import sys
    import getopt
    import time  # needed for python < 2.5

    try:
        opts, args = getopt.getopt(sys.argv[1:], "hvf:t:", ["help"])
    except getopt.GetoptError as err:
        # print help information and exit:
        print str(err)
        usage(sys.argv[0])
        sys.exit(2)
    cp_fname = None
    cp_type = DateTransactionCheckpoint
    verbose = False
    for o, a in opts:
        if o == "-v":
            verbose = True
        elif o in ("-h", "--help"):
            usage(sys.argv[0])
            sys.exit()
        elif o in ("-f"):
            cp_fname = a
        elif o in ("-t"):
            try:
                cp_type = CHECKPOINTS[a]
            except KeyError:
                print "Invalid checkpoint type: %s" % a
                usage(sys.argv[0])
                sys.exit(2)
        else:
            print "Invalid option %s" % o
            usage(sys.argv[0])
            sys.exit(2)
    if not args:
        print "Must have at least one argument (%s)" % args
        usage(sys.argv[0])
        sys.exit(2)

    if args[0] == 'test':
        test()
        sys.exit(0)
    cp = cp_type(cp_fname)
    if args[0] == 'read':
        if isinstance(cp, DateTransactionCheckpoint):
            print "Checkpoint (%s) value:\n%s\n%s" % (cp.get_target(), cp.date(), cp.transaction())
            if isinstance(cp, DateTransactionAuxCheckpoint):
                # print also this
                print "%s" % (repr(cp.aux()),)
        else:
            print "Checkpoint (%s/%s) value:\n%s" % (cp.get_target(), type(cp), repr(cp.get_val()))
    elif args[0] == 'write':
        if len(args) < 2:
            print "Must provide at least one value to write (%s)" % args[1:]
            usage(sys.argv[0])
            sys.exit(2)
        for i in range(len(args), 4):
            args.append(None)
        try:
            try:
                # time.strptime()
                # datetime.utcfromtimestamp()
                # datetime.strptime -is like- datetime(*(time.strptime(date_string, format)[0:6]))
                # python >= 2.5: tmp_date = datetime.strptime(sys.argv[3], "%Y-%m-%d %H:%M:%S")
                tmp_date = datetime(*(time.strptime(args[1], "%Y-%m-%d %H:%M:%S")[0:6]))
            except ValueError:
                # python >= 2.5: tmp_date = datetime.strptime(sys.argv[3], "%Y-%m-%d")
                tmp_date = datetime(*(time.strptime(args[1], "%Y-%m-%d")[0:6]))
        except ValueError:
            print "Warning: %s is not a valid time" % args[1]
            tmp_date = args[1]

        if isinstance(cp, DateTransactionAuxCheckpoint):
            cp.set_date_transaction_aux(tmp_date, args[2], args[3])
        elif isinstance(cp, DateTransactionCheckpoint):
            cp.set_date_transaction(tmp_date, args[2])
        else:
            cp.set_val(tmp_date)
        print "Checkpoint saved"
    else:
        print "Invalid argument (%s)" % args
        usage(sys.argv[0])
        sys.exit(2)
