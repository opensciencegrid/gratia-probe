#!/usr/bin/python

import os
import sys
import time
import socket

from gratia.onevm.process_utils import isList


class Queue:

    def __init__(self, queue_id=time.time(), hostname=socket.gethostname()):
        self.queueId = queue_id
        self.hostname = hostname


    def getJobIds(self):
        """
        Query the queue to get list of Ids for jobs currently in the queue
        """

        raise NotImplementedError


    def getJobsInfo(self, vm_ids=None):
        """
        For the list of VM IDs get detail info about the VMs and return a
        dictionary keyed on ID
        """

        info = {}
        if vm_ids == None:
            vm_ids = self.getJobIds()

        if not isList(vm_ids):
            raise "Unsupported data type for vm_ids. Should be None or list"

        for vm_id in vm_ids:
             info[vm_id] = self.getJobInfo(vm_id)

        return info


    def getJobInfo(self, vm_id):
        """
        Get detailed information about the job with given Id
        """

        raise NotImplementedError
