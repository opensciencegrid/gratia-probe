
#!/usr/bin/python
# /* vim: set expandtab tabstop=4 shiftwidth=4 softtabstop=4: */

###########################################################################
#
#
###########################################################################

# Standard libraries
import sys, os, stat
import time
import random
import pwd, grp
import socket   # to get hostname
import optparse
#import re  # rpm parsing
import signal  # is in the system library
from Alarm import Alarm

# Python profiler
import hotshot
import hotshot.stats

# Gratia libraries
import gratia.common.Gratia as Gratia
#import gratia.services.ComputeElement as ComputeElement
#import gratia.services.ComputeElementRecord as ComputeElementRecord

from gratia.common.Gratia import DebugPrint, LogFileName
import gratia.common.GratiaWrapper as GratiaWrapper

from probeinput import InputCheckpoint, ProbeInput

prog_version = "%%%RPMVERSION%%%"
prog_revision = '$Revision$'


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
    # Constants (defined to avoid different spellings/cases)
    UNKNOWN = "unknown"

    _opts = None
    _args = None
    checkpoint = None
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
            print >> sys.stderr, str(e)
            sys.exit(1)

    def start(self):
        """Initializes Gratia, does random sleep (if any),Must be invoked after options and parameters are parsed
        """

        # Initialize Gratia
        if not self._opts or not self._opts.gratia_config or not os.path.exists(self._opts.gratia_config):
            raise Exception("Gratia config file (%s) does not exist." %
                            self._opts.gratia_config)
        # Initialization parses the config file. No debug print will work before this
        Gratia.Initialize(self._opts.gratia_config)

        if self._opts.verbose:
            Gratia.Config.set_DebugLevel(5)

        # Sanity checks for the probe's runtime environment.
        GratiaWrapper.CheckPreconditions()

        if self._opts.sleep:
            rnd = random.randint(1, int(self._opts.sleep))
            DebugPrint(2, "Sleeping for %d seconds before proceeding." % rnd)
            time.sleep(rnd)

        # Make sure we have an exclusive lock for this probe.
        GratiaWrapper.ExclusiveLock()

        self.register_gratia()

        # Find the checkpoint filename (if enabled)
        if self._opts.checkpoint:
            checkpoint_file = os.path.join(
                Gratia.Config.get_WorkingFolder(), "checkpoint")
        else:
            checkpoint_file = None

        # Open the checkpoint file
        self.checkpoint = InputCheckpoint(checkpoint_file)

        # Only process DataFileExpiration days of history
        # (unless we're resuming from a checkpoint file)
        # TODO: is this a valid generic system?
        if self.checkpoint.val is None:
            self.checkpoint.val = int(time.time() - (Gratia.Config.get_DataFileExpiration() * 86400))

        # Get static information form the config file

        # Initialize input
        # input must specify which parameters it requires form the config file
        if not self._probeinput:
            self._probeinput = ProbeInput()
        input_parameters = self._probeinput.get_init_params()
        input_ini = self.get_config_params(input_parameters)
        #parameters passed in start: self._probeinput.add_static_info(input_ini)
        if 'input' in self._opts.test:
            DebugPrint(3, "Running input in test mode")
            self._probeinput.do_test()
        # Finish input initialization, including DB connection (if used)
        self._probeinput.start(input_ini)

        # Set other attributes form config file
        #self.cluster = Gratia.Config.getConfigAttribute('SlurmCluster')

    #### Alarm to notify user and signal handling

    def set_alarm(self):
        # Set up an alarm to send an email if the program terminates.
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

    #### Convenience functions

    def get_config_attribute(self, param, default=None, mandatory=False):
        """Return the value of the requested parameter
        - default is used if the value evaluates to False (None, empty string, ...)
        - raise exception if mandatory, and the value (or default) evaluates to False
        """
        retv = Gratia.Config.getConfigAttribute(param)
        # using Element.getAttribute from xml.dom underneath
        # getConfigAttribute returns the value of the attribute named by name as a string.
        # If no such attribute exists, an empty string is returned, as if the attribute had no value
        if not retv and default is not None:
            retv = default
        if mandatory and not retv:
                raise Exception("Attribute '%s' not found in config file %s" % (param, self._opts.gratia_config))
        return retv

    def get_config_params(self, param_list, mandatory=False):
        """Return a dictionary containing the values of a list of parameters"""
        #TODO: would an array be much more efficient?
        #TODO: check what happens if the parameter is not in the config file. Ideally None is returned
        retv = {}
        for param in param_list:
            retv[param] = Gratia.Config.getConfigAttribute(param)
            if mandatory and not retv[param]:
                raise Exception("Attribute '%s' not found in config file %s" % (param, self._opts.gratia_config))
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

    def parse_date(self, date_string):
        """
        Parse a date/time string in %Y-%m-%d or %Y-%m-%d %H:%M:%S format
    
        Returns None if string can't be parsed, otherwise returns time formatted
        as the number of seconds since the Epoch
        """    
        #TODO: convert in static function?
        result = None
        try:
            result = time.strptime(date_string, "%Y-%m-%d %H:%M:%S")        
            return int(round(time.mktime(result)))
        except ValueError:
            pass
        except Exception, e:
            return None
    
        try:
            result = time.strptime(date_string, "%Y-%m-%d")
            return int(round(time.mktime(result)))
        except ValueError:
            pass
        except Exception, e:
            return None
    
        return result

    def format_date(self, date_seconds):
        """ Format the date as %Y-%m-%d %H:%M:%S
        """
        result = None
        try:
            result = time.strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            pass
        except Exception, e:
            return None
    
        return result


    ## User functions (also in probeinput)
    def _get_user(self, uid, err=None):
        """Convenience functions to resolve uid to user"""
        try:
            return pwd.getpwuid(uid)[0]
        except (KeyError, TypeError):
            return err

    def _get_group(self, gid, err=None):
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

    def get_password(self, pwfile):
        """Read a password from a given file, checking permissions"""
        fp = open(pwfile)
        mode = os.fstat(fp.fileno()).st_mode

        if (stat.S_IMODE(mode) & (stat.S_IRGRP | stat.S_IROTH)) != 0:
            raise IOError("Password file %s is readable by group or others" %
                pwfile)

        return fp.readline().rstrip('\n')

    def get_probe_version(self):
        #TODO: get probe version form file
        #derived probes must override
        return "%s" % prog_version

    def get_version(self):
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

    def register_gratia(self):
        Gratia.RegisterReporter(self.probe_name, "%s (tag %s)" % \
            (prog_revision, prog_version))

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

        # TODO: check which attributes need to ne set here (and not init)
        # and which attributes are mandatory vs optional
        #Gratia.setProbeBatchManager("slurm")
        #GratiaCore.setProbeBatchManager("condor")


class GratiaMeter(GratiaProbe):

    def __init__(self, probe_name=None):
        # calls also command line option parsing
        GratiaProbe.__init__(self, probe_name)

        # Filter and adjust command line options
        if self._opts and self._opts.test:
            self._opts.test = self.check_test_values(self._opts.test)
        #TODO: check here start and end time?

        # Enable profiling
        if self._opts.profile:
            self._main = self.main
            self.main = self.do_profile

    def get_opts_parser(self):
        """Return an options parser. It must invoke the parent option parser
        """
        # this is not needed but for clarity
        parser = None
        try:
            # child classes will use the parent parser instead:
            parser = super.get_opts_parser()
        except AttributeError:
            # base class initializes the parser
            parser = optparse.OptionParser(usage="""%prog [options] [input1 [input2]]
Example cron usage: $prog --sleep SECONDS
Command line usage: $prog 
                    $prog --recovery --start-time=STARTTIME --end-time-ENDTIME""")

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
            help="Enable verbose logging to stdout.",
            dest="verbose", default=False, action="store_true")
        parser.add_option("-c", "--checkpoint", help="Only reports records past"
            " checkpoint; default is to report all records.",
            dest="checkpoint", default=False, action="store_true")
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

    def check_test_values(self, test_string):
        """Filter the test command line parameter
        """
        if test_string.strip() == 'all':
            return ['input', 'output']
        test_list = [i.strip() for i in test_string.split(',')]
        return test_list

    def check_start_end_times(self, start_time = None, end_time = None):
        """Both or none of the times have to be present. Start time has to be in the past,
        end time is after start time
        """
        if start_time is not None or end_time is not None:
            # using a start and end date
            DebugPrint(-1, "Data Recovery " \
                       "from %s to %s" % (start_time, end_time))
            if start_time is None or end_time is None:
                DebugPrint(-1, "Recovery mode ERROR: Either None or Both " \
                           "--start and --end args are required")
                sys.exit(1)
            start_time = self.parse_date(start_time)
            if start_time is None:
                DebugPrint(-1, "Recovery mode ERROR: Can't parse start time")
                sys.exit(1)
            end_time = self.parse_date(end_time)
            if end_time is None:
                DebugPrint(-1, "Recovery mode ERROR: Can't parse end time") 
                sys.exit(1)
            if start_time > end_time:
                DebugPrint(-1, "Recovery mode ERROR: The end time is after " \
                              "the start time")
                sys.exit(1)
            if start_time > time.time():
                DebugPrint(-1, "Recovery mode ERROR: The start time is in " \
                               "the future")
                sys.exit(1)
        else:  # using condor history for all dates
            DebugPrint(-1 , "RUNNING the probe MANUALLY in recovery mode ")

        return start_time, end_time

    def parse_opts(self, options=None):
        parser = self.get_opts_parser()
        # Options are stored into opts/args class variables
        return parser.parse_args()

    def do_profile(self):
        """Wrap the main method in profiler execution
        """
        profiler = hotshot.Profile("profile.dat")
        DebugPrint(4, "Enabled profiling")
        retv = profiler.run("self._main()")
        profiler.close()
        stats = hotshot.stats.load("profile.dat")
        stats.sort_stats('time', 'calls')
        stats.print_stats()
        return retv

    def main(self):
        # Loop over completed jobs
        time_end = None
        server_id = self.get_db_server_id()
        DebugPrint(5 , "GratiaProbe main - running")
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
