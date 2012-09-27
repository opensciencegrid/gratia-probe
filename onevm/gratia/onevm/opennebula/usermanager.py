#!/usr/bin/python

import os
import sys
import time
import socket

from  gratia.onevm.cloud.usermanager import UserManager
from gratia.onevm.process_utils import iexe_cmd

class OneUserManager(UserManager):

    def __init__(self, hostname=socket.gethostname()):
        UserManager.__init__(self, hostname=hostname)


    def getAllUsers(self):
        """
        Query to get map of Ids to user jobs
        """

        cmd = 'oneuser list --list id,user | grep -v ID'
        rc, stdout, stderr = iexe_cmd(cmd)

        for line in stdout:
            uinfo = line.strip().split()
            if len(uinfo) == 2:
                self.users[uinfo[0]] = uinfo[1]
