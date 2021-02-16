#!/usr/bin/python

import time

class VM:

    def __init__(self):
        self.vmId = time.time()

    def getDetails(self, vm_id):
        raise NotImplementedError

