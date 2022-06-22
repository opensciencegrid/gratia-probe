
## Updated by Brian Bockelman, University of Nebraska-Lincoln (http://rcf.unl.edu)

import time
import types
import socket
import xml.dom.minidom

import gratia.common.global_state as global_state
import gratia.common.xml_utils as xml_utils
import gratia.common.record as record
import gratia.common.utils as utils

from gratia.common.debug import DebugPrint

class StorageElement(record.Record):
    "Base class for the Gratia StorageElement"

    def __init__(self):
        # Initializer
        super(self.__class__,self).__init__()
        DebugPrint(0,"Creating a StorageElement Record"+utils.TimeToString())

    def Print(self):
        DebugPrint(1,"StorageElement: ",self)
        
    def XmlAddMembers(self):
        " This should add the value of the 'data' member of StorageElement "
        " (as opposed to the information entered directly into self.RecordData "
        super(self.__class__,self).XmlAddMembers()

    def XmlCreate(self):

        self.XmlAddMembers()

        self.XmlData = []
        self.XmlData.append("<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n")
        self.XmlData.append("<StorageElement xmlns:urwg=\"http://www.gridforum.org/2003/ur-wg\">\n")

        # Add the record indentity
        self.XmlData.append("<RecordIdentity urwg:recordId=\""+socket.getfqdn()+":"+
                            str(global_state.RecordPid)+"."+str(record.RecordId)+"\" urwg:createTime=\""+utils.TimeToString(time.gmtime())+"\" />\n")
        record.RecordId += 1

        for data in self.RecordData:
            self.XmlData.append("\t")
            self.XmlData.append(data)
            self.XmlData.append("\n")
        self.XmlData.append("</StorageElement>\n")

    def UniqueID(self,value):
        "Storage Space UniqueID"
        self.RecordData = self.AddToList(self.RecordData, "UniqueID", "", value)
        
    def SE(self,value):
        "GlueSEName"
        self.RecordData = self.AddToList(self.RecordData, "SE", "", value)
        
    def Name(self,value):
        """
        Storage Space Name
        """
        self.RecordData = self.AddToList(self.RecordData, "Name", "", value)
       
    def ParentID(self,value):
        "Storage space ParentID"
        self.RecordData = self.AddToList(self.RecordData, "ParentID", "", value)
        
    def VO(self,value):
        """
        Storage space associated VO
        """
        self.RecordData = self.AddToList(self.RecordData, "VO", "", value)
       
    def OwnerDN(self,value):
        """
        Storage space owner DN
        """
        self.RecordData = self.AddToList(self.RecordData, "OwnerDN", "", value)

    def SpaceType(self,value):
        """
        Storage SpaceType
        """
        self.RecordData = self.AddToList(self.RecordData, "SpaceType", "", value)
 
    def Timestamp(self,value):
        " The time the GlueCE was gathered "
        " Expressed in number of second since epoch or a string formated using the format xsd:dateTime. "
        if isinstance(value, str):
            realvalue = value
        else:
            realvalue = utils.TimeToString(time.gmtime(value))
        self.AppendToList(self.RecordData, "Timestamp", "", realvalue)
        
    def Implementation(self,value):
        """
        GlueSEImplementationName
        """
        self.RecordData = self.AddToList(self.RecordData, "Implementation", "", value)
 
    def Version(self,value):
        """
        GlueSEImplementationVersion
        """
        self.RecordData = self.AddToList(self.RecordData, "Version", "", value)
 
    def Status(self,value):
        """
        GlueSEStateStatus
        """
        self.RecordData = self.AddToList(self.RecordData, "Status", "", str(value))
  

def getStorageElements(xmlDoc):
    namespace = xmlDoc.documentElement.namespaceURI
    return xmlDoc.getElementsByTagNameNS(namespace, 'StorageElement')

def StorageElementCheckXmldoc(xmlDoc,external,resourceType = None):
    " Fill in missing field in the xml document if needed "
    " If external is true, also check for ProbeName, SiteName "

    if not xmlDoc.documentElement:
        return 0 # Major problem

    # Local namespace
    namespace = xmlDoc.documentElement.namespaceURI
    # Loop over (posibly multiple) jobUsageRecords
    for StorageElement in getStorageElements(xmlDoc):
        # Local namespace and prefix, if any
        prefix = ""
        for child in StorageElement.childNodes:
            if child.nodeType == xml.dom.minidom.Node.ELEMENT_NODE and \
                child.prefix:
                prefix = child.prefix + ":"
                break
                               
        xml_utils.StandardCheckXmldoc(xmlDoc,StorageElement,external,prefix)
            
    return len(getStorageElements(xmlDoc))

xml_utils.XmlChecker.AddChecker(StorageElementCheckXmldoc)


