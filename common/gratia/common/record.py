
import os
import shutil

import gratia.common.config as config
import gratia.common.utils as utils
import gratia.common.xml_utils as xml_utils

from gratia.common.file_utils import Mkdir, RemoveFile
from gratia.common.debug import DebugPrint

Config = config.ConfigProxy()

RecordId = 0

class Record(object):

    '''Base class for the Gratia Record'''

    # List the damember for documentation purpose only,
    # We do not want 'class-wide' variables
    # XmlData = []
    # RecordData = []
    # TransientInputFiles = []

    # __ProbeName = r''
    # __ProbeNameDescription = r''
    # __SiteName = r''
    # __SiteNameDescription = r''
    # __Grid = r''
    # __GridDescription = r''

    def __init__(self):

        # See the function ResourceType for details on the
        # parameter
        if not config.Config:
            DebugPrint(0,"Error: Configuration is not initialized")
            raise utils.InternalError("Configuration is not initialized") 

        DebugPrint(2, 'Creating a Record ' + utils.TimeToString())
        self.XmlData = []
        self.__ProbeName = Config.get_ProbeName()
        self.__ProbeNameDescription = r''
        self.__SiteName = Config.get_SiteName()
        self.__SiteNameDescription = r''
        self.__Grid = Config.get_Grid()
        self.__GridDescription = r''
        self.RecordData = []
        self.TransientInputFiles = []
        self.__VOOverrid = Config.get_VOOverride()

    def Print(self):
        DebugPrint(3, 'Usage Record: ', self)

    def VerbatimAppendToList(
        self,
        where,
        what,
        comment,
        value,
        ):
        ''' Helper Function to generate the xml (Do not call directly)'''

        where.append('<' + what + ' ' + comment + '>' + value + '</' + what + '>')
        return where

    def VerbatimAddToList(
        self,
        where,
        what,
        comment,
        value,
        ):
        ''' Helper Function to generate the xml (Do not call directly)'''

        # First filter out the previous value

        where = [x for x in where if x.find('<' + what) != 0]
        return self.VerbatimAppendToList(where, what, comment, value)

    def AddToList(
        self,
        where,
        what,
        comment,
        value,
        ):
        ''' Helper Function to generate the xml (Do not call directly)'''

        return self.VerbatimAddToList(where, what, comment, xml_utils.escapeXML(value))

    def AppendToList(
        self,
        where,
        what,
        comment,
        value,
        ):
        ''' Helper Function to generate the xml (Do not call directly)'''

        return self.VerbatimAppendToList(where, what, comment, xml_utils.escapeXML(value))

    def GenericAddToList(
        self,
        xmlelem,
        value,
        description=r'',
        ):
        self.RecordData = self.AddToList(self.RecordData, xmlelem, self.Description(description), value)

    def XmlAddMembers(self):
        self.GenericAddToList('ProbeName', self.__ProbeName, self.__ProbeNameDescription)
        self.GenericAddToList('SiteName', self.__SiteName, self.__SiteNameDescription)
        self.GenericAddToList('Grid', self.__Grid, self.__GridDescription)

    def Duration(self, value):
        """ Helper Function to generate the xml (Do not call directly)
        Duration ISO8601 format (PnYnMnDTnHnMnS): http://en.wikipedia.org/wiki/ISO_8601
        use function in gratia.common2.timeutil
        """

        seconds = long(value * 100) % 6000 / 100.0
        value = long((value - seconds) / 60)
        minutes = value % 60
        value = (value - minutes) / 60
        hours = value % 24
        value = (value - hours) / 24
        result = 'P'
        if value > 0:
            result = result + str(value) + 'D'
        if hours > 0 or minutes > 0 or seconds > 0:
            result = result + 'T'
            if hours > 0:
                result = result + str(hours) + 'H'
            if minutes > 0:
                result = result + str(minutes) + 'M'
            if seconds > 0:
                result = result + str(seconds) + 'S'
        else:
            result = result + 'T0S'
        return result

    def Description(self, value):
        ''' Helper Function to generate the xml (Do not call directly)'''

        if len(value) > 0:
            return 'urwg:description="' + xml_utils.escapeXML(value) + '" '
        else:
            return r''

    def ProbeName(self, value, description=r''):
        self.__ProbeName = value
        self.__ProbeNameDescription = description

    def SiteName(self, value, description=r''):
        ''' Indicates which site the service accounted for belong to'''

        self.__SiteName = value
        self.__SiteNameDescription = description

    def Grid(self, value, description=r''):
        ''' Indicates which grid the service accounted for belong to'''

        self.__Grid = value
        self.__GridDescription = description
        
    def AddTransientInputFile(self, filename):
        ''' Register a file that should be deleted if the record has been properly processed '''
       
        DebugPrint(1, 'Registering transient input file: '+filename)
        self.TransientInputFiles.append(filename)
        
    def QuarantineTransientInputFiles(self):
        ''' Copy to a quarantine directories any of the input files '''
        
        quarantinedir = os.path.join(Config.get_DataFolder(),"quarantine")
        Mkdir(quarantinedir)
        for filename in self.TransientInputFiles:
            DebugPrint(1, 'Moving transient input file: '+filename+' to quarantine in '+quarantinedir)
            shutil.copy2(filename,quarantinedir)
            RemoveFile(filename)
        self.TransientInputFiles = []
        
    def RemoveTransientInputFiles(self):
        ''' Delete all the transient input files. '''

        for filename in self.TransientInputFiles:
            DebugPrint(1, 'Deleting transient input file: '+filename)
            RemoveFile(filename)
        self.TransientInputFiles = []

