import os
import re
import grp
import pwd
import xml.sax.saxutils
import xml.dom.minidom

import gratia.common.vo as vo
import gratia.common.utils as utils
import gratia.common.config as config
import gratia.common.certinfo as certinfo
# there should be a flag not to use HTCondor-CE if not installed (probes run elsewhere)
import gratia.common.condor_ce as condor_ce
import gratia.common.sandbox_mgmt as sandbox_mgmt

from gratia.common.debug import DebugPrint, DebugPrintTraceback

Config = config.ConfigProxy()

def safeEncodeXML(xmlDoc):
    return utils.bytes2str(xmlDoc.toxml(encoding='utf-8'))


def safeParseXML(xmlString):
    return xml.dom.minidom.parseString(xmlString)


def escapeXML(xmlData):
##
## escapeXML
##
## Author - Tim Byrne
##
##  Replaces xml-specific characters with their substitute values.  Doing so allows an xml string
##  to be included in a web service call without interfering with the web service xml.
##
## param - xmlData:  The xml to encode
## returns - the encoded xml
##
    return xml.sax.saxutils.escape(xmlData, {"'": '&apos;', '"': '&quot;'})

class XmlCheckerObject(object):

    def __init__(self):
        self.XmlRecordCheckers = []

    def AddChecker(self, checker):
        self.XmlRecordCheckers.append(checker)

    def CheckXmlDoc(self, xmlDoc, external, resourceType=None):
        content = 0
        DebugPrint(4, 'DEBUG: In CheckXmlDoc')
        for checker in self.XmlRecordCheckers:
            DebugPrint(3, 'Running : ' + str(checker) + str(xmlDoc) + str(external) + str(resourceType))
            content = content + checker(xmlDoc, external, resourceType)
        return content


XmlChecker = XmlCheckerObject()


def FindBestJobId(usageRecord, namespace):

    # Get GlobalJobId first, next recordId

    jobIdentityNodes = usageRecord.getElementsByTagNameNS(namespace, 'JobIdentity')
    if jobIdentityNodes:
        globalJobIdNodes = jobIdentityNodes[0].getElementsByTagNameNS(namespace, 'GlobalJobId')
        if globalJobIdNodes and globalJobIdNodes[0].firstChild and globalJobIdNodes[0].firstChild.data:
            return [globalJobIdNodes[0].localName, globalJobIdNodes[0].firstChild.data]

    recordIdNodes = usageRecord.getElementsByTagNameNS(namespace, 'RecordId')
    if recordIdNodes and recordIdNodes[0].firstChild and recordIdNodes[0].firstChild.data:
        return [recordIdNodes[0].localName, recordIdNodes[0].firstChild.data]

    localJobIdNodes = usageRecord.getElementsByTagNameNS(namespace, 'LocalJobId')
    if localJobIdNodes and localJobIdNodes[0].firstChild and localJobIdNodes[0].firstChild.data:
        return [localJobIdNodes[0].localName, localJobIdNodes[0].firstChild.data]

    return ['Unknown', 'Unknown']


def StandardCheckXmldoc(xmlDoc, recordElement, external, prefix):      
    '''Check for and fill in suitable values for important attributes'''
        
    if not xmlDoc.documentElement:  # Major problem
        return
            
    if external:
            
        # Local namespace
        namespace = xmlDoc.documentElement.namespaceURI

        # ProbeName
        probeNameNodes = recordElement.getElementsByTagNameNS(namespace, 'ProbeName')
        if not probeNameNodes:
            node = xmlDoc.createElementNS(namespace, prefix + 'ProbeName')
            textNode = xmlDoc.createTextNode(Config.get_ProbeName())
            node.appendChild(textNode)
            recordElement.appendChild(node)
        elif probeNameNodes.length > 1:
            [jobIdType, jobId] = FindBestJobId(recordElement, namespace)
            DebugPrint(0, 'Warning: too many ProbeName entities in ' + jobIdType + ' ' + jobId)

        # SiteName
        siteNameNodes = recordElement.getElementsByTagNameNS(namespace, 'SiteName')
        if not siteNameNodes:
            node = xmlDoc.createElementNS(namespace, prefix + 'SiteName')
            textNode = xmlDoc.createTextNode(Config.get_SiteName())
            node.appendChild(textNode)
            recordElement.appendChild(node)
        elif siteNameNodes.length > 1:
            [jobIdType, jobId] = FindBestJobId(recordElement, namespace)
            DebugPrint(0, 'Warning: too many SiteName entities in ' + jobIdType + ' ' + jobId)

        # grid
        gridNodes = recordElement.getElementsByTagNameNS(namespace, 'Grid')
        if not gridNodes:
            node = xmlDoc.createElementNS(namespace, prefix + 'Grid')
            textNode = xmlDoc.createTextNode(Config.get_Grid())
            node.appendChild(textNode)
            recordElement.appendChild(node)
        elif gridNodes.length == 1:
            grid = gridNodes[0].firstChild.data
            grid_info = Config.get_Grid() 
            if grid_info and (not grid or grid == 'Unknown'):
                gridNodes[0].firstChild.data = grid_info
            if not gridNodes[0].firstChild.data:  # Remove null entry
                recordElement.removeChild(gridNodes[0])
                gridNodes[0].unlink()
        else:
            # Too many entries
            (jobIdType, jobId) = FindBestJobId(recordElement, namespace)
            DebugPrint(0, 'Warning: too many grid entities in ' + jobIdType + ' ' + jobId)


def getUsageRecords(xmlDoc):
    if not xmlDoc.documentElement:  # Major problem
        return []
    namespace = xmlDoc.documentElement.namespaceURI
    return xmlDoc.getElementsByTagNameNS(namespace, 'UsageRecord') + xmlDoc.getElementsByTagNameNS(namespace,
            'JobUsageRecord')


def UsageCheckXmldoc(xmlDoc, external, resourceType=None):
    '''Fill in missing field in the xml document if needed'''

    DebugPrint(4, 'DEBUG: In UsageCheckXmldoc')
    DebugPrint(4, 'DEBUG: Checking xmlDoc integrity')
    if not xmlDoc.documentElement:  # Major problem
        return 0
    DebugPrint(4, 'DEBUG: Checking xmlDoc integrity: OK')
    DebugPrint(4, 'DEBUG: XML record to send: \n' + xmlDoc.toxml())

    # Local namespace

    namespace = xmlDoc.documentElement.namespaceURI

    # Loop over (posibly multiple) jobUsageRecords

    DebugPrint(4, 'DEBUG: About to examine individual UsageRecords')
    for usageRecord in getUsageRecords(xmlDoc):
        DebugPrint(4, 'DEBUG: Examining UsageRecord')
        DebugPrint(4, 'DEBUG: Looking for prefix')

        # Local namespace and prefix, if any

        prefix = r''
        for child in usageRecord.childNodes:
            if child.nodeType == xml.dom.minidom.Node.ELEMENT_NODE and child.prefix:
                prefix = child.prefix + ':'
                break

        DebugPrint(4, 'DEBUG: Looking for prefix: ' + prefix)

        StandardCheckXmldoc(xmlDoc, usageRecord, external, prefix)

        # Add ResourceType if appropriate

        if external and resourceType != None:
            DebugPrint(4, 'DEBUG: Adding missing resourceType ' + str(resourceType))
            AddResourceIfMissingKey(
                xmlDoc,
                usageRecord,
                namespace,
                prefix,
                'ResourceType',
                resourceType,
                )

        # Identity info check

        VOName = None

        DebugPrint(4, 'DEBUG: Finding userIdentityNodes')
        userIdentityNodes = usageRecord.getElementsByTagNameNS(namespace, 'UserIdentity')
        DebugPrint(4, 'DEBUG: Finding userIdentityNodes (processing)')
        if not userIdentityNodes:
            DebugPrint(4, 'DEBUG: Finding userIdentityNodes: 0')
            [jobIdType, jobId] = FindBestJobId(usageRecord, namespace)
            DebugPrint(0, 'Warning: no UserIdentity block in ' + jobIdType + ' ' + jobId)
        else:
            try:
                id_info = {}
                DebugPrint(4, 'DEBUG: Finding userIdentityNodes (processing 2)')
                DebugPrint(4, 'DEBUG: Finding userIdentityNodes: ' + str(userIdentityNodes.length))
                if userIdentityNodes.length > 1:
                    [jobIdType, jobId] = FindBestJobId(usageRecord, namespace)
                    DebugPrint(0, 'Warning: too many UserIdentity blocks  in ' + jobIdType + ' ' + jobId)

                ResourceType = FirstResourceMatching(xmlDoc, usageRecord, namespace, prefix, 'ResourceType')
                DebugPrint(4, 'DEBUG: Read ResourceType as ' + str(ResourceType))
                use_certinfo = True
                # Storage (transfers on SEs) do not use certinfo files
                if ResourceType and ResourceType == 'Storage':
                    use_certinfo = False 
                DebugPrint(4, 'DEBUG: Call CheckAndExtendUserIdentity')
                id_info = CheckAndExtendUserIdentity(xmlDoc, userIdentityNodes[0], namespace, prefix, use_certinfo)
                DebugPrint(4, 'DEBUG: Call CheckAndExtendUserIdentity: OK')
                if Config.get_NoCertinfoBatchRecordsAreLocal() and ResourceType and ResourceType == 'Batch' \
                    and not ('has_certinfo' in id_info and id_info['has_certinfo']):

                    # Set grid local

                    DebugPrint(4, 'DEBUG: no certinfo: setting grid to Local')
                    UpdateOrInsertElement(
                        xmlDoc,
                        usageRecord,
                        namespace,
                        prefix,
                        'Grid',
                        'Local',
                        )
                if 'VOName' in id_info:
                    VOName = id_info['VOName']
            except KeyboardInterrupt:
                raise   
            except SystemExit:
                raise   
            except Exception as e:
                DebugPrint(0, 'DEBUG: Caught exception: ', e)
                DebugPrintTraceback()
                raise

        # If we are trying to handle only GRID jobs, optionally suppress records.
        #
        # Order of preference from the point of view of data integrity:
        #
        # 1. With grid set to Local (modern condor probe (only) detects
        # attribute inserted in ClassAd by Gratia JobManager patch found
        # in OSG 1.0+).
        #
        # 2, Missing DN (preferred, but requires JobManager patch and
        # could miss non-delegated WS jobs).
        #
        # 3. A null or unknown VOName (prone to suppressing jobs we care
        # about if osg-user-vo-map.txt is not well-cared-for).

        reason = None
        isQuarantined=False
        grid = GetElement(xmlDoc, usageRecord, namespace, prefix, 'Grid')
        if Config.get_SuppressgridLocalRecords() and grid and grid.lower() == 'local':
            # 1
            reason = 'Grid == Local'
        elif Config.get_SuppressNoDNRecords() and not usageRecord.getElementsByTagNameNS(namespace, 'DN'):
            # 2
            reason = 'missing DN'
        elif Config.get_SuppressUnknownVORecords() and (not VOName or VOName == 'Unknown'):
            # 3
            reason = 'unknown or null VOName'
        elif Config.get_QuarantineUnknownVORecords() and (not VOName or VOName == 'Unknown'):
            reason ='unknown or null VOName, will be quarantined in %s' % (os.path.join(os.path.join(Config.get_DataFolder(), "quarantine")))
            isQuarantined = True

        if reason:
            [jobIdType, jobId] = FindBestJobId(usageRecord, namespace)
            DebugPrint(0, 'Info: suppressing record with ' + jobIdType + ' ' + jobId + ' due to ' + reason)
            usageRecord.parentNode.removeChild(usageRecord)
            if isQuarantined:
                subdir = os.path.join(Config.get_DataFolder(), "quarantine", 'subdir.' + Config.getFilenameFragment())
                if not os.path.exists(subdir):
                    os.mkdir(subdir)
                fn = sandbox_mgmt.GenerateFilename("r.", subdir)
                writer = open(fn, 'w')
                usageRecord.writexml(writer)
                writer.close()
            usageRecord.unlink()
            continue

    return len(getUsageRecords(xmlDoc))


XmlChecker.AddChecker(UsageCheckXmldoc)


def CheckAndExtendUserIdentity(xmlDoc, userIdentityNode, namespace, prefix, use_certinfo=True):
    '''Check the contents of the UserIdentity block and extend if necessary
    - if Local user ID is not in the XML, then abort and return {}
    - if there are multiple (>1) VOName or ReportableVOName nodes then the XML is malformed,
      abort and return {}
    - otherwise get VOName, ReportableVOName from existing XML (if FQAN), certinfo file 
      (if use_certinfo=True), Condor-CE, 
      existing XML (also if not FQAN), reverse map file; update the values in XML and return them
    - result, dictionary w/ VOName, ReportableVOName and has_certinfo
    '''

    result = {}
    jobIdType, jobId = None, None

    # LocalUserId, used in log messages or to guess VO if all else fails 
    localUserIdNodes = userIdentityNode.getElementsByTagNameNS(namespace, 'LocalUserId')
    if not localUserIdNodes or localUserIdNodes.length != 1 or not (localUserIdNodes[0].firstChild
            and localUserIdNodes[0].firstChild.data):
        [jobIdType, jobId] = FindBestJobId(userIdentityNode.parentNode, namespace)
        DebugPrint(0, 'Warning: UserIdentity block does not have exactly ', 'one populated LocalUserId node in '
                    + jobIdType + ' ' + jobId)
        # Invalid condition, returning empty result
        return result

    LocalUserId = localUserIdNodes[0].firstChild.data

    # VOName

    VONameNodes = userIdentityNode.getElementsByTagNameNS(namespace, 'VOName')
    if VONameNodes and  VONameNodes.length == 1:
        if VONameNodes[0].hasChildNodes():
            if not VONameNodes[0].firstChild.data:
                [jobIdType, jobId] = FindBestJobId(userIdentityNode.parentNode, namespace)
                DebugPrint(0, 'Warning: UserIdentity block has VOName node, but value is set to None  in ' + jobIdType + ' ' + jobId)
                VONameNodes = None 
        else:
            VONameNodes = None 
    if not VONameNodes:
        DebugPrint(4, 'DEBUG: Creating VONameNodes elements')
        VONameNodes = []
        VONameNodes.append(xmlDoc.createElementNS(namespace, prefix + 'VOName'))
        textNode = xmlDoc.createTextNode(r'')
        VONameNodes[0].appendChild(textNode)
        userIdentityNode.appendChild(VONameNodes[0])
        DebugPrint(4, 'DEBUG: Creating VONameNodes elements DONE')
    elif VONameNodes.length > 1:
        [jobIdType, jobId] = FindBestJobId(userIdentityNode.parentNode, namespace)
        DebugPrint(0, 'Warning: UserIdentity block has multiple VOName nodes in ' + jobIdType + ' ' + jobId)
        # Invalid condition, returning empty result
        return result

    # ReportableVOName

    ReportableVONameNodes = userIdentityNode.getElementsByTagNameNS(namespace, 'ReportableVOName')
    if not ReportableVONameNodes:
        DebugPrint(4, 'DEBUG: Creating ReortableVONameNodes elements')
        ReportableVONameNodes.append(xmlDoc.createElementNS(namespace, prefix + 'ReportableVOName'))
        textNode = xmlDoc.createTextNode(r'')
        ReportableVONameNodes[0].appendChild(textNode)
        userIdentityNode.appendChild(ReportableVONameNodes[0])
        DebugPrint(4, 'DEBUG: Creating ReortableVONameNodes elements DONE')
    elif len(ReportableVONameNodes) > 1:
        [jobIdType, jobId] = FindBestJobId(userIdentityNode.parentNode, namespace)
        DebugPrint(0, 'Warning: UserIdentity block has multiple ', 'ReportableVOName nodes in ' + jobIdType
                   + ' ' + jobId)
        # Invalid condition, returning empty result
        return result

    # ###################################################################
    # Priority goes as follows:
    #
    # 1. Existing VOName if FQAN.
    #
    # 2. Certinfo.
    #
    # 3. Condor-CE direct query
    #
    # 4. Existing VOName if not FQAN.
    #
    # 5. VOName from reverse map file.
    #
    # If 1 has no value or invalid values, the first one of 2, 3, 4, 5 assigns the value (and other ar enot checked)

    vo_info = None
    no_initial_values = True
    real_fqan = False
 
    # 1. Initial values

    DebugPrint(4, 'DEBUG: reading initial VOName')
    VOName = VONameNodes[0].firstChild.data
    DebugPrint(4, 'DEBUG: current VOName = ' + VONameNodes[0].firstChild.data)

    DebugPrint(4, 'DEBUG: reading initial ReportableVOName')
    ReportableVOName = ReportableVONameNodes[0].firstChild.data
    DebugPrint(4, 'DEBUG: current ReportableVOName = ' + ReportableVONameNodes[0].firstChild.data)

    if VOName and VOName[0] == r'/':
        # Initial values are valid (1)
        # Information is available and is FQAN (starts with /)
        no_initial_values = False
 
    # 2. Certinfo (if initial values are not OK)

    if use_certinfo:
        if no_initial_values==False:
           # Initial values are valid (1)
           # Must delete possible certinfo file also when all information is available
           DebugPrint(4, 'DEBUG: Calling removeCertInfoFile')
           certinfo.removeCertInfoFile(xmlDoc, userIdentityNode, namespace)
           # Must set has_certinfo (to avoid to be considered local)
           result['has_certinfo'] = 1
        else:
            # Use certinfo
            DebugPrint(4, 'DEBUG: Calling verifyFromCertInfo')
            # look for vo_info and delete certinfo file
            vo_info = certinfo.verifyFromCertInfo(xmlDoc, userIdentityNode, namespace)
            DebugPrint(4, 'DEBUG: Calling verifyFromCertInfo: DONE')
            if vo_info:
                result['has_certinfo'] = 1
                if not (vo_info['VOName'] or vo_info['ReportableVOName']):
                    DebugPrint(4, 'DEBUG: No VOName data from verifyFromCertInfo')
                    vo_info = None  # Reset if no output.
        
            # need this because vo_info could have been reset above or may not have been set
            if vo_info:
                DebugPrint(4, 'DEBUG: Received values VOName: ' + str(vo_info['VOName']) + ' and ReportableVOName: '
                           + str(vo_info['ReportableVOName']))
                tmpVOName = vo_info['VOName']
                if vo_info['ReportableVOName'] == None:
                    if tmpVOName[0] == r'/':
                        vo_info['ReportableVOName'] = VOName.split('/')[1]
                    else:
                        vo_info['ReportableVOName'] = tmpVOName

    # 3. Condor-CE query

    if no_initial_values and not vo_info:
        DebugPrint(4, "Querying the Condor-CE directly")
        jobIdentityNode = certinfo.GetNode(xmlDoc.getElementsByTagNameNS(namespace, 'JobIdentity'))
        if jobIdentityNode:
            localJobId = certinfo.GetNodeData(jobIdentityNode.getElementsByTagNameNS(namespace, 'LocalJobId'))
            if localJobId:
                job_certinfo = condor_ce.queryJob(localJobId)
                if job_certinfo:
                    vo_info = certinfo.populateFromCertInfo(job_certinfo, xmlDoc, userIdentityNode, namespace)

    try:
        if vo_info['VOName'][0] == r'/':
            real_fqan = True
    except:
        # Could be NameError, TypeError, KeyError, IndexError 
        pass

    # 4. & 5.

    if no_initial_values and not vo_info:
        DebugPrint(4, 'DEBUG: Calling VOfromUser')
        vo_info = vo.VOfromUser(LocalUserId)
        if Config.get_MapUnknownToGroup() and not vo_info:
            fromuserid = LocalUserId
            groupid = "unknown"
            try:
                gid = pwd.getpwnam(LocalUserId)[3]
                fromuserid = grp.getgrgid(gid)[0]
                groupid = fromuserid
            except:
                pass

            # Check the differen VO mapping methods
            if Config.get_MapGroupToRole() and Config.get_VOOverride():
                # TODO: FQAN syntax is  <group>[/Role=[<role>][/Capability=<capability>]]
                # Group is part of the path, otherwise there are Role and Capability, no LocalGroup
                vo_info = {'VOName': "/%s/LocalGroup=%s" % (Config.get_VOOverride(), groupid), 'ReportableVOName': Config.get_VOOverride()}
            elif Config.get_VOOverride():
                vo_info = {'VOName': Config.get_VOOverride(), 'ReportableVOName': Config.get_VOOverride()}
            else:
                vo_info = {'VOName': fromuserid, 'ReportableVOName': fromuserid}

    # Resolve.

    if vo_info:
        DebugPrint(4, 'DEBUG: Deciding wether to use the new vo_info (%s, %s, %s, %s)' % (VOName, ReportableVOName, no_initial_values, real_fqan))
        if not (VOName and ReportableVOName) or VOName == 'Unknown' or (no_initial_values and real_fqan):
            # Update the VO values if:
            # 1. one of the initial VOName, ReportableVOName was null or empty OR
            # 2. the initial VOName is 'Unknown' OR
            # 3. the initial VOName is not a FQAN and vo_info['VOName'] is a real FQAN (from certinfo or HTCondor-CE) 
            if vo_info['VOName'] == None:
                vo_info['VOName'] = r''
            if vo_info['ReportableVOName'] == None:
                vo_info['ReportableVOName'] = r''
            DebugPrint(4, 'DEBUG: Updating VO info: (' + vo_info['VOName'] + r', ' + vo_info['ReportableVOName'
                       ] + ')')

            # VO info from reverse mapfile only overrides missing or
            # inadequate data.

            VONameNodes[0].firstChild.data = vo_info['VOName']
            ReportableVONameNodes[0].firstChild.data = vo_info['ReportableVOName']

    VOName = VONameNodes[0].firstChild.data
    ReportableVOName = ReportableVONameNodes[0].firstChild.data

    DebugPrint(4, 'DEBUG: final VOName = ' + VOName)
    DebugPrint(4, 'DEBUG: final ReportableVOName = ' + ReportableVOName)

    # ###################################################################

    # Clean up.

    if not VOName:
        userIdentityNode.removeChild(VONameNodes[0])
        VONameNodes[0].unlink()

    if not ReportableVOName:
        userIdentityNode.removeChild(ReportableVONameNodes[0])
        ReportableVONameNodes[0].unlink()

    result['VOName'] = VOName
    result['ReportableVOName'] = ReportableVOName

    return result


def __ResourceTool__(
    action,
    xmlDoc,
    usageRecord,
    namespace,
    prefix,
    key,
    value=r'',
    ):
    '''Private routine sitting underneath (possibly) several public ones'''

    if value == None:
        value = r''

    if action != 'UpdateFirst' and action != 'ReadValues' and action != 'ReadFirst' and action \
        != 'AddIfMissingValue' and action != 'AddIfMissingKey' and action != 'UnconditionalAdd':
        raise utils.InternalError("__ResourceTool__ gets unrecognized action '%s'" % action)

    resourceNodes = usageRecord.getElementsByTagNameNS(namespace, 'Resource')
    wantedResource = None
    foundValues = []

    # Look for existing resource of desired type

    for resource in resourceNodes:
        description = resource.getAttributeNS(namespace, 'description')
        if description == key:
            if action == 'UpdateFirst':
                wantedResource = resource
                break
            elif action == 'AddIfMissingValue':

                # Kick out if we have the attribute and value

                if resource.firstChild and resource.firstChild.data == value:
                    return None
            elif action == 'AddIfMissingKey':

                # Kick out, since we're not missing the key

                return None
            elif action == 'ReadFirst' and resource.firstChild:
                return resource.firstChild.data
            elif action == 'ReadValues' and resource.firstChild:
                foundValues.append(resource.firstChild.data)

    if action == 'ReadValues' or action == 'ReadFirst':
        return foundValues  # Done, no updating necessary

    # Found

    if wantedResource:  # UpdateFirst
        if wantedResource.firstChild:  # Return replaced value
            oldValue = wantedResource.firstChild.data
            wantedResource.firstChild.data = value
            return oldValue
        else:

              # No text data node

            textNode = xmlDoc.createTextNode(value)
            wantedResource.appendChild(textNode)
    else:

          # AddIfMissing{Key,Value}, UpdateFirst and UnconditionalAdd
            # should all drop through to here.
        # Create Resource node

        wantedResource = xmlDoc.createElementNS(namespace, prefix + 'Resource')
        wantedResource.setAttribute(prefix + 'description', key)
        textNode = xmlDoc.createTextNode(value)
        wantedResource.appendChild(textNode)
        usageRecord.appendChild(wantedResource)

    return None


def UpdateResource(
    xmlDoc,
    usageRecord,
    namespace,
    prefix,
    key,
    value,
    ):
    '''Update a resource key in the XML record'''

    return __ResourceTool__(
        'UpdateFirst',
        xmlDoc,
        usageRecord,
        namespace,
        prefix,
        key,
        value,
        )


def FirstResourceMatching(
    xmlDoc,
    usageRecord,
    namespace,
    prefix,
    key,
    ):
    '''Return value of first matching resource'''

    return __ResourceTool__(
        'ReadFirst',
        xmlDoc,
        usageRecord,
        namespace,
        prefix,
        key,
        )


def ResourceValues(
    xmlDoc,
    usageRecord,
    namespace,
    prefix,
    key,
    ):
    '''Return all found values for a given resource'''

    return __ResourceTool__(
        'ReadValues',
        xmlDoc,
        usageRecord,
        namespace,
        prefix,
        key,
        )


def AddResourceIfMissingValue(
    xmlDoc,
    usageRecord,
    namespace,
    prefix,
    key,
    value,
    ):
    """Add a resource key in the XML record if there isn't one already with the desired value"""

    return __ResourceTool__(
        'AddIfMissingValue',
        xmlDoc,
        usageRecord,
        namespace,
        prefix,
        key,
        value,
        )


def AddResourceIfMissingKey(
    xmlDoc,
    usageRecord,
    namespace,
    prefix,
    key,
    value=r'',
    ):
    """Add a resource key in the XML record if there isn't at least one resource with that key"""

    return __ResourceTool__(
        'AddIfMissingKey',
        xmlDoc,
        usageRecord,
        namespace,
        prefix,
        key,
        value,
        )


def AddResource(
    xmlDoc,
    usageRecord,
    namespace,
    prefix,
    key,
    value,
    ):
    '''Unconditionally add a resource key in the XML record'''

    return __ResourceTool__(
        'UnconditionalAdd',
        xmlDoc,
        usageRecord,
        namespace,
        prefix,
        key,
        value,
        )


def GetElement(
    xmlDoc,
    parent,
    namespace,
    prefix,
    tag,
    ):
    return __ElementTool__(
        xmlDoc,
        parent,
        namespace,
        prefix,
        tag,
        None,
        )


def GetElementOrCreateDefault(
    xmlDoc,
    parent,
    namespace,
    prefix,
    tag,
    default,
    ):
    if default == None:
        default = r''
    return __ElementTool__(
        xmlDoc,
        parent,
        namespace,
        prefix,
        tag,
        default,
        )


def __ElementTool__(
    xmlDoc,
    parent,
    namespace,
    prefix,
    tag,
    default,
    ):
    '''Get the value if the element exists; otherwise create with default value if specified.'''

    nodes = parent.getElementsByTagNameNS(namespace, tag)

    if nodes and nodes.length > 0 and nodes[0].firstChild:
        return nodes[0].firstChild.data
    elif default != None:
        UpdateOrInsertElement(
            xmlDoc,
            parent,
            namespace,
            prefix,
            tag,
            default,
            )
        return default
    else:
        return None


def UpdateOrInsertElement(
    xmlDoc,
    parent,
    namespace,
    prefix,
    tag,
    value,
    ):
    '''Update or insert the first matching node under parent.'''

    if value == None:
        value = r''

    nodes = parent.getElementsByTagNameNS(namespace, tag)

    if nodes and nodes.length > 0:
        if nodes[0].firstChild:
            nodes[0].firstChild.data = value
        else:
            textNode = xmlDoc.createTextNode(value)
            nodes[0].appendChild(textNode)
    else:
        node = xmlDoc.createElementNS(namespace, prefix + tag)
        textNode = xmlDoc.createTextNode(value)
        node.appendChild(textNode)
        parent.appendChild(node)


