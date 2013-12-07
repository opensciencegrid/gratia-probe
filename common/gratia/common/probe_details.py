
import time
import socket

import gratia.common.global_state as global_state
import gratia.common.utils as utils
import gratia.common.record as record
from gratia.common.debug import DebugPrint


__handshakeReg__ = []

def RegisterReporterLibrary(name, version):
    """Register the library named 'name' with version 'version'"""

    __handshakeReg__.append(('ReporterLibrary', 'version="' + version[0:254] + '"', name))


def RegisterReporter(name, version):
    """Register the software named 'name' with version 'version'"""

    __handshakeReg__.append(('Reporter', 'version="' + version[0:254]+ '"', name))


def RegisterService(name, version):
    '''Register the service (Condor, PBS, LSF, DCache) which is being reported on '''

    __handshakeReg__.append(('Service', 'version="' + version[0:254] + '"', name))


class ProbeDetails(record.Record):

    def __init__(self):

        # Initializer

        super(self.__class__, self).__init__()
        DebugPrint(1, 'Creating a ProbeDetails record ' + utils.TimeToString())

        self.__ProbeDetails__ = []

        # Extract the revision number

        rev = utils.ExtractSvnRevision('$Revision: 3997 $')

        self.ReporterLibrary('Gratia', rev)

        for data in __handshakeReg__:
            self.__ProbeDetails__ = self.AppendToList(self.__ProbeDetails__, data[0], data[1], data[2])

    def ReporterLibrary(self, name, version):
        self.__ProbeDetails__ = self.AppendToList(self.__ProbeDetails__, 'ReporterLibrary', 'version="' + version[0:254] + '"'
                                              , name)

    def Reporter(self, name, version):
        self.__ProbeDetails__ = self.AppendToList(self.__ProbeDetails__, 'Reporter', 'version="' + version[0:254] + '"', name)

    def Service(self, name, version):
        self.__ProbeDetails__ = self.AppendToList(self.__ProbeDetails__, 'Service', 'version="' + version[0:254] + '"', name)

    def XmlAddMembers(self):
        """ This should add the value of the 'data' member of ProbeDetails """

        super(self.__class__, self).XmlAddMembers()

    def XmlCreate(self):

        self.XmlAddMembers()

        self.XmlData = []
        self.XmlData.append('<?xml version="1.0" encoding="UTF-8"?>\n')
        self.XmlData.append('<ProbeDetails>\n')

        # Add the record indentity

        self.XmlData.append('<RecordIdentity recordId="' + socket.getfqdn() + ':' + str(global_state.RecordPid) + '.'
                            + str(record.RecordId) + '" createTime="' + utils.TimeToString(time.gmtime()) + '" />\n')
        record.RecordId += 1

        for data in self.RecordData:
            self.XmlData.append('\t')
            self.XmlData.append(data)
            self.XmlData.append('\n')

        if len(self.__ProbeDetails__) > 0:
            for data in self.__ProbeDetails__:
                self.XmlData.append('\t')
                self.XmlData.append(data)
                self.XmlData.append('\n')

        self.XmlData.append('</ProbeDetails>\n')

    def Print(self):
        DebugPrint(1, 'ProbeDetails Record: ', self)


