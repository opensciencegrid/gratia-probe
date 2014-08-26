#!/usr/bin/python
# -*- coding: utf-8 -*-
# @(#)gratia/probe/common:$HeadURL: https://gratia.svn.sourceforge.net/svnroot/gratia/trunk/probe/common/Gratia.py $:$Id$

"""
Gratia Core Probe Library
"""

#pylint: disable=W0611

import os
import sys
import time
import xml.dom.minidom
import StringIO
import traceback
import re
import fileinput
import atexit
import urllib

import gratia.common.ProxyUtil as ProxyUtil
import gratia.common.send as send
import gratia.common.config as config
import gratia.common.sandbox_mgmt as sandbox_mgmt
import gratia.common.global_state as global_state
import gratia.common.reprocess as reprocess
import gratia.common.bundle as bundle
import gratia.common.connect_utils as connect_utils
import gratia.common.probe_config as probe_config
import gratia.common.probe_details as probe_details
# TODO: why condor_ce is always imported and initialization is always looking for its history directory?
import gratia.common.condor_ce as condor_ce

# These are not necessary but for backward compatibility
from gratia.common.record import Record
from gratia.common.probe_details import ProbeDetails, RegisterReporter, RegisterReporterLibrary, RegisterService
from gratia.common.probe_config import ProbeConfiguration
from gratia.common.sandbox_mgmt import QuarantineFile, SearchOutstandingRecord

from gratia.common.utils import niceNum, InternalError, ExtractCvsRevision, ExtractCvsRevisionFromFile, ExtractSvnRevision, ExtractSvnRevisionFromFile, TimeToString, setProbeBatchManager
from gratia.common.debug import Error, DebugPrint, DebugPrintTraceback
from gratia.common.xml_utils import XmlChecker, escapeXML
from gratia.common.send import Send, SendXMLFiles, Handshake
from gratia.common.reprocess import Reprocess

# Public switches
Config = config.ConfigProxy()

# List of externals files used:
# Probe configuration file
# Grid mapfile as defined by Config.get_UserVOMapFile()
# Certificate information files matching the pattern: Config.get_DataFolder() + 'gratia_certinfo' + r'_' + jobManager + r'_' + localJobId

def __disconnect_at_exit__():
    """
    Insure that we properly shutdown the connection at the end of the process.
    
    This includes sending any outstanding records and printing the statistics
    """

    if global_state.bundle_size > 1 and global_state.CurrentBundle.nItems > 0:
        responseString, _ = bundle.ProcessBundle(global_state.CurrentBundle)
        DebugPrint(0, responseString)
        DebugPrint(0, '***********************************************************')
    connect_utils.disconnect()
    if config.Config:
        try:
            sandbox_mgmt.RemoveOldLogs(Config.get_LogRotate())
            sandbox_mgmt.RemoveOldJobData(Config.get_DataFileExpiration())
            sandbox_mgmt.RemoveOldQuarantine(Config.get_DataFileExpiration(), Config.get_QuarantineSize())
        except KeyboardInterrupt:
            raise
        except SystemExit:
            raise
        except Exception, exception:
            DebugPrint(0, 'Exception caught at top level: ' + str(exception))
            DebugPrintTraceback()
    DebugPrint(0, 'End of execution summary: new records sent successfully: ' + str(bundle.successfulSendCount))
    DebugPrint(0, '                          new records suppressed: ' + str(bundle.suppressedCount))
    DebugPrint(0, '                          new records failed: ' + str(bundle.failedSendCount))
    DebugPrint(0, '                          records reprocessed successfully: '
               + str(bundle.successfulReprocessCount))
    DebugPrint(0, '                          reprocessed records failed: ' + str(bundle.failedReprocessCount))
    DebugPrint(0, '                          handshake records sent successfully: ' + str(bundle.successfulHandshakes))
    DebugPrint(0, '                          handshake records failed: ' + str(bundle.failedHandshakes))
    DebugPrint(0, '                          bundle of records sent successfully: '
               + str(bundle.successfulBundleCount))
    DebugPrint(0, '                          bundle of records failed: ' + str(bundle.failedBundleCount))
    DebugPrint(0, '                          outstanding records: ' + str(sandbox_mgmt.outstandingRecordCount))
    DebugPrint(0, '                          outstanding staged records: ' + str(sandbox_mgmt.outstandingStagedRecordCount))
    DebugPrint(0, '                          outstanding records tar files: ' + str(sandbox_mgmt.outstandingStagedTarCount))
    DebugPrint(1, 'End-of-execution disconnect ...')


def Initialize(customConfig='ProbeConfig'):
    '''This function initializes the Gratia metering engine'''

    if len(sandbox_mgmt.backupDirList) == 0:

        # This has to be the first thing done (DebugPrint uses
        # the information

        config.Config = probe_config.ProbeConfiguration(customConfig)

        DebugPrint(0, 'Initializing Gratia with ' + customConfig)

        # Initialize cleanup function.
        atexit.register(__disconnect_at_exit__)

        global_state.bundle_size = Config.get_BundleSize()
        connect_utils.timeout = Config.get_ConnectionTimeout()
        
        global_state.CurrentBundle = bundle.Bundle()

        send.Handshake()

        # Need to initialize the list of possible directories
        sandbox_mgmt.InitDirList()

        # Need to look for left over files
        sandbox_mgmt.SearchOutstandingRecord()

        # Process the Condor-CE history directory.
        condor_ce.processHistoryDir()

        # Attempt to reprocess any outstanding records

        reprocess.Reprocess()


def Maintenance():
    '''This perform routine maintenance that is usually done at'''

    send.Handshake()

    # Need to look for left over files

    sandbox_mgmt.SearchOutstandingRecord()

    # Attempt to reprocess any outstanding records

    reprocess.Reprocess()

    if global_state.bundle_size > 1 and global_state.CurrentBundle.nItems > 0:
        responseString, _ = bundle.ProcessBundle(global_state.CurrentBundle)
        DebugPrint(0, responseString)
        DebugPrint(0, '***********************************************************')


