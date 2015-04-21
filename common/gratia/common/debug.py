
import os
import sys
import time
import string
import syslog
import traceback

from gratia.common.file_utils import Mkdir

__logFileIsWriteable__ = True
__quiet__ = 0


# TODO: Why this is not using the ConfigProxy like other modules?
# getGratiaConfig seems complex and unnecessary
# And GratiaCore seems not involved, it is config
# The lines below and returning Config should be a better solution
#from gratia.common.config import ConfigProxy
#Config = ConfigProxy()

# There's a circular dependency between core and debug;
# this function breaks it.
def getGratiaConfig():
    GratiaCore = __import__("gratia.common.config").common.config
    return GratiaCore.Config

def GenerateOutput(prefix, *arg):
    out = prefix
    for val in arg:
        out = out + str(val)
    return out

def Error(*arg):
    out = GenerateOutput('Error in Gratia probe: ', *arg)
    print >> sys.stderr, time.strftime(r'%Y-%m-%d %H:%M:%S %Z', time.localtime()) + ' ' + out
    if getGratiaConfig() and getGratiaConfig().get_UseSyslog():
        LogToSyslog(-1, GenerateOutput(r'', *arg))
    else:
        LogToFile(time.strftime(r'%H:%M:%S %Z', time.localtime()) + ' ' + out)

def DebugPrint(level, *arg):
    """Print debug messages if the level is smaller than the debug level set in the configuration file
    Here some suggestion on how to choose the level (the names are the same used by logging, but the numeric 
    values are different, in logging higher numbers are more critical)
    0 - CRITICAL
    1 - ERROR 
    2 - WARNING
    3 - INFO
    4 - DEBUG
    5 or bigger (more verbose debug messages)
    """
    if __quiet__:
        return
    try:
        if not getGratiaConfig():
            return
        if  level < getGratiaConfig().get_DebugLevel():
            out = time.strftime(r'%Y-%m-%d %H:%M:%S %Z', time.localtime()) + ' ' + GenerateOutput('Gratia: ',
                    *arg)
            print >> sys.stderr, out
        if getGratiaConfig() and level < getGratiaConfig().get_LogLevel():
            out = GenerateOutput('Gratia: ', *arg)
            if getGratiaConfig().get_UseSyslog():
                LogToSyslog(level, GenerateOutput(r'', *arg))
            else:
                LogToFile(time.strftime(r'%H:%M:%S %Z', time.localtime()) + ' ' + out)
    except:
        out = time.strftime(r'%Y-%m-%d %H:%M:%S %Z', time.localtime()) + ' ' \
            + GenerateOutput('Gratia: printing failed message: ', *arg)
        sys.stderr.write(out + '\n')
        sys.exit()


def LogFileName():
    """Return the name of the current log file. If there is no LogFileName set in the configuration
    a default yy-mm-dd.log is returned
    """

    filename = getGratiaConfig().get_LogFileName()
    if not filename:
        filename = time.strftime('%Y-%m-%d') + '.log'
    return os.path.join(getGratiaConfig().get_LogFolder(), filename)


def LogToFile(message):
    '''Write a message to the Gratia log file'''

    global __logFileIsWriteable__
    current_file = None
    filename = 'none'

    try:

        # Ensure the 'logs' folder exists

        if os.path.exists(getGratiaConfig().get_LogFolder()) == 0:
            Mkdir(getGratiaConfig().get_LogFolder())

        filename = LogFileName()

        if os.path.exists(filename) and not os.access(filename, os.W_OK):
            os.chown(filename, os.getuid(), os.getgid())
            os.chmod(filename, 0755)

        # Open/Create a log file for today's date

        current_file = open(filename, 'a')

        # Append the message to the log file

        current_file.write(message + '\n')

        __logFileIsWriteable__ = True
    except:
        if __logFileIsWriteable__:

            # Print the error message only once

            print >> sys.stderr, 'Gratia: Unable to log to file:  ', filename, ' ', sys.exc_info(), '--', \
                sys.exc_info()[0], '++', sys.exc_info()[1]
        __logFileIsWriteable__ = False

    if current_file != None:

        # Close the log file

        current_file.close()


def LogToSyslog(level, message):
    global __logFileIsWriteable__
    if level == -1:
        syslevel = syslog.LOG_ERR
    else:
        if level == 0:
            syslevel = syslog.LOG_INFO
        else:
            if level == 1:
                syslevel = syslog.LOG_INFO
            else:
                syslevel = syslog.LOG_DEBUG

    try:
        syslog.openlog('Gratia ')
        syslog.syslog(syslevel, message)

        __logFileIsWriteable__ = True
    except:
        if __logFileIsWriteable__:

            # Print the error message only once

            print >> sys.stderr, 'Gratia: Unable to log to syslog:  ', sys.exc_info(), '--', sys.exc_info()[0], \
                '++', sys.exc_info()[1]
        __logFileIsWriteable__ = False

    syslog.closelog()


def DebugPrintTraceback(debugLevel=4):
    DebugPrint(4, 'In traceback print (0)')
    message = string.join(traceback.format_exception(*sys.exc_info()), r'')
    DebugPrint(4, 'In traceback print (1)')
    DebugPrint(debugLevel, message)

