#!/usr/bin/python
# /* vim: set expandtab tabstop=4 shiftwidth=4 softtabstop=4: */

###########################################################################
# slurm_meter
#
# Python-based probe for SLURM accounting database
# 
# John Thiltges, 2012-Jun-19
# Based on condor_meter by Brian Bockelman
# 
# Copyright 2012 University of Nebraska-Lincoln. Released under GPL v2.
###########################################################################

import sys, os, stat
import time, random
import pwd, grp
import subprocess

from gratia.common.Gratia import DebugPrint
import gratia.common.GratiaWrapper as GratiaWrapper
import gratia.common.Gratia as Gratia

import MySQLdb
import MySQLdb.cursors
import re
from distutils.version import LooseVersion

prog_version = "%%%RPMVERSION%%%"

class SlurmProbe:

    opts       = None
    args       = None
    checkpoint = None
    conn       = None
    cluster    = None
    sacct      = None

    def __init__(self):
        try:
            self.opts, self.args = self.parse_opts()
        except Exception, e:
            print >> sys.stderr, str(e)
            sys.exit(1)

        # Initialize Gratia
        if not self.opts.gratia_config or not os.path.exists(self.opts.gratia_config):
            raise Exception("Gratia config, %s, does not exist." %
                    self.opts.gratia_config)
        Gratia.Initialize(self.opts.gratia_config)

        if self.opts.verbose:
            Gratia.Config.set_DebugLevel(5)

        # Sanity checks for the probe's runtime environment.
        GratiaWrapper.CheckPreconditions()

        if self.opts.sleep:
            rnd = random.randint(1, int(self.opts.sleep))
            DebugPrint(2, "Sleeping for %d seconds before proceeding." % rnd)
            time.sleep(rnd)

        # Make sure we have an exclusive lock for this probe.
        GratiaWrapper.ExclusiveLock()

        self.register_gratia("slurm_meter")

        # Find the checkpoint filename (if enabled)
        if self.opts.checkpoint:	
            checkpoint_file = os.path.join(
                Gratia.Config.get_WorkingFolder(), "checkpoint")
        else:
            checkpoint_file = None

        # Open the checkpoint file
        self.checkpoint = SlurmCheckpoint(checkpoint_file)

        # Only process DataFileExpiration days of history
        # (unless we're resuming from a checkpoint file)
        if self.checkpoint.val is None:
            self.checkpoint.val = int(time.time() - (Gratia.Config.get_DataFileExpiration() * 86400))

        # Connect to database
        self.conn = self.get_db_conn()

        self.cluster = Gratia.Config.getConfigAttribute('SlurmCluster')

        # SLURM made changes to the accounting database schema
        slurm_version = self.get_slurm_version()
        if LooseVersion(slurm_version) < LooseVersion("15.08.0"):
            # Original schema
            self.sacct = SlurmAcct_v1(self.conn, self.cluster, slurm_version)
        else:
            # Added TRES (Trackable resources) in 15.08.0pre5
            self.sacct = SlurmAcct_v2(self.conn, self.cluster, slurm_version)

    def parse_opts(self):
        """Hook to parse command-line options"""
        return

    def get_db_server_id(self):
        """Return database server ID: server/port/database"""
        return "/".join([
            Gratia.Config.getConfigAttribute('SlurmDbHost'),
            Gratia.Config.getConfigAttribute('SlurmDbPort'),
            Gratia.Config.getConfigAttribute('SlurmDbName'), ])

    def get_db_conn(self):
        """Return a database connection"""
        return MySQLdb.connect(
            host   = Gratia.Config.getConfigAttribute('SlurmDbHost'),
            port   = int(Gratia.Config.getConfigAttribute('SlurmDbPort')),
            user   = Gratia.Config.getConfigAttribute('SlurmDbUser'),
            passwd = self.get_password(Gratia.Config
                            .getConfigAttribute('SlurmDbPasswordFile')),
            db     = Gratia.Config.getConfigAttribute('SlurmDbName'),
            cursorclass = MySQLdb.cursors.SSDictCursor)

    def get_password(self, pwfile):
        """Read a password from a given file, checking permissions"""
        fp = open(pwfile)
        mode = os.fstat(fp.fileno()).st_mode

        if (stat.S_IMODE(mode) & (stat.S_IRGRP | stat.S_IROTH)) != 0:
            raise IOError("Password file %s is readable by group or others" %
                pwfile)

        return fp.readline().rstrip('\n')

    def get_slurm_version(self):
        prog = "srun"
        path = Gratia.Config.getConfigAttribute("SlurmLocation")
        fd = None

        # Unless there is a specific path configured
        if path:
            c = os.path.join(path, "bin", prog)
            if os.path.exists(c):
                prog = c

        cmd = [prog, "--version"]
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        output, _ = p.communicate()

        if p.returncode != 0:
            raise Exception("Unable to invoke %s" % cmd)

        name, version = output.split()
        return version

    def register_gratia(self, name):
        Gratia.RegisterReporter(name)

        try:
            slurm_version = self.get_slurm_version()
        except Exception, e:
            DebugPrint(0, "Unable to get SLURM version: %s" % str(e))
            raise

        Gratia.RegisterService("SLURM", slurm_version)
        Gratia.setProbeBatchManager("slurm")

class SlurmCheckpoint(object):
    """Read and write a checkpoint file
    If class is instantiated without a filename, class works as expected but
    data is not stored to disk
    """

    _val = None
    _fp  = None

    def __init__(self, target=None):
        """
        Create a checkpoint file
        target - checkpoint filename (optionally null)
        """
        if target:
            try:
                fd        = os.open(target, os.O_RDWR | os.O_CREAT)
                self._fp  = os.fdopen(fd, 'r+')
                self._val = long(self._fp.readline())
                DebugPrint(1, "Resuming from checkpoint in %s" % target)
            except IOError:
                raise IOError("Could not open checkpoint file %s" % target)
            except ValueError:
                DebugPrint(1, "Failed to read checkpoint file %s" % target)

    def get_val(self):
        """Get checkpoint value"""
        return self._val

    def set_val(self, val):
        """Set checkpoint value"""
        self._val = long(val)
        if (self._fp):
            self._fp.seek(0)
            self._fp.write(str(self._val) + "\n")
            self._fp.truncate()

    val = property(get_val, set_val)

class SlurmAcctBase(object):
    def __init__(self, conn, cluster, slurm_version):
        self._conn = conn

        cluster = re.sub('\W+', '', cluster)
        self._cluster = cluster
        self._slurm_version = slurm_version

    def completed_jobs(self, ts):
        """Completed jobs, ordered by completion time"""

        # We need *all* job_table records for jobs which completed inside the
        # time range. This needs to include jobs which were preempted and
        # resumed.
        where = '''id_job IN (
                SELECT id_job FROM %(cluster)s_job_table
                WHERE time_start > 0 AND time_end >= %(end)s
            )
        ''' % { 'cluster': self._cluster, 'end': long(ts) }

        # The job is not running and has not been requeued
        having = 'MIN(j.time_end) > 0 AND MIN(j.time_start) > 0'

        return self._jobs(where, having)

    def running_jobs(self):
        where = 'j.time_end = 0'
        return self._jobs(where)

    def running_users(self, ts=None):
        """Running jobs, grouped by user, ordered by completion time"""
        where = 'j.time_end = 0'

        # Also include users with recently ended jobs
        if ts is not None:
            where = where + " OR j.time_end >= %s" % long(ts)

        return self._users(where)

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
            r['user'] = self._get_user(r['id_user'], 'unknown')
        if r['acct'] is None:
            # Set acct to info from NSS, or unknown
            r['acct'] = self._get_group(r['id_group'], 'unknown')

class SlurmAcct_v1(SlurmAcctBase):

    def _users(self, where):
        cursor = self._conn.cursor()

        # See enum job_states in slurm/slurm.h for state values
        sql = '''SELECT j.id_user
            , j.id_group
            , (SELECT SUM(cpus_req)   FROM %(cluster)s_job_table WHERE
                  id_user = j.id_user AND state IN (0,2)) AS cpus_pending
            , (SELECT SUM(cpus_alloc) FROM %(cluster)s_job_table WHERE
                  id_user = j.id_user AND state IN (1)  ) AS cpus_running
            , MAX(j.time_end) AS time_end
            , a.acct
            , a.user
            FROM %(cluster)s_job_table as j
            LEFT JOIN %(cluster)s_assoc_table AS a ON j.id_assoc = a.id_assoc
            WHERE %(where)s
            GROUP BY j.id_user, j.id_group, a.acct, a.user
            ORDER BY time_end
        ''' % { 'cluster': self._cluster, 'where': where }

        DebugPrint(5, "Executing SQL: %s" % sql)
        cursor.execute(sql)

        for r in cursor:
            # Add handy data to job record
            r['cluster'] = self._cluster
            # Return 0 instead of None where we don't have values
            if r['cpus_pending'] is None:
                r['cpus_pending'] = 0
            if r['cpus_running'] is None:
                r['cpus_running'] = 0
            self._addUserInfoIfMissing(r)
            yield r

    def _jobs(self, where, having = '1=1'):
        cursor = self._conn.cursor()

        # Note: When jobs are preempted, multiple cluster_job_table records
        #       are inserted, each with distinct start and end times.
        #       We consider the walltime to be the total time running,
        #       adding up all the records.

        if LooseVersion(self._slurm_version) < LooseVersion("18"):
            max_rss = '''( SELECT MAX(s.max_rss)
                FROM %(cluster)s_step_table s
                WHERE s.job_db_inx = j.job_db_inx
                /* Note: Will underreport mem for jobs with simultaneous steps */
              )'''
        else:
            max_rss = '''MAX(j.mem_req)'''

        sql = '''SELECT j.id_job
            , j.exit_code
            , j.id_group
            , j.id_user
            , j.job_name
            , j.cpus_alloc
            , j.partition
            , j.state
            , MIN(j.time_start) AS time_start
            , MAX(j.time_end) AS time_end
            , SUM(j.time_suspended) AS time_suspended
            , SUM(CASE WHEN j.time_end < j.time_start + j.time_suspended
                       THEN 0
                       ELSE j.time_end - j.time_start - j.time_suspended
                  END) AS wall_time
            , a.acct
            , a.user
            , %(max_rss)s AS max_rss
            , ( SELECT SUM(s.user_sec) + SUM(s.user_usec/1000000)
                FROM %(cluster)s_step_table s
                WHERE s.job_db_inx = j.job_db_inx
              ) AS cpu_user
            , ( SELECT SUM(s.sys_sec) + SUM(s.sys_usec/1000000)
                FROM %(cluster)s_step_table s
                WHERE s.job_db_inx = j.job_db_inx
              ) AS cpu_sys
            FROM %(cluster)s_job_table as j
            LEFT JOIN %(cluster)s_assoc_table AS a ON j.id_assoc = a.id_assoc
            WHERE %(where)s
            GROUP BY j.id_job
                   , j.exit_code
                   , j.id_group
                   , j.id_user
                   , j.job_name
                   , j.cpus_alloc
                   , j.partition
                   , j.state
                   , a.acct
                   , a.user
                   , j.job_db_inx
            HAVING %(having)s
            ORDER BY j.time_end
        ''' % { 'cluster': self._cluster, 'where': where, 'having': having,
                'max_rss': max_rss }

        DebugPrint(5, "Executing SQL: %s" % sql)
        cursor.execute(sql)

        for r in cursor:
            # Add handy data to job record
            r['cluster'] = self._cluster
            self._addUserInfoIfMissing(r)
            yield r

class SlurmAcct_v2(SlurmAcctBase):

    def _parse_tres(self, tres):
        """Parse SLURM database tres_alloc job data into dict"""
        # SLURM 15 changed its job_table.cpus_alloc database column to tres_alloc
        #    and converted the data to a comma separated list of "key=value" pairs
        # Keys are defined in tres_types_t in src/common/slurmdb_defs.h
        #    1 => CPU, 2 => MEM, 3 => ENERGY, 4 => NODE

        ret = dict()

        for item in tres.split(','):
            # Skip blank entries
            if not item:
                continue

            try:
                k, v = item.split('=', 1)
                ret[int(k)] = int(v)
            except ValueError:
                # TRES string is damaged? Continuing.
                DebugPrint(1, "Error parsing TRES string '%s'" % tres)

        return ret

    def _users(self, where):
        cursor = self._conn.cursor()

        # Default GROUP_CONCAT() maximum length is 1024 chars
        # Increase it to 64MB
        cursor.execute('SET SESSION group_concat_max_len=64*1024*1024;');

        # See enum job_states in slurm/slurm.h for state values
        sql = '''SELECT j.id_user
            , j.id_group
            , (SELECT SUM(cpus_req)   FROM %(cluster)s_job_table WHERE
                  id_user = j.id_user AND state IN (0,2)) AS cpus_pending
            , (SELECT GROUP_CONCAT('|', tres_alloc) FROM %(cluster)s_job_table WHERE
                  id_user = j.id_user AND state IN (1)  ) AS tres_alloc_list
            , MAX(j.time_end) AS time_end
            , a.acct
            , a.user
            FROM %(cluster)s_job_table as j
            LEFT JOIN %(cluster)s_assoc_table AS a ON j.id_assoc = a.id_assoc
            WHERE %(where)s
            GROUP BY j.id_user, j.id_group, a.acct, a.user
            ORDER BY time_end
        ''' % { 'cluster': self._cluster, 'where': where }

        DebugPrint(5, "Executing SQL: %s" % sql)
        cursor.execute(sql)

        for r in cursor:
            # Add handy data to job record
            r['cluster'] = self._cluster

            # Extract cpus_alloc from tres_alloc and sum to get cpus_running
            # We were formerly relying on SQL to sum the cpus_alloc.
            # Now we get a list of tres_alloc parameters, parse them, and sum
            # the CPU count ourselves.
            r['cpus_running'] = 0
            if r['tres_alloc_list']:
                for tres_txt in r['tres_alloc_list'].split('|'):
                    tres = self._parse_tres(tres_txt)
                    # tres_types_t.TRES_CPU = 1
                    r['cpus_running'] += tres.get(1, 0)

            # Return 0 instead of None where we don't have values
            if r['cpus_pending'] is None:
                r['cpus_pending'] = 0
            self._addUserInfoIfMissing(r)
            yield r

    def _jobs(self, where, having = '1=1'):
        cursor = self._conn.cursor()

        # Note: When jobs are preempted, multiple cluster_job_table records
        #       are inserted, each with distinct start and end times.
        #       We consider the walltime to be the total time running,
        #       adding up all the records.

        if LooseVersion(self._slurm_version) < LooseVersion("18"):
            max_rss = '''( SELECT MAX(s.max_rss)
                FROM %(cluster)s_step_table s
                WHERE s.job_db_inx = j.job_db_inx
                /* Note: Will underreport mem for jobs with simultaneous steps */
              )'''
        else:
            max_rss = '''MAX(j.mem_req)'''

        sql = '''SELECT j.id_job
            , j.exit_code
            , j.id_group
            , j.id_user
            , j.job_name
            , j.tres_alloc
            , j.partition
            , j.state
            , MIN(j.time_start) AS time_start
            , MAX(j.time_end) AS time_end
            , SUM(j.time_suspended) AS time_suspended
            , SUM(CASE WHEN j.time_end < j.time_start + j.time_suspended
                       THEN 0
                       ELSE j.time_end - j.time_start - j.time_suspended
                  END) AS wall_time
            , a.acct
            , a.user
            , %(max_rss)s AS max_rss
            , ( SELECT SUM(s.user_sec) + SUM(s.user_usec/1000000)
                FROM %(cluster)s_step_table s
                WHERE s.job_db_inx = j.job_db_inx
              ) AS cpu_user
            , ( SELECT SUM(s.sys_sec) + SUM(s.sys_usec/1000000)
                FROM %(cluster)s_step_table s
                WHERE s.job_db_inx = j.job_db_inx
              ) AS cpu_sys
            FROM %(cluster)s_job_table as j
            LEFT JOIN %(cluster)s_assoc_table AS a ON j.id_assoc = a.id_assoc
            WHERE %(where)s
            GROUP BY j.id_job
                   , j.exit_code
                   , j.id_group
                   , j.id_user
                   , j.job_name
                   , j.tres_alloc
                   , j.partition
                   , j.state
                   , a.acct
                   , a.user
                   , j.job_db_inx
            HAVING %(having)s
            ORDER BY j.time_end
        ''' % { 'cluster': self._cluster, 'where': where, 'having': having,
                'max_rss': max_rss }

        DebugPrint(5, "Executing SQL: %s" % sql)
        cursor.execute(sql)

        for r in cursor:
            # Add handy data to job record
            r['cluster'] = self._cluster

            # Extract cpus_alloc from tres_alloc
            tres = self._parse_tres(r['tres_alloc'])
            r['cpus_alloc'] = tres.get(1, 0) # tres_types_t.TRES_CPU = 1

            self._addUserInfoIfMissing(r)
            yield r
