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

    def close_db_conn(self):
        """Explicitly close the connection.
        Connection is closed automatically at del
        """
        # NOTE: uncommitted operations are rolled back but inputs are read only
        if self._connection is not None:
            if self._cursor is not None:
                try:
                    self._cursor.close()
                except psycopg2.InterfaceError:
                    # was already closed
                    pass
                self._cursor = None
            try:
                self._connection.close()
            except psycopg2.InterfaceError:
                # was already closed
                pass
            self._connection = None

    def status_ok(self):
        """Return True if OK, False if the connection is closed"""
        if self._connection is None or self._cursor is None:
            return False
        # TODO: do a select 1 test? The only way to really test
        # try:
        #    self._cursor.execute("SELECT 1")
        #    return True
        #except:
        #    return False
        return True

    def status_string(self):
        """Return a string describing the current status"""
        if self._connection is None:
            return "NOT CONNECTED"
        if self._cursor is None:
            return "NO CURSOR"
        retv = "CONNECTED"
        trans_status = self._cursor.get_transaction_status()
        trans_string = ""
        if trans_status == psycopg2.extensions.STATUS_READY:
            trans_string = "STATUS_READY"
        elif trans_status == psycopg2.extensions.STATUS_BEGIN:
            trans_string = "STATUS_BEGIN"
        elif trans_status == psycopg2.extensions.STATUS_IN_TRANSACTION:
            trans_string = "STATUS_IN_TRANSACTION"
        elif trans_status == psycopg2.extensions.STATUS_PREPARED:
            trans_string = "STATUS_PREPARED"
        if trans_status is not None:
            retv = "%s (%s/%s)" % (retv, trans_status, trans_string)
        
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


