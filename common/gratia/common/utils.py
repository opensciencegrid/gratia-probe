
import os
import sys
import math
import time

# Returns a nicely formatted string for the floating point number
# provided.  This number will be rounded to the supplied accuracy
# and commas and spaces will be added.  I think every language should
# do this for numbers.  Why don't they?  Here are some examples:
# >>> print niceNum(123567.0, 1000)
# 124,000
# >>> print niceNum(5.3918e-07, 1e-10)
# 0.000 000 539 2
# This kind of thing is wonderful for producing tables for
# human consumption.
#

def niceNum(num, precision=1):
    """Returns a string representation for a floating point number
    that is rounded to the given precision and displayed with
    commas and spaces."""
    
    accpow = int(math.floor(math.log10(precision)))
    if num < 0:
        digits = int(math.fabs(num / pow(10, accpow) - 0.5))
    else:
        digits = int(math.fabs(num / pow(10, accpow) + 0.5))
    result = r''
    if digits > 0:
        for i in range(0, accpow):
            if i % 3 == 0 and i > 0:
                result = '0,' + result
            else:
                result = '0' + result
        curpow = int(accpow)
        while digits > 0: 
            adigit = chr(digits % 10 + ord('0'))
            if curpow % 3 == 0 and curpow != 0 and len(result) > 0:
                if curpow < 0:
                    result = adigit + ' ' + result
                else:
                    result = adigit + ',' + result
            elif curpow == 0 and len(result) > 0:
                result = adigit + '.' + result
            else:
                result = adigit + result
            digits = digits / 10
            curpow = curpow + 1
        for i in range(curpow, 0):
            if i % 3 == 0 and i != 0:
                result = '0 ' + result
            else:
                result = '0' + result
        if curpow <= 0:
            result = '0.' + result
        if num < 0:
            result = '-' + result
    else:
        result = '0'
    return result


# Check Python version number against requirements
def pythonVersionRequire(
    major,
    minor=0,
    micro=0,
    releaseLevel='final',
    serial=0,
    ):
    result = False
    if not 'version_info' in dir(sys):
        if major < 2:  # Unlikely
            return True
        else:
            return False
    releaseLevelsDir = {
        'alpha': 0,
        'beta': 1,
        'candidate': 2,
        'final': 3,
        }
    if major > sys.version_info[0]:
        result = False
    elif major < sys.version_info[0]:
        result = True
    elif minor > sys.version_info[1]:
        result = False
    elif minor < sys.version_info[1]:
        result = True
    elif micro > sys.version_info[2]:
        result = False
    elif micro < sys.version_info[2]:
        result = True
    else:
        try:
            releaseLevelIndex = releaseLevelsDir[releaseLevel.lower()]
            releaseCompareIndex = releaseLevelsDir[sys.version_info[3].lower()]
        except KeyError:
            result = False
        if releaseLevelIndex > releaseCompareIndex:
            result = False
        elif releaseLevelIndex < releaseCompareIndex:
            result = True
        elif serial > sys.version_info[4]:
            result = False
        else:
            result = True
    return result


class InternalError(Exception):
    pass


def ExtractSvnRevision(revision):

    # Extra the numerical information from the SVN keyword:
    # $Revision\: $

    return revision.split('$')[1].split(':')[1].strip()

def TimeToString(targ=None):
    ''' Return the XML version of the given time.  Default to the current time '''
    if not targ:
        targ = time.gmtime()
    return time.strftime('%Y-%m-%dT%H:%M:%SZ', targ)

__lrms = None
def setProbeBatchManager(lrms):
    global __lrms
    __lrms = lrms.lower()

def getProbeBatchManager():
    return __lrms

def genDefaultProbeName():
    f = os.popen('hostname -f')
    meterName = 'auto:' + f.read().strip()
    f.close()
    return meterName

