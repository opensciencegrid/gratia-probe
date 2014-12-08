#!/usr/bin/python

#import sys,
#import os  # for os.popen
# , stat
import time
import datetime
#import random
#import pwd, grp

from gratia.common.Gratia import DebugPrint
#import gratia.common.GratiaWrapper as GratiaWrapper
import gratia.common.Gratia as Gratia
from gratia.services.StorageElement import StorageElement
from gratia.services.StorageElementRecord import StorageElementRecord

from meter import GratiaProbe, GratiaMeter

from pgpinput import PgInput

def DebugPrintLevel(level, *args):
    if level <= 0:
        level_str = "CRITICAL"
    elif level >= 4:
        level_str = "DEBUG"
    else:
        level_str = ["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"][level]
    level_str = "%s - EnstoreStorage: " % level_str
    #DBMM
    #print "***MM calling DbP %s %s %s" % (level, level_str, args)
    DebugPrint(level, level_str, *args)


class _EnstoreStorageInputStub:
    """Stub class, needs to be defined before the regular one, to avoid NameError
    """
    value_matrix = [[ '2013-05-01 00:00:00', 'ALEX',              27501971200 ,    29502252800 ,           94 ,         101],
[ '2013-05-01 00:00:00', 'AMN',                         0 ,              0 ,            0 ,           0],
[ '2013-05-01 00:00:00', 'ANM',             5324442004458 ,  5489039007858 ,         1645 ,        2087],
[ '2013-05-01 00:00:00', 'none',                        0 ,              0 ,            0 ,           0],
[ '2013-06-01 00:00:00', 'ALEX',              32502444800 ,    34502726400 ,          111 ,         118],
[ '2013-06-01 00:00:00', 'AMN',                         0 ,              0 ,            0 ,           0],
[ '2013-06-01 00:00:00', 'ANM',             5330140154858 ,  5494737158258 ,         1654 ,        2096],
[ '2013-06-01 00:00:00', 'none',                        0 ,              0 ,            0 ,           0],
[ '2013-07-01 00:00:00', 'ALEX',              32702534400 ,    34702816000 ,          112 ,         119],
[ '2013-07-01 00:00:00', 'AMN',                         0 ,              0 ,            0 ,           0],
[ '2013-07-01 00:00:00', 'ANM',             5363559205866 ,  5533639729266 ,         1745 ,        2190],
[ '2013-07-01 00:00:00', 'none',                        0 ,              0 ,            0 ,           0],
[ '2013-08-01 00:00:00', 'ANM',             9715492242387 ,  9894136393825 ,         7715 ,        8179],
[ '2013-08-01 00:00:00', 'none',                        0 ,              0 ,            0 ,           0],
[ '2014-02-01 00:00:00', 'ANM',             9999003890760 , 10599915674909 ,         7964 ,        8601],
[ '2014-02-01 00:00:00', 'litvinse',            231480377 ,      231480377 ,          120 ,         120],
[ '2014-02-01 00:00:00', 'test',                  2100468 ,        4200936 ,            3 ,           6],
[ '2014-03-01 00:00:00', 'ALEX',              10400563200 ,    10400563200 ,           62 ,          62],
[ '2014-03-01 00:00:00', 'ANM',             9343845119048 , 10192509713697 ,         7914 ,        8621],
[ '2014-03-01 00:00:00', 'litvinse',            231480377 ,      231480377 ,          120 ,         120],
[ '2014-03-01 00:00:00', 'none',                        0 ,              0 ,            0 ,           0],
[ '2014-03-01 00:00:00', 'test',                  2100468 ,        4200936 ,            3 ,           6],
[ '2014-04-01 00:00:00', 'ALEX',              10400563200 ,    10400563200 ,           62 ,          62],
[ '2014-04-01 00:00:00', 'ANM',             9430388985014 , 10280528687817 ,         8222 ,        9025],
[ '2014-04-01 00:00:00', 'e906',                        0 ,              0 ,            0 ,           0],
[ '2014-04-01 00:00:00', 'litvinse',            231480377 ,      231480377 ,          120 ,         120],
[ '2014-04-01 00:00:00', 'none',                        0 ,              0 ,            0 ,           0],
[ '2014-04-01 00:00:00', 'test',                  2100468 ,        4200936 ,            3 ,           6],
[ '2014-05-01 00:00:00', 'ALEX',              15002131200 ,    15002131200 ,           54 ,          54],
[ '2014-05-01 00:00:00', 'ANM',             9433767656334 ,  9654836052415 ,         8108 ,        8965],
[ '2014-05-01 00:00:00', 'e906',                        0 ,              0 ,            0 ,           0],
[ '2014-05-01 00:00:00', 'litvinse',            231480377 ,      231480377 ,          120 ,         120],
[ '2014-05-01 00:00:00', 'test',                  2100468 ,        4200936 ,            3 ,           6],
[ '2014-06-01 00:00:00', 'ALEX',               2900518400 ,     2900518400 ,           11 ,          11],
[ '2014-06-01 00:00:00', 'ANM',             9434587326624 ,  9655655722705 ,         8145 ,        9002],
[ '2014-06-01 00:00:00', 'e906',                        0 ,              0 ,            0 ,           0],
[ '2014-06-01 00:00:00', 'litvinse',            231480377 ,      231480377 ,          120 ,         120],
[ '2014-07-01 00:00:00', 'ALEX',             910905676800 ,   910905676800 ,         3044 ,        3044],
[ '2014-07-01 00:00:00', 'ANM',            10344072760622 , 10565385542446 ,         8877 ,        9846],
[ '2014-07-01 00:00:00', 'e906',                        0 ,              0 ,            0 ,           0],
[ '2014-07-01 00:00:00', 'litvinse',            231480377 ,     1102439795 ,          120 ,      377322]
]

    def get_records():
        for i in _EnstoreStorageInputStub.value_matrix:
            retv = {'date': i[0],
                    'storage_group': i[1],
                    'active_bytes': i[2],
                    'total_bytes': i[3],
                    'active_files': i[4],
                    'total_files': i[5]
                    }
            yield retv
    get_records = staticmethod(get_records)


class EnstoreStorageInput(PgInput):
    """Query the records form the Enstore enstoredb DB
    """

    VERSION_ATTRIBUTE = 'EnstoreVersion'

    def get_init_params(self):
        """Return list of parameters to read form the config file"""
        return PgInput.get_init_params(self) + [EnstoreStorageInput.VERSION_ATTRIBUTE]

    def start(self, static_info):
        PgInput.start(self, static_info)
        DebugPrint(4, "ESI start, static info: %s" % static_info)
        if EnstoreStorageInput.VERSION_ATTRIBUTE in static_info:
            self._set_version_config(static_info[EnstoreStorageInput.VERSION_ATTRIBUTE])

    def _start_stub(self, static_info):
        """start replacement for testing: database connection errors are trapped"""
        try:
            DebugPrintLevel(4, "Testing DB connection. The probe will not use it")
            PgInput.start(self, static_info)
            if self.status_ok():
                DebugPrintLevel(4, "Connection successful")
            else:
                DebugPrintLevel(4, "Connection failed")
            DebugPrintLevel(4, "Closing the connection")
            self.stop()
        except:
            DebugPrint(1, "Database connection failed. The test can continue since stubs are used.")
        DebugPrint(4, "ESI start stub, static info: %s" % static_info)
        if EnstoreStorageInput.VERSION_ATTRIBUTE in static_info:
            self._set_version_config(static_info[EnstoreStorageInput.VERSION_ATTRIBUTE])

    def get_version(self):
        # RPM package is 'enstore'
        return self._get_version('enstore')

    def get_records(self, limit=None):
        """Select the usage records from the storage table
        enstoredb=> \d historic_tape_bytes;
          Table "public.historic_tape_bytes"
   Column     |            Type             | Modifiers
---------------+-----------------------------+-----------
date          | timestamp without time zone | not null
storage_group | character varying           | not null
active_bytes  | bigint                      |
unknown_bytes | bigint                      |
deleted_bytes | bigint                      |
active_files  | bigint                      |
unknown_files | bigint                      |
deleted_files | bigint                      |
Indexes:
   "historic_tape_bytes_pkeys" PRIMARY KEY, btree (date, storage_group)


Table is updated monthly and for each storage group contains
record about number of bytes.

We are interested in

active_bytes and (active_bytes+deleted_bytes+unknown_bytes) as total_bytes
active_files and (active_files+deleted_files+unknown_files) as total_files
        """

        #TODO: double check what time format is returned:
        # - float (timestamp without zone)
        # - datetime (timestamp with time zone)
        # it seems that some records return one, some the other
        # checkpoint was complaining that was not a datetime
        # StorageElement building is complaining that it is not a float/int
        # GratiaProbe.format_date() will accept both, but would be nice to understand

        checkpoint = self.checkpoint
        if checkpoint:
            checkpoint_sql = "WHERE date >= '%s'" % GratiaProbe.format_date(checkpoint.date())
        else:
            checkpoint_sql = ""
        if limit:
            limit_sql = "LIMIT %s" % limit
        else:
            limit_sql = ""

        sql = '''SELECT
            date,
            storage_group, active_bytes,
            (active_bytes+unknown_bytes+deleted_bytes) as total_bytes,
            active_files,
            (active_files+unknown_files+deleted_files) as total_files
            FROM historic_tape_bytes
            %s
            ORDER BY date, storage_group
            %s
            ''' % (checkpoint_sql, limit_sql)

        DebugPrint(4, "Requesting new Enstore records %s" % sql)
        new_checkpoint = None
        for r in self.query(sql):
            # Add handy data to job record
            #r['cluster'] = self._cluster
            #self._addUserInfoIfMissing(r)
            yield r
            if checkpoint:
                # psycopg2 returns datetime obj (ok for checkpoint)
                #  timestamp->datetime, timestamp without time zone -> float (seconds since Epoch)
                new_date = GratiaProbe.parse_date(r['date'])
                if new_checkpoint is None or new_date > new_checkpoint:
                    new_checkpoint = new_date
        if new_checkpoint:
            #print "****** MMDB Saving New Checkpoint: %s, %s, %s" % (type(new_checkpoint), new_checkpoint, datetime.datetime.fromtimestamp(new_checkpoint))
            checkpoint.set_date_transaction(datetime.datetime.fromtimestamp(new_checkpoint))

    def _get_records_stub(self):
        """get_records replacement for tests: records are from a pre-filled array"""
        for i in _EnstoreStorageInputStub.get_records():
            yield i

    def do_test(self):
        """Test with pre-arranged DB query results
        """
        # replace DB calls with stubs
        self.start = self._start_stub
        self.get_records = self._get_records_stub


class EnstoreStorageProbe(GratiaMeter):

    PROBE_NAME = 'enstorestorage'
    # dCache, xrootd, Enstore
    SE_NAME = 'Enstore'
    # Production
    SE_STATUS = 'Production'
    # disk, tape
    SE_TYPE = 'tape'
    # raw, logical
    SE_MEASUREMENT_TYPE = 'logical'

    def __init__(self):
        GratiaMeter.__init__(self, self.PROBE_NAME)
        self._probeinput = EnstoreStorageInput()

    def get_storage_element(self, unique_id, site, name, parent_id=None, timestamp=None):
        #if not timestamp:
        #    timestamp = time.time()
        if not parent_id:
            parent_id = unique_id
        gse = StorageElement()
        gse.UniqueID(unique_id)
        gse.SE(site)
        gse.Name(name)
        gse.ParentID(parent_id)
        # VO
        # OwnerDN
        gse.SpaceType("StorageGroup") # PoolGroup, StorageGroup in enstore terminology
        if timestamp:
            gse.Timestamp(timestamp)
        gse.Implementation(self.SE_NAME)
        gse.Version(self.get_version())
        gse.Status(self.SE_STATUS)
        # ProbeName
        # probeid
        # SiteName
        # Grid
        return gse

    def get_storage_element_record(self, unique_id, timestamp=None):
        #if not timestamp:
        #    timestamp = time.time()
        gser = StorageElementRecord()
        gser.UniqueID(unique_id)
        gser.MeasurementType(self.SE_MEASUREMENT_TYPE)
        gser.StorageType(self.SE_TYPE)
        # StorageType
        if timestamp:
            gser.Timestamp(timestamp)
        # TotalSpace, Free, Used
        # FileCountLimit
        # FileCount
        # Probename
        # probeid
        return gser

    def input_to_gsrs(self, inrecord, selement, serecord):
        """Add input values to storage element and storage element record
        Return the tuple VO,tot,free,used,f_tot,f_used to allow cumulative counters
        """
        # SE
        selement.VO(inrecord['storage_group'])
        selement.Name(inrecord['storage_group'])
        timestamp = self.format_date(inrecord['date'])
        selement.Timestamp(timestamp)
        # SER
        serecord.Timestamp(timestamp)
        used = inrecord['active_bytes']
        total = inrecord['total_bytes']
        # Values are in bytes
        serecord.TotalSpace(total)
        serecord.FreeSpace(total-used)
        serecord.UsedSpace(used)
        # Add file counts
        # different form total_files - serecord.FileCountLimit()
        serecord.FileCount(inrecord['active_files'])
        return inrecord['storage_group'], total, total-used, used, 0, inrecord['active_files']

    def main(self):
        # Initialize the probe an the input
        self.start()
        DebugPrintLevel(4, "Enstore storage probe started")

        se = "MyTestName4Now"  # self.get_sitename()
        # Understand the meaning of the name: name = self.get_probename()
        name = "parent"
        timestamp = time.time()

        # Parent storage element
        DebugPrintLevel(4, "Sending the parent StorageElement (%s/%s)" % (se, name))
        unique_id = "%s:SE:%s" % (se, se)
        parent_id = unique_id
        gse = self.get_storage_element(unique_id, se, name, timestamp=timestamp)
        Gratia.Send(gse)
        # TODO: is a SER with totals needed?

        # Loop over storage records
        for srecord in self._probeinput.get_records():
            vo_name = srecord['storage_group']
            DebugPrint(4, "Sending SE/SER for VO %s" % vo_name)
            unique_id = "%s:StorageGroup:%s" % (se, vo_name)
            # the name of the se is the vo_name
            # the timestamp is coming from the 'date' value in the record
            gse = self.get_storage_element(unique_id, se, vo_name, parent_id)
            gser = self.get_storage_element_record(unique_id)

            self.input_to_gsrs(srecord, gse, gser)

            # To print the records being sent
            #gse.Print()
            #gser.Print()

            Gratia.Send(gse)
            Gratia.Send(gser)

        #server_id = self.probeinput.get_db_server_id()
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
        #if self.checkpoint.val == time_end:
        #    self.checkpoint.val = time_end + 1


if __name__ == "__main__":
    EnstoreStorageProbe().main()



