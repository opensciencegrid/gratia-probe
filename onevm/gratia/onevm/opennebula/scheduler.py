#!/usr/bin/python

import os
import sys
import string


from gratia.onevm.cloud.scheduler import Queue
from usermanager import OneUserManager
from gratia.onevm.process_utils import iexe_cmd
from gratia.onevm.process_utils import representsInt
from gratia.onevm.process_utils import isList


class OneQueue (Queue):

    def __init__(self, hostname):
        Queue.__init__(self, hostname=hostname)
        self.userManager = OneUserManager(hostname=hostname)
        self.fields = [
            'ID', 'STATE', 'LCM_STATE', 'STIME', 'ETIME',
            'MEMORY', 'CPU', 'VCPU',
            'HOSTNAME', 'HID', 'REASON',
            'MAC', 'IP', 'NETWORK', 'NETWORK_ID',
            'UID', 'NAME', 'GID', 'GNAME', 'USERNAME'
        ]

        self.historyFields = ['STIME', 'ETIME', 'REASON']
        # Missing info
        # 'DISK_TYPE', 'DISK_IMAGE', 'DISK_SIZE', 'DISK_IMAGE_ID', 'DISK_ID',
        # 'GID', 'GNAME', 

        self.vmStateMap = { 
            '0': 'INIT',
            '1': 'PENDING',
            '2': 'HOLD',
            '3': 'ACTIVE',
            '4': 'STOPPED',
            '5': 'SUSPENDED',
            '6': 'DONE',
            '7': 'FAILED',
        }

        self.lcmStateMap = { 
            '0': 'LCM_INIT',
            '1': 'PROLOG',
            '2': 'BOOT',
            '3': 'RUNNING',
            '4': 'MIGRATE',
            '5': 'SAVE_STOP',
            '6': 'SAVE_SUSPEND',
            '7': 'SAVE_MIGRATE',
            '8': 'PROLOG_MIGRATE',
            '9': 'PROLOG_RESUME',
            '10': 'EPILOG_STOP ',
            '11': 'EPILOG ',
            '12': 'SHUTDOWN ',
            '13': 'CANCEL',
            '14': 'FAILURE',
            '15': 'CLEANUP',
            '16': 'UNKNOWN',
        }
                        
        # Anythin not in multi entry field will have info over written
        self.multi_entry_fields = ['HOSTNAME']

        self.version = 'OpenNebula 2'

        rc,stdout,stderr = iexe_cmd('onevm list --version')
        if rc == 0:
            if stdout[0].startswith('OpenNebula 3'):
                self.version = 'OpenNebula 3'


    def getJobIds(self):
        vm_ids = []
        cmd = 'onevm list all --list ID'

        if self.version == 'OpenNebula 2':
            cmd = 'onevm list all --list id'

        rc,stdout,stderr = iexe_cmd(cmd)

        for line in stdout:
            l = line.strip()
            if representsInt(l):
                vm_ids.append(l)
        return vm_ids

    
    def getJobsInfoFiltered(self, cols=None):
        info = {}

        if cols == None:
            return info

        if not isList(cols):
            raise "Unsupported data type for cols. Should be None or list"

        if len(cols) == 0:
            return info

        cmd = 'onevm list all --list %s' % (string.join(cols)).replace(' ',',')
        rc, stdout, stderr = iexe_cmd(cmd)
        for line in stdout:
            entry = line.split()
            if (len(entry) == len(cols)) and (representsInt(entry[0])):
                info[entry[0]] = {}
                for i in range(len(cols)):
                    info[entry[0]][cols[i]] = entry[i]

        return info
                


    def getJobsInfo(self, vm_ids=None):
        """
        For the list of VM IDs get detail info about the VMs and return a
        dictionary keyed on ID
        """

        info = {}
       
        if vm_ids == None:
            #vm_ids = self.getJobIds()
            cmd = 'onevm list all --xml'
        else:
            cmd = 'onevm show --xml %s' % ' '.join(map(str, vm_ids))

        if not isList(vm_ids):
            raise "Unsupported data type for vm_ids. Should be None or list"

        rc, stdout, stderr = iexe_cmd(cmd)

        cols=['ID','USER','STAT']
        
        if self.version == 'OpenNebula 2':
            cols=['id','user','stat']

        # Just to get the username information
        filtered_info = self.getJobsInfoFiltered(cols=cols)

        vm_id = None
        vm_info = {}
        in_history = False

        for line in stdout:
            l = line.strip()
            if l == '<HISTORY>':
                in_history = True
                continue
            if l == '</HISTORY>':
                in_history = False
                continue
            for field in self.fields:
                s_str = '<%s>' % field
                e_str = '</%s>' % field

                if l.startswith(s_str) and l.endswith(e_str):
                    f_info = l.replace(s_str, '').replace(e_str, '')
                    if f_info.startswith('<![CDATA['):
                        field_info = f_info.replace('<![CDATA[', '').replace(']]>', '')
                        if field == 'MEMORY':
                            info[vm_id]['MEMORY_REQ(MB)'] = field_info
                            break
                    else:
                        field_info = f_info

                    if field == 'ID':
                        vm_id = field_info
                        info[vm_id] = {}
                        uid = 0

                        #if filtered_info.has_key(vm_id):
                        #    if filtered_info[vm_id].has_key('user'):
                        #        info[vm_id]['USERNAME'] = filtered_info[vm_id]['user']
                        #    elif filtered_info[vm_id].has_key('USER'):
                        #        info[vm_id]['USERNAME'] = filtered_info[vm_id]['USER']
                        #if not info[vm_id].has_key('USERNAME'):
                        #    if info[vm_id][uid] == 0:
                        #        info[vm_id]['USERNAME'] = 'oneadmin'

                    if field == 'USERNAME':
                        break
                    if field == 'UID':
                        try:
                            info[vm_id]['USERNAME'] = self.userManager.users[field_info]
                        except:
                            info[vm_id]['USERNAME'] = 'UNKNOWN'
                    if field == 'STATE':
                        info[vm_id]['STATE_STR'] = self.vmStateMap[field_info]
                    if field == 'LCM_STATE':
                        info[vm_id]['LCM_STATE_STR'] = self.lcmStateMap[field_info]
                    if field in self.historyFields:
                        if in_history == True:
                            if field not in ('STIME', 'ETIME'):
                                info[vm_id]['HISTORY_%s'%field] = field_info
                            break
                        else:
                            if field in ('STIME', 'ETIME'):
                                info[vm_id][field] = field_info
                                info[vm_id]['HISTORY_%s'%field] = field_info
                            break
                    
                    info[vm_id][field] = field_info
                    break

        return info


    def getJobInfo(self, vm_id):
        """
        This whole function is a quick hack to get the info
        """

        vm_info = {}
        cmd = 'onevm show --xml %s' % vm_id
        rc, stdout, stderr = iexe_cmd(cmd)

        # TODO:  Re write using python xml libs. For now just hack it up
        #        till we decide if we want to go with ruby ot python
        #        We may not even need xml in case we query the DB directly
        #        Following could be BUGGY and INEFFICIENT
        for line in stdout:
            l = line.strip()
            for field in self.fields:
                s_str = '<%s>' % field
                e_str = '</%s>' % field
                if l.startswith(s_str) and l.endswith(e_str):
                    f_info = l.replace(s_str, '').replace(e_str, '')
                    if f_info.startswith('<![CDATA['):
                        vm_info[field] = f_info.replace('<![CDATA[', '').replace(']]>', '')
                    else:
                        vm_info[field] = f_info

        return vm_info
