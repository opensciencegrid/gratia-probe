
import os
import re
import glob
import string
import fnmatch
import xml.dom.minidom

import gratia.common.config as config
import gratia.common.utils as utils
import gratia.common.file_utils as file_utils
from gratia.common.debug import DebugPrint

Config = config.ConfigProxy()

__quoteSplit = re.compile(' *"([^"]*)"')
__certinfoLocalJobIdMunger = re.compile(r'(?P<ID>\d+(?:\.\d+)*)')
__certinfoJobManagerExtractor = re.compile(r'gratia_certinfo_(?P<JobManager>(?:[^\d_][^_]*))')

def FixDN(DN):

    # Put DN into a known format: /-separated with USERID= instead of UID=

    fixedDN = string.replace(string.join(string.split(DN, r', '), r'/'), r'/UID=', r'/USERID=')
    if fixedDN[0] != r'/':
        fixedDN = r'/' + fixedDN
    return fixedDN


def GetNode(nodeList, nodeIndex=0):
    if nodeList == None or nodeList.length <= nodeIndex:
        return None
    return nodeList.item(0)


def GetNodeData(nodeList, nodeIndex=0):
    if nodeList == None or nodeList.length <= nodeIndex or nodeList.item(0).firstChild == None:
        return None
    return nodeList.item(0).firstChild.data


def removeCertInfoFile(xmlDoc, userIdentityNode, namespace):
    ''' Use localJobID and probeName to find cert info file and remove file'''
    # Collect data needed by certinfo reader

    DebugPrint(4, 'DEBUG: Get JobIdentity')
    jobIdentityNode = GetNode(xmlDoc.getElementsByTagNameNS(namespace, 'JobIdentity'))
    if jobIdentityNode == None:
        return
    DebugPrint(4, 'DEBUG: Get JobIdentity: OK')
    localJobId = GetNodeData(jobIdentityNode.getElementsByTagNameNS(namespace, 'LocalJobId'))
    DebugPrint(4, 'DEBUG: Get localJobId: ', localJobId)
    usageRecord = userIdentityNode.parentNode
    probeName = GetNodeData(usageRecord.getElementsByTagNameNS(namespace, 'ProbeName'))
    DebugPrint(4, 'DEBUG: Get probeName: ', probeName)

    # Use _findCertinfoFile to find and remove the file, XML is ignored
    # Looking only for exact match, globbing is disabled. 
    # Use _findCertinfoFile(localJobId, probeName) to look for more files with globbing if the exact matck
    # is not found (gratia_certinfo_*_localJobId*)
    DebugPrint(4, 'DEBUG: call _findCertinfoFile(' + str(localJobId) + r', ' + str(probeName) + ')')
    certinfo_touple = _findCertinfoFile(localJobId, probeName)
    if not certinfo_touple:
        # matching certinfo file not found
        DebugPrint(4, 'DEBUG: unable to find and remove  certinfo file')
        return None
    # Get results and remove file
    certinfo_fname =  certinfo_touple[0]
    DebugPrint(4, 'DEBUG: removing certinfo file' + str(certinfo_fname))
    file_utils.RemoveFile(certinfo_fname)  # Clean up.
    return certinfo_fname


def verifyFromCertInfo(xmlDoc, userIdentityNode, namespace):
    ''' Use localJobID and probeName to find cert info file and insert info into XML record'''

    # Collect data needed by certinfo reader

    DebugPrint(4, 'DEBUG: Get JobIdentity')
    jobIdentityNode = GetNode(xmlDoc.getElementsByTagNameNS(namespace, 'JobIdentity'))
    if jobIdentityNode == None:
        return
    DebugPrint(4, 'DEBUG: Get JobIdentity: OK')
    localJobId = GetNodeData(jobIdentityNode.getElementsByTagNameNS(namespace, 'LocalJobId'))
    DebugPrint(4, 'DEBUG: Get localJobId: ', localJobId)
    usageRecord = userIdentityNode.parentNode
    probeName = GetNodeData(usageRecord.getElementsByTagNameNS(namespace, 'ProbeName'))
    DebugPrint(4, 'DEBUG: Get probeName: ', probeName)

    # Read certinfo

    DebugPrint(4, 'DEBUG: call readCertInfo(' + str(localJobId) + r', ' + str(probeName) + ')')
    certInfo = readCertInfo(localJobId, probeName)
    DebugPrint(4, 'DEBUG: call readCertInfo: OK')
    DebugPrint(4, 'DEBUG: certInfo: ' + str(certInfo))
    if certInfo == None:
        DebugPrint(4, 'DEBUG: Returning without processing certInfo')
        return

    return populateFromCertInfo(certInfo, xmlDoc, userIdentityNode, namespace)


def populateFromCertInfo(certInfo, xmlDoc, userIdentityNode, namespace):
    # If DN is missing, return quickly.
    # If returning something not empty it must contain both VOName and ReportableVOName keys
    if 'DN' not in certInfo or not certInfo['DN']:
        DebugPrint(4, 'Certinfo with no DN: %s' % str(certInfo))
        if 'FQAN' in certInfo and 'VO' in certInfo:
            return {'VOName': certInfo['FQAN'], 'ReportableVOName': certInfo['VO']}
        else:
            return None

    DebugPrint(4, 'DEBUG: fixing DN')
    certInfo['DN'] = FixDN(certInfo['DN'])  # "Standard" slash format

    # First, find a KeyInfo node if it is there

    DebugPrint(4, 'DEBUG: looking for KeyInfo node')

    #    keyInfoNS = 'http://www.w3.org/2000/09/xmldsig#';
    #    keyInfoNode = GetNode(userIdentityNode.getElementsByTagNameNS(keyInfoNS, 'KeyInfo'))

    DNnode = GetNode(userIdentityNode.getElementsByTagNameNS(namespace, 'DN'))
    if DNnode and DNnode.firstChild:  # Override
        DebugPrint(4, 'DEBUG: overriding DN from certInfo')
        DNnode.firstChild.data = certInfo['DN']
    else:
        DebugPrint(4, 'DEBUG: creating fresh DN node')
        if not DNnode:
            DNnode = xmlDoc.createElementNS(namespace, 'DN')
        textNode = xmlDoc.createTextNode(certInfo['DN'])
        DNnode.appendChild(textNode)
        if not DNnode.parentNode:
            userIdentityNode.appendChild(DNnode)
        DebugPrint(4, 'DEBUG: creating fresh DN node: OK')

    # Return VO information for insertion in a common place.

    DebugPrint(4, 'DEBUG: returning VOName ' + str(certInfo['FQAN']) + ' and ReportableVOName '
               + str(certInfo['VO']))
    return {'VOName': certInfo['FQAN'], 'ReportableVOName': certInfo['VO']}



def readCertInfoLog(localJobId):
    ''' Look for and read contents of certificate log if present'''

    DebugPrint(4, 'readCertInfoLog: received (' + str(localJobId) + r')')

    # First get the list of accounting log file
    pattern = Config.get_CertInfoLogPattern()

    if pattern == r'': 
        return None
    logs = glob.glob(pattern)
    if not logs:
        return None

    # Sort from newest first
    logs_sorting = [(-os.path.getmtime(filename), filename) for filename in logs]
    logs_sorting.sort()
    logs = [filename for (_, filename) in logs_sorting]
    
    # Search in each log
    what = "lrmsID=" + str(localJobId)
    for myfile in logs:
        for line in open(myfile).readlines():
            if what in line:
                # If we could use a newer version of python (we have to work with 1.4), we could use
                # shlex:
                # res = dict(item.split('=',1) for item in shlex.split(line))
                # Newer version of python support this one line creation of the dictionary by not 1.3.4 (SL4 :()
                # res = dict(item.split('=',1) for item in __quoteSplit.findall(line))
                res = {}
                for item in __quoteSplit.findall(line):
                    split_item = item.split('=', 1)
                    res[split_item[0]] = split_item[1]
                if res.has_key('lrmsID') and res['lrmsID'] == str(localJobId):
                    if res.has_key('userDN'):
                        res['DN'] = res['userDN']
                    else:
                        res['DN'] = None
                    if res.has_key('userFQAN'):
                        res['FQAN'] = res['userFQAN']
                    else:
                        res['FQAN'] = None
                    res['VO'] = None
                    DebugPrint(0, 'Warning: found valid certinfo file for '+str(localJobId)+' in the log files: ' + pattern + ' with ' + str(res))
                    return res
    DebugPrint(0, 'Warning: unable to find valid certinfo file for '+str(localJobId)+' in the log files: ' + pattern)
    return None

# update this list as new job managers are added
jobManagers = ['batch', 'condor', 'sge', 'slurm', 'pbs', 'lsf']

def _bumpJobManager(i):
    # move jobManager[i] to the front of the list
    if i > 0:
        jobManagers.insert(0, jobManagers.pop(i))

def _findCertinfoFile(localJobId, probeName):
    ''' Look for cert info file if present.'''
    certinfo_files = []
    
    # certinfo file name is composed by job ID and jobManager (LRMS) name
    DebugPrint(4, 'findCertInfoFile: received (' + str(localJobId) + r', ' + str(probeName) + ')')

    
    # Ascertain LRMS type (jobManager) -- from explicit set method if possible, from probe name if not
    lrms = utils.getProbeBatchManager()
    if lrms == None:
        match = re.search(r'^(?P<Type>.*?):', probeName)
        if match:
            lrms = string.lower(match.group('Type'))
            DebugPrint(4, 'findCertInfoFile: obtained LRMS type ' + lrms + ' from ProbeName')

    # Ascertain local job ID

    idMatch = __certinfoLocalJobIdMunger.search(localJobId)
    if idMatch:
        DebugPrint(4, 'findCertInfoFile: trimming ' + localJobId + ' to ' + idMatch.group(1))
        localJobId = idMatch.group('ID')
    if localJobId == None:  # No LocalJobId, so no dice
        return None

    DebugPrint(4, 'findCertInfoFile: continuing to process')

    for i,jobManager in enumerate(jobManagers):
        filestem = os.path.join(Config.get_DataFolder(), 'gratia_certinfo' + r'_' + jobManager + r'_' + localJobId)
        DebugPrint(4, 'findCertInfoFile: looking for ' + filestem)
        if os.path.exists(filestem):
            certinfo_files.append(filestem)
            _bumpJobManager(i)
            break
        elif os.path.exists(filestem + '.0.0'):
            certinfo_files.append(filestem + '.0.0')
            _bumpJobManager(i)
            break

    if len(certinfo_files) == 1:
        DebugPrint(4, 'findCertInfoFile: found certinfo files %s' % (certinfo_files))

    for certinfo in certinfo_files:
        found = 0  # Keep track of whether to return info for this file.

        try:
            certinfo_doc = xml.dom.minidom.parse(certinfo)
        except KeyboardInterrupt:
            raise
        except SystemExit:
            raise
        except Exception, e:
            DebugPrint(0, 'ERROR: Unable to parse XML file ' + certinfo, ': ', e)
            continue

        # Next, find the correct information and send it back.

        certinfo_nodes = certinfo_doc.getElementsByTagName('GratiaCertInfo')
        if certinfo_nodes.length == 1:
            if len(certinfo_files) == 1:
                found = 1  # Only had one candidate -- use it
            else:

                # Check LRMS as recorded in certinfo matches our LRMS ascertained from system or probe.

                certinfo_lrms = string.lower(GetNodeData(certinfo_nodes[0].getElementsByTagName('BatchManager'
                                             ), 0))
                DebugPrint(4, 'findCertInfoFile: want LRMS ' + lrms + ': found ' + certinfo_lrms)
                if certinfo_lrms == lrms:  # Match
                    found = 1

            if found == 1:
                DebugPrint(4, 'findCertInfoFile: found certinfo ' + str(certinfo))
                return (certinfo, certinfo_nodes[0])
                #result = {'DN': GetNodeData(certinfo_nodes[0].getElementsByTagName('DN'), 0),
                #          'VO': GetNodeData(certinfo_nodes[0].getElementsByTagName('VO'), 0),
                #          'FQAN': GetNodeData(certinfo_nodes[0].getElementsByTagName('FQAN'), 0)}
                #DebugPrint(4, 'readCertInfo: removing ' + str(certinfo))
                #file_utils.RemoveFile(certinfo)  # Clean up.
                #break  # Done -- stop looking
        else:
            DebugPrint(0, 'ERROR: certinfo file ' + certinfo + ' does not contain one single valid GratiaCertInfo node'
                       )

    # if here, no result found
    DebugPrint(0, 'ERROR: unable to find valid certinfo file for job ' + localJobId)
    return None

def readCertInfoFile(localJobId, probeName):
    ''' Look for and read contents of cert info file if present. And delete the file'''
    certinfo_touple = _findCertinfoFile(localJobId, probeName)
    if not certinfo_touple:
        # matching certinfo file not found
        return None
    # Get results and remove file 
    result = {'DN': GetNodeData(certinfo_touple[1].getElementsByTagName('DN'), 0),
              'VO': GetNodeData(certinfo_touple[1].getElementsByTagName('VO'), 0),
              'FQAN': GetNodeData(certinfo_touple[1].getElementsByTagName('FQAN'), 0)}
    DebugPrint(4, 'readCertInfo: removing ' + str(certinfo_touple[0]))
    file_utils.RemoveFile(certinfo_touple[0])  # Clean up.
    return result


def readCertInfo(localJobId, probeName):
    ''' Look for the certifcate information for a job if available'''

    # First try the one per job CertInfo file
    result = readCertInfoFile(localJobId, probeName)
    
    if (result == None):
        # Second try the log files containing many certicate info, one per line.
        result = readCertInfoLog(localJobId)
    
    return result

