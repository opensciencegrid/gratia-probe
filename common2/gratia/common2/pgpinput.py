#!/usr/bin/python


import sys
import traceback

# For PostgresSQL
import psycopg2
import psycopg2.extras
try:
    import uuid  # for unique cursor name
except ImportError:
    # for python < 2.5 (uuid not available)
    import uuid_replacement as uuid

from gratia.common.Gratia import DebugPrint

from probeinput import DbInput


class PgInput(DbInput):
    """PostgreSQL input
    Database name, host, user are mandatory parameters. Port (5432) and password are optional

    Type conversion is done by psycopg2:
    http://initd.org/psycopg/docs/usage.html

    *Python	*PostgreSQL
    None	NULL
    bool	bool
    float   real, double
    int     smallint
    long    integer, bigint
    Decimal numeric
    str     varchar
    unicode text
    buffer, memoryview, bytearray, bytes, Buffer protocol   bytea
    date	date
    time	time
    datetime    timestamp, timestamptz
    timedelta	interval
    list	ARRAY
    tuple, namedtuple   Composite types
    dict	hstore
    Psycopg's Range	range
    Anything(TM)	json
    uuid	uuid
    """

    def __init__(self, conn=None):
        DbInput.__init__(self)
        # PsycoPG 2.4 or greater support itersize, so that iterable named cursor
        # is not fetching only 1 row at the time
        self.support_itersize = True
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
            self._cursor = self._get_cursor(self._connection)
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

    def _get_cursor(self, connection, buffer_size=None):
        """Return a cursor for the given connection

        :param connection: PG connection
        :param buffer_size: size used when fetching resultsets (None for the default one)
        :return: cursor
        """
        # give the cursor a unique name which will invoke server side cursors
        # TODO: should this be unique each time or for input?
        cursor = connection.cursor(name='cur%s' % str(uuid.uuid4()).replace('-', ''),
                                   cursor_factory=psycopg2.extras.DictCursor)
        #cursor.tzinfo_factory = None
        if not buffer_size:
            cursor.arraysize = self._max_select_mem()
        else:
            cursor.arraysize = buffer_size
        try:
            cursor.itersize = cursor.arraysize
        except AttributeError:
            self.support_itersize = False
        return cursor

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
        """Generator returning one row at the time as pseudo-dictionary (DictCursor)
        psycopg2.extras.DictCursor is a tuple, accessible by indexes and returned as
        values, not keys, in a loop (for i in row) but row.keys() lists the columns
        and row['column_name'] accesses the column.
        It is compatible w/ standard cursors
        For proper dictionary see psycopg2.extras.RealDictCursor
        NOTE that the values are not mutable (cannot be changed)

        :param sql: string w/ the SQL query
        :return: row as psycopg2.extras.DictCursor (tuple and dictionary)
        """
        if not sql:
            DebugPrint(2, "WARNING: No SQL provided: no query.")
            return
        if not self._connection:
            DebugPrint(4, "WARNING: No connection provided: trying to (re)open connection.")
            if not self.open_db_conn():
                DebugPrint(2, "WARNING: Unable to open connection: no query.")
            return
        if not self._cursor:
            self._cursor = self._get_cursor(self._connection)
            if not self._cursor:
                DebugPrint(2, "WARNING: Unable to get cursor: no query.")
                return
        cursor = self._cursor
        DebugPrint(4, "Executing SQL: %s" % sql)
        try:
            cursor.execute(sql)
        except psycopg2.ProgrammingError, er:
            DebugPrint(2, "ERROR, error running the query: %s" % er)
        if cursor.rowcount is None:
            DebugPrint(2, "WARNING, problems running the query: %s" % sql)
        elif cursor.rowcount <= 0:
            DebugPrint(3, "WARNING, no rows returned by the query (rowcount: %s). OK for iterators." %
                       cursor.rowcount)
        # resultset = self._cur.fetchall()
        if self.support_itersize:
            for r in cursor:
                yield r
        else:
            # implement itersize manually (for psycopg < 2.4)
            # normal iteration would be inefficient fetching one record at the time
            while True:
                resultset = cursor.fetchmany()
                if not resultset:
                    break
                for r in resultset:
                    yield r
