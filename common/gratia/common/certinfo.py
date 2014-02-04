
import os
import re
import glob
import string
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


def verifyFromCertInfo(
    xmlDoc,
    userIdentityNode,
    namespace,
    ):
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


jobManagers = []
glob_files = True

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

def readCertInfoFile(localJobId, probeName):
    ''' Look for and read contents of cert info file if present'''

    certinfo_files = []

    DebugPrint(4, 'readCertInfo: received (' + str(localJobId) + r', ' + str(probeName) + ')')

    # Ascertain LRMS type -- from explicit set method if possible, from probe name if not

    lrms = utils.getProbeBatchManager()
    if lrms == None:
        match = re.search(r'^(?P<Type>.*?):', probeName)
        if match:
            lrms = string.lower(match.group('Type'))
            DebugPrint(4, 'readCertInfo: obtained LRMS type ' + lrms + ' from ProbeName')
        elif len(jobManagers) == 0:
            DebugPrint(0,
                       'Warning: unable to ascertain lrms to match against multiple certinfo entries and no other possibilities found yet -- may be unable to resolve ambiguities'
                       )
    elif len(jobManagers) == 0:
        jobManagers.append(lrms)  # Useful default
        DebugPrint(4, 'readCertInfo: added default LRMS type ' + lrms + ' to search list')

    # Ascertain local job ID

    idMatch = __certinfoLocalJobIdMunger.search(localJobId)
    if idMatch:
        DebugPrint(4, 'readCertInfo: trimming ' + localJobId + ' to ' + idMatch.group(1))
        localJobId = idMatch.group('ID')
    if localJobId == None:  # No LocalJobId, so no dice
        return

    DebugPrint(4, 'readCertInfo: continuing to process')

    for jobManager in jobManagers:
        filestem = Config.get_DataFolder() + 'gratia_certinfo' + r'_' + jobManager + r'_' + localJobId
        DebugPrint(4, 'readCertInfo: looking for ' + filestem)
        if os.path.exists(filestem):
            certinfo_files.append(filestem)
            break
        elif os.path.exists(filestem + '.0.0'):
            certinfo_files.append(filestem + '.0.0')
            break

    if len(certinfo_files) == 1:
        DebugPrint(4, 'readCertInfo: found certinfo file ' + certinfo_files[0])
    elif glob_files:
        DebugPrint(4, 'readCertInfo: globbing for certinfo file')
        certinfo_files = glob.glob(Config.get_DataFolder() + 'gratia_certinfo_*_' + localJobId + '*')
        if certinfo_files == None or len(certinfo_files) == 0:
            DebugPrint(4, 'readCertInfo: could not find certinfo files matching localJobId ' + str(localJobId))
            glob_files = False
            DebugPrint(4, 'readCertInfo: could not find certinfo files, disabling globbing')
            return None  # No files

        if len(certinfo_files) == 1:
            fileMatch = __certinfoJobManagerExtractor.search(certinfo_files[0])
            if fileMatch:
                if fileMatch.group(1) in jobManagers:
                    # we're already checking for this jobmanager so future globbing won't help
                    glob_files = False
                    DebugPrint(4, 'readCertInfo: (1) jobManager ' + fileMatch.group(1)
                           + 'already being checked, disabling globbing')
                    
                else:
                    jobManagers.insert(0, fileMatch.group(1))  # Save to short-circuit glob next time
                    DebugPrint(4, 'readCertInfo: (1) saving jobManager ' + fileMatch.group(1)
                           + ' for future reference')

    result = None
    for certinfo in certinfo_files:
        found = 0  # Keep track of whether to return info for this file.
        result = None

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
                DebugPrint(4, 'readCertInfo: want LRMS ' + lrms + ': found ' + certinfo_lrms)
                if certinfo_lrms == lrms:  # Match
                    found = 1
                    fileMatch = __certinfoJobManagerExtractor.search(certinfo)
                    if fileMatch:
                        jobManagers.insert(0, fileMatch.group(1))  # Save to short-circuit glob next time
                        DebugPrint(4, 'readCertInfo: saving jobManager ' + fileMatch.group(1)
                                   + ' for future reference')

            if found == 1:
                result = {'DN': GetNodeData(certinfo_nodes[0].getElementsByTagName('DN'), 0),
                          'VO': GetNodeData(certinfo_nodes[0].getElementsByTagName('VO'), 0),
                          'FQAN': GetNodeData(certinfo_nodes[0].getElementsByTagName('FQAN'), 0)}
                DebugPrint(4, 'readCertInfo: removing ' + str(certinfo))
                file_utils.RemoveFile(certinfo)  # Clean up.
                break  # Done -- stop looking
        else:
            DebugPrint(0, 'ERROR: certinfo file ' + certinfo + ' does not contain one valid GratiaCertInfo node'
                       )

    if result == None:
        DebugPrint(0, 'ERROR: unable to find valid certinfo file for job ' + localJobId)
    return result


def readCertInfo(localJobId, probeName):
    ''' Look for the certifcate information for a job if available'''

    # First try the one per job CertInfo file
    result = readCertInfoFile(localJobId, probeName)
    
    if (result == None):
        # Second try the log files containing many certicate info, one per line.
        result = readCertInfoLog(localJobId)
    
    return result

