#!/usr/bin/python

# inputs for probes


from gratia.common.Gratia import DebugPrint

from probeinput import DbInput


# for mysql probe
import MySQLdb
import MySQLdb.cursors
import re

class MySQLInput(ProbeInput):
    """MySQL input
    """

    def __init__(self, conn=None):
        if conn:
            self._connection = conn

    def open_db_conn(self):
        """Return a database connection"""
        self._connection = MySQLdb.connect(
            host   = self.static_info['DbHost'],
            port   = int(self.static_info['DbPort']),
            user   = self.static_info['DbUser'],
            passwd = self.static_info['DbPassword'],
            db     = self.static_info['DbName'],
            cursorclass = MySQLdb.cursors.SSDictCursor)
        return self._connection

    def query(self, sql):
        if not sql:
            DebugPrint(5, "No SQL provided: no query.")
            return            
        cursor = self._conn.cursor()
        DebugPrint(5, "Executing SQL: %s" % sql)
        cursor.execute(sql)
        for r in cursor:
            # Add handy data to job record
            r['cluster'] = self._cluster
            self._addUserInfoIfMissing(r)
            yield r



