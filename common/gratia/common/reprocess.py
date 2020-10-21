

import gratia.common.global_state as global_state
import gratia.common.sandbox_mgmt as sandbox_mgmt
import gratia.common.config as config
import gratia.common.connect_utils as connect_utils
import gratia.common.response as response
import gratia.common.bundle as bundle

from gratia.common.debug import DebugPrint

Config = config.ConfigProxy()

#
# Reprocess
#
#  Loops through all outstanding records and attempts to send them again
#
def Reprocess():
    _, result = ReprocessList()
    while not connect_utils.connectionError and result and sandbox_mgmt.hasMoreOutstandingRecord:
        # This is decreased in SearchOutstanding

        tarcount = sandbox_mgmt.outstandingStagedTarCount
        scount = sandbox_mgmt.outstandingStagedRecordCount

        # Need to look for left over files
        sandbox_mgmt.SearchOutstandingRecord()
        
        if len(sandbox_mgmt.outstandingRecord) == 0:
            DebugPrint(4, 'DEBUG: quit reprocessing loop due empty list')
            break
        
        # This is potentially decreased in ReprocessList
        rcount = sandbox_mgmt.outstandingRecordCount
        
        # Attempt to reprocess any outstanding records
        ReprocessList()
        if rcount == sandbox_mgmt.outstandingRecordCount and scount == sandbox_mgmt.outstandingStagedRecordCount and tarcount \
            == sandbox_mgmt.outstandingStagedTarCount:
            DebugPrint(3, 'Reprocessing seems stalled, stopping it until next successful send')
            # We are not making progress
            break

#
# ReprocessList
#
#  Loops through all the record in the OustandingRecord list and attempts to send them again
#


def ReprocessList():
    
    currentFailedCount = 0
    currentSuccessCount = 0
    currentBundledCount = 0
    prevBundled = global_state.CurrentBundle.nItems
    prevQuarantine = bundle.quarantinedFiles
    
    responseString = r''
    
    # Loop through and try to send any outstanding records
    
    filenames = list(sandbox_mgmt.outstandingRecord.keys())
    filenames.sort() 
    for failedRecord in filenames:
        if connect_utils.connectionError:
            
            # Fail record without attempting to send.
            
            bundle.failedReprocessCount += 1
            currentFailedCount += 1
            continue
        
        xmlData = None
        
        # if os.path.isfile(failedRecord):
        
        DebugPrint(1, 'Reprocessing:  ' + failedRecord)

        # Read the contents of the file into a string of xml
        
        try:
            in_file = open(failedRecord, 'r')
            xmlData = in_file.read()
            in_file.close()
        except:
            DebugPrint(1, 'Reprocess failure: unable to read file: ' + failedRecord)
            responseString = responseString + '\nUnable to read from ' + failedRecord
            bundle.failedReprocessCount += 1
            currentFailedCount += 1
            sandbox_mgmt.RemoveRecordFile(failedRecord)
            del sandbox_mgmt.outstandingRecord[failedRecord]
            continue
        
        if not xmlData:
            DebugPrint(1, 'Reprocess failure: ' + failedRecord + ' was empty: skip send')
            responseString = responseString + '\nEmpty file ' + failedRecord + ': XML not sent'
            bundle.failedReprocessCount += 1
            currentFailedCount += 1
            sandbox_mgmt.RemoveRecordFile(failedRecord)
            del sandbox_mgmt.outstandingRecord[failedRecord]
            continue
        
        if global_state.bundle_size > 1:
            
            _, response_obj = global_state.CurrentBundle.addReprocess(failedRecord, xmlData)
            
            if response_obj.getCode() == response.Response.BundleNotSupported:
                
                # The bundling was canceled, Reprocess was called recursively, we are done.
                
                break
            elif response_obj.getCode() != 0:
                currentFailedCount += global_state.CurrentBundle.nLastProcessed - prevBundled
                currentBundledCount = global_state.CurrentBundle.nItems
                prevBundled = 0
                if connect_utils.connectionError:
                    DebugPrint(1,
                               'Connection problems: reprocessing suspended; new record processing shall continue'
                               )
            else:
                if global_state.CurrentBundle.nReprocessed == 0:
                    currentSuccessCount += global_state.CurrentBundle.nLastProcessed - prevBundled
                    currentBundledCount = global_state.CurrentBundle.nItems
                    prevBundled = 0
                else:
                    currentBundledCount += 1
        else:

            # Send the xml to the collector for processing

            response_obj = connect_utils.sendUsageXML(Config.get_ProbeName(), xmlData)

            # Determine if the call succeeded, and remove the file if it did

            if response_obj.getCode() == 0:
                DebugPrint(3, 'Processing bundle Response code for ' + failedRecord + ':  '
                           + str(response_obj.getCode()))
                DebugPrint(3, 'Processing bundle Response message for ' + failedRecord + ':  '
                           + response_obj.getMessage())
                DebugPrint(1, 'Response indicates success, ' + failedRecord + ' will be deleted')
                currentSuccessCount += 1
                bundle.successfulReprocessCount += 1
                sandbox_mgmt.RemoveRecordFile(failedRecord)
                del sandbox_mgmt.outstandingRecord[failedRecord]
            else:
                DebugPrint(1, 'Processing bundle Response code for ' + failedRecord + ':  '
                           + str(response_obj.getCode()))
                DebugPrint(1, 'Processing bundle Response message for ' + failedRecord + ':  '
                           + response_obj.getMessage())
                currentFailedCount += 1
                if connect_utils.connectionError:
                    DebugPrint(1,
                               'Connection problems: reprocessing suspended; new record processing shall continue'
                               )
                bundle.failedReprocessCount += 1

    if currentFailedCount == 0:
        responseString = 'OK'
    elif currentSuccessCount != 0:
        responseString = 'Warning'
    else:
        responseString = 'Error'
    responseString += ' - Reprocessing ' + str(currentSuccessCount) + ' record(s) uploaded, ' \
        + str(currentBundledCount) + ' bundled, ' + str(currentFailedCount) + ' failed'

    DebugPrint(0, 'Reprocessing response: ' + responseString)
    DebugPrint(1, 'After reprocessing: ' + str(sandbox_mgmt.outstandingRecordCount) + ' in outbox '
               + str(sandbox_mgmt.outstandingStagedRecordCount) + ' in staged outbox ' + str(sandbox_mgmt.outstandingStagedTarCount)
               + ' tar files')
    return (responseString, currentSuccessCount > 0 or currentBundledCount == len(list(sandbox_mgmt.outstandingRecord.keys()))
            or prevQuarantine != bundle.quarantinedFiles)

