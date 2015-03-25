# Copyright 2007 Cornell University, Ithaca, NY. All rights reserved.
#
# Author:  Gregory J. Sharp
# Version: $Id: DCacheAggregator.py,v 1.29 2009/10/21 20:24:46 greenc Exp $
#
# This is a first attempt at a python program that reads the dCache billing
# database, aggregates any new content, and posts it to Gratia.

"""
This module implements the logic of the dCache transfer probe.

It handles the querying of the billing DB and the translation of the queries
to Gratia UsageRecord format.

If the probe is meant to summarize the transfers before sending them to Gratia,
the probe does this using the TimeBinRange and Collapse helper modules.  It
groups on DCACHE_AGG_FIELDS and sums the values of DCACHE_SUM_FIELDS.

There is no index column on the billing DB, meaning we have to be very careful
about aggregating.  If we, for example, use LIMIT 100 and restrict the date
range to dates less than '2010-03-01 00:00:00', then:
  a) len(results) < 100: In this case, we have successfully retrieved all
     records less than the specified date.
  b) len(results) == 100: In this case, we don't know how many remaining
     records there are.  We ought to query again with a smaller time window or
     with an increased limit until case (a) happens.
We quit recursing in (b) if the limit hits the maximum size of returned result
(which is estimated by looking at the amount of memory in the machine).

We repeat the queries above until we have an entire hour's worth of data,
summarizing the partial results as we go.  Finally, once an hour's worth of
data has been constructed, we send the results to Gratia.

TODO list for this probe:
   1) Remove sqlalchemy -- DONE
   2) Remove python logging in favor of Gratia logging.
"""

import os
import sys
import logging
import time
import psycopg2
import psycopg2.extras

import traceback
import pwd
import locale
import datetime
import re

import gratia.common.Gratia as Gratia
from Checkpoint import Checkpoint
from Alarm import Alarm

import TimeBinRange
import Collapse
import BillingRecSimulator
import TestContainer


DCACHE_AGG_FIELDS = ['initiator', 'client', 'protocol', 'errorcode', 'isnew']
DCACHE_SUM_FIELDS = ['njobs', 'transfersize', 'connectiontime']

def sleep_check(length, stopFileName):
    """
    Sleep for the number of seconds specified by `length`.  Check to see if the
    stop file exists at most once a second.  If the stop file is present, then
    return immediately.
    """
    while length > 1:
        if os.path.exists(stopFileName):
            return
        length -= 1
        time.sleep(1)
    if length > 0:
        time.sleep(length)

# If the DB query takes more than this amount of time, something is very wrong!
# The probe will throw an exception and exit.
MAX_QUERY_TIME_SECS = 180

# The next two functions determine the amount of RAM available on the machines
# and hence the maximum number of rows we are willing to query.

re_parser = re.compile(r'^(?P<key>\S*):\s*(?P<value>\d*)\s*kB' )
def _Meminfo():
    """-> dict of data from meminfo (str:int).
    Values are in kilobytes.
    """
    result = dict()
    for line in open('/proc/meminfo'):
        match = re_parser.match(line)
        if not match:
            continue # skip lines that don't parse
        key, value = match.groups(['key', 'value'])
        result[key] = int(value)
    return result

def _CalcMaxSelect():
    """
    Returns the maximum number of sql results so that
    we do not use more than half of the install RAM on
    the current machine.
    """
    try:
        mem = _Meminfo()["MemTotal"]
        if ( mem < 2048000 ):
            mem = 2048000
        return int(mem / 4)
    except:
        return 512000

if TestContainer.isTest():
    STARTING_MAX_SELECT = 50
    MAX_SELECT = 100
    STARTING_RANGE = 60
    MIN_RANGE = 1
else:
    STARTING_MAX_SELECT = 32000
    MAX_SELECT = _CalcMaxSelect()
    STARTING_RANGE = 60
    MIN_RANGE = 1

BILLINGDB_SELECT_CMD = """
 SELECT
        b.datestamp AS datestamp,
        b.transaction AS transaction,
        b.cellname AS cellname,
        b.action AS action,
        b.transfersize AS transfersize,
        b.connectiontime AS connectiontime,
        b.isnew AS isnew,
        b.client AS client,
        b.errorcode AS errorcode,
        b.protocol AS protocol,
        b.initiator AS doorlink,
        COALESCE(d.owner, split_part(b.storageclass,'.',1)) AS initiator,
        CASE WHEN d.client = 'unknown'  THEN
                COALESCE(b.client,'Unknown')
             ELSE
                COALESCE(d.client, 'Unknown')
        END AS initiatorHost,
        d.mappeduid as mappeduid,
        d.mappedgid as mappedgid
    FROM
        billinginfo b INNER JOIN  doorinfo d ON b.initiator = d.transaction
        WHERE b.datestamp >= '%s' AND b.datestamp < '%s'
        AND b.p2p='f'
        AND d.datestamp >= '%s' AND d.datestamp < '%s'
        ORDER BY datestamp
        LIMIT %i
"""

import warnings
warnings.simplefilter('ignore', FutureWarning)

class DCacheAggregator:
    """
    This class reads the dCache billing database on the specified host
    and pulls out the next set of data to be sent to gratia. It remembers
    what it has already sent by looking at the last successful checkpoint.
    When summarizing, checkpoints are only sent after an hour's worth of data
    is done.

    Note that we limit the select to _maxSelect items to moderate memory
    usage.  _maxSelect may grow until we think we're hitting memory limits.
    We also shrink the query interval size until we are able to get less than
    the limit returned.
    """

    _connection = None
    _maxSelect = STARTING_MAX_SELECT
    _range = STARTING_RANGE

    # Do not send in records older than 30 days
    _maxAge = 30

    def __init__( self, configuration, chkptdir=None ):
        # Pick up the logger
        self._log = logging.getLogger( 'DCacheAggregator' )
        self.__user_map = {}
        self.__uuid_file_mod_time = int(time.time())
        self._unix_id_list_file_name = configuration.get_UnixIdListFileName()
        if os.path.exists(self._unix_id_list_file_name) :
            self.__uuid_file_mod_time = os.stat(self._unix_id_list_file_name).st_mtime
            self.__refresh_user_map()
        # Neha - 03/17/2011
        # Using psycopg2 instead of sqlalchemy
        DBurl = 'dbname=%s user=%s ' % (configuration.get_DBName(), configuration.get_DBLoginName())
        DBurl += 'password=%s ' % (configuration.get_DBPassword())
        DBurl += 'host=%s' % (configuration.get_DBHostName())

        # Neha - 03/17/2011
        # Commenting out as not using sqlalchemy anymore
        #DBurl = 'postgres://%s:%s@%s:5432/%s' % \ (configuration.get_DBLoginName(), configuration.get_DBPassword(), configuration.get_DBHostName(), configuration.get_DBName())
        self._skipIntraSite = configuration.get_OnlySendInterSiteTransfers()
        self._stopFileName = configuration.get_StopFileName()
        self._dCacheSvrHost = configuration.get_DCacheServerHost()
        # Create the billinginfo database checkpoint.
        self._maxAge = configuration.get_MaxBillingHistoryDays()
        if ( TestContainer.isTest() ):
           self._maxAge = TestContainer.getMaxAge()

        billinginfoChkpt = 'chkpt_dcache_xfer_DoNotDelete'
        if chkptdir != None:
            billinginfoChkpt = os.path.join(chkptdir, billinginfoChkpt)
        self._BIcheckpoint = Checkpoint(billinginfoChkpt, self._maxAge)

        self._sendAlarm = Alarm(
                configuration.get_EmailServerHost(),
                configuration.get_EmailFromAddress(),
                configuration.get_EmailToList(),
                'dCacheTransfer probe aggregator alarm',
                'The dCache Transfer Probe was not able to send to Gratia.',
                2,    # If more than two errors have occurred
                1800, # Max of once per half hour complaining
                True )

        self._summarize = configuration.get_Summarize()

        # Connect to the dCache postgres database.
        # TODO: Using sqlalchemy gives us nothing but a new dependency.  Remove - Done
        # Neha: 03/17/2011 - Removing sqlalchemy. Using psycopg2 instead
        try:
            if TestContainer.isTest():
                self._db = None
            else:
                #self._db = sqlalchemy.create_engine(DBurl)
                #self._connection = self._db.connect()
                self._connection = psycopg2.connect(DBurl)
                self._cur = self._connection.cursor(cursor_factory=psycopg2.extras.DictCursor)
        except:
            tblist = traceback.format_exception(sys.exc_type,
                                                sys.exc_value,
                                                sys.exc_traceback)
            errmsg = 'Failed to connect to %s\n\n%s' % (DBurl, "\n".join(tblist))
            self._log.error(errmsg)
            raise

        self._grid = configuration.get_Grid()

    def __refresh_user_map(self) :
        self.__user_map.clear()
        try:
            fd=open(self._unix_id_list_file_name,'r')
            for line in fd:
                if not line : continue
                try:
                    uid,gid,fullname,uname=line.strip().split(":")
                    self.__user_map[(uid,gid)] = uname
                except:
                    pass
            fd.close()
        except:
            self._log.warn("Make sure %s is on this host" % (self._unix_id_list_file_name))



    def _skipIntraSiteXfer(self, row):
        """
        Boolean method that returns true if the specified row is for an
        intra-site transfer and we the configuration file said to skip
        such records.
        """
        return self._skipIntraSite and row['protocol'].startswith("DCap")

    def _execute(self, starttime, endtime, maxSelect):
        """
        Execute the select command against the Billing DB return the results
        (possibly summarized)

        It is guaranteed this function will return an endtime greater than the
        starttime, but not guaranteed by how much.

        Note on the time returned as the first part of the tuple:
        We guarantee two things:
           a) returned time is strictly greater than starttime
           b) We return *all* records in the interval [starttime, return time).
        We do not guarantee that return time == parameter endtime.
        Thus it is suitable to use as the start time of the next select query.
        To do this, we reduce the range until it reaches 1 second or the
        query returns less than maxSelect results.   If the interval is one
        second and it still returns maxSelect results then we extend the limit
        of the query until all records fit.

        @param starttime: Datetime object for the start of the query interval.
        @param endtime: Datetime object for the end of the query interval.
        @param maxSelect: The maximum number of rows to select
        @return: Tuple containing the a time that is greater than all the
           records and the results
        """
        assert starttime < endtime
        if (maxSelect > MAX_SELECT) and ((endtime-starttime).seconds <= \
                MIN_RANGE):
            raise Exception("Fatal error - more than %i transfers in %i" \
                " second(s)." % (MAX_SELECT,(endtime-starttime).seconds))
        datestr = str(starttime)
        datestr_end = str(endtime)

        # Query the database.  If it takes more than MAX_QUERY_TIME_SECS, then
        # have the probe self-destruct.
        query=BILLINGDB_SELECT_CMD% ((datestr, datestr_end, datestr, datestr_end, maxSelect))
        self._log.debug('_sendToGratia: will execute ' + query)
        select_time = -time.time()
        if not TestContainer.isTest():
            self._cur.execute(query)
            result = self._cur.fetchall()
        else:
            result = BillingRecSimulator.execute(query)
        select_time += time.time()
        if select_time > MAX_QUERY_TIME_SECS:
            raise Exception("Postgres query took %i seconds, more than " \
                "the maximum allowable of %i; this is a sign the DB is " \
                "not properly optimized!" % (int(select_time),
                MAX_QUERY_TIME_SECS))
        self._log.debug("BillingDB query finished in %.02f seconds and " \
            "returned %i records." % (select_time, len(result)))

        if not result:
            self._log.debug("No results from %s to %s." % (starttime, endtime))
            return endtime, result
        # dCache sometimes returns a negative transfer size; when this happens,
        # it also tosses up a complete garbage duration
        filtered_result = []
        for row in result:
            row = dict(row)
            #print row
            if row['transfersize'] < 0:
                row['transfersize'] = 0
                row['connectiontime'] = 0
            filtered_result.append(row)
        result = filtered_result

        # If we hit our limit, there's no telling how many identical records
        # there are on the final millisecond; we must re-query with a smaller
        # interval or a higher limit on the select.
        if len(result) == maxSelect:
            diff = endtime - starttime
            interval = diff.days*86400 + diff.seconds
            # Ensure that self._range is such that we always end up on a minute boundary (eventually).
            # Whenever we decrease the interval size it is guaranteed to be a multiple of what's left
            # of the interval to the  next minute.  I.e the transitions are:
            #   60s ->  30s
            #   30s ->  15s (which can only happen at :30s)
            #   15s ->   5s (which can only happen at :15s :30s or :45s)
            #    5s ->   1s
            if   (interval > 60):
                new_interval = 60
            elif (interval > 30):
                new_interval = 30
            elif (interval > 15):
                new_interval = 15
            elif (interval >  5):
                new_interval =  5
            else:
                new_interval =  1
            new_endtime = starttime + datetime.timedelta(0, new_interval)
            # Guard against the DST jump by making sure new_endtime > starttime.
            if (interval == new_interval) or (new_interval == 0) or \
                (new_endtime <= starttime):
                self._log.warning("Limit hit; increasing from %i to %i." % \
                    (maxSelect, maxSelect*2))
                endtime, result = self._execute(starttime, endtime, maxSelect*2)
                assert endtime > starttime
                return endtime, result
            else:
                self._log.warning("Limit hit; decreasing time interval from %i" \
                   " to %i." % (interval, new_interval))
                self._range = new_interval
                endtime, result = self._execute(starttime, new_endtime,
                    maxSelect)
                assert endtime > starttime
                return endtime, result

        return endtime, result

    def _processResults(self, results):
        """
        Process all of the results.
        This method basically is a `for` loop around _processDBRow.  It does
        make sure the row is a real python dict, has njobs set, and catches
        any exceptiond Gratia might throw at it
        """
        numDone = 0
        for row in results:
            row = dict(row)
            row.setdefault("njobs", 1)
            try:
                numDone += self._processDBRow(row)
            except (KeyboardInterrupt, SystemExit, TestContainer.SimInterrupt):
                raise
            except Exception, e:
                self._log.warning("Unable to make a record out of the " \
                    "following SQL row: %s." % str(row))
                self._log.exception(e)
                # Increment numDone, otherwise we will exit early.
                numDone += row['njobs']
        return numDone

    def _processDBRow(self, row):
        """
        Completely process a single DB row.  Take the row, convert it to a
        UsageRecord, and send it up to Gratia.  Process any recoverable errors
        which occurred during the process.

        Note we skip a row if it is an Intra-site transfer and we are instructed
        not to send them.

        Otherwise, we process the row in Gratia or exit the probe.

        @return: The number of jobs in this row, regardless of whether we sent
           them successfully or not.
        """
        # Skip intra-site transfers if required
        if self._skipIntraSiteXfer(row):
           return row['njobs']

        if ( TestContainer.isTest() ):
           if ( self._summarize ):
              TestContainer.sendInterrupt(15)
           return TestContainer.processRow(row,self._log)

        usageRecord = self._convertBillingInfoToGratiaUsageRecord(\
                        row)

        # Send to gratia, and see what it says.
        response = Gratia.Send(usageRecord)
        baseMsg = "Record: %s, %s, njobs %i" % (str(row['datestamp']),
            row['transaction'], row['njobs'])
        if response == "Fatal Error: too many pending files":
            # The server is currently not accepting record and
            # Gratia.py was not able to store the record, we will
            # need to resend it.
            # For now take a long nap and then by 'break' we
            # force a retry for this record.
            self._log.error("Error sending : too many pending files")
            longsleep = 15*60
            self._log.warn("sleeping for = %i seconds." % longsleep)
            sleep_check(longsleep, self._stopFileName)
        elif response.startswith('Fatal Error') or \
            response.startswith('Internal Error'):
            self._log.critical('error sending ' + baseMsg + \
                '\ngot response ' + response)
            sys.exit(2)
            self._log.debug('sent ' + baseMsg)
        # If we got a non-fatal error, slow down since the server
        # might be overloaded.
        if response[:2] != 'OK':
            self._log.error('error sending ' + baseMsg + \
                            '\ngot response ' + response)

        return row['njobs']

    def _convertBillingInfoToGratiaUsageRecord(self, row):
        """
        Take a record returned from the database and convert it to a Gratia
        UsageRecord

        @param row: A dictionary-like object describing the Billing DB entry.
        @return: UsageRecord equivalent to the input row
        """
        # Convert date to utc. This can't be done perfectly, alas, since we
        # don't have the original timezone. We assume localtime.
        # This code is horrible, but it should work. row['datestamp'] should
        # be a datetime.datetime object.
        # make the time into a float
        fltTime = time.mktime(row['datestamp'].timetuple())
        startTime = time.strftime('%Y-%m-%dT%H:%M:%S', time.gmtime(fltTime))
        # NOTE WELL: we need the time accurate to milliseconds. So we
        # add it back to the UTC time.
        startTime = startTime + "." + \
                    locale.format("%06d", row['datestamp'].microsecond) + "Z"

        # convert the connection time in milliseconds to a decimal in seconds
        connectTime = float(row['connectiontime']) / 1000.0
        connectionTimeStr = 'PT' + str(connectTime) + 'S'

        # Check for the link to the doorinfo table being bad and log a
        # warning in the hope that somebody notices a bug has crept in.
        if row['doorlink'] == '<undefined>' and \
                   not row['protocol'].startswith('DCap'):
            self._log.warn( 'billinginfo record with datestamp ' + \
                        startTime + ' contained undefined initiator field' )

        # Work out the end points of the data transfer.
        thisHost = str(row['cellname']) + '@' + self._dCacheSvrHost
        if row['isnew']:
            srcHost = row['client']
            dstHost = thisHost
            isNew = 1
        else:
            srcHost = thisHost
            dstHost = row['client']
            isNew = 0

        rec = Gratia.UsageRecord('Storage')
        rec.Njobs(row['njobs'])
        rec.AdditionalInfo('Source', srcHost)
        rec.AdditionalInfo('Destination', dstHost)
        rec.AdditionalInfo('Protocol', row['protocol'])
        rec.AdditionalInfo('IsNew', isNew)
        rec.LocalJobId(row['transaction'])
        if row['protocol'].startswith("DCap"):
            rec.Grid("Local")
        else:
            # Set the grid name to the default in the ProbeConfig
            rec.Grid(self._grid)
        rec.StartTime(startTime)
        rec.Network(row['transfersize'], 'b', connectionTimeStr, 'total',
            row['action'])
        rec.WallDuration(connectionTimeStr)

        # only send the initiator if it is known.
        if row['initiator'] != 'unknown':
            rec.DN(row['initiator'])
        # if the initiator host is "unknown", make it "Unknown".
        initiatorHost = row['initiatorhost']
        if initiatorHost == 'unknown':
            initiatorHost = 'Unknown'
        rec.SubmitHost(initiatorHost)
        rec.Status(row['errorcode'])
        # If we included the mapped uid as the local user id, then
        # Gratia will make a best effort to map this to the VO name.
        mappedUID = row['mappeduid']
        mappedGID = row['mappedgid']
        if row['protocol'] == 'NFS4-4.1':
            username = row['initiator']
            rec.LocalUserId(username)
            return rec
        try:
            username = 'Unknown'
            if row['initiator'] != 'unknown':
                username = row['initiator']
            if mappedUID != None and int(mappedUID) >= 0:
                try:
                    info = pwd.getpwuid(int(mappedUID))
                    username = info[0]
                except:
                    #will try to get id from storage-authzdb
                    try:
                        mtime = os.stat(self._unix_id_list_file_name).st_mtime
                        if self.__uuid_file_mod_time != mtime:
                            self.__uuid_file_mod_time = mtime
                            self.__refresh_user_map()
                        username=self.__user_map.get((str(mappedUID),str(mappedGID)))
                        if not username :
                            self._log.warn("UID %s %s not found locally; make sure " \
                                           "/etc/passwd or %s on this host and your dCache are using " \
                                           "the same UIDs,GIDs!" % (self._unix_id_list_file_name,str(int(mappedUID)),str(int(mappedGID))))
                    except:
                        self._log.warn("UID %s not found locally in /etc/passwed and %s does not exist or "\
                                "inaccessible " % (str(int(mappedUID)),self._unix_id_list_file_name))
            rec.LocalUserId(username)
        except (KeyboardInterrupt, SystemExit):
            raise
        except Exception, e:
            self._log.info("Failed to map UID %s to VO." % mappedUID)
        return rec


    def sendBillingInfoRecordsToGratia(self):
        """
        This is the public method for starting the dCache-transfer reporting.

        This will query records no more than _maxAge old, and always starts
        queries on hour time boundaries (i.e., 1:00:00 not 1:02:00).

        This will continue to query until we hit records starting less than 75
        minutes ago, then return.

        By default, we start with querying 60-second intervals, but will shrink
        this window if we encounter lots of data.

        If not summarizing: this method uses _execute to get all the data for
           a given interval, then uses _processResults to send them to Gratia.
           Once the query for a time interval is done, then we immediately
           checkpoint.

        If summarizing: this method continues to query until it hits the end of
           an hour interval.  At that point, it summarizes once again, and sends
           the summaries up to Gratia.  We then only checkpoint on the hour.
        """
        self._log.debug("sendBillingInfoRecordsToGratia")

        # Query no more than a set number of days in the past
        minTime = datetime.datetime.now() - datetime.timedelta(self._maxAge, 0)
        minTime = datetime.datetime(minTime.year, minTime.month, minTime.day,
            minTime.hour, 0, 0)

        # The latest allowed record is 75 minutes in the past, in order to make
        # sure we only query complete intervals
        latestAllowed = datetime.datetime.now() - datetime.timedelta(0, 75*60)

        if ( TestContainer.isTest() ):
           latestAllowed = TestContainer.getEndDateTime()

        # Start with either the last checkpoint or minTime days ago, whichever
        # is more recent.
        starttime = max(self._BIcheckpoint.lastDateStamp(), minTime)
        self._log.info("Starting queries at time %s." % starttime)

        dictRecordAgg = TimeBinRange.DictRecordAggregator(DCACHE_AGG_FIELDS,
            DCACHE_SUM_FIELDS)

        nextSummary = self._determineNextEndtime(starttime, summary=True)
        if self._summarize:
            self._log.debug("Next summary send time: %s." % nextSummary)

        results = []
        endtime = self._determineNextEndtime(starttime)
        totalRecords = 0
        # Loop until we have caught up to latestAllowed.
        while starttime < latestAllowed:
            assert starttime < endtime
            self._log.debug('sendBillingInfoRecordsToGratia: Processing ' \
                'starting at %s.' % starttime)
            # We are guaranteed that starttime will move forward to the value of
            # endtime every time we call execute.
            next_starttime, rows = self._execute(starttime, endtime, self._maxSelect)

            results += rows
            totalRecords += len(rows)
            if self._summarize:
                # Summarize the partial results
                results = Collapse.collapse(results, dictRecordAgg)
            assert next_starttime > starttime
            next_endtime = self._determineNextEndtime(next_starttime)

            # If we're not summarizing, we send up records each loop.
            if (not self._summarize) and results:
                totalRecords = 0
                # We now have all the rows we want; process them
                self._BIcheckpoint.createPending(endtime, '')
                self._processResults(results)
                self._BIcheckpoint.commit()
                if (self._range < STARTING_RANGE and len(results)*4 < \
                       self._maxSelect):
                    self._range = STARTING_RANGE
                results = []
            # If we are summarizing, send records only per hour of data
            elif (next_endtime > nextSummary) and results:
                num_agg = totalRecords - len(results)
                if num_agg:
                    factor = float(totalRecords)/float(len(results))
                    self._log.info("Aggregated %i of %i records for time " \
                        "interval ending in %s.  %.1fx reduction." % \
                        (num_agg, totalRecords, nextSummary, factor))
                else:
                    self._log.debug("Unable to aggregate any of %i records" \
                        % totalRecords)
                totalRecords = 0
                self._BIcheckpoint.createPending(nextSummary, '')
                self._processResults(results)
                self._BIcheckpoint.commit()
                results = []
                self._range = STARTING_RANGE

            nextSummary = self._determineNextEndtime(next_starttime,
                summary=True)

            endtime = next_endtime
            starttime = next_starttime

            # Check to see if the stop file has been created.  If so, break
            if os.path.exists(self._stopFileName):
                #Neha - 03/17/2011
                #Don't need to commit anything since we are only doing select and no inserts or updates
                self._cur.close()
                self._connection.close()
                break


    def _determineNextEndtime(self, starttime, summary=False):
        """
        If self._range == 60, given a starttime, determine the next full minute.
        Examples:
           - 01:06:00 -> 01:07:00
           - 01:00:40 -> 01:01:00
           - 01:59:59 -> 02:00:00
        Otherwise just add self._range to starttime

        If summary=True, determine the next full hour instead.
        """
        assert isinstance(starttime, datetime.datetime)
        if summary:
            endtime = datetime.datetime(starttime.year, starttime.month,
                starttime.day, starttime.hour, 0, 0)
            endtime += datetime.timedelta(0, 3600)
        else:
            if ( self._range < 60 ) :
                endtime = starttime + datetime.timedelta(0, self._range)
            else:
                endtime = datetime.datetime(starttime.year, starttime.month,
                    starttime.day, starttime.hour, starttime.minute, 0)
                endtime += datetime.timedelta(0, 60)
        # Watch out for DST issues
        if endtime == starttime:
            endtime += datetime.timedelta(0, 7200)
        return endtime

# end class dCacheRecordAggregator

