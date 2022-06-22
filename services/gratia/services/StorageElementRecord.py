
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

class StorageElementRecord(record.Record):
    "Base class for the Gratia StorageElementRecord"

    def __init__(self):
        # Initializer
        super(self.__class__,self).__init__()
        DebugPrint(0,"Creating a StorageElementRecord Record"+utils.TimeToString())

    def Print(self):
        DebugPrint(1,"StorageElementRecord: ",self)
        
    def XmlAddMembers(self):
        " This should add the value of the 'data' member of StorageElementRecord "
        " (as opposed to the information entered directly into self.RecordData "
        super(self.__class__,self).XmlAddMembers()

    def XmlCreate(self):

        self.XmlAddMembers()

        self.XmlData = []
        self.XmlData.append("<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n")
        self.XmlData.append("<StorageElementRecord xmlns:urwg=\"http://www.gridforum.org/2003/ur-wg\">\n")

        # Add the record indentity
        self.XmlData.append("<RecordIdentity urwg:recordId=\""+socket.getfqdn()+":"+
                            str(global_state.RecordPid)+"."+str(record.RecordId)+"\" urwg:createTime=\""+utils.TimeToString(time.gmtime())+"\" />\n")
        record.RecordId += 1

        for data in self.RecordData:
            self.XmlData.append("\t")
            self.XmlData.append(data)
            self.XmlData.append("\n")
        self.XmlData.append("</StorageElementRecord>\n")

    def UniqueID(self,value):
        "Storage space UniqueID"
        self.RecordData = self.AddToList(self.RecordData, "UniqueID", "", value)
        
    def MeasurementType(self,value):
        """
        Measurement type
        """
        self.RecordData = self.AddToList(self.RecordData, "MeasurementType", "", value)

    def StorageType(self,value):
        """
        Space type
        """
        self.RecordData = self.AddToList(self.RecordData, "StorageType", "", value)

    def Timestamp(self,value):
        " The time the GlueCE was gathered "
        " Expressed in number of second since epoch or a string formated using the format xsd:dateTime. "
        if isinstance(value, str):
            realvalue = value
        else:
            realvalue = utils.TimeToString(time.gmtime(value))
        self.AppendToList(self.RecordData, "Timestamp", "", realvalue)
        
    def TotalSpace(self,value):
        """
        Total space (GB)
        """
        self.RecordData = self.AddToList(self.RecordData, "TotalSpace", "", str(value))
 
    def FreeSpace(self,value):
        """
        Free space (GB)
        """
        self.RecordData = self.AddToList(self.RecordData, "FreeSpace", "", str(value))
 
    def UsedSpace(self,value):
        """
        Used space (GB)
        """
        self.RecordData = self.AddToList(self.RecordData, "UsedSpace", "", str(value)) 

    def FileCountLimit(self,value):
        """
        Number of files that can be stored in this space.
        """
        self.RecordData = self.AddToList(self.RecordData, "FileCountLimit", "", str(value))
 
    def FileCount(self,value):
        """
        Number of files currently in this space.
        """
        self.RecordData = self.AddToList(self.RecordData, "FileCount", "", str(value))

def getStorageElementRecords(xmlDoc):
    namespace = xmlDoc.documentElement.namespaceURI
    return xmlDoc.getElementsByTagNameNS(namespace, 'StorageElementRecord')

def StorageElementRecordCheckXmldoc(xmlDoc,external,resourceType = None):
    " Fill in missing field in the xml document if needed "
    " If external is true, also check for ProbeName, SiteName "

    if not xmlDoc.documentElement:
        return 0 # Major problem

    # Local namespace
    namespace = xmlDoc.documentElement.namespaceURI
    # Loop over (posibly multiple) jobUsageRecords
    for StorageElementRecord in getStorageElementRecords(xmlDoc):
        # Local namespace and prefix, if any
        prefix = ""
        for child in StorageElementRecord.childNodes:
            if child.nodeType == xml.dom.minidom.Node.ELEMENT_NODE and \
                child.prefix:
                prefix = child.prefix + ":"
                break
                               
        xml_utils.StandardCheckXmldoc(xmlDoc,StorageElementRecord,external,prefix)
            
    return len(getStorageElementRecords(xmlDoc))

xml_utils.XmlChecker.AddChecker(StorageElementRecordCheckXmldoc)


