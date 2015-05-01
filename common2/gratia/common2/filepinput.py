#!/usr/bin/python
#
# File input using iterators
# By Marco Mambelli; Jun 9, 2014
#

import os
import re
import glob
import os.path

from gratia.common.Gratia import DebugPrint
import gratia.common.GratiaCore as GratiaCore
#import gratia.common.GratiaWrapper as GratiaWrapper
import gratia.common.Gratia as Gratia
import gratia.common.file_utils as file_utils

import gratia.common2.checkpoint as checkpoint

# package inputs are ahead

prog_version = "%%%RPMVERSION%%%"
prog_revision = '$Revision: 5268 $'


# --- functions -----------------------------------------------------------------------


val_bool_re = re.compile("^(\w{1,255}) = (true|True|TRUE|false|False|FALSE)$")
val_int_re = re.compile("^(\w{1,255}) = (-?\d{1,30})$")
val_double_re = re.compile("^(\w{1,255}) = ([+-]? *(?:\d{1,30}\.?\d{0,30}|\.\d{1,30})(?:[Ee][+-]?\d{1,30})?)$")
val_string_re = re.compile("^(\S+) = \"(.*)\"$")
val_catchall_re = re.compile("^(\S+) = (.*)$")
def lines_to_record(lines):
    """Parse one or more lines of data into a record (data structure)
    Here regular expressions are used to match values for a dictionary
    The input steram is a series of "name = value" lines with
    empty lines or the end of a stream separating records
    '#' at the beginning of the line is used to add comments (skipped)

    :param lines:
    :return:
    """
    # dictionary, caseless_dictionary, sorted dictionary, array
    # are all possible structures, be consistent with what you use in process_record
    record = {}
    if not type(lines) == type([]):
        lines = [lines]
    for line in lines:
        line = line.strip()
        m = val_bool_re.match(line)
        if m:
            attr, val = m.groups()
            if val.lower().find("true") >= 0:
                record[attr] = True
            else:
                record[attr] = False
            continue
        m = val_int_re.match(line)
        if m:
            attr, val = m.groups()
            record[attr] = int(val)
            continue
        m = val_double_re.match(line)
        if m:
            attr, val = m.groups()
            record[attr] = float(val)
            continue
        m = val_string_re.match(line)
        if m:
            attr, val = m.groups()
            record[attr] = str(val)
            continue
        m = val_catchall_re.match(line)
        if m:
            attr, val = m.groups()
            record[attr] = str(val)
            continue
        if not line:
            yield record
            record = {}
            continue
        if line[0] == '#':
            continue
        DebugPrint(2, "Invalid line in record stream: %s" % line)

    yield record


digits = re.compile(r'(\d+)')
def tokenize(filename):
    return tuple(int(token) if match else token
                 for token, match in
                 ((fragment, digits.search(fragment))
                  for fragment in digits.split(filename)))

# http://blog.codinghorror.com/sorting-for-humans-natural-sort-order/
convert = lambda text: int(text) if text.isdigit() else text
alphanum_key = lambda key: [convert(c) for c in re.split('([0-9]+)', key)]


# --- classes -------------------------------------------------------------------------
# TODO: evaluate the possibility of a separate iterator class
# Distinguish CommandInput (no checkpoint/ w/ checkpoint), FileInput (MultiFileInput?)
# use of fileinput?
# TODO: evaluate how to improve performance:
# linecache ?
# mmap ? mf = mmap.mmap(fin.fileno(), 0, access=mmap.ACCESS_READ)


from probeinput import ProbeInput, IgnoreRecordException


class FileInput(ProbeInput):
    """Input file
    """

    ########## Utility functions ########

    # Regular expression to recognize log files within a directory
    # examples:
    # condor_history_re = re.compile("^history.(\d+)\.(\d+)")
    # logfile_re = re.compile("^history\.(?:.*?\#)?\d+\.\d+")
    #

    SORT_NAME_NATURAL = "natural_order"
    SORT_NAME = "ascii"
    SORT_MDATE = "mdate"
    SORT_DATE = SORT_MDATE
    SORT_CDATE = "cdate"
    SORT_SIZE = "size"

    FILE_FILTER_RE = re.compile("^datafile\.(?:.*?\#)?\d+\.log")

    def name_filter_re(self, name):
        """Verify that it is a valid name using the regex FILE_FILTER_RE

        :param name: name of the file or directory
        :return: True if match, False otherwise
        """
        # more complex check
        # check multiple extension
        # if fname.endswith('.txt'):
        if self.FILE_FILTER_RE.match(name):
            return True
        else:
            return False

    @staticmethod
    def name_filter_ok(name):
        """Test function returning True all the time"""
        return True

    @staticmethod
    def name_filter_no_bck(name):
        if name == 'bck':
            return False
        return True

    @staticmethod
    def iter_tree(top_directory, dirname_filter=None, filename_filter=None):
        """Generator: iterate over all relevant files in the directory tree, yielding one
        (file name) at a time.

        :param top_directory:
        :param dirname_filter:
        :param filename_filter:
        :yield: file name (path)
        """
        # find all .txt documents, no matter how deep under top_directory
        for root, dirs, files in os.walk(top_directory):
            if dirname_filter:
                for i in dirs:
                    if not dirname_filter(i):
                        dirs.remove(i)
            #for fname in filter(lambda fname: fname.endswith('.txt'), files):
            for fname in files:
                if filename_filter:
                    if not filename_filter(fname):
                        continue
                # do some further processing?
                yield os.path.join(root, fname)

    @staticmethod
    def iter_directory(directory, filename_filter=None, filename_re="*", sort=None):
        """Generator: iterate over all relevant files in the directory, yielding one
        (file name) at a time.

        :param directory: directory name
        :param filename_filter: function accepting a file name and returning if it is valid True/False
                                (Default: None)
        :param filename_re: regular expression to filter file names (Default: *)
        :param sort: sorting of file names (Default: None)
        :yield: file name (path)
        """
        # find all files matching the RE
        files = [os.path.basename(i) for i in glob.glob(os.path.join(directory, filename_re))]
        # Sorting if defined
        if sort:
            if sort == FileInput.SORT_NAME:
                files.sort()
            elif sort == FileInput.SORT_NAME_NATURAL:
                files.sort(key=alphanum_key)
            elif sort == FileInput.SORT_MDATE:
                # TODO: extract mdate of the files and sort
                pass
            elif sort == FileInput.SORT_CDATE:
                # TODO: extract cdate of the files and sort
                pass
            elif sort == FileInput.SORT_SIZE:
                # TODO: extract size of the files and sort
                pass
        for fname in files:
            if filename_filter:
                if not filename_filter(fname):
                    continue
            # do some further processing?
            yield os.path.join(directory, fname)

    # TODO: add iter_file_binary()

    @staticmethod
    def iter_file(fname, buffering=None):
        """Generator returning all the lines of the file

        :param fname: file name
        :yield: line of the file
        """
        # Discussion about file buffer size
        # http://seann.herdejurgen.com/resume/samag.com/html/v11/i04/a6.htm
        # http://stackoverflow.com/questions/14863224/efficient-reading-of-800-gb-xml-file-in-python-2-7
        # open('foo.xml', buffering=(2<<16) + 8)
        # TODO: auto expand compressed files (.gz)
        # TODO: use buffering
        for line in open(fname):
            yield line

    @staticmethod
    def iter_enumerate_file(fname, buffering=None):
        """Generator returning all the lines of the file

        :param fname: file name
        :return: a tuple containing the line, the line number and the position in the file
        """
        # Discussion about file buffer size
        # http://seann.herdejurgen.com/resume/samag.com/html/v11/i04/a6.htm
        # http://stackoverflow.com/questions/14863224/efficient-reading-of-800-gb-xml-file-in-python-2-7
        # open('foo.xml', buffering=(2<<16) + 8)
        # TODO: auto expand compressed files (.gz)
        # TODO: use buffering
        # NOTE that the position returned by f.tell may be inaccurate because the use of buffering (in the system)
        f = open(fname)
        pre = f.tell()
        for line, i in enumerate(f):
            # should be returning the position before (pre) or after (f.tell()) the line?
            yield line, i, f.tell()
            pre = f.tell()

    ########### Main methods #########

    def __init__(self):
        ProbeInput.__init__(self)
        self.data_dir = None
        self.data_file = None

    def get_init_params(self):
        """Return list of parameters to read form the config file"""
        return ['InputDataDirectory', 'InputDataFile']

    def start(self, static_info):
        """start: initialize variables"""
        self.add_static_info(static_info)
        if static_info['InputDataDirectory']:
            self.data_dir = static_info['InputDataDirectory']
        if static_info['InputDataFile']:
            self.data_file = static_info['InputDataFile']

    def add_checkpoint(self, fname=None, max_val=None, default_val=None, fullname=False):
        """Add a checkpoint, default file name is cfp-INPUT_NAME

        :param fname: checkpoint file name (considered as prefix unless fullname=True)
                file name is fname-INPUT_NAME
        :param max_val: trim value for the checkpoint
        :param default_val: value if no checkpoint is available
        :param fullname: Default: False, if true, fname is considered the full file name
        :return:
        """

        if not fname:
            fname = "cpf-%s" % self.get_name()
        else:
            if not fullname:
                fname = "%s-%s" % (fname, self.get_name())
        if max_val is not None or default_val is not None:
            self.checkpoint = checkpoint.DateTransactionCheckpoint(fname, max_val, default_val)
        else:
            self.checkpoint = checkpoint.DateTransactionCheckpoint(fname)

    def get_records(self, limit=None):
        """Return lines as records
        """
        if self.data_file:
            for line in self.iter_file(self.data_file):
                yield line
        if self.data_dir:
            for fname in self.iter_tree(self.data_dir):
                for line in self.iter_file(fname):
                    yield line

    def get_named_records(self, limit=None):
        """Return a generator yielding id, record tuples with
        files content (whole file) as records and file name as ids

        :param limit: return only the first limit records
        :return:
        """
        if self.data_file:
            f = open(self.data_file)
            # should readall() be used instead?
            retv = f.readlines()
            yield self.data_file, retv
        if self.data_dir:
            for fname in self.iter_tree(self.data_dir):
                f = open(fname)
                # should readall() be used instead?
                retv = f.readlines()
                yield fname, retv

    def finalize_record(self, record_id):
        """Delete the file containing the record (the file name is passed as record_id)

        :param record_id: file name of the record
        :return: True if the record is found and the action performed
        """
        if os.path.isfile(record_id):
            file_utils.RemoveFile(record_id)
            return True
        return False


class TextFileInput(FileInput):
    """
    Text input file
    """

    ########### Auxiliary Functions #######

    ########### Main methods ##############

    def __init__(self):
        FileInput.__init__(self)

    #def get_init_params(self):
    #    """Return list of parameters to read form the config file"""
    #    retv = FileInput.get_init_params()
    #    # add some
    #    return retv

    def get_records(self, limit=None):
        """Return lines as records
        """
        if self.data_file:
            for line in self.iter_file(self.data_file):
                yield line
        if self.data_dir:
            for fname in self.iter_tree(self.data_dir):
                for line in self.iter_file(fname):
                    yield line


################################################################
# TODO: remove in future releases
# make sure that is not used anymore
class OldFileInput(ProbeInput):
    """File input. Allows for both single file processing and directory processing
    """
    
    # These prametrized command strings take:
    # data: data dircetory or log file
    # start: start time
    # end: end time
    RECOVERY_COMMAND = "rec %(data)s"
    TIMED_RECOVERY_COMMAND = "rec %(data)s %(start)s %(end)s" 

    # Regular expression to recognize log files within a directory
    # examples:
    # condor_history_re = re.compile("^history.(\d+)\.(\d+)")
    # logfile_re = re.compile("^history\.(?:.*?\#)?\d+\.\d+")
    #
    LOGFILE_RE = re.compile("^datafile\.(?:.*?\#)?\d+\.log")

    def __init__(self):
        ProbeInput.__init__(self)
        self.data_dir = None

    def get_init_params(self):
        """Return list of parameters to read form the config file"""
        return ['InputDataDirectory', 'InputDataFile']

    def start(self, static_info):
        """start: connect to the database"""
        self._static_info = static_info
        if static_info['InputDataDirectory']:
            self.data_dir = static_info['InputDataDirectory']

    def logfiles_to_process(self, args):
        """List all the log files. args is a list of file names or directory names
        """
        for arg in args:
            if os.path.isfile(arg) and os.stat(arg).st_size:
                DebugPrint(5, "Processing logfile %s" % arg)
                yield arg
            elif os.path.isdir(arg):
                DebugPrint(5, "Processing directory %s." % arg)
                for logfile in os.listdir(arg):
                    m = self.LOGFILE_RE.match(logfile)
                    if m:
                        DebugPrint(5, "Processing logfile %s" % logfile)
                        yield os.path.join(arg, logfile)

    def process_data_dirs(self, dirs=None):
        submit_count = 0
        found_count = 0
        logs_found = 0
        logfile_errors = 0
        # Note we are not ordering logfiles by type, as we don't want to
        # pull them all into memory at once.
        DebugPrint(4, "We will process the following directories: %s." % ", ".join(dirs))
        for log in self.logfiles_to_process(dirs):
            logs_found += 1
            _, logfile_name = os.path.split(log)
            # This should actually not be needed (done in the itarator)
            # Make sure the filename is in a reasonable format
            m = self.LOGFILE_RE.match(logfile_name)
            if not m:
                DebugPrint(2, "Ignoring log file with invalid name: %s" % log)
                continue
            cnt_submit, cnt_found = self.process_data_file(log)
            if cnt_submit == cnt_found and cnt_submit > 0:
                DebugPrint(5, "Processed %i records from file %s" % (cnt_submit, log))
            else:
                DebugPrint(2, "Unable to process records from file (will add to quarantine): %s.  Submit count %d; found count %d" % (log, cnt_submit, cnt_found))
                GratiaCore.QuarantineFile(log, False)
                logfile_errors += 1
            submit_count += cnt_submit
            found_count += cnt_found

        DebugPrint(2, "Number of logfiles processed: %d" % logs_found)
        DebugPrint(2, "Number of logfiles with errors: %d" % logfile_errors)
        DebugPrint(2, "Number of usage records submitted: %d" % submit_count)
        DebugPrint(2, "Number of usage records found: %d" % found_count)

    def process_data_file(self, logfile):
        # Open the file and send it to process
        try:
            fd = open(logfile, 'r')
        except IOError, ie:
            DebugPrint(2, "Cannot process %s: (errno=%d) %s" % (logfile, ie.errno,
                ie.strerror))
            return 0, 0

        return self.process_data_fd(fd, logfile)

    def do_process_recovery(self, start_time = None, end_time = None):
        """ Recovery procedure
        the recovery command will output the records that are 
        processed and sent to Gratia by process_recovery_fd
        """
        rec_command = None
        if start_time is not None and end_time is not None:
            rec_command = self.RECOVERY_COMMAND % {'data':"", 'start':start_time, 'end':end_time}
        else:
            rec_command = self.RECOVERY_COMMAND % {'data':""}
        DebugPrint(-1, "RUNNING: %s" % rec_command)
        fd = os.popen(rec_command)
        submit_count, found_count = self.process_data_fd(fd)
        if fd.close():
            DebugPrint(-1, "Recovery mode ERROR: Call to rec " \
                           "failed: %s" % rec_command)

        DebugPrint(-1, "Recovery mode: Records submitted: " \
                       "%d" % submit_count)
        DebugPrint(-1, "Recovery mode: Records found: " \
                       "%d" % found_count)

    def process_data_fd(self, fd, filename=None):
        """
        Process records from a file descriptor.  
        If filename is None there are no transient files (e.g. recovery mode)
        Otherwise filename is a transient file Gratia will attempt to cleanup 
        afterward.
        Transient files are associated with the first record in the file. This 
        works well only if transient files habe only one record, otherwise they 
        will be deleted if the first record is processed successfully (or 
        deemed uninteresting), quarantined if the first record fails to process.
        """
        count_submit = 0
        count_found  = 0
        if filename:
            added_transient = False
        else:
            added_transient = True        

        for record in lines_to_record(fd):
            count_found += 1
            if not record:
                DebugPrint(5, "Ignoring empty record from file: %s" % fd.name)
                continue
            if not added_transient:
                record['gratia_logfile'] = filename
                added_transient = True
            try:
                yield record
            except KeyboardInterrupt:
                raise
            except SystemExit:
                raise
            except IgnoreRecordException, e:
                DebugPrint(3, "Ignoring Record: %s" % str(e))
                count_submit += 1
                continue
            except Exception, e:
                DebugPrint(2, "Exception while processing the record: %s" % str(e))
                continue

            # In the probe you can add some additional filtering (conditions to exclude records)
            #TODO: ignore count_submit? assume that all records are submitted OK?
            # there may be filtering or transmission errors    
            count_submit += 1

        return
        #return count_submit, count_found

    def process_record(self, record):
        #TODO: yield the value for processing to gratia ()
        # logfile attribute (if present) is used to keep track and delete files

        DebugPrint(5, "Creating JUR for %s" % record)

        # Filter out uninteresting records (and remove their files)
        if False:
            if 'gratia_logfile' in record:
                DebugPrint(1, 'Deleting transient record file: '+record["gratia_logfile"])
                file_utils.RemoveFile(record['gratia_logfile'])
            raise IgnoreRecordException("Ignoring record.")

        # Define the record
        # UsageRecord is defined in https://twiki.opensciencegrid.org/bin/view/Accounting/ProbeDevelopement
        # setters have the name of the attribute 
        # Set resource type ( Batch, BatchPilot, GridMonitor, Storage, ActiveTape )
        resource_type = "Batch"
        r = Gratia.UsageRecord(resource_type)

        # fill r using the values in record

        # remember to specify the transient file (that will be removed if the record 
        # is acquired successfully)
        if 'logfile' in record:
            r.AddTransientInputFile(record['gratia_logfile'])

        return r

# TODO: end of part to remove
#############################################################


# Some references
# http://seann.herdejurgen.com/resume/samag.com/html/v11/i04/a6.htm
# http://stackoverflow.com/questions/14863224/efficient-reading-of-800-gb-xml-file-in-python-2-7
# http://radimrehurek.com/2014/03/data-streaming-in-python-generators-iterators-iterables/