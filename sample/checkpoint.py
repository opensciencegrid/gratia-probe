#!/usr/bin/python
__author__ = 'marcom'

#import sys, os, stat
#import time
#import calendar

import sys
import os
import logging
import stat
import tempfile
from datetime import datetime, timedelta
try:
    import cPickle
except ImportError:
    import pickle as cPickle

try:
    from gratia.common.Gratia import DebugPrint
except ImportError:
    def DebugPrint(val, msg):
        print ("DEBUG LEVEL %s: %s" % (val, msg))


class Checkpoint(object):
    """Checkpoint base class to enforce attributes
    """
    #def __init__(self):
    #    pass

    def get_val(self):
        raise AttributeError

    def set_val(self, val):
        raise AttributeError

    value = property(get_val, set_val)

    def conditional_set(self, val):
        raise AttributeError

    def sync(self):
        pass

    def close(self):
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
        # should never get here
        return None, None


class SimpleCheckpoint(Checkpoint):
    """Read and write a checkpoint file
    This class is a singleton (only one checkpoint is allowed)
    Checkpoint value is number of seconds from epoch
    If class is instantiated without a filename, class works as expected but
    data is not stored to disk
    """
    #TODO: long int is OK for all?
    #TODO: extend to support multiple checkpoints on different files?

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
        if target:
            try:
                fd = os.open(target, os.O_RDWR | os.O_CREAT)
                self._fp = os.fdopen(fd, 'r+')
                self._val = long(self._fp.readline())
                if self._val < min_val:
                    self._val = min_val
                DebugPrint(3, "Resuming from checkpoint in %s" % target)
            except IOError:
                raise IOError("Could not open checkpoint file %s" % target)
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
        if val<self._val:
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
            date - datestamp in UTC  or  seconds from the Epoch in UTC
            txn - integer (can be None)
    """
    #TODO: test and choose the following
    # - add also checksum (for consistency)?
    # - append multiple lines to the pending file and use the last one (better performance?)
    _single = None

    def __init__(self, target, max_age=-1, default_age=30, full_precision=False):
        """
        target - can be the name of the table in the DB for which we are keeping
        a checkpoint. It is used to locate the file with the pickled record
        of the last checkpoint. Default: dtcheckpoint
        max_age - maximum age for records. -1, no limit. Default: -1
        default_age - default age in days, used if no checkpoint is provided. Default: 30
        full_precision - if True, checkpoints read from file are not truncated to the beginning
                         of the hour. Default: False
        """
        if not target:
            target = 'dtcheckpoint'
        self._target = target  # both file name (abs path) and checkpoint ID
        self._tmp_fp = None
        self._tmp_filename = ''
        self._pending = False
        self._pending_dateStamp = datetime.min
        self._pending_transaction = None

        default_day = None

        if max_age is None or max_age < 0:
            min_day = datetime.min  # down of time: datetime(1, 1, 1, 0, 0)
        else:
            # datetime.utcnow() is unbound
            # datetime.now(utc) , with utc=UTC(), a subclass of tzinfo would be better
            # https://docs.python.org/2/library/datetime.html
            now = datetime.utcnow()
            now = datetime(now.year, now.month, now.day, 0, 0, 0)
            min_day = now - timedelta(max_age, 0)
            if default_age is None or default_age > max_age:
                default_age = max_age
                default_day = min_day

        try:
            pklFile = open(target, 'rb')
            self._dateStamp, self._transaction = cPickle.load(pklFile)
            if max_age >= 0:
                if self._dateStamp < min_day:
                    self._dateStamp = min_day
            if not full_precision:
                # restart from the beginning of the hour
                ds = self._dateStamp
                self._dateStamp = datetime(ds.year, ds.month, ds.day, ds.hour, 0, 0)
            pklFile.close()
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
            if default_day is None:
                # delayed to evaluate only if needed
                now = datetime.utcnow()
                now = datetime(now.year, now.month, now.day, 0, 0, 0)
                default_day = now - timedelta(default_age, 0)
            self._dateStamp = default_day
            self._transaction = None

    def get_val(self):
        return {'date': self._dateStamp,
                'transaction': self._transaction}

    def set_date_transaction(self, date, transaction=None):
        self.set_val({'date': date, 'transaction': transaction})

    def set_val(self, val):
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

    def prepare(self, val):
        """
        Saves the specified primary key string as the new checkpoint.
        The Checkpoint value is a dictionary {'date': date, 'transaction': txn}
            date - datestamp in UTC  or  seconds from the Epoch in UTC
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
            datestamp = datetime.utcfromtimestamp(datetime)
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
            # raise a warning?
            raise IOError("Checkpoint.commit called with no transaction")
            return

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

    def close(self):
        if os.path.exists(self._tmp_filename):
            os.chmod(self._tmp_filename, stat.S_IWRITE)
            os.remove(self._tmp_filename)  # remove and unlink are the same

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






get_checkpoint = SimpleCheckpoint.get_checkpoint


def test():
    print "Checkpoint test"
    print "File list (in %s)" % os.curdir
    print "%s" % [ i for i in os.listdir(os.curdir) if i.startswith('cptest')]
    c1 = SimpleCheckpoint() #('checkpoint-file')
    c1.value = '55'
    c2 = SimpleCheckpoint('cptestfile-simplecheckpoint')
    c2.value = '66'
    c3 = DateTransactionCheckpoint('cptestfile-dtcheckpoint')
    c3.value = {'date': datetime.now(),
                'transaction': 77}
    print "Before close"
    print "%s" % [ i for i in os.listdir(os.curdir) if i.startswith('cptest')]
    c3.close()
    print "After close"
    print "%s" % [ i for i in os.listdir(os.curdir) if i.startswith('cptest')]
    cc1 = SimpleCheckpoint()
    cc2 = SimpleCheckpoint('cptestfile-simplecheckpoint')
    cc3 = DateTransactionCheckpoint('cptestfile-dtcheckpoint')
    print "Checkpoint values: %s, %s, %s." % (cc1.value, cc2.value, cc3.value)
    print "Before final close"
    print "%s" % [ i for i in os.listdir(os.curdir) if i.startswith('cptest')]
    cc3.close()
    print "At end"
    print "%s" % [ i for i in os.listdir(os.curdir) if i.startswith('cptest')]

if __name__ == "__main__":
    import sys
    import time # needed for python < 2.5
    if sys.argv[1] == 'test':
        test()
        sys.exit(0)
    if sys.argv[1] == 'read':
        cp = DateTransactionCheckpoint(sys.argv[2])
        print "Checkpoint value:\n%s\n%s" % (cp.date(), cp.transaction())
    elif sys.argv[1] == 'write':
        cp = DateTransactionCheckpoint(sys.argv[2])
        tmp = None
        if len(sys.argv) > 4:
            tmp = sys.argv[4]
        try:
            # time.strptime()
            # datetime.utcfromtimestamp()
            # datetime.strptime -is like- datetime(*(time.strptime(date_string, format)[0:6]))
            # python >= 2.5: tmp_date = datetime.strptime(sys.argv[3], "%Y-%m-%d %H:%M:%S")
            tmp_date = datetime(*(time.strptime(sys.argv[3], "%Y-%m-%d %H:%M:%S")[0:6]))
        except ValueError:
            # python >= 2.5: tmp_date = datetime.strptime(sys.argv[3], "%Y-%m-%d")
            tmp_date = datetime(*(time.strptime(sys.argv[3], "%Y-%m-%d")[0:6]))
        cp.set_date_transaction(tmp_date, tmp)
        print "Checkpoint saved"
    else:
        name = sys.argv[0]
        print "Usage:"
        print "%s test - run a checksum test" % name
        print "%s read file_name - read a  DateTransactionCheckpoint" % name
        print "%s write file_name date [transaction] - write a DateTransactionCheckpoint" % name




