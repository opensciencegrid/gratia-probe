#!/usr/bin/python
#
# sample_probe - Python-based sample probe for Gratia
#       By Marco Mambelli; Jun 9, 2014
#

import os
import re
import sys
import time
import random
import os.path
import optparse
import subprocess

from gratia.common.Gratia import DebugPrint
import gratia.common.GratiaCore as GratiaCore
import gratia.common.GratiaWrapper as GratiaWrapper
import gratia.common.Gratia as Gratia

# package inputs are ahead

prog_version = "%%%RPMVERSION%%%"
prog_revision = '$Revision: 5268 $'

# --- constants -----------------------------------------------------------------------
PROBE_NAME="sample"
DEFAULT_CONFIG="/etc/gratia/%s/ProbeConfig" % PROBE_NAME
min_start_time = time.time() - 120*86400



# -- exceptions ---------
class SampleException(Exception):
    pass



# --- functions -----------------------------------------------------------------------


val_bool_re = re.compile("^(\w{1,255}) = (true|True|TRUE|false|False|FALSE)$")
val_int_re = re.compile("^(\w{1,255}) = (-?\d{1,30})$")
val_double_re = re.compile("^(\w{1,255}) = ([+-]? *(?:\d{1,30}\.?\d{0,30}|\.\d{1,30})(?:[Ee][+-]?\d{1,30})?)$")
val_string_re = re.compile("^(\S+) = \"(.*)\"$")
val_catchall_re = re.compile("^(\S+) = (.*)$")
def fd_to_record(fd):
    """Parse a stream of data into a record (data structure)
    Here regular expressions are used to match values for a dictionary
    The input steram is a series of "name = value" lines with
    empty lines or the end of a stream separating records
    '#' at the beginning of the line is used to add comments (skipped)
    """
    # dictionary, caseless_dictionary, sorted dictionary, array
    # are all possible structures, be consistent with what you use in process_record
    record = {}
    for line in fd.readlines():
        line = line.strip()
        m = var_bool_re.match(line)
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
            yield add_unique_id(record)
            record = {}
            continue
        if line[0]=='#':
            continue
        DebugPrint(2, "Invalid line in record stream: %s" % line)

    yield add_unique_id(record)

def add_unique_id(record):
    # Using IDs unique in the space of the records measured by the probe
    # e.g. GlobalJobId for HTCondor
    if 'GlobalId' in record:
        record['UniqGlobalId'] = '%s.%s' % (PROBE_NAME, record['GlobalId'])
        DebugPrint(6, "Unique ID: %s" % record['UniqGlobalId'])
    return record

def parse_opts():
    # TODO: option parsing for the test
    pass

def main():
    try:
        opts, dirs = parse_opts()
    except SystemExit:
        raise
    except KeyboardInterrupt:
        raise
    except Exception, e:
        print >> sys.stderr, str(e)
        sys.exit(1)

    # Sanity checks for the probe's runtime environment.
    GratiaWrapper.CheckPreconditions()

      
    if opts.sleep:
        rnd = random.randint(1, int(opts.sleep))
        DebugPrint(2, "Sleeping for %d seconds before proceeding." % rnd)
        time.sleep(rnd)

    # Make sure we have an exclusive lock for this probe.
    GratiaWrapper.ExclusiveLock()

    register_gratia()
    GratiaCore.Initialize(opts.gratia_config)

    # Do all setup and checks (environment systems the probe interacts with)
    setup_environment()
        
    # Check to make sure HTCondor config is set correctly
    if not system_configured():
        DebugPrint(-1, "ERROR: The system is not configured correctly, exiting")
        sys.exit(1)

    # Do some sanity checks of gratia configuration before starting    
    if not check_gratia():
        DebugPrint(-1, "ERROR: Gratia settings not correct, exiting")
        sys.exit(1)
    
    if opts.recovery_mode is True:
        process_recovery(opts.recovery_start_time, opts.recovery_end_time)
    else:
        process_data_dirs(dirs)


# --- classes -------------------------------------------------------------------------
# TODO: evaluate the possibility of a separate iterator class
# Distinguish CommandInput (no checkpoint/ w/ checkpoint), FileInput (MultiFileInput?)
# use of fileinput?

from probeinput import ProbeInput, IgnoreRecordException

class CommandInput(ProbeInput):   
    def __init__(self):
        ProbeInput.__init__(self)
        pass


class FileInput(ProbeInput):   
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
        return ['DataDir', 'DataFile' ]

    def start(self, static_info):
        """start: connect to the database"""
        self._static_info = static_info
        if static_info['DataDir']:
            self.data_dir = static_info['DataDir']

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

        for record in fd_to_record(fd):
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
                Gratia.RemoveFile(record['gratia_logfile'])
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

val_bool_re = re.compile("^(\w{1,255}) = (true|True|TRUE|false|False|FALSE)$")
val_int_re = re.compile("^(\w{1,255}) = (-?\d{1,30})$")
val_double_re = re.compile("^(\w{1,255}) = ([+-]? *(?:\d{1,30}\.?\d{0,30}|\.\d{1,30})(?:[Ee][+-]?\d{1,30})?)$")
val_string_re = re.compile("^(\S+) = \"(.*)\"$")
val_catchall_re = re.compile("^(\S+) = (.*)$")
def fd_to_record(fd):
    """Parse a stream of data into a record (data structure)
    Here regular expressions are used to match values for a dictionary
    The input steram is a series of "name = value" lines with
    empty lines or the end of a stream separating records
    '#' at the beginning of the line is used to add comments (skipped)
    """
    # dictionary, caseless_dictionary, sorted dictionary, array
    # are all possible structures, be consistent with what you use in process_record
    record = {}
    for line in fd.readlines():
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
            yield add_unique_id(record)
            record = {}
            continue
        if line[0]=='#':
            continue
        DebugPrint(2, "Invalid line in record stream: %s" % line)

    yield add_unique_id(record)

def add_unique_id(record):
    # Using IDs unique in the space of the records measured by the probe
    # e.g. GlobalJobId for HTCondor
    if 'GlobalId' in record:
        record['UniqGlobalId'] = '%s.%s' % (PROBE_NAME, record['GlobalId'])
        DebugPrint(6, "Unique ID: %s" % record['UniqGlobalId'])
    return record

