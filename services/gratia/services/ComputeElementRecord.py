
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

class ComputeElementRecord(record.Record):
    "Base class for the Gratia ComputeElementRecord"

    def __init__(self):
        # Initializer
        super(self.__class__,self).__init__()
        DebugPrint(0,"Creating a ComputeElementRecord Record"+utils.TimeToString())

    def Print(self):
        DebugPrint(1,"ComputeElementRecord: ",self)
        
    def XmlAddMembers(self):
        " This should add the value of the 'data' member of ComputeElementRecord "
        " (as opposed to the information entered directly into self.RecordData "
        super(self.__class__,self).XmlAddMembers()

    def XmlCreate(self):

        self.XmlAddMembers()

        self.XmlData = []
        self.XmlData.append("<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n")
        self.XmlData.append("<ComputeElementRecord xmlns:urwg=\"http://www.gridforum.org/2003/ur-wg\">\n")

        # Add the record indentity
        self.XmlData.append("<RecordIdentity urwg:recordId=\""+socket.getfqdn()+":"+
                            str(global_state.RecordPid)+"."+str(record.RecordId)+"\" urwg:createTime=\""+utils.TimeToString(time.gmtime())+"\" />\n")
        record.RecordId += 1

        for data in self.RecordData:
            self.XmlData.append("\t")
            self.XmlData.append(data)
            self.XmlData.append("\n")
        self.XmlData.append("</ComputeElementRecord>\n")

    def UniqueID(self,value):
        "GlueCEUniqueID"
        self.RecordData = self.AddToList(self.RecordData, "UniqueID", "", value)
        
    def VO(self,value):
        """
        GlueCEAccessControlBaseRule
        """
        self.RecordData = self.AddToList(self.RecordData, "VO", "", value)
       
    def Timestamp(self,value):
        " The time the GlueCE was gathered "
        " Expressed in number of second since epoch or a string formated using the format xsd:dateTime. "
        if isinstance(value, str):
            realvalue = value
        else:
            realvalue = utils.TimeToString(time.gmtime(value))
        self.AppendToList(self.RecordData, "Timestamp", "", realvalue)
        
    def RunningJobs(self,value):
        """
        GlueCEStateRunningJobs
        """
        self.RecordData = self.AddToList(self.RecordData, "RunningJobs", "", str(value))
 
    def TotalJobs(self,value):
        """
        GlueCEStateTotalJobs
        """
        self.RecordData = self.AddToList(self.RecordData, "TotalJobs", "", str(value))
 
    def WaitingJobs(self,value):
        """
        GlueCEStateWaitingJobs
        """
        self.RecordData = self.AddToList(self.RecordData, "WaitingJobs", "", str(value)) 

def getComputeElementRecords(xmlDoc):
    namespace = xmlDoc.documentElement.namespaceURI
    return xmlDoc.getElementsByTagNameNS(namespace, 'ComputeElementRecord')

def ComputeElementRecordCheckXmldoc(xmlDoc,external,resourceType = None):
    " Fill in missing field in the xml document if needed "
    " If external is true, also check for ProbeName, SiteName "

    if not xmlDoc.documentElement:
        return 0 # Major problem

    # Local namespace
    namespace = xmlDoc.documentElement.namespaceURI
    # Loop over (posibly multiple) jobUsageRecords
    for ComputeElementRecord in getComputeElementRecords(xmlDoc):
        # Local namespace and prefix, if any
        prefix = ""
        for child in ComputeElementRecord.childNodes:
            if child.nodeType == xml.dom.minidom.Node.ELEMENT_NODE and \
                child.prefix:
                prefix = child.prefix + ":"
                break
                               
        xml_utils.StandardCheckXmldoc(xmlDoc,ComputeElementRecord,external,prefix)
            
    return len(getComputeElementRecords(xmlDoc))

xml_utils.XmlChecker.AddChecker(ComputeElementRecordCheckXmldoc)

