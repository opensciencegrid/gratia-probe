
import os
import re
import sys
import glob
import xml.dom.minidom

from gratia.common.config import ConfigProxy
from gratia.common.debug import DebugPrint, DebugPrintTraceback
from gratia.common.xml_utils import safeParseXML, safeEncodeXML, XmlChecker
from gratia.common.file_utils import RemoveFile
from gratia.common.probe_details import ProbeDetails
import gratia.common.sandbox_mgmt as sandbox_mgmt
import gratia.common.bundle as bundle
import gratia.common.connect_utils as connect_utils
import gratia.common.global_state as global_state
import gratia.common.reprocess as reprocess
import gratia.common.utils as utils

Config = ConfigProxy()

successfulHandshakes = 0
failedHandshakes = 0


def Send(record):

    try:
        DebugPrint(0, '***********************************************************')
        DebugPrint(4, 'DEBUG: In Send(record)')
        DebugPrint(4, 'DEBUG: Printing record to send')
        record.Print()
        DebugPrint(4, 'DEBUG: Printing record to send: OK')

        DebugPrint(4, 'DEBUG: File Count: ' + str(sandbox_mgmt.outstandingRecordCount))
        toomanyfiles = sandbox_mgmt.outstandingRecordCount >= Config.get_MaxPendingFiles()

        if global_state.estimatedServiceBacklog > 0:
            global_state.estimatedServiceBacklog -= 1

        # Assemble the record into xml

        DebugPrint(4, 'DEBUG: Creating XML')
        record.XmlCreate()
        DebugPrint(4, 'DEBUG: Creating XML: OK')

        # Parse it into nodes, etc

        DebugPrint(4, 'DEBUG: parsing XML')
        xmlDoc = safeParseXML(''.join(record.XmlData))
        DebugPrint(4, 'DEBUG: parsing XML: OK')

        if not xmlDoc:
            responseString = 'Internal Error: cannot parse internally generated XML record'
            # We intentionally do not delete the input files.
            DebugPrint(0, responseString)
            DebugPrint(0, '***********************************************************')
            return responseString

        DebugPrint(4, 'DEBUG: Checking XML content')
        if not XmlChecker.CheckXmlDoc(xmlDoc, False):
            DebugPrint(4, 'DEBUG: Checking XML content: BAD')
            xmlDoc.unlink()
            responseString = 'OK: No unsuppressed usage records in this packet: not sending'
            record.QuarantineTransientInputFiles()
            bundle.suppressedCount += 1
            DebugPrint(0, responseString)
            DebugPrint(0, '***********************************************************')
            return responseString
        DebugPrint(4, 'DEBUG: Checking XML content: OK')

        DebugPrint(4, 'DEBUG: Normalizing XML document')
        xmlDoc.normalize()
        DebugPrint(4, 'DEBUG: Normalizing XML document: OK')

        # Generate the XML

        DebugPrint(4, 'DEBUG: Generating data to send')
        record.XmlData = utils.bytes2str(safeEncodeXML(xmlDoc)).splitlines(True)
        DebugPrint(4, 'DEBUG: Generating data to send: OK')

        # Close and clean up the document2

        xmlDoc.unlink()

        dirIndex = 0
        success = False
        f = 0

        DebugPrint(4, 'DEBUG: Attempt to back up record to send')
        while not success:
            (f, dirIndex) = sandbox_mgmt.OpenNewRecordFile(dirIndex)
            DebugPrint(3, 'Will save the record in:', f.name)
            DebugPrint(3, 'dirIndex=', dirIndex)
            if f.name != '<stdout>':
                try:
                    for line in record.XmlData:
                        f.write(line)
                    f.flush()
                    if f.tell() > 0:
                        success = True
                        DebugPrint(1, 'Saved record to ' + f.name)
                    else:
                        DebugPrint(0, 'failed to fill: ', f.name)
                        if f.name != '<stdout>':
                            sandbox_mgmt.RemoveRecordFile(f.name)
                    f.close()
                    record.RemoveTransientInputFiles()
                except:
                    DebugPrint(
                        0,
                        'failed to fill with exception: ',
                        f.name,
                        '--',
                        sys.exc_info(),
                        '--',
                        sys.exc_info()[0],
                        '++',
                        sys.exc_info()[1],
                        )
                DebugPrint(4, 'DEBUG: Backing up record to send: OK')
            else:
                break

        # Currently, the recordXml is in a list format, with each item being a line of xml.
        # the collector web service requires the xml to be sent as a string.
        # This logic here turns the xml list into a single xml string.

        usageXmlString = r''
        for line in record.XmlData:
            usageXmlString = usageXmlString + line
        DebugPrint(3, 'UsageXml:  ' + usageXmlString)

        connectionProblem = connect_utils.connectionRetries > 0 or connect_utils.connectionError

        if global_state.bundle_size > 1 and f.name != '<stdout>':

            # Delay the sending until we have 'bundle_size' records.

            (responseString, response_obj) = global_state.CurrentBundle.addRecord(f.name, usageXmlString)
        else:

            # Attempt to send the record to the collector

            response_obj = connect_utils.sendUsageXML(Config.get_ProbeName(), usageXmlString)
            responseString = response_obj.getMessage()

            DebugPrint(1, 'Response code:  ' + str(response_obj.getCode()))
            DebugPrint(1, 'Response message:  ' + response_obj.getMessage())

            # Determine if the call was successful based on the response
            # code.  Currently, 0 = success

            if response_obj.getCode() == 0:
                if f.name != '<stdout>':
                    DebugPrint(1, 'Response indicates success, ' + f.name + ' will be deleted')
                    sandbox_mgmt.RemoveRecordFile(f.name)
                else:
                    record.RemoveTransientInputFiles()
                    DebugPrint(1, 'Response indicates success')
                bundle.successfulSendCount += 1
            else:
                bundle.failedSendCount += 1
                if toomanyfiles:
                    DebugPrint(1,
                               'Due to too many pending files and a connection error, the following record was not sent and has not been backed up.'
                               )
                    DebugPrint(1, 'Lost record: ' + usageXmlString)
                    responseString = 'Fatal Error: too many pending files'
                elif f.name == '<stdout>':
                    DebugPrint(0, 'Record send failed and no backup made: record lost!')
                    responseString += '\nFatal: failed record lost!'
                    match = re.search(r'^<(?:[^:]*:)?RecordIdentity.*/>$', usageXmlString, re.MULTILINE)
                    if match:
                        DebugPrint(0, match.group(0))
                        responseString += ('\n', match.group(0))
                    match = re.search(r'^<(?:[^:]*:)?GlobalJobId.*/>$', usageXmlString, re.MULTILINE)
                    if match:
                        DebugPrint(0, match.group(0))
                        responseString += ('\n', match.group(0))
                    responseString += '\n' + usageXmlString
                else:
                    DebugPrint(1, 'Response indicates failure, ' + f.name + ' will not be deleted')

        DebugPrint(0, responseString)
        DebugPrint(0, '***********************************************************')

        if (connectionProblem or sandbox_mgmt.hasMoreOutstandingRecord) and global_state.CurrentBundle.nItems == 0 \
            and response_obj.getCode() == 0:

            # Reprocess failed records before attempting more new ones

            sandbox_mgmt.SearchOutstandingRecord()
            reprocess.Reprocess()

        return responseString
    except KeyboardInterrupt:
        raise
    except SystemExit:
        raise
    except Exception as e:
        DebugPrint(0, 'ERROR: ' + str(e) + ' exception caught while processing record ')
        DebugPrint(0, '       This record has been LOST')
        DebugPrintTraceback()
        return 'ERROR: record lost due to internal error!'


# This sends the file contents of the given directory as raw XML. The
# writer of the XML files is responsible for making sure that it is
# readable by the Gratia server.


def SendXMLFiles(fileDir, removeOriginal=False, resourceType=None):

    path = os.path.join(fileDir, '*')
    files = glob.glob(path)

    responseString = r''

    for xmlFilename in files:

        DebugPrint(0, '***********************************************************')
        if os.path.getsize(xmlFilename) == 0:
            DebugPrint(0, 'File ' + xmlFilename + ' is zero-length: skipping')
            RemoveFile(xmlFilename)
            continue
        DebugPrint(2, 'xmlFilename: ', xmlFilename)
        if sandbox_mgmt.outstandingRecordCount >= Config.get_MaxPendingFiles():
            responseString = 'Fatal Error: too many pending files'
            DebugPrint(0, responseString)
            DebugPrint(0, '***********************************************************')
            return responseString

        # Open the XML file

        try:
            xmlDoc = xml.dom.minidom.parse(xmlFilename)
        except:
            DebugPrint(
                0,
                'Failed to parse XML file ',
                xmlFilename,
                '--',
                sys.exc_info(),
                '--',
                sys.exc_info()[0],
                '++',
                sys.exc_info()[1],
                )
            xmlDoc = None

        if xmlDoc:
            DebugPrint(3, 'Adding information to parsed XML')

            xmlDoc.normalize()

            if not XmlChecker.CheckXmlDoc(xmlDoc, True, resourceType):
                xmlDoc.unlink()
                DebugPrint(0, 'No unsuppressed usage records in ' + xmlFilename + ': not sending')
                bundle.suppressedCount += 1

                # Cleanup old records - SPC - NERSC 08/28/07

                if removeOriginal:
                    RemoveFile(xmlFilename)
                continue

            # Generate the XML

            xmlData = safeEncodeXML(xmlDoc)

            # Close and clean up the document

            xmlDoc.unlink()
        else:

              # XML parsing failed: slurp the file in to xmlData and
            # send as-is.

            DebugPrint(1, 'Backing up and sending failed XML as is.')
            try:
                in_file = open(xmlFilename, 'r')
            except:
                DebugPrint(0, 'Unable to open xmlFilename for simple read')
                continue

            xmlData = in_file.readlines()
            in_file.close()

        # Open the back up file
        # fill the back up file

        dirIndex = 0
        success = False
        f = 0

        toomanyfiles = sandbox_mgmt.outstandingRecordCount >= Config.get_MaxPendingFiles()
        toomanystaged = sandbox_mgmt.outstandingStagedTarCount >= Config.get_MaxStagedArchives()

        if toomanyfiles and toomanystaged:
            DebugPrint(4, 'DEBUG: Too many pending files, the record has not been backed up')
            f = sys.stdout
        else:
            DebugPrint(4, 'DEBUG: Back up record to send')
            while not success:
                (f, dirIndex) = sandbox_mgmt.OpenNewRecordFile(dirIndex)
                DebugPrint(3, 'Will save in the record in:', f.name)
                DebugPrint(3, 'dirIndex=', dirIndex)
                if f.name == '<stdout>':
                    responseString = 'Fatal Error: unable to save record prior to send attempt'
                    DebugPrint(0, responseString)
                    DebugPrint(0, '***********************************************************')
                    return responseString
                else:
                    try:
                        for line in xmlData:
                            f.write(line)
                        f.flush()
                        if f.tell() > 0:
                            success = True
                            DebugPrint(3, 'suceeded to fill: ', f.name)
                        else:
                            DebugPrint(0, 'failed to fill: ', f.name)
                            if f.name != '<stdout>':
                                sandbox_mgmt.RemoveRecordFile(f.name)
                    except:
                        DebugPrint(
                            0,
                            'failed to fill with exception: ',
                            f.name,
                            '--',
                            sys.exc_info(),
                            '--',
                            sys.exc_info()[0],
                            '++',
                            sys.exc_info()[1],
                            )
                        if f.name != '<stdout>':
                            sandbox_mgmt.RemoveRecordFile(f.name)
                    DebugPrint(4, 'DEBUG: Backing up record to send: OK')

        if removeOriginal and f.name != '<stdout>':
            RemoveFile(xmlFilename)

        DebugPrint(1, 'Saved record to ' + f.name)

        # Currently, the recordXml is in a list format, with each
        # item being a line of xml. The collector web service
        # requires the xml to be sent as a string. This logic here
        # turns the xml list into a single xml string.

        usageXmlString = r''
        for line in xmlData:
            usageXmlString = usageXmlString + line
        DebugPrint(3, 'UsageXml:  ' + usageXmlString)

        if global_state.bundle_size > 1 and f.name != '<stdout>':

            # Delay the sending until we have 'bundle_size' records.

            (responseString, response_obj) = global_state.CurrentBundle.addRecord(f.name, usageXmlString)
        else:

            # If XMLFiles can ever be anything else than Update messages,
            # then one should be able to deduce messageType from the root
            # element of the XML.

            messageType = 'URLEncodedUpdate'

            # Attempt to send the record to the collector

            response_obj = connect_utils.sendUsageXML(Config.get_ProbeName(), usageXmlString, messageType)
            responseString = response_obj.getMessage()

            DebugPrint(1, 'Response code:  ' + str(response_obj.getCode()))
            DebugPrint(1, 'Response message:  ' + response_obj.getMessage())

            # Determine if the call was successful based on the
            # response code.  Currently, 0 = success

            if response_obj.getCode() == 0:
                if f.name != '<stdout>':
                    DebugPrint(1, 'Response indicates success, ' + f.name + ' will be deleted')
                    sandbox_mgmt.RemoveRecordFile(f.name)
                else:
                    DebugPrint(1, 'Response indicates success')
                bundle.successfulSendCount += 1
            else:
                bundle.failedSendCount += 1
                DebugPrint(1, 'Response indicates failure, ' + f.name + ' will not be deleted')

    DebugPrint(0, responseString)
    DebugPrint(0, '***********************************************************')
    return responseString


def Handshake():
    global failedHandshakes
    pdetails = ProbeDetails()

    if connect_utils.connectionError:
        # We are not currently connected, the SendHandshake
        # will reconnect us if it is possible
        result = SendHandshake(pdetails)
    else:
        # We are connected but the connection may have timed-out
        result = SendHandshake(pdetails)
        if connect_utils.connectionError:
            # Case of timed-out connection, let's try again
            failedHandshakes -= 1  # Take a Mulligan
            result = SendHandshake(pdetails)

    return result


def SendHandshake(record):
    global successfulHandshakes
    global failedHandshakes

    DebugPrint(0, '***********************************************************')

    # Assemble the record into xml

    record.XmlCreate()

    # Parse it into nodes, etc (transitional: this will eventually be native format)

    xmlDoc = safeParseXML(''.join(record.XmlData))

    if not xmlDoc:
        failedHandshakes += 1
        responseString = 'Internal Error: cannot parse internally generated XML record'
        DebugPrint(0, responseString)
        DebugPrint(0, '***********************************************************')
        return responseString

    xmlDoc.normalize()

    # Generate the XML

    record.XmlData = utils.bytes2str(safeEncodeXML(xmlDoc)).splitlines(True)

    # Close and clean up the document

    xmlDoc.unlink()

    # Currently, the recordXml is in a list format, with each item being a line of xml.
    # the collector web service requires the xml to be sent as a string.
    # This logic here turns the xml list into a single xml string.

    usageXmlString = r''
    for line in record.XmlData:
        usageXmlString = usageXmlString + line
    DebugPrint(3, 'UsageXml:  ' + usageXmlString)

    connectionProblem = connect_utils.connectionRetries > 0 or connect_utils.connectionError

    if global_state.bundle_size > 1:

        # Delay the sending until we have 'bundle_size' records.

        responseString, response_obj = global_state.CurrentBundle.addHandshake(usageXmlString)
    else:

        # Attempt to send the record to the collector. Note that this must
        # be sent currently as an update, not as a handshake.

        response_obj = connect_utils.sendUsageXML(Config.get_ProbeName(), usageXmlString)
        responseString = response_obj.getMessage()

        DebugPrint(1, 'Response code:  ' + str(response_obj.getCode()))
        DebugPrint(1, 'Response message:  ' + response_obj.getMessage())

        # Determine if the call was successful based on the response
        # code.  Currently, 0 = success

        if response_obj.getCode() == 0:
            DebugPrint(1, 'Response indicates success, ')
            successfulHandshakes += 1
            if connectionProblem or sandbox_mgmt.hasMoreOutstandingRecord:

                # Reprocess failed records before attempting more new ones

                sandbox_mgmt.SearchOutstandingRecord()
                reprocess.Reprocess()
        else:
            DebugPrint(1, 'Response indicates failure, ')
            failedHandshakes += 1

    DebugPrint(0, responseString)
    DebugPrint(0, '***********************************************************')
    return responseString


