#!/usr/bin/python

#import sys, os, stat
#import time, random
#import pwd, grp

from gratia.common.Gratia import DebugPrint
#import gratia.common.GratiaWrapper as GratiaWrapper
import gratia.common.Gratia as Gratia

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

    def __init__(self):
        GratiaProbe.__init__(self, self.PROBE_NAME)
        self._probeinput = EnstoreStorageInput()

    def input_to_sr(self, inrecord):
        pass


    def main(self):
        # Initialize the probe an the input
        self.start()

        # Loop over storage records
        for srecord in self._probeinput.get_records():
            r = self.input_to_sr(srecord)
            Gratia.Send(r)

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
