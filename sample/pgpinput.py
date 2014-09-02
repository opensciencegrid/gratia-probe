#!/usr/bin/python


import sys
import traceback

# For PostgresSQL
import psycopg2
import psycopg2.extras

from gratia.common.Gratia import DebugPrint

from probeinput import DbInput



class PgInput(DbInput):
    """PostgreSQL input
    Database name, host, user are mandatory parameters. Port (5432) and password are optional
    """

    def __init__(self, conn=None):
        DbInput.__init__(self)
        self._cursor = None
        if conn:
            self._connection = conn
        else:
            self._connection = None

    def open_db_conn(self):
        """Return a database connection"""
        #  PG Defaults in libpq connection string / dsn parameters:
        #  DbUser,user: same as UNIX user
        #  DbName,dbname: DbUser
        #  DbHost,host: UNIX socket
        #  DbPort,port: 5432
        # Other optional PG parameters:
        # http://www.postgresql.org/docs/current/static/libpq-connect.html#LIBPQ-PARAMKEYWORDS
        dburl = 'dbname=%s user=%s host=%s' % (
                self._static_info['DbName'],
                self._static_info['DbUser'],
                self._static_info['DbHost'] )
        if self._static_info['DbPort']:
            dburl += ' port=%s' % self._static_info['DbPort']
        if self._static_info['DbPassword']:
            dburl += ' password=%s' % self._static_info['DbPassword']
        DebugPrint(4, "Connecting to PgSQL database: %s" % dburl)
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
            # Masking connection failure
            #self._connection = None
        return self._connection
        
    def query(self, sql):
        if not sql:
            DebugPrint(2, "WARNING: No SQL provided: no query.")
            return
        if not self._connection:
            DebugPrint(2, "WARNING: No connection provided: no query.")
            return
        cursor = self._connection.cursor(cursor_factory=psycopg2.extras.DictCursor)
        DebugPrint(4, "Executing SQL: %s" % sql)
        cursor.execute(sql)
        if cursor.rowcount is None:
            DebugPrint(2, "WARNING, problems running the query: %s" % sql)
        elif cursor.rowcount<=0:
            DebugPrint(2, "WARNING, no rows returned by the query: %s" % sql)
        # resultset = self._cur.fetchall()
        for r in cursor:
            yield r


