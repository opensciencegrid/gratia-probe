#!/usr/bin/python

# inputs for probes

import os
import re  # re to parse rpm -q output
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
                DebugPrint(3, "Resuming from checkpoint in %s" % target)
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
        if self._fp:
            self._fp.seek(0)
            self._fp.write(str(self._val) + "\n")
            self._fp.truncate()

    val = property(get_val, set_val)

    date = get_val

    def transaction(self):
        return None

class DBInputCheckpoint(InputCheckpoint):
    """Read and write a checkpoint file
    Checkpoint value is number of seconds from epoch
    If class is instantiated without a filename, class works as expected but
    data is not stored to disk
    """
    _dbval = []

    def set_dbval(self, name, val, expression="%s > %s"):
        dbval = { 'name': name,
                  'value': val,
                  'expression': expression
        }
        self._dbval.append(dbval)

    def get_where(self):
        try:
            ret_list = [i['expression'] % (i['name'], i['value']) for i in self._dbval]
            retval = " AND ".join(ret_list)
        except:
            return ""
        return retval

    def get_select(self):
        return ""


class ProbeInput(object):
    """Abstract probe input interface
    Includes some utility functions
    """

    UNKNOWN = "unknown"

    def __init__(self):
        self.checkpoint = None
        self._version = None

        # Filter static info if needed
        self._static_info = {'version': None}

    def add_checkpoint(self, fname=None):
        self.checkpoint = InputCheckpoint(fname)

    def do_test(self, static_info=None):
        """Prepare the input for testing, e.g. replacing some methods with stubs,
        increasing verbosity, limiting actions, ...
        Invoked after init (object has been created and initialized) and before start
        (static_info from config file not passed, final initialization not done) and get_records
        """
        DebugPrint(4, "ProbeInput test invoked but not defined")
        pass

    def start(self, static_info):
        """Initialize and start the input"""
        self.add_static_info(static_info)

    def stop(self):
        """Stop and cleanup the input:
        - release memory (caches, ...)
        - delete objects, invoke finalize
        - close connections
        - stop worker threads
        - ...
        Possibly these should happen automatically withous explicit invocation
        """
        pass

    def status_ok(self):
        """Return True if OK, False if the connection is closed"""
        return False

    def status_string(self):
        """Return a string describing the current status"""
        return ""

    def get_init_params(self):
        """Return list of parameters to read form the config file"""
        return []

    def add_static_info(self, static_info):
        if not static_info:
            return
        for k in static_info:
            if k in self._static_info:
                DebugPrint(4, "Updating probe %s from %s to %s" %
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
        # or fetch all records and use yield to return them one at the time

    def recover_records(self, start_time=None, end_time=None):
        """Recover all records in the selected time interval. Ignore the checkpoint
        """
        return None

    def _set_version_config(self, value):
        """Set the version provided by the config file (used only as fallback)"""
        self._static_info['version'] = value

    def _get_version(self, rpm_package_name=None, version_command=None, version_command_filter=None):
        """Get program version looking in order for:
        0. self._version (caching the value form previous executions)
        1. rpm -q
        2. the output of version_command filtered by version_command_filter
        3. the value in the config file (stored in self._static_info['version']
        This is a protected method
        """
        DebugPrint(5, "Called get_version (%s, %s; %s, %s, %s)" % (self._version, self._static_info['version'], rpm_package_name,
                                                               version_command, version_command_filter))
        if self._version:
            return self._version
        if rpm_package_name:
            # Use RPM version, as specified in
            # http://fedoraproject.org/wiki/Packaging%3aNamingGuidelines#Package_Versioning
            # rpm --queryformat "%{NAME} %{VERSION} %{RELEASE} %{ARCH}" -q
            # %% to escape %
            fd = os.popen('rpm --queryformat "%%{NAME} %%{VERSION} %%{RELEASE} %%{ARCH}" -q %s' % rpm_package_name)
            version = fd.read()
            if fd.close():
                DebugPrint(4, "Unable to invoke rpm to retrieve the %s version" % rpm_package_name)
                #raise Exception("Unable to invoke rpm to retrieve version")
            else:
                rpm_version_re = re.compile("^(.*)\s+(.*)\s+(.*)\s+(.*)$")
                m = rpm_version_re.match(version.strip())
                if m:
                    self._version = "%s-%s" % (m.groups()[1], m.groups()[2])
                    return self._version
                DebugPrint(4, "Unable to parse the %s version from 'rpm -q'" % rpm_package_name)
        if version_command:
            # Use version command
            fd = os.popen(version_command)
            version = fd.read()
            if fd.close():
                DebugPrint(4, "Unable to invoke '%s' to retrieve the version" % version_command)
                #raise Exception("Unable to invoke command")
            else:
                if version_command_filter:
                    version = version_command_filter(version.strip())
                if version:
                    self._version = version
                    return self._version
                DebugPrint(4, "Unable to parse the version from '%s'" % version_command)
        # If other fail try the version attribute
        retv = self._static_info['version']
        if not retv:
            DebugPrint(2, "Unable to retrieve the ProbeInput (%s) version" % type(self).__name__)
            # raise Exception("Unable to parse condor_version output: %s" % version)
            return ProbeInput.UNKNOWN
        self._version = retv
        return retv

    def get_version(self):
        """Return the input version (LRM version, server version). Normally form an external program.
        This is not the probe version"""
        #For error:    raise Exception("Unable to invoke %s" % cmd)
        DebugPrint(2, "Called ProbeInput get_version instead of the Probe specific one.")
        return ProbeInput.UNKNOWN

    def get_name(self):
        return ProbeInput.UNKNOWN




class DbInput(ProbeInput):
    """Database input
    """

    def __init__(self):
        """First initialization. Config file values are available only for start, not here"""
        ProbeInput.__init__(self)
        # this is not used here, define it in child classes:  self._connection = None

    def get_init_params(self):
        """Return list of parameters to read form the config file"""
        return ['DbHost', 'DbPort', 'DbName', 'DbUser', 'DbPassword', 'DbPasswordFile']

    def start(self, static_info):
        """start: initialize adding values coming form the config file and connect to the database"""
        # Protecting for missing optional parameters
        for i in ['DbPort', 'DbPassword', 'DbPasswordFile']:
            if not i in static_info:
                static_info[i] = ""
        if static_info['DbPasswordFile'] and not static_info['DbPassword']:
            static_info['DbPassword'] = self.get_password(static_info['DbPasswordFile'])
        self.add_static_info(static_info)
        # Connect to DB
        self.open_db_conn()

    def stop(self):
        """stop: close the DB connection if any. It should be idempotent"""
        self.close_db_conn()

    def open_db_conn(self):
        """Open the Database connection"""
        pass

    def close_db_conn(self):
        """Close the Database connection"""
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




