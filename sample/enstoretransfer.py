#!/usr/bin/python

#import sys, os, stat
import time
#import random
#import pwd, grp
import os
import signal
from urlparse import urlparse

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
    print "***MM calling DbP %s %s %s" % (level, level_str, args)
    DebugPrint(level, level_str, *args)


class _EnstoreTransferInputStub:
    """Stub class, needs to be defined before the regular one, to avoid NameError
    """
    """ Query: accounting=> select * from xfer_by_day where date>'2014-08-25';
    date    | storage_group |   read    |    write     | n_read | n_write
------------+---------------+-----------+--------------+--------+---------
 2014-08-26 | ANM           |         0 | 115070377984 |      0 |    7377
 2014-08-27 | ANM           |  11535362 |            0 |      3 |       0
 2014-08-28 | ANM           |  94470144 |            0 |      3 |       0
 2014-08-29 | ALEX          | 900096000 |            0 |      3 |       0

 accounting=> select * from encp_xfer where date > '2014-08-27';
        date         |       node       |  pid  | username |                                                              src                                                               |
                                           dst                                                       |   size    | rw | overall_rate | network_rate | drive_rate |                      volume
             |      mover      |  drive_id   |  drive_sn  |    elapsed    |     media_changer      | mover_interface |   driver   | storage_group |    encp_ip    |               encp_id
| disk_rate | transfer_rate |          encp_version          |   file_family    | wrapper  |  library
---------------------+------------------+-------+----------+--------------------------------------------------------------------------------------------------------------------------------+-----------
-----------------------------------------------------------------------------------------------------+-----------+----+--------------+--------------+------------+--------------------------------------
-------------+-----------------+-------------+------------+---------------+------------------------+-----------------+------------+---------------+---------------+-------------------------------------
+-----------+---------------+--------------------------------+------------------+----------+------------
 2014-08-27 13:58:15 | dmsen03.fnal.gov |  7770 | root     | /pnfs/fs/usr/data2/file_aggregation/LTO4/moibenko/tape/encp_test_for_enstore/file_clerk3/test_files_for_enstore/1MB_002        | /dev/null
                                                                                                     |   1048577 | r  |        14636 |      9150443 |     810559 | TST066
             | LTO4_022.mover  | ULTRIUM-TD4 | 1310249035 | 72.5509800911 | SL8500GS.media_changer | enmvr022        | FTTDriver  | ANM           | 131.225.13.26 | dmsen03.fnal.gov-1409165822-7770-0
|   9150443 |       4533208 | v3_11c CVS $Revision$ encp.pyc | volume_read_test | cpio_odc | LTO4GS
 2014-08-27 13:58:23 | dmsen03.fnal.gov |  7770 | root     | /pnfs/fs/usr/data2/file_aggregation/LTO4/moibenko/tape/encp_test_for_enstore/file_clerk3/test_files_for_enstore/10MB_002       | /dev/null
                                                                                                     |  10485761 | r  |      1571134 |      7546562 |    7455045 | TST066
             | LTO4_022.mover  | ULTRIUM-TD4 | 1310249035 |  7.6930038929 | SL8500GS.media_changer | enmvr022        | FTTDriver  | ANM           | 131.225.13.26 | dmsen03.fnal.gov-1409165895-7770-1
|   7546562 |       4215884 | v3_11c CVS $Revision$ encp.pyc | volume_read_test | cpio_odc | LTO4GS
 2014-08-27 13:58:24 | dmsen03.fnal.gov |  7770 | root     | /pnfs/fs/usr/data2/file_aggregation/LTO4/moibenko/tape/encp_test_for_enstore/file_clerk3/test_files_for_enstore/1KB_001        | /dev/null
                                                                                                     |      1024 | r  |          783 |     12341860 |      55531 | TST066
             | LTO4_022.mover  | ULTRIUM-TD4 | 1310249035 | 1.61123895645 | SL8500GS.media_changer | enmvr022        | FTTDriver  | ANM           | 131.225.13.26 | dmsen03.fnal.gov-1409165903-7770-2
|  12341860 |           914 | v3_11c CVS $Revision$ encp.pyc | volume_read_test | cpio_odc | LTO4GS
 2014-08-28 16:04:53 | dmsen03.fnal.gov |  8583 | root     | /pnfs/fs/usr/data2/file_aggregation/packages/ANM.FF1_NEW.cpio_odc/TST084/package-M1W-2014-08-26T17:20:35.959Z.tar              | /volumes/a
ggread/cache/tmp_stage/package-M1W-2014-08-26T17:20:35.959Z/package-M1W-2014-08-26T17:20:35.959Z.tar |  74547200 | r  |       421630 |     60217146 |   39859591 | TST084
             | LTO4_021B.mover | ULTRIUM-TD4 | 1310206564 | 487.945667982 | SL8500GS.media_changer | enmvr021        | FTTDriver  | ANM           | 131.225.13.26 | dmsen03.fnal.gov-1409259405-8583-0
|  67758717 |      34457635 | v3_11c CVS $Revision$ encp.pyc | FF1_NEW          | cpio_odc | LTO4GS
 2014-08-28 16:04:55 | dmsen06.fnal.gov | 20374 | enstore  | /pnfs/fs/usr/data2/file_aggregation/LTO4/moibenko/torture_test/new_lib/dmsen06/7/dmsen06_f2f6cda82d6e11e4af4700304831518c.data | /dev/null
                                                                                                     |  10485760 | r  |        21336 |     76052612 |   77875300 | common1:ANM.FF1_NEW.cpio_odc:2013-07-
02T14:33:50Z | disk5.mover     | Unknown     | 0          | 492.506582975 | UNKNOWN                | dmsen03         | DiskDriver | ANM           | 131.225.13.37 | dmsen06.fnal.gov-1409259403-20374-0
|  76052612 |      58762140 | v3_11c CVS $Revision$ encp     | FF1_NEW          | cpio_odc | diskSF_NEW
 2014-08-28 16:07:06 | dmsen06.fnal.gov | 20733 | enstore  | /pnfs/fs/usr/data2/file_aggregation/LTO4/moibenko/torture_test/new_lib/dmsen06/4/dmsen06_e8ea85a22d6e11e4a6bc00304831518c.data | /dev/null
                                                                                                     |   9437184 | r  |     41230225 |     79026540 |   88431780 | common1:ANM.FF1_NEW.cpio_odc:2013-07-
02T14:33:50Z | disk7.mover     | Unknown     | 0          | 1.27875304222 | UNKNOWN                | dmsen03         | DiskDriver | ANM           | 131.225.13.37 | dmsen06.fnal.gov-1409260025-20733-0
|  79026540 |      61668401 | v3_11c CVS $Revision$ encp     | FF1_NEW          | cpio_odc | diskSF_NEW
 2014-08-29 19:59:27 | dmsen03.fnal.gov | 11611 | root     | /pnfs/fs/usr/data2/file_aggregation/packages/ALEX.TestClone_7.cpio_odc/TST083/package-M2W-2014-07-30T19:21:25.77Z.tar          | /dev/null
                                                                                                     | 300032000 | r  |      2096428 |    112118327 |  135221272 | TST083
             | LTO4_021B.mover | ULTRIUM-TD4 | 1310206564 | 144.629033089 | SL8500GS.media_changer | enmvr021        | FTTDriver  | ALEX          | 131.225.13.26 | dmsen03.fnal.gov-1409360223-11611-0
| 112118327 |     107459278 | v3_11c CVS $Revision$ encp.pyc | TestClone_7      | cpio_odc | LTO4GS
 2014-08-29 20:00:34 | dmsen03.fnal.gov | 11611 | root     | /pnfs/fs/usr/data2/file_aggregation/packages/ALEX.TestClone_7.cpio_odc/TST083/package-M2W-2014-07-30T19:27:56.844Z.tar         | /dev/null
                                                                                                     | 300032000 | r  |      4526877 |     80136089 |   85963956 | TST083
             | LTO4_021B.mover | ULTRIUM-TD4 | 1310206564 | 67.3343689442 | SL8500GS.media_changer | enmvr021        | FTTDriver  | ALEX          | 131.225.13.26 | dmsen03.fnal.gov-1409360367-11611-1
|  80136089 |      77746704 | v3_11c CVS $Revision$ encp.pyc | TestClone_7      | cpio_odc | LTO4GS
 2014-08-29 20:02:16 | dmsen03.fnal.gov | 11611 | root     | /pnfs/fs/usr/data2/file_aggregation/packages/ALEX.TestClone_7.cpio_odc/TST083/package-M2W-2014-07-30T18:58:22.864Z.tar         | /dev/null
                                                                                                     | 300032000 | r  |      2987800 |    111891277 |  135991153 | TST083
             | LTO4_021B.mover | ULTRIUM-TD4 | 1310206564 | 101.175196171 | SL8500GS.media_changer | enmvr021        | FTTDriver  | ALEX          | 131.225.13.26 | dmsen03.fnal.gov-1409360435-11611-2
| 111891277 |     107261667 | v3_11c CVS $Revision$ encp.pyc | TestClone_7      | cpio_odc | LTO4GS
"""
    value_matrix = [['2014-08-26', 'ANM', 0, 115070377984, 0, 7377],
                    ['2014-08-27', 'ANM', 11535362, 0, 3, 0],
                    ['2014-08-28', 'ANM', 94470144, 0, 3, 0],
                    ['2014-08-29', 'ALEX', 900096000, 0, 3, 0]
                    ]
    value_matrix2 = [['2014-08-26', 'ANM', 0, 115070377984, 0, 7377],
                    ['2014-08-27', 'ANM', 11535362, 115070377984, 3, 7377],
                    ['2014-08-28', 'ANM', 94470144, 0, 3, 0],
                    ['2014-08-29', 'ALEX', 900096000, 0, 3, 0]
                    ]

    value_matrix3 = [['']
                     [ '2014-10-01 12:41:55', 'enstore',  '/pnfs/fs/usr/data2/file_aggregation/LTO4/moibenko/tape/encp_test_for_enstore/test_files_for_enstore/0B_001', '/dev/null',     0, 'r',  'ANM' ],
                     [ '2014-10-01 12:43:09', 'enstore',  '/tmp/encp_test/test_files_for_enstore/1B_001', '/pnfs/fs/usr/data2/file_aggregation/LTO4/moibenko/tape/encp_test_for_enstore/encp_test_for_enstore/1B_001',     1, 'w',  'ANM' ],
                     [ '2014-10-01 12:44:05', 'enstore',  '/pnfs/fs/usr/data2/file_aggregation/LTO4/moibenko/tape/encp_test_for_enstore/encp_test_for_enstore/1B_001', '/tmp/encp_test/encp_test_for_enstore/1B_001',     1, 'r',  'ANM' ],
                     [ '2014-10-01 12:44:29', 'enstore',  '/tmp/encp_test/test_files_for_enstore/0B_001', '/pnfs/fs/usr/data2/file_aggregation/LTO4/moibenko/tape/encp_test_for_enstore/encp_test_for_enstore/0B_001',     0, 'w',  'ANM' ],
                     [ '2014-10-01 12:44:56', 'enstore',  '/pnfs/fs/usr/data2/file_aggregation/LTO4/moibenko/tape/encp_test_for_enstore/encp_test_for_enstore/0B_001', '/tmp/encp_test/encp_test_for_enstore/0B_001',     0, 'r',  'ANM' ],
                     [ '2014-10-01 12:44:59', 'enstore',  '/pnfs/fs/usr/data2/file_aggregation/LTO4/moibenko/tape/encp_test_for_enstore/encp_test_for_enstore/0B_001 ', '/tmp/encp_test/encp_test_for_enstore/0B_001',     0, 'r',  'ANM' ],
                     [ '2014-10-01 12:45:27', 'enstore',  '/tmp/encp_test/test_files_for_enstore/1KB_002', '/pnfs/fs/.(access)(00002DB28146F4624708908011210EC4876B)',  1025, 'w',  'ANM' ],
                     [ '2014-10-01 12:46:19', 'enstore',  '/pnfs/fs/.(access)(00002DB28146F4624708908011210EC4876B)', '/tmp/encp_test/encp_test_for_enstore/1KB_002',  1025, 'r',  'ANM' ],
                     [ '2014-10-01 12:46:23', 'enstore',  '/pnfs/fs/.(access)(00002DB28146F4624708908011210EC4876B)', '/tmp/encp_test/encp_test_for_enstore/1KB_002',  1025, 'r',  'ANM' ],
                     [ '2014-10-01 12:46:46', 'enstore',  '/tmp/encp_test/test_files_for_enstore/10KB_002', '/pnfs/fs/usr/data2/file_aggregation/LTO4/moibenko/tape/encp_test_for_enstore/encp_test_for_enstore/10KB_002', 10241, 'w',  'ANM' ],
                     [ '2014-10-02 09:21:17', 'root',  '/pnfs/fs/usr/data2/file_aggregation/packages/ANM.FF1_NEW.cpio_odc/TST084/package-M1W-2014-10-01T13:17:55.694Z.tar', '/volumes/aggread/cache/tmp_stage/package-M1W-2014-10-01T13:17:55.694Z/package-M1W-2014-10-01T13:17:55.694Z.tar', 136396800, 'r',  'ANM' ],
                     [ '2014-10-02 09:21:20', 'enstore',  '/pnfs/fs/usr/data2/file_aggregation/LTO4/moibenko/torture_test/new_lib/dmsen06/0/dmsen06_06e607e0499711e4912800304831518c.data', '/dev/null',  11534336, 'r', 'ANM']
    ]

    def get_records_summary():
        for i in _EnstoreTransferInputStub.value_matrix:
            retv = {'date': i[0],
                    'storage_group': i[1],
                    'read': i[2],
                    'write': i[3],
                    'n_read': i[4],
                    'n_write': i[5]
                    }
            yield retv
    get_records_summary = staticmethod(get_records_summary)

    def get_records():
        for i in _EnstoreTransferInputStub.value_matrix:
            retv = {'date': i[0],
                    'username': i[1],
                    'src': i[2],
                    'dst': i[3],
                    'size': i[4],
                    'rw': i[5],
                    'storage_group': i[6]
                    }
            yield retv
    get_records = staticmethod(get_records)


class EnstoreTransferInput(PgInput):
    """Get transfer information from the Enstore accounting DB
    """

    VERSION_ATTRIBUTE = 'EnstoreVersion'

    def get_init_params(self):
        """Return list of parameters to read form the config file"""
        return PgInput.get_init_params(self) + [EnstoreTransferInput.VERSION_ATTRIBUTE]

    def start(self, static_info):
        """open DB connection and set version form config file"""
        PgInput.start(self, static_info)
        DebugPrint(4, "ESI start, static info: %s" % static_info)
        if EnstoreTransferInput.VERSION_ATTRIBUTE in static_info:
            self._set_version_config(static_info[EnstoreTransferInput.VERSION_ATTRIBUTE])

    def _start_stub(self, static_info):
        """start replacement for testing: database connection errors are trapped"""
        try:
            PgInput.start(self, static_info)
        except:
            DebugPrint(1, "Database connection may fail and is OK since stubs are used")
        DebugPrint(4, "ESI start stub, static info: %s" % static_info)
        if EnstoreTransferInput.VERSION_ATTRIBUTE in static_info:
            self._set_version_config(static_info[EnstoreTransferInput.VERSION_ATTRIBUTE])

    def get_version(self):
        # RPM package is 'enstore'
        return self._get_version('enstore')

    def get_records(self):
        """Select the transfer records from the transfer table
        accounting=> \d encp_xfer;
                Table "public.encp_xfer"
    Column      |            Type             | Modifiers
-----------------+-----------------------------+-----------
date            | timestamp without time zone | not null - StartTime
node            | character varying           | not null - hostname?
pid             | integer                     | not null
username        | character varying(32)       | not null - LocalUser
src             | text                        | not null +- FileName (depending on direction)
dst             | text                        | not null +
size            | bigint                      | not null - size in Network
rw              | character(1)                | not null - isNew r->0, w->1
overall_rate    | bigint                      | not null
network_rate    | bigint                      | not null
drive_rate      | bigint                      | not null
volume          | character varying           | not null
mover           | character varying(32)       | not null
drive_id        | character varying(16)       | not null
drive_sn        | character varying(16)       | not null
elapsed         | double precision            | not null
media_changer   | character varying(32)       | not null
mover_interface | character varying(32)       | not null
driver          | character varying(16)       | not null
storage_group   | character varying(16)       | not null
encp_ip         | character varying(16)       | not null
encp_id         | character varying(64)       | not null
disk_rate       | bigint                      |
transfer_rate   | bigint                      |
encp_version    | character varying(48)       |
file_family     | character varying           |
wrapper         | character varying           |
library         | character varying           |
Indexes:
    "encp_error_library_idx" btree (library)
    "encp_xfer_library_idx" btree (library)
    "xfr_date_idx" btree (date)
    "xfr_file_family_idx" btree (file_family)
    "xfr_media_changer_idx" btree (media_changer)
    "xfr_mover_idx" btree (mover)
    "xfr_node_idx" btree (node)
    "xfr_oid_idx" btree (oid)
    "xfr_pid_idx" btree (pid)
    "xfr_storage_group_idx" btree (storage_group)
    "xfr_user_idx" btree (username)
    "xfr_volume_idx" btree (volume)
    "xfr_wrapper_idx" btree (wrapper)
        """
        checkpoint = self.checkpoint

        if checkpoint:
            sql = '''SELECT
            date,
            node, pid,
            username,
            src, dst,
            size,
            rw,
            overall_rate,
            storage_group
            FROM encp_xfer
            WHERE date >= '%s'
            ORDER BY date, storage_group
            ''' % GratiaProbe.format_date(checkpoint.val)
        else:
            sql = '''SELECT
            date,
            node, pid,
            username,
            src, dst,
            size,
            rw,
            overall_rate,
            storage_group
            FROM encp_xfer
            ORDER BY date, storage_group
            '''

        DebugPrint(4, "Requesting new Enstore records %s" % sql)
        new_checkpoint = None
        for r in self.query(sql):
            yield r
            if checkpoint:
                new_date = GratiaProbe.parse_date(r['date'])
                if new_date>new_checkpoint:
                    new_checkpoint = new_date
        if new_checkpoint:
            checkpoint.val = new_checkpoint


    def get_records_summary(self):
        """Select the transfer records from the daily summary table
        accounting=> \d xfer_by_day;
         Table "public.xfer_by_day"
    Column     |       Type        | Modifiers
---------------+-------------------+-----------
 date          | date              | not null
 storage_group | character varying | not null
 read          | bigint            |
 write         | bigint            |
 n_read        | bigint            |
 n_write       | bigint            |
Indexes:
    "xfer_by_date_pkey" PRIMARY KEY, btree (date, storage_group)
Daily summary pre-calculated by trigger in the enstore DB

We are interested in

        """
        # TODO: is daily summary OK or detailed values are needed?

        checkpoint = self.checkpoint

        if checkpoint:
            sql = '''SELECT
            date,
            storage_group,
            read, write,
            n_read, n_write
            FROM xfer_by_day
            WHERE date >= '%s'
            ORDER BY date, storage_group
            ''' % GratiaProbe.format_date(checkpoint.val)
        else:
            sql = '''SELECT
            date,
            storage_group,
            read, write,
            n_read, n_write
            FROM xfer_by_day
            ORDER BY date, storage_group
            ''' 

        DebugPrint(4, "Requesting new Enstore records %s" % sql)
        new_checkpoint = None
        for r in self.query(sql):
            yield r
            if checkpoint:
                new_date = GratiaProbe.parse_date(r['date'])
                if new_date>new_checkpoint:
                    new_checkpoint = new_date
        if new_checkpoint:
            checkpoint.val = new_checkpoint

    def _get_records_stub(self):
        """get_records replacement for tests: records are from a pre-filled array"""
        for i in _EnstoreTransferInputStub.get_records():
            yield i

    def do_test(self):
        """Test with pre-arranged DB query results
        replacing: start, get_records
        """
        # replace DB calls with stubs
        self.start = self._start_stub
        self.get_records = self._get_records_stub


class EnstoreTransferProbe(GratiaMeter):

    PROBE_NAME = 'enstoretransfer'
    # dCache, xrootd, Enstore
    SE_NAME = 'Enstore'
    # Production
    SE_STATUS = 'Production'
    # disk, tape
    SE_TYPE = 'tape'
    # raw, logical
    SE_MEASUREMENT_TYPE = 'logical'

    def __init__(self):
        GratiaProbe.__init__(self, self.PROBE_NAME)
        self._probeinput = EnstoreTransferInput()

    #def get_storage_element(self, unique_id, site, name, parent_id=None, timestamp=None):
    #    return gse

    #def get_storage_element_record(self, unique_id, timestamp=None):
    #    return gser

    #def input_to_gsrs(self, inrecord, selement, serecord):
    #    """Add input values to storage element and storage element record
    #    Return the tuple VO,tot,free,used,f_tot,f_used to allow cumulative counters
    #    """
    #    return inrecord['storage_group'], total, total-used, used, 0, inrecord['active_files']

    def get_usage_record(self):
        r = Gratia.UsageRecord("Storage")
        r.AdditionalInfo("Protocol", "enstore")
        r.Grid("Local")

    def URL2host(self, urltoparse):
        tmp = urlparse(urltoparse)
        if tmp.hostname:
            return tmp.hostname
        return self.get_hostname()

    def main(self):
        # Initialize the probe an the input
        self.start()
        DebugPrintLevel(4, "Enstore transfer probe started")

        se = self.get_sitename()
        name = self.get_probename()
        timestamp = time.time()

        # Parent storage element
        #DebugPrintLevel(4, "Sending the parent StorageElement (%s/%s)" % (se, name))
        #unique_id = "%s:SE:%s" % (se, se)
        #parent_id = unique_id
        #gse = self.get_storage_element(unique_id, se, name, timestamp=timestamp)
        #Gratia.Send(gse)
        # TODO: is a SER with totals needed?

        hostname = self.get_hostname()

        # Loop over storage records
        for srecord in self._probeinput.get_records():
            """
            date,
            node, pid,
            username,
            src, dst,
            size,
            rw,
            storage_group
            """
            isNew = srecord['rw'] == 'w'
            if isNew:
                filepath = srecord['dst']
            else:
                filepath = srecord['src']
            r = self.get_usage_record()
            vo_name = srecord['storage_group']
            r.VOName(vo_name)
            r.AdditionalInfo("Source", self.URL2host(srecord['src']))
            r.AdditionalInfo("Destination", self.URL2host(srecord['dst']))
            r.AdditionalInfo("Protocol", "enstore")
            r.AdditionalInfo("IsNew", isNew)
            r.AdditionalInfo("File", filepath)
            uniq_id = "%s.%s" % (srecord['node'], srecord['pid'])
            r.LocalJobId(uniq_id)
            r.Grid("Local")
            r.StartTime(srecord['date'])
            # TODO: double check unit conversion. Must be always bytes
            size = srecord['size']
            if size == 0:
                duration = 0
            else:
                duration = int(size/srecord['overall_rate'])
            r.Network(size, 'b', duration, "transfer")
            r.WallDuration(duration)
            r.LocalUserId(srecord['username'])
            r.SubmitHost(srecord['node']) # TODO: node in the record or host running the probe?
            #r.Status(0)
            # TODO: can we ask to store DN of enstore transfers? Does it make sense?
            r.DN("/OU=UnixUser/CN=%s" % srecord['username'])
            DebugPrint(4, "Sending transfer record for VO %s" % vo_name)
            Gratia.Send(r)


            """ Summary record
            #vo_name = srecord['storage_group']
            # Avoid empty records
            if srecord['read']+srecord['write']+srecord['n_read']+srecord['n_write'] == 0:
                continue
            if srecord['read']>0:
                # outgoing traffic
                r = self.get_usage_record()
                r.AdditionalInfo("Source", hostname)
                # unknown destination: r.AdditionalInfo("Destination", dstHost)
                r.AdditionalInfo("Protocol", "enstore")
                r.AdditionalInfo("IsNew", isNew)
            """
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
    # Do the work
    EnstoreTransferProbe().main()



