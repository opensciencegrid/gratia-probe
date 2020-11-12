# Copyright 2007 Cornell University, Ithaca, NY. All rights reserved.
#
# Author:  Gregory J. Sharp
#
# This stores a checkpoint to a file to remember which record was last sent
# to the Gratia repository. This allows us to begin searching from this
# checkpoint after a restart of the probe.

from __future__ import print_function

import os
import logging
import stat
import pickle
from datetime import datetime, timedelta


class Checkpoint:
    """
    This attempts to record a checkpoint to remember the last record read
    from a database table.
    This code is not thread safe. It is only suitable for the dCache
    aggregation system.
    """
    # The epoch timestamp is 1990/Jan/01 at midnight
    # This predates all possible log entries in the dCache billing db.
    _dateStamp = datetime(1990, 1, 1, 0, 0, 0, 0, None)
    _transaction = ""
    _pending_dateStamp = None
    _pending_transaction = None
    _pending = False

    def __init__(self, tablename, maxAge=30):
        """
        Tablename is the name of the table in db for which we are keeping
        a checkpoint. It is used to locate the file with the pickled record
        of the last checkpoint.
        """
        self._tablename = tablename
        self._tmpFile = tablename + ".pending"

        now = datetime.now()
        now = datetime(now.year, now.month, now.day, 0, 0, 0)
        minDay = now - timedelta(maxAge, 0)

        try:
            pklFile = open(tablename, 'rb')
            self._dateStamp, self._transaction = pickle.load(pklFile)
            if self._dateStamp < minDay:
                self._dateStamp = minDay
            ds = self._dateStamp
            self._dateStamp = datetime(ds.year, ds.month, ds.day, ds.hour, 0, 0)
            pklFile.close()
        except IOError as xxx_todo_changeme1:
            # This is not really an error, since it might be the first
            # time we try to make this checkpoint.
            # We log a warning, just in case some nice person has
            # deleted the checkpoint file.
            (errno, strerror) = xxx_todo_changeme1.args
            # This is not really an error, since it might be the first
            # time we try to make this checkpoint.
            # We log a warning, just in case some nice person has
            # deleted the checkpoint file.
            log = logging.getLogger('DCacheAggregator')
            msg = "Checkpoint: couldn't read %s: %s." % \
                  (tablename, strerror)
            msg += "\nThis is okay the first time you run the probe."
            log.warn(msg)
            self._dateStamp = minDay


    def createPending(self, datestamp, txn):
        """
        Saves the specified primary key string as the new checkpoint.
        """
        if datestamp == None or txn == None:
            raise IOError("Checkpoint.createPending was passed null values")

        # Get rid of extant pending file, if any.
        try:
            os.chmod(self._tmpFile, stat.S_IWRITE)
            os.unlink(self._tmpFile)
        except:
            pass # no problem if it isn't there.
        dir, file = os.path.split(self._tmpFile)
        if not os.path.exists(dir):
            try:
                os.makedirs(dir)
            except IOError as xxx_todo_changeme:
                (errno, strerror) = xxx_todo_changeme.args
                print("Checkpoint.save: IOError creating directory %s: %s" % \
                    (dir, strerror))
                raise
        # Create new pending file.
        try:
            pklFile = open(self._tmpFile, 'wb')
            pickle.dump([datestamp, txn], pklFile, -1)
            pklFile.close()
            self._pending = True
            self._pending_dateStamp = datestamp
            self._pending_transaction = txn
        except IOError as xxx_todo_changeme2:
            (errno, strerror) = xxx_todo_changeme2.args
            print("Checkpoint.save: IOError creating file %s: %s" % \
                (self._tmpFile, strerror))
            raise


    def commit(self):
        """
        We created the tmp file. Now make it the actual file with an atomic
        rename.
        We make the file read-only, in the hope it will reduce the risk
        of accidental/stupid deletion by third parties.
        """
        if not self._pending:
            raise IOError("Checkpoint.commit called with no transaction")

        self._pending = False
        try:
            if os.path.exists(self._tablename):
                os.chmod(self._tablename, stat.S_IWRITE)
            os.rename(self._tmpFile, self._tablename)
            os.chmod(self._tablename, stat.S_IREAD)
            self._dateStamp = self._pending_dateStamp
            self._transaction = self._pending_transaction
        except OSError as xxx_todo_changeme3:
            (errno, strerror) = xxx_todo_changeme3.args
            print("Checkpoint.save could not rename %s to %s: %s" % \
                  (self._tmpFile, self._tablename, strerror))
            raise


    def lastDateStamp(self):
        """
        Returns last stored dateStamp. It returns the epoch, if there is no
        stored checkpoint.
        """
        return self._dateStamp


    def lastTransaction(self):
        """
        Returns last stored transaction id. It returns the empty string if
        there is no stored checkpoint.
        """
        return self._transaction

# end class Checkpoint
