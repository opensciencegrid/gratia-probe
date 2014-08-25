#!/usr/bin/python


import sys
import traceback

# For Postgress
import psycopg2
import psycopg2.extras

from gratia.common.Gratia import DebugPrint

from probeinput import DbInput



class PgInput(DbInput):
    """Postgress input
    """

    def __init__(self, conn=None):
        DbInput.__init__(self)
        self._cursor = None
        if conn:
            self._connection = conn

    def open_db_conn(self):
        """Return a database connection"""
        dburl = 'dbname=%s user=%s password=%s host=%s' % (
            self._static_info['DbName'],
            self._static_info['DbUser'],
            self._static_info['DbPassword'],
	    self._static_info['DbHost'] )
        try:
            self._connection = psycopg2.connect(dburl)
            self._cursor = self._connection.cursor(cursor_factory=psycopg2.extras.DictCursor)
        except:
            tblist = traceback.format_exception(sys.exc_type,
                                                sys.exc_value,
                                                sys.exc_traceback)
            errmsg = 'Failed to connect to %s:\n%s' % (dburl, "\n".join(tblist))
            DebugPrint(1, errmsg)
            raise
        return self._connection
        
    def query(self, sql):
        if not sql:
            DebugPrint(5, "No SQL provided: no query.")
            return            
        cursor = self._connection.cursor(cursor_factory=psycopg2.extras.DictCursor)
        DebugPrint(5, "Executing SQL: %s" % sql)
        cursor.execute(sql)
        # resultset = self._cur.fetchall()
        for r in cursor:
            yield r


