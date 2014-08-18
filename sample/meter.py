
#!/usr/bin/python
# /* vim: set expandtab tabstop=4 shiftwidth=4 softtabstop=4: */

###########################################################################
# slurm_meter_running
#
# Python-based Gratia probe for SLURM accounting database
# This probe reports ComputeElementRecords for running and waiting jobs
# 
# John Thiltges, 2012-Jun-19
# Based on condor_meter by Brian Bockelman
# 
# Copyright 2012 University of Nebraska-Lincoln. Released under GPL v2.
###########################################################################

import sys, os, stat
import time, random
import pwd, grp

from gratia.common.Gratia import DebugPrint
import gratia.common.GratiaWrapper as GratiaWrapper
import gratia.common.Gratia as Gratia

import MySQLdb
import MySQLdb.cursors
import re

prog_version = "%%%RPMVERSION%%%"
prog_revision = '$Revision$'

class GratiaProbe:

    # Constants (defined to avoid different spellins/cases)
    UNKNOWN = "unknown"

    opts       = None
    args       = None
    checkpoint = None
    conn       = None
    cluster    = None
    sacct      = None
    # probe name, e.g. slurm_meter 
    #TODO: get it form config?
    probe_name = "gratia_probe"

    def __init__(self, probe_name=None):
        try:
            self.opts, self.args = self.parse_opts()
        except Exception, e:
            print >> sys.stderr, str(e)
            sys.exit(1)

        if probe_name:
            self.probe_name = probe_name

        self.default_config = "/etc/gratia/%s/ProbeConfig" % self.probe_name


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

        self.register_gratia(self.probe_name)

        # Find the checkpoint filename (if enabled)
        if self.opts.checkpoint:	
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

    def start(self)

        # Initialize input
        # input must specify which parameters it requires form the config file
        self.probeinput = ProbeInput()
        input_parameters = self.probeinput.get_init_params()
        input_ini = self.get_config_params(input_parameters)

        # Connect to database

        self.cluster = Gratia.Config.getConfigAttribute('SlurmCluster')
        self.sacct = SlurmAcct(self.conn, self.cluster)


    # convenience functions

    def get_config_params(param_list):
        """Return a dictionary containing the values of a list of parameters"""
        #TODO: would an array be much more efficient?
        #TODO: check what happens if the parameter is not in the config file. Ideally None is returned
        retv = {}
        for param in param_list:
            retv[param] = Gratia.Config.getConfigAttribute(param)
        return retv

    def parse_opts(self):
        """Hook to parse command-line options"""
        return

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
        if self.probeinput:
            try:
                input_version = self.probeinput.get_version()
            except Exception, e:
                DebugPrint(0, "Unable to get input version: %s" % str(e))
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
        except Exception, e:
            DebugPrint(0, "Unable to get input version: %s" % str(e))
            raise

        # TODO: check the meaning of RegisterReporter vs RegisterService
        Gratia.RegisterService(self.probeinput.get_name(), input_version)

        # TODO: check which attributes need to ne set here (and not init)
        # and which attributes are mandatori vs optional
        #Gratia.setProbeBatchManager("slurm")




from SlurmProbe import SlurmProbe

import optparse
import datetime

import gratia.common.Gratia as Gratia
import gratia.services.ComputeElement as ComputeElement
import gratia.services.ComputeElementRecord as ComputeElementRecord


class GratiaMeter(GratiaProbe):
    # Default configuration file, choose RPM location
    default_config="/etc/gratia/slurm/ProbeConfig"

    def get_opts_parser(self):
        # this is not needed but for clarity
        parser = None
        try:
            # child classes will use the parent parser instead:
            parser = super.get_opts_parser()
        except AttributeError:
            # base class initializes the parser
            parser = optparse.OptionParser(usage="%prog [options]")


        # add (other) options
        parser.add_option("-f", "--gratia_config", help="Location of the Gratia"
            " config [default: %default].",
            dest="gratia_config", default=self.default_config)
        parser.add_option("-s", "--sleep", help="Do a random amount of sleep, "
            "up to the specified number of seconds before running.",
            dest="sleep", default=0, type="int")
        parser.add_option("-v", "--verbose", help="Enable verbose logging to "
            "stdout.",
            default=False, action="store_true", dest="verbose")
        parser.add_option("-c", "--checkpoint", help="Only reports records past"
            " checkpoint; default is to report all records.",
            default=False, action="store_true", dest="checkpoint")
        return parser

    def parse_opts(self, options=None):
        parser = self.get_opts_parser()
        # Options are stored into opts/args class variables
        return parser.parse_args()

    def main(self):
        # Loop over completed jobs
        time_end = None
        server_id = self.get_db_server_id()
        for job in self.sacct.completed_jobs(self.checkpoint.val):
            r = job_to_jur(job, server_id)
            Gratia.Send(r)

            # The query sorted the results by time_end, so our last value will
            # be the greatest
            time_end = job['time_end']
            self.checkpoint.val = time_end

        # If we found at least one record, but the time_end has not increased since
        # the previous run, increase the checkpoint by one so we avoid continually
        # reprocessing the last records.
        # (This assumes the probe won't be run more than once per second.)
        if self.checkpoint.val == time_end:
            self.checkpoint.val = time_end + 1

if __name__ == "__main__":
    GratiaMeter().main()
