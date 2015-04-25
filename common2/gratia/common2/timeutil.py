#!/usr/bin/python
# /* vim: set expandtab tabstop=4 shiftwidth=4 softtabstop=4: */
__author__ = 'marcom'

###########################################################################
#
# TODO: support microseconds
# time supports only seconds (no milli/microseconds)
# datetime does have microseconds resolution
# Some systems have microseconds resolution
# e.g. Postgresql: http://www.postgresql.org/docs/9.2/static/functions-datetime.html
# This module uses time
# Some useful functions in datetime are available only starting with Python 2.5
# This is compatible with Python 2.4
#
###########################################################################

# Standard libraries
import os
import time
from datetime import datetime, timedelta, tzinfo
import calendar

# Gratia libraries
try:
    from gratia.common.debug import DebugPrint
except ImportError:
    def DebugPrint(val, msg):
        print ("DEBUG LEVEL %s: %s" % (val, msg))



### Auxiliary functions

# TODO: how are fractional system/user times handled?
def total_seconds(td, positive=True):
    """
    Returns the total number of seconds in a time interval
    :param td: time interval (datetime.timedelta)
    :param positive: if True return only positive values (or 0) - default: False
    :return: number of seconds (int)
    """
    # More accurate: (td.microseconds + (td.seconds + td.days * 24 * 3600) * 10**6) / 10**6
    # Only int # of seconds is needed
    retv = long(td.seconds + td.days * 24 * 3600)
    if positive and retv < 0:
        return 0
    return retv


def total_seconds_precise(td, positive=True):
    """
    Returns the total number of seconds in a time interval
    :param td: time interval (datetime.timedelta)
    :param positive: if True return only positive values (or 0) - default: False
    :return: number of seconds (float)
    """
    # More accurate: (td.microseconds + (td.seconds + td.days * 24 * 3600) * 10**6) / 10**6
    # Only int # of seconds is needed
    retv = long(td.seconds + td.days * 24 * 3600 + td.microseconds/1e6)
    if positive and retv < 0:
        return 0
    return retv

try:
    # string formatter is available from py 2.6
    from string import Formatter

    def strfdelta(tsec, format_str="P", format_no_day="PT{H}H{M}M{S}S", format_zero="PT0S"):
        """Formatting the time duration
        Duration ISO8601 format (PnYnMnDTnHnMnS): http://en.wikipedia.org/wiki/ISO_8601
        Choosing the format P[nD]TnHnMnS where days is the total number of days (if not 0), 0 values may be omitted,
        0 duration is PT0S

        :param tsec: float, number of seconds
        :param format_str: Format string, ISO 8601 is "P{D}DT{H}H{M}M{S}S". Default is a format string "P": will
            use ISO 8601 but skip elements that have 0 value, e.g. P1H7S instead of P1H0M7S
        :param format_no_day: Format string,  ISO 8601, default "PT{H}H{M}M{S}S"
        :param format_zero: format for when tsec is 0 or None, default "PT0S"
        :return: Formatted time duration
        """
        if not tsec:
            # 0 or None
            return format_zero

        f = Formatter()
        d = {}
        l = {'D': 86400, 'H': 3600, 'M': 60, 'S': 1}
        rem = long(tsec)

        if format_str == "P":
            # variable format
            if 0 < tsec < 86400:
                format_str = "PT"
            for i in ('D', 'H', 'M', 'S'):
                if i in l.keys():
                    d[i], rem = divmod(rem, l[i])
                    if d[i] != 0:
                        format_str = "%s{%s}%s" % (format_str, i, i)
        else:
            if 0 < tsec < 86400:
                format_str = format_no_day
            k = map(lambda x: x[1], list(f.parse(format_str)))

            for i in ('D', 'H', 'M', 'S'):
                if i in k and i in l.keys():
                    d[i], rem = divmod(rem, l[i])

        return f.format(format_str, **d)

except ImportError:
    # pre 2.6
    def strfdelta(tsec, format_str="P", format_no_day="PT%(H)dH%(M)dM%(S)dS", format_zero="PT0S"):
        """Formatting the time duration
        Duration ISO8601 format (PnYnMnDTnHnMnS): http://en.wikipedia.org/wiki/ISO_8601
        Choosing the format P[nD]TnHnMnS where days is the total number of days (if not 0), 0 values may be omitted,
        0 duration is PT0S

        :param tsec: float, number of seconds
        :param format_str: Format string, default is ISO 8601 "P", "P%(D)dDT%(H)dH%(M)dM%(S)dS"
            with 0 values skipped; use "P%(D)dDT%(H)dH%(M)dM%(S)dS" to have 0s kept in the string
        :param format_no_day: Format string,  ISO 8601, default "PT%(H)dH%(M)dM%(S)dS"
        :param format_zero: format for when tsec is 0 or None, default "PT0S"
        :return: Formatted time duration
        """
        if not tsec:
            # 0 or None
            return format_zero
        d = {}
        l = {'D': 86400, 'H': 3600, 'M': 60, 'S': 1}
        rem = long(tsec)

        for i in ('D', 'H', 'M'):  # needed because keys are not sorted
            d[i], rem = divmod(rem, l[i])
        d['S'] = rem
        if format_str == "P":
            # Variable duration format, omit 0 values
            ret_str = "P"
            for i in ('D', 'H', 'M', 'S'):
                if d[i] != 0:
                    ret_str += "%s%s" % (d[i], i)
            return ret_str

        # Otherwise use fixed formats (they will include 0s)
        if d['D'] == 0:
            format_str = format_no_day

        return format_str % d


ZERO = timedelta(0)
HOUR = timedelta(hours=1)

class TzUTC(tzinfo):
    """UTC"""
    def utcoffset(self, dt):
        return ZERO

    def tzname(self, dt):
        return "UTC"

    def dst(self, dt):
        return ZERO

UTC = TzUTC()

UTCTIME_DELTA = None

def get_current_utctime_delta():
    """Sum this to a local time to get UTC time"""
    global UTCTIME_DELTA
    if UTCTIME_DELTA is not None:
        return UTCTIME_DELTA
    tnow = time.time()
    UTCTIME_DELTA = (datetime.utcfromtimestamp(tnow) - datetime.fromtimestamp(tnow))
    return UTCTIME_DELTA

try:
    import pytz
    try:
        import tzlocal

        def get_localzone():
            return tzlocal.get_localzone()
    except ImportError:
        def get_localzone():
            retv = None
            try:
                # This should work on RHEL based systems
                for line in open("/etc/sysconfig/clock").readlines():
                    if line.startswith("ZONE="):
                        retv = line.strip()[6:-1]
            except IOError:
                pass
            if retv is None:
                try:
                    retv = os.environ['TZ']
                except KeyError:
                    pass
            if retv is None:
                try:
                    # This should work on Debian based systems
                    retv = open("/etc/timezone").readlines()[0].strip()
                except IOError:
                    pass
            # Further attempts can be done checking the link (not content) of /etc/localtime
            # or comparing the content of /etc/localtime w/ /usr/share/zoneinfo/ files
            if not retv:
                return None
            return pytz.timezone(retv)

    def _get_utc_from_local(dt):
        """ Return UTC time. If dt is naive (no timezone set) it is assumed local time """
        tz = get_localzone()
        if tz is None and dt.tzinfo is None:
            retv = dt + get_current_utctime_delta()
            return retv.replace(tzinfo=UTC)
        retv = dt
        try:
            retv = tz.localize(dt, is_dst=None)
        except ValueError:
            # not naive time value
            pass
        return retv.astimezone(pytz.utc)

except ImportError:
    # alternative
    # works correctly if the time offset is the same as now
    def _get_utc_from_local(dt):
        """ Return UTC time. If dt is naive (no timezone set) it is assumed local time """
        if dt.tzinfo is None:
            # naive time
            retv = dt + get_current_utctime_delta()
            return retv.replace(tzinfo=UTC)
        # timezone set
        return dt.astimezone(UTC)


## Public functions

# This is the same than datetime_to_utc
# def fix_datetime(dt_in, assume_local=True):
#     pass


def datetime_to_utc(dt_in, assume_local=True, naive=False):
    """
    Get a datetime and convert it to
    If no timezone is set assume that it is local
    :param dt_in: datetime.datetime object (naive, UTC or some other time zone)
    :param assume_local: assume that an unbound datetime is local (default is True). UTC is assumed if set False.
    :param naive: if true return a naive timestamp (the value is still the UTC time but the time zone is not set)
    :return: datetime.datetime object (naive or UTC)
    """
    if dt_in is None:
        # leave None - return time.time() OR datetime.utcnow()
        return None
    if dt_in.tzinfo is None:
        if not assume_local:
            if not naive:
                dt_in = dt_in.replace(tzinfo=UTC)
            return dt_in
    #  get_utc_from_local both if timezone is set or time is naive and assumed local
    dt_in = _get_utc_from_local(dt_in)
    if naive:
        dt_in = dt_in.replace(tzinfo=None)
    return dt_in


## Parse and format dates

def parse_datetime(date_string_in, return_seconds=False, assume_local=False):
    """Parse date/time string and return datetime object
    This function provides only limited support of the iso8601 format
    e.g. Time zone specifications (different from Z for UTC) are not supported
    Can raise ValueError is the format is not valid

    :param date_string_in: date/time string in iso8601 (%Y-%m-%dT%H:%M:%S[Z]) format
        Other formats are accepted: %Y-%m-%d, %Y%m%d[T%H:%M:%S[Z]], %Y-%m-%d %H:%M:%S
    :param return_seconds: return seconds form the Epoch instead of a datetime object
    :param assume_local: assume that a naive time is local when returning seconds (cannot express naive time)
    :return: datetime, None if errors occur
    """
    # from python 2.5 datetime.strptime(date_string, format)
    # previous: datetime(*(time.strptime(date_string, format)[0:6]))
    # These external modules provide robust parsing/formatting:
    #  pyiso8601 - https://pypi.python.org/pypi/iso8601
    #  isodate - https://pypi.python.org/pypi/isodate
    #  dateutil -
    #  ciso8601 - https://github.com/elasticsales/ciso8601
    date_string = date_string_in.strip()
    is_utc = None
    # TODO: add support for timezones different form Z
    if date_string[-1] == 'Z':
        is_utc = True
        date_string = date_string[:-1]
    try:
        # fast track for the most likely format
        result = time.strptime(date_string, "%Y-%m-%dT%H:%M:%S")
    except ValueError:
        # normalize the string to %Y%m%d[ %H:%M:%S]
        dt_arr = date_string.split('T')
        if not len(dt_arr) == 2:
            dt_arr = date_string.split()
            if not len(dt_arr) == 2:
                dt_arr.append('')
        date_string = ("%s %s" % (dt_arr[0].replace('-', ''), dt_arr[1])).strip()
        try:
            result = time.strptime(date_string, "%Y%m%d %H:%M:%S")
        except ValueError:
            # Wrong format, try the next
            try:
                # try second string format
                result = time.strptime(date_string, "%Y%m%d")
            except ValueError, e:
                # No valid format
                DebugPrint(2, "Wrong format, Date parsing failed for %s: %s" % (date_string_in, e))
                #return None
                raise
            except Exception, e:
                DebugPrint(2, "Date parsing failed for %s: %s" % (date_string_in, e))
                #return None
                raise
    except Exception, e:
        # TODO: which other exception can happen?
        DebugPrint(2, "Date parsing failed for %s: %s" % (date_string_in, e))
        #return None
        raise
    if return_seconds:
        if is_utc and not assume_local:
            # time.mktime() uses local time, not UTC
            return long(round(calendar.timegm(result)))
        else:
            # assume local time for naive time
            return long(round(time.mktime(result)))
    if is_utc:
        return datetime(*result[0:6], tzinfo=UTC)
    return datetime(*result[0:6])


def format_datetime(date_in, iso8601=True):
    """
    Format the date as iso8601 or %Y-%m-%d %H:%M:%S. iso8601 datetime is %Y-%m-%dT%H:%M:%SZ for UTC, Z is omitted for
    naive time (only if date_in is a datetime object), +HH:MM is added for other time zones.
    Gratia service (collector) expects timestamps with T and Z.
    Can rise exceptions if times are out of range.
    :param date_in: date in seconds from the Epoch (float), time-tuple, or datetime object.
        The first 2 and naive datetime objects are assumed in UTC time.
        None is considered now.
    :param iso8601: use the "%Y-%m-%d %H:%M:%S" alternative format if False (default: True)
    :return: String with formatted date, None if failing
    """
    result = None
    try:
        try:
            # convert directly datetime and return
            padding = 'Z'
            if iso8601:
                result = date_in.isoformat()
            else:
                result = date_in.isoformat(' ')
                padding = ''
            if result.endswith('+00:00'):
                result = "%s%s" % (result[:-6], padding)
            return result
        except AttributeError:
            # not datetime, try other formats
            pass
        try:
            # seconds from Epoch (float) or None to time-tuple
            date_in = time.gmtime(date_in)
        except TypeError:
            # no seconds from Epoch
            pass
        # Here date_in should be a time-tuple
        # Gratia expects timestamps with T and Z
        # TODO: remove this comment if fixed:
        # Observing this warning in Gratia Service
        # 12 Feb 2015 19:49:04,572 gratia.service(Thread-109) [FINE]: DateElement: caught problem with date element, "2006-03-01 00:00:00", fixed to "2006-03-01T00:00:00Z"
        # The desired format is
        if iso8601:
            result = time.strftime("%Y-%m-%dT%H:%M:%SZ", date_in)
        else:
            result = time.strftime("%Y-%m-%d %H:%M:%S", date_in)
    except Exception, e:
        DebugPrint(2, "Date conversion failed for %s: %s" % (date_in, e))
        raise
    return result


def format_interval(time_interval):
    """
    Format time interval as Duration ISO8601 (PnYnMnDTnHnMnS): http://en.wikipedia.org/wiki/ISO_8601
    :param time_interval: time interval in seconds
    :return: formatted ISO8601 time interval
    """
    return strfdelta(time_interval)


def datetime_to_unix_time(time_in):
    """
    Convert datetime to seconds from the epoch (keeping the provided precision)
    http://en.wikipedia.org/wiki/Unix_time
    dts.strftime("%s.%f")  # datetime to unix_time, not all OS have %s,%f

    :param time_in: datetime to convert
    :return: seconds form the epoch (float including milliseconds)
    """
    # time_in.strftime("%s.%f")  # not all OS have %s,%f
    epoch = datetime.utcfromtimestamp(0)
    delta = time_in - epoch
    # only form py2.7: return delta.total_seconds()
    return total_seconds_precise(delta)


def datetime_timedelta_to_seconds(delta):
    return total_seconds_precise(delta)


## Truncating functions

def at_minute(ds):
    """
    Truncate the datetime timestamp at the beginning of the minute
    :param ds: input datetime timestamp
    :return: output datetime timestamp where seconds are set to 0
    """
    return datetime(ds.year, ds.month, ds.day, ds.hour, ds.minute, 0)


def at_hour(ds):
    """
    Truncate the datetime timestamp at the beginning of the hour
    :param ds: input datetime timestamp
    :return: output datetime timestamp where minutes and seconds are set to 0
    """
    return datetime(ds.year, ds.month, ds.day, ds.hour, 0, 0)


def at_day(ds):
    """
    Truncate the datetime timestamp at the beginning of the day
    :param ds: input datetime timestamp
    :return: output datetime timestamp where time is set to 0 (only date is kept)
    """
    return datetime(ds.year, ds.month, ds.day, 0, 0, 0)


## Increment functions

def wind_time(dtin, days=0, hours=0, minutes=0, seconds=0, backward=True):
    """
    (Re) wind the time backward or forward.
    All the values are added. e.g. 1 day, 25 hours, 62 minutes is 2days, 2hours, 2 minutes
    :param dtin: Initial time
    :param days: Number of days to subtract/add
    :param hours: Number of hours to subtract/add
    :param minutes: Number of minutes to subtract/add
    :param seconds: Number of days to subtract/add
    :param backward: direction, if True time is subtracted, if False it is added
    :return: datetime shifted backward or forward
    """
    td = timedelta(days=days, hours=hours, minutes=minutes, seconds=seconds)
    if backward:
        return dtin - td
    else:
        return dtin + td


def conditional_increment(dtin, dt_condition, seconds=1, microseconds=0):
    """
    If dtin precedes dt_condition of at least 1 second more then the increment (seconds+microseconds),
    then the increment is added to dtin, otherwise dtin is returned.
    1 second gap is chosen because it is the time resolution of this module (timeutil).
    It may change once Python 2.4 is no more supported
    :param dtin: input datetime object
    :param dt_condition: condition time (datetime or UNIX timestamp)
    :param seconds: number of seconds (int) to add to dtin
    :param microseconds: number of microseconds (int) to add to dtin
    :return: datetime object, incremented if needed
    """
    dt_safe = dtin + timedelta(seconds=seconds+1, microseconds=microseconds)
    try:
        if dt_safe >= dt_condition:
            return dtin
    except TypeError:
        if dt_safe.timetuple() >= time.localtime(dt_condition):
            return dtin
    return dtin + timedelta(seconds=seconds, microseconds=microseconds)


def main():
    # add here the tests
    pass

if __name__ == "__main__":
    main()
