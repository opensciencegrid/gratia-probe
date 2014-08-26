#!/usr/bin/python

#import sys, os, stat
import time
#import random
#import pwd, grp

from gratia.common.Gratia import DebugPrint
#import gratia.common.GratiaWrapper as GratiaWrapper
import gratia.common.Gratia as Gratia
from gratia.services.StorageElement import StorageElement
from gratia.services.StorageElementRecord import StorageElementRecord

from meter import GratiaProbe, GratiaMeter

from pgpinput import PgInput

class EnstoreStorageInput(PgInput):
    def get_records(self):
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

        checkpoint = self.checkpoint

        if checkpoint:
            sql = '''SELECT
            date,
            storage_group, active_bytes,
            (active_bytes+unknown_bytes+deleted_bytes) as total_bytes,
            active_files,
            (active_files+unknown_files+deleted_files) as total_files
            FROM historic_tape_bytes
            WHERE date >= '%s'
            ORDER BY date, storage_group
            ''' % GratiaProbe.format_date(checkpoint.val)
        else:
            sql = '''SELECT
            date,
            storage_group, active_bytes,
            (active_bytes+unknown_bytes+deleted_bytes) as total_bytes,
            active_files,
            (active_files+unknown_files+deleted_files) as total_files
            FROM historic_tape_bytes
            ORDER BY date, storage_group
            ''' 
        
        new_checkpoint = None
        for r in self.query(sql):
            # Add handy data to job record
            #r['cluster'] = self._cluster
            #self._addUserInfoIfMissing(r)
            yield r
            if checkpoint:
                new_date = GratiaProbe.parse_date(r['date'])
                if new_date>new_checkpoint:
                    new_checkpoint = new_date
        if new_checkpoint:
            checkpoint.val = new_checkpoint


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
        GratiaProbe.__init__(self, self.PROBE_NAME)
        self._probeinput = EnstoreStorageInput()

    def get_storage_element(self, unique_id, site, name, parent_id=None, timestamp=None):
        if not timestamp:
            timestamp = time.time()
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
        if not timestamp:
            timestamp = time.time()
        gser = StorageElementRecord()
        gser.UniqueID(unique_id)
        gser.MeasurementType(self.SE_MEASUREMENT_TYPE)
        gser.StorageType(self.SE_TYPE)
        # StorageType
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
        # SER
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
        DebugPrint(5, "Starting the Enstore storage probe")
        self.start()


        se = self.get_site_name()
        name = self.get_probe_name()
        timestamp = time.time()

        # Parent storage element
        DebugPrint(5, "Sending the parent StorageElement")
        unique_id = "%s:SE:%s" % (se, se)
        parent_id = unique_id
        gse = self.get_storage_element(unique_id, se, name, timestamp=timestamp)
        Gratia.Send(gse)
        # TODO: is a SER with totals needed?

        # Loop over storage records
        for srecord in self._probeinput.get_records():
            vo_name = srecord['storage_group']
            DebugPrint(5, "Sending SE/SER for VO %s" % vo_name)
            unique_id = "%s:StorageGroup:%s" % (se, vo_name)
            gse = self.get_storage_element(unique_id, se, name, parent_id, timestamp)
            gser = self.get_storage_element_record(unique_id, timestamp)

            self.input_to_gsrs(srecord, gse, gser)

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
