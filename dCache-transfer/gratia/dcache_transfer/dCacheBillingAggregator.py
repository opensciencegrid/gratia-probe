# Copyright 2007 Cornell University, Ithaca, NY. All rights reserved.
#
# Author:  Gregory J. Sharp
# Version: $Id: dCacheBillingAggregator.py,v 1.13 2009/09/03 15:52:06 greenc Exp $
#
# This is a Python program that reads the dCache billing database, aggregates
# any new content, and sends it to Gratia.

import os
import sys
import time
import signal
import string
import logging
import traceback
import xml.dom.minidom
# Python profiler
import hotshot
import hotshot.stats

from logging.handlers import RotatingFileHandler

# The gratia probe code
import gratia.common.Gratia as Gratia
from gratia.common.probe_config import ProbeConfiguration
# Local modules
import TestContainer
from Alarm import Alarm
from DCacheAggregator import DCacheAggregator, sleep_check

ProgramName = "dCacheBillingAggregator"

UNIX_GID_LIST_FILE_NAME_DEFAULT = "/etc/gratia/dCache-transfer/group"

class dCacheProbeConfig(ProbeConfiguration):
    """
    This class extends the gratia ProbeConfiguration class so that we can
    add our own configuration parameters to the ProbeConfig file.
    The additional supported variables each have their own get_ function below.
    """
    _emailList = [ 'notdefined' ]
    def __init__( self ):
        # Just call the parent class to read in the file.
        # We just add some extra name/value readouts.
        ProbeConfiguration.__init__(self)

    def getConfigAttribute(self, name):
        return ProbeConfiguration.getConfigAttribute(self, name)

    def get_UpdateFrequency(self):
        return self.getConfigAttribute('UpdateFrequency')

    def get_StopFileName(self):
        return self.getConfigAttribute('StopFileName')

    def get_DBHostName(self):
        return self.getConfigAttribute('DBHostName')

    def get_DBLoginName(self):
        return self.getConfigAttribute('DBLoginName')

    def get_DBName(self):
        dbname = self.getConfigAttribute("DBName")
        if not dbname:
            dbname = 'billing'
        return dbname

    def get_DBPassword(self):
        return self.getConfigAttribute('DBPassword')

    def get_DCacheServerHost(self):
        return self.getConfigAttribute('DCacheServerHost')

    def get_Summarize(self):
        try:
            return int(self.getConfigAttribute("Summarize"))
        except:
            return False

    # This is the name of a host that is running an SMTP server to which
    # email messages can be submitted.
    def get_EmailServerHost(self):
        return self.getConfigAttribute('EmailServerHost')

    # This is the email address from which the email allegedly originated.
    # Some email servers will tweak it if they don't like it, rather than
    # rejecting it. Caveat emptor.
    def get_EmailFromAddress(self):
        return self.getConfigAttribute('EmailFromAddress')

    # This is the list of recipients for emails about pressing problems
    # encountered by the dCache probe. We save the list for subsequent
    # calls, since multiple alarms may be set up.
    def get_EmailToList( self ):
        if self._emailList[0] == 'notdefined':
            value = self.getConfigAttribute( 'EmailToList' )
            if value == '':
                print "WARNING: EmailToList is empty. Will use stdout."
            self._emailList = value.split( ", " )
        return self._emailList

    # OnlySendInterSiteTransfers is used to restrict reporting of
    # intra-site file copying. That information would only be reported
    # if using a local gratia repository.
    def get_OnlySendInterSiteTransfers( self ):
        result = self.getConfigAttribute( 'OnlySendInterSiteTransfers' );
        return ((result == None) or (string.lower(result) == 'true'))

    def get_MaxBillingHistoryDays( self ):
        default = 30
        result = self.getConfigAttribute( 'MaxBillingHistoryDays' )
        if result:
            try:
                result = int(result)
            except:
                result = default
        else:
            result = default
        return result

    # The logging level for this program is distinct from the logging
    # level for Gratia. We default to DEBUG if we don't recognize the
    # log level as "error", "warn" or "info"
    def get_AggrLogLevel( self ):
        level = self.getConfigAttribute( 'AggrLogLevel' )
        if level == "error":
            return logging.ERROR
        elif level == "warn":
            return logging.WARN
        elif level == "info":
            return logging.INFO
        else:
            return logging.DEBUG

    def get_UnixGidListFileName(self):
        fname = self.getConfigAttribute('UnixGidListFileName')
        if not fname:
            return UNIX_GID_LIST_FILE_NAME_DEFAULT
        return fname

# end class dCacheProbeConfig


# Forward declare the terminationAlarm object.
terminationAlarm = None


def warn_of_signal( signum, frame ):
    logger = logging.getLogger( 'DCacheAggregator' )
    if logger != None:
        logger.critical( "Going down on signal " + str( signum ) );
    if terminationAlarm != None:
        terminationAlarm.event()
    os._exit( 1 )

def main():
    # We need the logger variable in the exception handler.
    # So we create it here.
    logger = logging.getLogger( 'DCacheAggregator' )

    # Ignore hangup signals. We shouldn't die just because our parent
    # shell logs out.
    signal.signal( signal.SIGHUP, signal.SIG_IGN )
    # Try to catch common signals and send email before we die
    signal.signal( signal.SIGINT,  warn_of_signal );
    signal.signal( signal.SIGQUIT, warn_of_signal );
    signal.signal( signal.SIGTERM, warn_of_signal );

    try:
        # Tell Gratia what versions we are using.
        # CHRIS: is there a way to automate the version extraction
        #        using the pkg_resource package?
        Gratia.RegisterReporterLibrary( "psycopg2", "2.0.6" )
        #Gratia.RegisterReporterLibrary( "SQLAlchemy", "0.4.1" )
        rev =  Gratia.ExtractCvsRevision("$Revision: 1.13 $")
        tag =  Gratia.ExtractCvsRevision("$Name:  $")
        Gratia.RegisterReporter( "dCacheBillingAggregator.py",
                                 str(rev) + " (tag " + str(tag) + ")")

        # BRIAN: attempt to pull the dCache version from RPM.
        version = "UNKNOWN"
        try:
            version = os.popen("rpm -q --qf '%{VERSION}-%{RELEASE}' " \
                               "dcache-server").read()
        except:
            pass
        Gratia.RegisterService( "dCache", version )


        # Initialize gratia before attempting to read its config file.
        Gratia.Initialize()
        # Extract the configuration information into local variables.
        myconf = dCacheProbeConfig()

        # Get the name of the directory where we are to store the log files.
        logDir = myconf.get_LogFolder()

        # Make sure that the logging directory is present
        if not os.path.isdir( logDir ):
            os.mkdir( logDir, 0755 )

        logFileName = os.path.join( logDir, "dcacheTransfer.log" )

        # Set up an alarm to send an email if the program terminates.
        termSubject = "dCache-transfer probe is going down"
        termMessage = "The dCache transfer probe for Gratia has " + \
                      "terminated.\nPlease check the logfile\n\n   " + \
                      logFileName + \
                      "\n\nfor the cause.\n"

        terminationAlarm = Alarm( myconf.get_EmailServerHost(),
                                  myconf.get_EmailFromAddress(),
                                  myconf.get_EmailToList(),
                                  termSubject, termMessage, 0, 0, False )

        # Set up the logger with a suitable format
        hdlr = RotatingFileHandler( logFileName, 'a', 512000, 10 )
        formatter = logging.Formatter( '%(asctime)s %(levelname)s %(message)s' )
        hdlr.setFormatter( formatter )
        logger.addHandler( hdlr )
        logger.setLevel( myconf.get_AggrLogLevel() )
        logger.info( "starting " + ProgramName )

        stopFileName = myconf.get_StopFileName()
        updateFreq = float(myconf.get_UpdateFrequency())
        logger.warn("update freq = %.2f" % updateFreq)

        # Create the aggregator instance that we will use.
        dataDir = myconf.get_DataFolder()
        aggregator = DCacheAggregator(myconf, dataDir)

        # If profiling was requested, turn it on.
        profiling = sys.argv.count('-profile') > 0
        if profiling:
            profiler = hotshot.Profile("profile.dat")
            logger.info( "Enabling Profiling" )

        # Now aggregate new records, then sleep, until somebody creates
        # the stop file...
        while 1:
            # Make sure we (still) have a connection to Gratia.
            if ( not TestContainer.isTest() ): # no need in that during self test
               Gratia.Maintenance()
          
            if profiling:
                profiler.run("aggregator.sendBillingInfoRecordsToGratia()")
            else:
                try:
                    aggregator.sendBillingInfoRecordsToGratia()
                except TestContainer.SimInterrupt:
                    logger.info("BillingRecSimulator.SimInterrupt caught, " \
                        "restarting")
                    aggregator = DCacheAggregator(myconf, dataDir)
                    continue
            # Are we are shutting down?
            if os.path.exists(stopFileName):
                break

            if TestContainer.isTest():
                break

            logger.warn("sleeping for = %.2f seconds" % updateFreq)
            sleep_check(updateFreq, stopFileName)

        # If we are profiling, print the results...
        if profiling:
            profiler.close()
            stats = hotshot.stats.load("profile.dat")
            stats.sort_stats('time', 'calls')
            stats.print_stats()

        logger.warn(ProgramName + " stop file detected.")
    except (KeyboardInterrupt, SystemExit):
        raise
    except:
        # format the traceback into a string
        tblist = traceback.format_exception( sys.exc_type,
                                             sys.exc_value,
                                             sys.exc_traceback )
        msg = ProgramName + " caught an exception:\n" + "".join(tblist)
        print msg
        logger.error(msg)

    TestContainer.dumpStatistics(logger)

    # shut down the logger to make sure nothing is lost.
    logger.critical(ProgramName + " shutting down.")
    logging.shutdown()
    # try to send an email warning of the shutdown.
    if terminationAlarm != None:
        terminationAlarm.event()

    sys.exit(1)

if __name__ == '__main__':
    main()

