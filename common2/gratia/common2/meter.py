
#!/usr/bin/python

###########################################################################
# Base classes for Gratia probes
#
###########################################################################

# Standard libraries
import sys
import os
import stat
import time
import random
import pwd, grp
import socket   # to get hostname
import optparse
#import re  # rpm parsing
import signal  # is in the system library
from alarm import Alarm

# Python profiler
import hotshot
import hotshot.stats

# Gratia libraries
import gratia.common.Gratia as Gratia
#import gratia.services.ComputeElement as ComputeElement
#import gratia.services.ComputeElementRecord as ComputeElementRecord

# TODO: change once common.Gratia is modified
from gratia.common.debug import DebugPrint, LogFileName
#from gratia.common.Gratia import DebugPrint, LogFileName
import gratia.common.GratiaWrapper as GratiaWrapper

# in same package gratia.common2
import timeutil
from probeinput import ProbeInput

prog_version = "%%%RPMVERSION%%%"
prog_revision = '$Revision$'


# This should be added as improvement of Gratia logging in gratia.common.debug
def DebugPrintLevel(level, *args):
    if level <= 0:
        level_str = "CRITICAL"
    elif level >= 4:
        level_str = "DEBUG"
    else:
        level_str = ["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"][level]
    level_str = "%s - EnstoreStorage: " % level_str
    DebugPrint(level, level_str, *args)


def warn_of_signal_generator(alarm):
    """Callback function for signal handling
    alarm is curried by the method setting the handler
    """
    def f(signum, frame):
        DebugPrint(2, "Going down on signal " + str(signum))
        if alarm is not None:
            alarm.event()
        os._exit(1)
    return f


class GratiaProbe(object):
    """GratiaProbe base class
    """
    # TODO: consider merging with GratiaMeter
    # TODO: consider using multiprocess.Pool to speed up
    # Constants (defined to avoid different spellings/cases)
    UNKNOWN = "unknown"

    _opts = None
    _args = None
    #checkpoint = None
    _conn = None
    cluster = None
    # probe name, e.g. slurm_meter
    #TODO: get it form config?
    probe_name = "gratia_probe"
    _probeinput = None
    _default_config = UNKNOWN
    _version = None
    _alarm = None

    #### Initialization and setup

    def __init__(self, probe_name=None):
        if probe_name:
            self.probe_name = probe_name

        self._default_config = "/etc/gratia/%s/ProbeConfig" % self.probe_name

        # Option parsing must be after defaults
        try:
            self._opts, self._args = self.parse_opts()
        except Exception, e:
            DebugPrint(1, "Error parsing the command line: %s" % e)
            # print >> sys.stderr, str(e)
            sys.exit(1)

        # Set to verbose from the beginning (if requested)
        # will work only if Gratia.Config has been initialised
        self.set_verbose()

        DebugPrint(4, "Command line parsed.\nOptions: %s\nArguments: %s" % (self._opts, self._args))
        # Place to handle special options (help, ...)

    def set_verbose(self):
        if self._opts.verbose:
            # TODO: change also LogLevel?
            # set/get_LogLevel
            try:
                # Config used by Gratia.Config can be None (instance)
                current = Gratia.Config.get_DebugLevel()
                if current < 5:
                    Gratia.Config.set_DebugLevel(5)
            except AttributeError:
                return

    def start(self):
        """Initializes Gratia (to read the option file), does random sleep (if any), acquires the lock,
        initializes the input and registers Gratia.
        Must be invoked after options and parameters are parsed (option file name is needed)
        """

        ### Initialize Gratia
        if not self._opts or not self._opts.gratia_config or not os.path.exists(self._opts.gratia_config):
            # TODO: print a message instead of an exception?
            raise Exception("Gratia config file (%s) does not exist." %
                            self._opts.gratia_config)
        # Print options and initial conditions
        DebugPrint(5, "Initial options: %s" % self._opts)

        # Initialization parses the config file. No debug print will work before this
        Gratia.Initialize(self._opts.gratia_config)

        # Set to verbose in case the config changed it
        self.set_verbose()

        # Sanity checks for the probe's runtime environment.
        if self._opts.enable:
            GratiaWrapper.CheckPreconditions(check_enabled=False)
        else:
            GratiaWrapper.CheckPreconditions()

        if self._opts.sleep:
            rnd = random.randint(1, int(self._opts.sleep))
            DebugPrint(2, "Sleeping for %d seconds before proceeding." % rnd)
            time.sleep(rnd)

        # Make sure we have an exclusive lock for this probe.
        GratiaWrapper.ExclusiveLock()

        ### Initialize input (config file must be available)
        # Input must specify which parameters it requires form the config file
        # The probe provides static information form the config file
        if not self._probeinput:
            self._probeinput = ProbeInput()
        input_parameters = self._probeinput.get_init_params()
        input_ini = self.get_config_att_list(input_parameters)
        # Check for test mode: start and other methods may change
        if 'input' in self._opts.test:
            DebugPrint(3, "Running input in test mode")
            self._probeinput.do_test()
        # Finish input initialization, including DB connection (if used)
        self._probeinput.start(input_ini)

        # get_DataFileExpiration() returns the value in the config file or 31
        # TODO: Do we want to always not consider values older than 31 days or only when checkpointing is
        # enabled?
        # data_expiration = Gratia.Config.get_DataFileExpiration()

        # Find the checkpoint filename (if enabled) - after initializing the input!
        if self._opts.checkpoint:
            checkpoint_file = self.get_config_attribute('CheckpointFile')
            full_checkpoint_name = True
            if not checkpoint_file:
                full_checkpoint_name = False
                checkpoint_file = os.path.join(Gratia.Config.get_WorkingFolder(), "checkpoint")
            data_expiration = Gratia.Config.get_DataFileExpiration()
            # Only process DataFileExpiration days of history
            # (unless we're resuming from a checkpoint file)
            # TODO: is datafileexpiration a maximum value or a default (if no checkpoint is specified)?
            #       Do we want both?
            # Open the checkpoint file
            self._probeinput.add_checkpoint(checkpoint_file, default_val=data_expiration, fullname=full_checkpoint_name)

        ### Complete Gratia initialization
        # This uses the input version (after Input initialization)
        self.register_gratia()

        ###
        # Set other attributes form config file
        #self.cluster = Gratia.Config.getConfigAttribute('SlurmCluster')

    ####
    #### Alarm to notify user and signal handling

    def set_alarm(self):
        """Set up an alarm to send an email if the program terminates."""
        subject = "%s probe is going down unexpectedly" % self.probe_name
        message = "The Gratia probe %s has terminated unexpectedly.\nPlease check the logfile\n   %s\n" \
                  "for the cause.\n" % (self.probe_name, LogFileName())

        self._alarm = Alarm(Gratia.Config.get_EmailServerHost(),
                            Gratia.Config.get_EmailFromAddress(),
                            Gratia.Config.get_EmailToList(),
                            subject, message, 0, 0, False)

    def add_signal_handlers(self):
        # Ignore hangup signals. We shouldn't die just because our parent
        # shell logs out.
        signal.signal(signal.SIGHUP, signal.SIG_IGN)
        # Try to catch common signals and send email before we die
        warn_of_signal = warn_of_signal_generator(self._alarm)
        signal.signal(signal.SIGINT,  warn_of_signal)
        signal.signal(signal.SIGQUIT, warn_of_signal)
        signal.signal(signal.SIGTERM, warn_of_signal)

    ####
    #### Convenience functions

    @staticmethod
    def parse_config_boolean(value):
        """Evaluates to True if lowercase value matches "true", False otherwise

        :param value: input string
        :return: True/False
        """
        try:
            if value.tolower() == "true":
                return True
        except:
            pass
        return False

    def get_config_attribute(self, attr, default=None, mandatory=False):
        """Return the value of the requested parameter.

        Note that parameters are strings: use "True"/"False" and self.parse_config_boolean for booleans

        :param attr: name of the parameter
        :param default: if not None, default used if the value evaluates to False (None, empty string, ...)
        :param mandatory: if mandatory is True ValueError is risen if the attribute is not in the configuration
            (evaluates to false)
        :return: the value of the parameter or None (if not available)
        """
        retv = Gratia.Config.getConfigAttribute(attr)
        # using Element.getAttribute from xml.dom underneath
        # getConfigAttribute returns the value of the attribute named by name as a string.
        # If no such attribute exists, an empty string is returned, as if the attribute had no value
        # TODO: disambiguate between False values and NULL values (set to None)
        if not retv and default is not None:
            retv = default
        if mandatory and not retv:
                raise ValueError("Attribute '%s' not found in config file %s" % (attr, self._opts.gratia_config))
        return retv

    def get_config_att_list(self, param_list, mandatory=False):
        """Return a dictionary containing the values of a list of parameters

        :param param_list: list of parameter names
        :param mandatory: if mandatory is True ValueError is risen if an attribute is not in the configuration
            (evaluates to false)
        :return: dictionary with all attributes: value is None if they are not in the configuration
        """
        #TODO: would an array be much more efficient?
        #TODO: check what happens if the parameter is not in the config file. Ideally None is returned
        retv = {}
        for param in param_list:
            retv[param] = Gratia.Config.getConfigAttribute(param)
            if mandatory and not retv[param]:
                raise ValueError("Attribute '%s' not found in config file %s" % (param, self._opts.gratia_config))
        return retv

    def get_hostname(self):
        """Look for the host name in the configuration file first and second use fqdn
        """
        retv = self.get_config_attribute("HostName")
        if not retv:
            retv = socket.getfqdn()
        return retv

    def get_sitename(self):
        return self.get_config_attribute("SiteName", mandatory=True)

    def get_probename(self):
        return self.get_config_attribute("ProbeName", mandatory=True)

    def get_input_max_length(self):
        """Return the max number of input records. 0 (or anything different form a positive integer) for no limit.

        Uses the DataLengthMax attribute in the configuration.
        E.g. this is used for the LIMIT clause in inputs with SQL queries.

        :return: the value of DataLengthMax, None if it is missing or not a positive integer
        """
        try:
            limit = int(self.get_config_attribute('DataLengthMax'))
            if limit == 0:
                limit = None
        except:
            limit = None
        return limit

    def get_opts(self, option=None):
        """Return the command line option
        """
        if not option:
            return self._opts
        try:
            return self._opts[option]
        except (TypeError, KeyError):
            DebugPrint(5, "No option %s, returning None" % option)
        return None

    def parse_opts(self, options=None):
        """Hook to parse command-line options"""
        return

    ## User functions (also in probeinput)
    @staticmethod
    def _get_user(uid, err=None):
        """Convenience functions to resolve uid to user"""
        try:
            return pwd.getpwuid(uid)[0]
        except (KeyError, TypeError):
            return err

    @staticmethod
    def _get_group(gid, err=None):
        """Convenience function to resolve gid to group"""
        try:
            return grp.getgrgid(gid)[0]
        except (KeyError, TypeError):
            return err

    def _addUserInfoIfMissing(self, r):
        """Add user/acct if missing (resolving uid/gid)"""
        if r['user'] is None:
            # Set user to info from NSS, or unknown
            r['user'] = self._get_user(r['id_user'], GratiaProbe.UNKNOWN)
        if r['acct'] is None:
            # Set acct to info from NSS, or unknown
            r['acct'] = self._get_group(r['id_group'], GratiaProbe.UNKNOWN)

    @staticmethod
    def _isWrite2isNew(is_write):
        """Return the correct isNew value 1/write(True) 0/read(False)"""
        # https://github.com/dCache/dcap/blob/master/src/dcap_open.c
        if is_write:
            return 1
        return 0

    def _normalize_hostname(self, inname):
        """Add DefaultDomainName domain name if missing (i.e. no dots in the name)"""
        if not '.' in inname:
            domainname = self.get_config_attribute("DefaultDomainName")
            if domainname:
                return "%s.%s" % (inname, domainname)
        return inname

    @staticmethod
    def get_password(pwfile):
        """Read a password from a given file, checking permissions"""
        fp = open(pwfile)
        mode = os.fstat(fp.fileno()).st_mode

        if (stat.S_IMODE(mode) & (stat.S_IRGRP | stat.S_IROTH)) != 0:
            raise IOError("Password file %s is readable by group or others" % pwfile)

        return fp.readline().rstrip('\n')

    @staticmethod
    def run_command(cmd, cmd_filter=None, timeout=None, get_stderr=False):
        # TODO: better, more robust and with timeout
        # timeout ignored for now
        DebugPrint(5, "Invoking: %s" % cmd)
        if get_stderr:
            cmd = "%s 2>&1" % cmd
        fd = os.popen(cmd)
        res = fd.read()
        if fd.close():
            DebugPrint(4, "Unable to invoke '%s'" % cmd)
            #raise Exception("Unable to invoke command")
        else:
            if cmd_filter:
                res = cmd_filter(res.strip())
            if not res:
                DebugPrint(4, "Unable to parse the command output (filter %s): %s" % (cmd_filter, cmd))
            return res

    def get_probe_version(self):
        #derived probes must override
        # derived probes may need self
        # using global prog_version . Is it there a better way to get probe version form file?
        return "%s" % prog_version

    def get_version(self):
        """Return the version of the input used by the probe (UNKNOWN if there is no input)
        """
        if self._probeinput:
            try:
                input_version = self._probeinput.get_version()
            except Exception, e:
                DebugPrint(1, "Unable to get input version: %s" % str(e))
                raise
            return input_version
        return GratiaProbe.UNKNOWN
        # TODO: should instead raise an exception?
        # DebugPrint(0, "Unable to get input version: no input defined.")
        # raise Exception("No input defiled")

    def get_description(self):
        """Describe the probe: name, cinfiguration
        """
        rets = "Probe: %s (v. %s)\n" % (self.get_probename(), self.get_probe_version())
        rets += "Host: %s (def. domain %s)\n" % (self.get_hostname(), self._normalize_hostname("HOST"))
        rets += "Site: %s\n" % self.get_sitename()
        rets += "Config file: %s\n" % self._default_config
        rets += "Log file directory (: %s\n" % self.get_config_attribute('LogFolder')
        rets += "Lock file: %s\n" % self.get_config_attribute('Lockfile')
        rets += "Working directory: %s\n" % self.get_config_attribute('WorkingFolder')
        rets += "Data directory: %s\n" % self.get_config_attribute('DataFolder')
        rets += "Input %s (v. %s)\n" % (self._probeinput, self.get_version())
        return rets

    def register_gratia(self):
        """Register in Gratia the Reporter (gratia probe), ReporterLibrary (Gratia library version)
        and the Service (input)

        :return:
        """
        Gratia.RegisterReporter(self.probe_name, "%s (tag %s)" % (prog_revision, prog_version))

        try:
            input_version = self.get_version()
        except SystemExit:
            raise
        except KeyboardInterrupt:
            raise
        except Exception, e:
            DebugPrint(0, "Unable to get input version: %s" % str(e))
            raise

        # TODO: check the meaning of RegisterReporter vs RegisterService
        Gratia.RegisterService(self._probeinput.get_name(), input_version)

        # TODO: check which attributes need to be set here (and not init)
        # and which attributes are mandatory vs optional
        #Gratia.setProbeBatchManager("slurm")
        #GratiaCore.setProbeBatchManager("condor")


class GratiaMeter(GratiaProbe):

    def __init__(self, probe_name=None):
        # calls also command line option parsing
        GratiaProbe.__init__(self, probe_name)

        # Filter and adjust command line options
        if self._opts and self._opts.test:
            self._opts.test = self._check_test_values(self._opts.test)
        #TODO: check here start and end time?

        # Enable profiling
        if self._opts.profile:
            self._main = self.main
            self.main = self.do_profile

    def get_opts_parser(self):
        """Return an options parser. It must invoke the parent option parser.

        All children will have the same structure to add options to the parent options parser.
        If extending this function remember to:
        1. invoke the parent with super() at the beginning and assign it to parser
        2. return the parser at the end of get_opts_parser.
        If you miss one of these two the probe will fail and there will probably be no output helping in troubleshooting
        """
        # this is not needed but for clarity
        parser = None
        try:
            # child classes will use the parent parser instead:
            # For GratiaMeter this will trigger an AttributeError because it is not defined in the parent
            # Children should have their class name here
            parser = super(GratiaMeter, self).get_opts_parser()
        except AttributeError:
            # base class initializes the parser
            parser = optparse.OptionParser(usage="""%prog [options] [input1 [input2]]
Example cron usage: %prog --sleep SECONDS
Command line usage: %prog
                    %prog --recovery --start-time=STARTTIME --end-time=ENDTIME""")

        # add (other) options
        parser.add_option("-f", "--gratia_config", 
            help="Location of the Gratia config [default: %default].",
            dest="gratia_config", default=self._default_config)
        parser.add_option("-s", "--sleep", help="Do a random amount of sleep, "
            "up to the specified number of seconds before running."
            "For use in cron invocation, to reduce Collector load from concurrent requests",
            dest="sleep", default=0, type="int")
        parser.add_option("--test", help="Comma separated list of probe components to test using stubs, "
            "e.g. input, output, all (=input,output).",
            dest="test", default="")
        parser.add_option("--profile", help="Enable probe profiling ",
            dest="profile", default=False, action="store_true")
        parser.add_option("-v", "--verbose",
            help="Enable verbose logging to stderr.",
            dest="verbose", default=False, action="store_true")
        parser.add_option("-c", "--checkpoint", help="Only reports records past"
            " checkpoint; default is to report all records.",
            dest="checkpoint", default=False, action="store_true")
        parser.add_option("-e", "--enable", help="Force the probe to be enabled ignoring"
            " the setting in the config file; default is False, follow the config file setting.",
            dest="enable", default=False, action="store_true")
        parser.add_option("-r", "--recovery", 
            help="Recovers the records from come history or log file (e.g. condor_history, "
                 "accounting, ...), ignoring the live records. "
                 "This works also because Gratia recognizes and ignores duplicate records. "
                 "This option should be used with the --start-time and --end-time options "
                 "to reduce the load on the Gratia collector.  It will look through all the "
                 "historic records (or the ones in the selected time interval) and attempt to "
                 "send them to Gratia.",
            dest="recovery_mode", default=False, action="store_true")
        parser.add_option("--start-time", 
            help="First time to include when processing records using --recovery "
                 "option. Time should be formated as YYYY-MM-DD HH:MM:SS where HH:MM:SS "
                 "is assumed to be 00:00:00 if omitted.",
            dest="recovery_start_time", default=None)
        parser.add_option("--end-time",
                          help="Last time to include when processing records using --recovery "
                               "option. Time should be formated as YYYY-MM-DD HH:MM:SS where HH:MM:SS "
                               "is assumed to be 00:00:00 if omitted",
                          dest="recovery_end_time", default=None)

        return parser

    def _check_test_values(self, test_string):
        """Filter the test command line parameter
        """
        if test_string.strip() == 'all':
            return ['input', 'output']
        test_list = [i.strip() for i in test_string.split(',')]
        return test_list

    def _check_start_end_times(self, start_time=None, end_time=None, assume_local=False):
        """Parse and verify the validity of the time interval parameters.

        Both or none of the times have to be present. Start time has to be in the past,
        end time is after start time
        Time strings have to be in ISO8601 or other format compatible w/ timeutil.parse_datetime

        :param start_time: Start time
        :param end_time: End time
        :param assume_local: if False (default) naive time values are assumed UTC, if True they are assumed local
        :return: start and end time in second from the Epoch (UTC)
        """
        if start_time is not None or end_time is not None:
            # using a start and end date
            DebugPrint(-1, "Data Recovery "
                       "from %s to %s" % (start_time, end_time))
            if start_time is None or end_time is None:
                DebugPrint(-1, "Recovery mode ERROR: Either None or Both "
                           "--start and --end args are required")
                sys.exit(1)
            try:
                start_time = timeutil.parse_datetime(start_time, return_seconds=True, assume_local=assume_local)
            except ValueError:
                DebugPrint(-1, "Recovery mode ERROR: Can't parse start time")
                sys.exit(1)
            try:
                end_time = timeutil.parse_datetime(end_time, return_seconds=True, assume_local=assume_local)
            except:
                DebugPrint(-1, "Recovery mode ERROR: Can't parse end time")
                sys.exit(1)
            if start_time > end_time:
                DebugPrint(-1, "Recovery mode ERROR: The end time is after the start time")
                sys.exit(1)
            if start_time > time.time():
                DebugPrint(-1, "Recovery mode ERROR: The start time is in the future")
                sys.exit(1)
        else:  # using condor history for all dates
            DebugPrint(-1, "RUNNING the probe MANUALLY in recovery mode ")

        return start_time, end_time

    def parse_opts(self, options=None):
        parser = self.get_opts_parser()
        # Options are stored into opts/args class variables
        # parser.print_help() if needs to invoke the help printout
        # by default it is invoked only if --help is the first and only option
        # TODO: Trigger error for unsupported options?
        return parser.parse_args()

    def do_profile(self):
        """Wrap the main method in profiler execution
        """
        # Interesting use: http://code.activestate.com/recipes/576656-quick-python-profiling-with-hotshot/
        # http://blog.brianbeck.com/post/22199891/the-state-of-python-profilers-in-two-words
        # http://nose.readthedocs.org/en/latest/plugins/prof.html
        # pass name, use in profiler file name, return profiling function
        # TODO: provide a standard probe profiling

        fname = "gratiaprobe_%s.prof" % self.probe_name
        profiler = hotshot.Profile(fname)
        DebugPrint(4, "Enabled profiling to %s" % fname)
        retv = profiler.run("self._main()")
        profiler.close()
        stats = hotshot.stats.load(fname)
        stats.sort_stats('time', 'calls')
        stats.print_stats()
        return retv

    def main(self):
        # Loop over completed jobs
        time_end = None
        server_id = self.get_probename()
        DebugPrint(5, "GratiaProbe main - running")
        # TODO: add a loop sending test records
        #for job in self.sacct.completed_jobs(self.checkpoint.val):
        #    r = job_to_jur(job, server_id)
        #    Gratia.Send(r)
        #    # The query sorted the results by time_end, so our last value will
        #    # be the greatest
        #    time_end = job['time_end']
        #    self.checkpoint.val = time_end

        # If we found at least one record, but the time_end has not increased since
        # the previous run, increase the checkpoint by one so we avoid continually
        # reprocessing the last records.
        # (This assumes the probe won't be run more than once per second.)
        if self.checkpoint.val == time_end:
            self.checkpoint.val = time_end + 1

if __name__ == "__main__":
    GratiaMeter().main()
