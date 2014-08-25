#!/usr/bin/python

# inputs for probes

import os
import stat
import pwd, grp   # for user utility

from gratia.common.Gratia import DebugPrint


class IgnoreRecordException(Exception):
    """Allows to skip code when ignoring a record
    """


class InputCheckpoint(object):
    """Read and write a checkpoint file
    Checkpoint value is number of seconds from epoch
    If class is instantiated without a filename, class works as expected but
    data is not stored to disk
    """
    #TODO: long int is OK for all?

    _val = None
    _fp  = None

    def __init__(self, target=None):
        """
        Create a checkpoint file
        target - checkpoint filename (optionally null)
        """
        if target:
            try:
                fd = os.open(target, os.O_RDWR | os.O_CREAT)
                self._fp = os.fdopen(fd, 'r+')
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

    date = get_val

    def transaction(self):
        return None


class ProbeInput(object):
    """Abstract probe input interface
    Includes some utility functions
    """

    UNKNOWN = "unknown"

    def __init__(self):
        self.checkpoint = None

        # Filter static info if needed
        self._static_info = None


    def add_checkpoint(self, fname=None):
        self.checkpoint = InputCheckpoint(fname)

    def start(self, static_info):
        self._static_info = static_info

    def add_static_info(self, static_info):
        if not static_info:
            return
        for k in static_info:
            if k in self._static_info:
                DebugPrint(5, "Updating probe %s from %s to %s" % 
                    (k, self._static_info[k], static_info[k]))
            self._static_info[k] = static_info[k]

    # Utility functions
    ## User functions 
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
            r['user'] = self._get_user(r['id_user'], ProbeInput.UNKNOWN)
        if r['acct'] is None:
            # Set acct to info from NSS, or unknown
            r['acct'] = self._get_group(r['id_group'], ProbeInput.UNKNOWN)

    # Main functions, implemented by the child class
    def get_records(self):
        """Return one iterators with all the records from the checkpoint on
        """
        return None
        # fetch one record at the time
        # or fetch all records and use yeld to return them one at the time

    def recover_records(self, start_time=None, end_time=None):
        """Recoever all records in the selected time interval. Ignore the checkpoint
        """
        return None

    def get_version(self):
        """Return the input version (LRM version, server version). Normally form an external program.
        This is not the probe version"""
        #For error:    raise Exception("Unable to invoke %s" % cmd)
        return ProbeInput.UNKNOWN

    def get_name(self):
        return ProbeInput.UNKNOWN



class DbInput(ProbeInput):
    """Database input
    """

    def __init__(self):
        ProbeInput.__init__(self)
        self._connection = None

    def get_init_params(self):
        """Return list of parameters to read form the config file"""
        return ['DbHost', 'DbPort', 'DbName', 'DbUser', 'DbPassword', 'DbPasswordFile']

    def start(self, static_info):
        """start: connect to the database"""
        self._static_info = static_info
        if static_info['DbPasswordFile'] and not static_info['DbPassword']:
            static_info['DbPassword'] = self.get_password(static_info['DbPasswordFile'])
        self.open_db_conn()

    def open_db_conn(self):
        pass

    def get_password(self, pwfile):
        """Read a password from a given file, checking permissions"""
        fp = open(pwfile)
        mode = os.fstat(fp.fileno()).st_mode

        if (stat.S_IMODE(mode) & (stat.S_IRGRP | stat.S_IROTH)) != 0:
            # Exception if permissions are too loose
            raise IOError("Password file %s is readable by group or others" %
                pwfile)

        return fp.readline().rstrip('\n')

    def get_db_server_id(self):
        """Return database server ID: server/port/database"""
        return "/".join([
            self.static_info['DbHost'],
            self.static_info['DbPort'],
            self.static_info['DbName'], ])




