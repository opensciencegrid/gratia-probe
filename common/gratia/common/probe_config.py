
import os
import re
import sys
import urllib
import httplib
import xml.dom.minidom

from OpenSSL import crypto

import gratia.common.connect_utils as connect_utils
import gratia.common.utils as utils
import gratia.common.bundle as bundle

from gratia.common.file_utils import Mkdir
from gratia.common.debug import DebugPrint, DebugPrintTraceback

__certrequestRejected__ = False

def isCertrequestRejected():
    return __certrequestRejected__


def setCertrequestRejected():
    global __certrequestRejected__
    connect_utils.connectionError = True
    __certrequestRejected__ = True

class ProbeConfiguration:
    """
    Class giving access (and in some cases override capability) to the ProbeConfig files
    """
    
    __doc = None
    __configname = 'ProbeConfig'
    __CollectorHost = None
    __ProbeName = None
    __SiteName = None
    __Grid = None
    __DebugLevel = None
    __LogLevel = None
    __LogRotate = None
    __DataFileExpiration = None
    __QuarantineSize = None
    __UseSyslog = None
    __UserVOMapFile = None
    __FilenameFragment = None
    __CertInfoLogPattern = None
    __VOOverride = None

    def __init__(self, customConfig='ProbeConfig'):
        if os.path.exists(customConfig):
            self.__configname = customConfig
        else:
            DebugPrint(0,"Error: configuration file %s doesn't exist" % (customConfig,))
            raise utils.InternalError("Error: configuration file %s doesn't exist" % (customConfig,))

    def __loadConfiguration__(self):
        self.__doc = xml.dom.minidom.parse(self.__configname)
        DebugPrint(1, 'Using config file: ' + self.__configname)

    def __getConfigAttribute(self, attributeName):
        """
        Return the value of a configuration attribute name 'attributeName' as a string.
        If no such attribute exists, an empty string is returned, as if the attribute had no value
        """
        if self.__doc == None:
            try:
                self.__loadConfiguration__()
            except xml.parsers.expat.ExpatError, ex:
                sys.stderr.write('Parse error in ' + self.__configname + ': ' + str(ex) + '\n')
                raise

        # TODO:  Check if the ProbeConfiguration node exists
        # TODO:  Check if the requested attribute exists

        return self.__doc.getElementsByTagName('ProbeConfiguration')[0].getAttribute(attributeName)

    # Public interface


    def getConfigAttribute(self, attributeName):
        return self.__getConfigAttribute(attributeName)

    def get_SSLHost(self):
        return self.__getConfigAttribute('SSLHost')

    def get_SSLRegistrationHost(self):
        return self.__getConfigAttribute('SSLRegistrationHost')

    def get_SOAPHost(self):
        return self.get_CollectorHost()

    def get_CollectorHost(self):
        if self.__CollectorHost != None:
            return self.__CollectorHost
        coll = self.__getConfigAttribute('CollectorHost')
        soap = self.__getConfigAttribute('SOAPHost')
        if coll == 'gratia-osg.fnal.gov:8880' and soap != None and soap != r'' and soap \
            != 'gratia-osg.fnal.gov:8880':
            self.__CollectorHost = soap
        elif coll != None and coll != r'':
            self.__CollectorHost = coll
        else:
            self.__CollectorHost = soap
        return self.__CollectorHost

    def get_CollectorService(self):
        return self.__getConfigAttribute('CollectorService')

    def get_SSLCollectorService(self):
        return self.__getConfigAttribute('SSLCollectorService')

    def get_RegistrationService(self):
        result = self.__getConfigAttribute('RegistrationService')
        if result == None or result == r'':
            return '/gratia-registration/register'
        else:
            return result

    def __createCertificateFile(self, keyfile, certfile):

        # Get a fresh certificate.

        # if (False):
        #  cakey = createKeyPair(crypto.TYPE_RSA, 1024)
        #  careq = createCertRequest(cakey, CN='Certificate Authority')
        #  cacert = createCertificate(careq, (careq, cakey), 0, (0, 60*60*24*365*1)) # one year
        #  open(keyfile, 'w').write(crypto.dump_privatekey(crypto.FILETYPE_PEM, cakey))
        #  open(certfile, 'w').write(crypto.dump_certificate(crypto.FILETYPE_PEM, cacert))
        #  return True
        # else:
        # Download it from the server.

        # Try this only once per run

        if isCertrequestRejected():
            return False

        # qconnection = ProxyUtil.HTTPConnection(self.get_SSLRegistrationHost(),
        #                                       http_proxy = ProxyUtil.findHTTPProxy())

        qconnection = httplib.HTTPConnection(self.get_SSLRegistrationHost())
        qconnection.connect()

        queryString = urllib.urlencode([('command', 'request'), ('from', self.get_ProbeName()), ('arg1',
                                       'not really')])
        headers = {'Content-type': 'application/x-www-form-urlencoded'}
        qconnection.request('POST', self.get_RegistrationService(), queryString, headers)
        responseString = qconnection.getresponse().read()
        resplist = responseString.split(':')
        if len(resplist) == 3 and resplist[0] == 'ok':

            # We received the info, let's store it
            # cert = crypto.load_certificate(crypto.FILETYPE_PEM,resplist[1])
            # key = crypto.load_privatekey(crypto.FILETYPE_PEM,resplist[1])

            # First create any sub-directory if needed.

            keydir = os.path.dirname(keyfile)
            if keydir != r'' and os.path.exists(keydir) == 0:
                Mkdir(keydir)
            certdir = os.path.dirname(certfile)
            if certdir != r'' and os.path.exists(certdir) == 0:
                Mkdir(certdir)

            # and then save the pem files

            open(keyfile, 'w').write(resplist[2])
            open(certfile, 'w').write(resplist[1])
        else:

            # We could do
            # os.chmod(keyfile,0600)

            DebugPrint(4, 'DEBUG: Connect: FAILED')
            DebugPrint(0, 'Error: while getting new certificate: ' + responseString)
            DebugPrintTraceback()
            setCertrequestRejected()
            return False
        return True

    def __get_fullpath_cert(self, filename):
        cdir = os.path.dirname(filename)
        if cdir != r'' or cdir == None:
            return filename
        return os.path.join(os.path.join(self.get_WorkingFolder(), 'certs'), filename)

    def get_GratiaCertificateFile(self):
        filename = self.__getConfigAttribute('GratiaCertificateFile')
        if filename == None or filename == r'':
            filename = 'gratia.probecert.pem'
        filename = self.__get_fullpath_cert(filename)
        keyfile = self.get_GratiaKeyFile()
        try:
            cryptofile = open(filename, 'r')
            cert = crypto.load_certificate(crypto.FILETYPE_PEM, cryptofile.read())
            if cert.has_expired() or os.path.exists(keyfile) == 0:
                if not self.__createCertificateFile(keyfile, filename):
                    return None
        except IOError:

            # If we can not read it, let get a new one.

            if not self.__createCertificateFile(keyfile, filename):
                return None

        return filename

    def get_GratiaKeyFile(self):
        filename = self.__getConfigAttribute('GratiaKeyFile')
        if filename == None or filename == r'':
            filename = 'gratia.probekey.pem'
        return self.__get_fullpath_cert(filename)

    def setMeterName(self, name):
        self.__ProbeName = name

    def get_MeterName(self):
        return self.get_ProbeName()

    def setProbeName(self, name):
        self.__ProbeName = name
        self.__FilenameFragment = None

    def get_ProbeName(self):
        if self.__ProbeName == None:
            result = self.__getConfigAttribute('ProbeName')
            if result == None or result == r'':
                result = self.__getConfigAttribute('MeterName')
            elif result == 'generic':

                # If ProbeName has not been changed, maybe MeterName has been

                mresult = self.__getConfigAttribute('MeterName')
                if mresult != None and mresult != r'':
                    result = mresult
            if result == None or result == r'':
                self.setProbeName(utils.genDefaultProbeName())
                DebugPrint(0, 'INFO: ProbeName not specified in ' + self.__configname + ': defaulting to '
                           + self.__ProbeName)
            else:
                self.setProbeName(result)
        return self.__ProbeName

    def getFilenameFragment(self):
        '''Generate a filename fragment based on the collector destination'''

        if self.__FilenameFragment == None:
            fragment = self.get_ProbeName()
            if fragment:
                fragment += r'_'
            fragment += self.get_SOAPHost()
            __FilenameFragment = re.sub(r'[:/]', r'_', fragment)
        return __FilenameFragment

    def get_Grid(self):
        if self.__Grid == None:
            val = self.__getConfigAttribute('Grid')
            if val == None or val == r'':
                self.__Grid = 'OSG'
            else:
                self.__Grid = val
        return self.__Grid

    def setSiteName(self, name):
        self.__SiteName = name

    def get_SiteName(self):
        if self.__SiteName == None:
            val = self.__getConfigAttribute('SiteName')
            if val == None or val == r'':
                self.__SiteName = 'generic Site'
            else:
                self.__SiteName = val
        return self.__SiteName

    def get_UseSSL(self):
        val = self.__getConfigAttribute('UseSSL')
        if val == None or val == r'':
            return 0
        else:
            return int(val)

    def get_UseSoapProtocol(self):
        val = self.__getConfigAttribute('UseSoapProtocol')
        if val == None or val == r'':
            return 0
        else:
            return int(val)

    def get_UseGratiaCertificates(self):
        return int(self.__getConfigAttribute('UseGratiaCertificates'))

    def get_DebugLevel(self):
        if self.__DebugLevel == None:
            self.__DebugLevel = int(self.__getConfigAttribute('DebugLevel'))
        return self.__DebugLevel

    def set_DebugLevel(self, val):
        self.__DebugLevel = int(val)

    def get_LogLevel(self):
        if self.__LogLevel == None:
            val = self.__getConfigAttribute('LogLevel')
            if val == None or val == r'':
                self.__LogLevel = self.get_DebugLevel()
            else:
                self.__LogLevel = int(val)
        return self.__LogLevel

    def get_LogRotate(self):
        if self.__LogRotate == None:
            val = self.__getConfigAttribute('LogRotate')
            if val == None or val == r'':
                self.__LogRotate = 31
            else:
                self.__LogRotate = int(val)
        return self.__LogRotate

    def get_DataFileExpiration(self):
        if self.__DataFileExpiration == None:
            val = self.__getConfigAttribute('DataFileExpiration')
            if val == None or val == r'':
                self.__DataFileExpiration = 31
            else:
                self.__DataFileExpiration = int(val)
        return self.__DataFileExpiration

    def get_QuarantineSize(self):
        if self.__QuarantineSize == None:
            val = self.__getConfigAttribute('QuarantineSize')
            if val == None or val == r'':
                self.__QuarantineSize = 200 * 1000 * 1000
            else:
                self.__QuarantineSize = int(val) * 1000 * 1000
        return self.__QuarantineSize

    def get_UseSyslog(self):
        if self.__UseSyslog == None:
            val = self.__getConfigAttribute('UseSyslog')
            if val == None or val == r'':
                self.__UseSyslog = False
            else:
                self.__UseSyslog = int(val)
        return self.__UseSyslog

    def get_GratiaExtension(self):
        return self.__getConfigAttribute('GratiaExtension')

    def get_CondorCEHistoryFolder(self):
        return self.__getConfigAttribute('CondorCEHistoryFolder')

    def get_CertificateFile(self):
        return self.__getConfigAttribute('CertificateFile')

    def get_KeyFile(self):
        return self.__getConfigAttribute('KeyFile')

    def get_MaxPendingFiles(self):
        val = self.__getConfigAttribute('MaxPendingFiles')
        if val == None or val == r'':
            return 100000
        else:
            return int(val)

    def get_MaxStagedArchives(self):
        val = self.__getConfigAttribute('MaxStagedArchives')
        if val == None or val == r'':
            return 400
        else:
            return int(val)

    def get_DataFolder(self):
        return self.__getConfigAttribute('DataFolder')

    def get_WorkingFolder(self):
        return self.__getConfigAttribute('WorkingFolder')

    def get_LogFolder(self):
        return self.__getConfigAttribute('LogFolder')

    def get_LogFileName(self):
        return self.__getConfigAttribute('LogFileName')

    def get_CertInfoLogPattern(self):
        if self.__CertInfoLogPattern:
            return self.__CertInfoLogPattern
        val = self.__getConfigAttribute('CertInfoLogPattern')
        if val == None:
            val = ''
        self.__CertInfoLogPattern = val
        return self.__CertInfoLogPattern

    def get_UserVOMapFile(self):
        if self.__UserVOMapFile:
            return self.__UserVOMapFile
        val = self.__getConfigAttribute('UserVOMapFile')

        if val and os.path.isfile(val):
            self.__UserVOMapFile = val
        else:
            self.__UserVOMapFile = '/var/lib/osg/user-vo-map'
            if not os.path.isfile(self.__UserVOMapFile):
                self.__UserVOMapFile = None

        return self.__UserVOMapFile

    def get_SuppressUnknownVORecords(self):
        result = self.__getConfigAttribute('SuppressUnknownVORecords')
        if result:
            match = re.search(r'^(True|1|t)$', result, re.IGNORECASE)
            if match:
                return True
            else:
                return False
        else:
            return None

    def get_MapUnknownToGroup(self):
        result = self.__getConfigAttribute('MapUnknownToGroup')
        if result:
            match = re.search(r'^(True|1|t)$', result, re.IGNORECASE)
            if match:
                return True
            else:
                return False
        else:
            return None

    def get_SuppressNoDNRecords(self):
        result = self.__getConfigAttribute('SuppressNoDNRecords')
        if result:
            match = re.search(r'^(True|1|t)$', result, re.IGNORECASE)
            if match:
                return True
            else:
                return False
        else:
            return None
    def get_QuarantineUnknownVORecords(self):
        result = self.__getConfigAttribute('QuarantineUnknownVORecords')
        if result:
            match = re.search(r'^(True|1|t)$', result, re.IGNORECASE)
            if match:
                return True
            else:
                return False
        else:
            return True 


    def get_SuppressgridLocalRecords(self):
        result = self.__getConfigAttribute('SuppressGridLocalRecords')
        if result:
            match = re.search(r'^(True|1|t)$', result, re.IGNORECASE)
            if match:
                return True
            else:
                return False
        else:
            return False  # If the config entry is missing, default to false

    def get_NoCertinfoBatchRecordsAreLocal(self):
        result = self.__getConfigAttribute('NoCertinfoBatchRecordsAreLocal')
        if result:
            match = re.search(r'^(True|1|t)$', result, re.IGNORECASE)
            if match:
                return True
            else:
                return False
        else:
            return True  # If the config entry is missing, default to true

    def get_BundleSize(self):
        result = self.__getConfigAttribute('BundleSize')
        if result:
            bundle.bundle_size = int(result)
        elif result == None or result == r'':
            bundle.bundle_size = 100
        maxpending = self.get_MaxPendingFiles()
        if bundle.bundle_size > maxpending:
            bundle.bundle_size = maxpending
        return bundle.bundle_size

    def get_ConnectionTimeout(self):
        val = self.__getConfigAttribute('ConnectionTimeout')
        if val == None or val == r'':
            return 900
        else:
            return int(val)    

    def get_VOOverride(self):
        # Get the VOOverride, which can be 'None', therefore using the 
        # probe's detected VO
        if self.__VOOverride == None:
            self.__VOOverride = self.__getConfigAttribute('VOOverride')

        return self.__VOOverride

    def get_MapGroupToRole(self):
        if self.__getConfigAttribute('MapGroupToRole') == "1":
            return True
        else:
            return False

