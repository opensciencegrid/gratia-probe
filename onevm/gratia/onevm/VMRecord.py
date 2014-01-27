#===============================================================================
# VMRecord - similar to JobUsageRecord 
#===============================================================================

#"46": {"VCPU": "1", "MEMORY": "290852", "NAME": "test-1", "STIME": "1319047739", "USERNAME": "tlevshin", 
#"GID": "102", "MEMORY_REQ(MB)": "256", "HID": ["6", "6"], "NETWORK_ID": "0", "DISK_IMAGE_ID": [None, None, None], 
#"LCM_STATE_STR": "RUNNING", "MAC": "02:00:c0:a8:9a:99", 
#"STATE_STR": "ACTIVE", "ID": "46", "NETWORK": "Fermicloud-Private", 
#"DISK_IMAGE": [None, None, None], "UID": "6", 
# "HISTORY_ETIME": ["1320957756", "0"],"HISTORY_REASON": ["2", "0"], "HISTORY_STIME": ["1319047755", "1320958744"], "HOSTNAME": ["fcl322", "fcl322"]},
#"DISK_TYPE": [None, "swap", "fs"], 
#"IP": "192.168.154.153", "DISK_ID": ["0", "1", "2"], "DISK_SIZE": [None, "5120", "4096"], 
#"GNAME": "docs", "STATE": "3", "CPU": "0", "ETIME": "0", "LCM_STATE": "3", 
import time
import sys

class Record:
    def __init__(self, stime,endtime,host,state,reason):
        
        self.stime=stime
        self.endtime=endtime
        self.host=host
        self.state=state
        self.reason=reason
        self.status=self.translate()
        
    def isValid(self):
        if self.status==None:
            return False
        else:
            return True
    def isRunning(self):
        if self.state=='ACTIVE' and self.reason=='0':
            return True 
        return False
    
    def translate(self):
        #0     NONE     Normal termination in host
        #1     ERROR     The VM was migrated because of an error
        #2     STOP_RESUME     The VM was migrated because of a stop/resume request
        #3     USER     The VM was migrated because of an explicit request 
        #4     CANCEL    The VM was migrated because of an explicit cancel 

        status=None
	result=-1
        if self.reason!=None:
            result=int(self.reason)
        description='VM exit code'
        if self.state =="ACTIVE":
            if result ==0:
                status=0
                description='VM is still running'
            if result>=2:
                description=description+', VM was migrated'
                status=0
        elif self.state =="DONE":
            if result == -1 or result == 1:
                status=1
            if result >=2:
                status=0
        elif self.state == "FAILED":
                status=1
        return status, description    
    
    def getSubmitHost(self):
        return self.host
    
    def getStartTime(self):
            return self.stime
        
    def getEndTime(self):
        return self.endtime
    
    def getStatus(self):
        return self.status
    def dump(self):
        print >> sys.stdout,"Start_Time: %s, End_Time: %s , Host: %s, State: %s, Reason %s, Status: %s" % (self.stime,self.endtime,self.host,
		self.state, self.reason, self.status)
    
class VMRecord:
    def __init__(self,jid,info):
 	if type(jid)== int:
 		self.jid=repr(jid)
 	else:
         	self.jid=jid
        self.info=info
        self.job_name=self.info["NAME"]
	if self.info.has_key("VCPU"):
        	self.vcpu=self.info["VCPU"]
	else:
		self.vcpu=0
        self.memory=self.info["MEMORY"]
        self.user_name=self.info["USERNAME"]
        self.state=self.info["STATE_STR"]
        self.ip=""
        if self.info.has_key("IP"):
            if type(self.info["IP"])==list:
                for ip in self.info["IP"]:
		    if self.ip=="":
			self.ip=ip
		    else:
                    	self.ip="%s/%s" % (self.ip,ip)
            else:
                self.ip=self.info["IP"]
	if self.info.has_key("DN"):
		if type(self.info["DN"])==list and len(self.info["DN"]):
			#don't know what to do with multiple dn
			self.dn=self.info["DN"][0].replace("\\20"," ")
		else:
			self.dn=self.info["DN"]
        self.records=[]
        self.setRecords()
        
    def isValid(self):
        if len(self.records)==0 or self.info['STIME']==None or int(self.info['STIME'])==0:
            return False
        else:
            return True

    def createRecord(self,ct, stime,etime,hn,state,reason):
	from datetime import date, datetime
 	if (stime == None or int(stime) == 0):
 		return
        end=int(etime)
        st=int(stime)
	d=date.fromtimestamp(st)
        # we want to report until the end of the day of GMT
	# otherwise summarization is skewed in gratia
        tdelta=datetime.utcnow()-datetime.now()
	h=23
	if tdelta.days == 0:
		h=h-int(round(tdelta.seconds/3600.))
        et=time.mktime(time.strptime("%s %s %s %s %s %s" % (d.year,d.month,d.day,h,59,59),'%Y %m %d %H %M %S'))
        if end != 0:
            ct=end
		
        while et < ct:
            tmp=Record(st,et,hn,"ACTIVE",0)
            if tmp.isValid():
                    self.records.append(tmp)
            st=et
            et=st+24*60*60

        tmp=Record(st,ct,hn,state,reason)
        if tmp.isValid():
            self.records.append(tmp)
        
    def setRecords(self):
        ct=time.time()
        if type(self.info['HISTORY_STIME'])==list:
            for i in range(len(self.info['HISTORY_STIME'])):
		stime=self.info["HISTORY_STIME"][i]
		if (i==0):
			if ( stime == None) or (int(stime)==0):
				stime=self.info["STIME"]
		else:
			if ( stime == None ) or (int(stime) == 0):
				#something is wrong with HISTORY_STIME - skiping the rest
				return

		if self.info["HISTORY_ETIME"][i]==None:
			self.info["HISTORY_ETIME"][i]=self.info["ETIME"]
			#another weird case HISTORY_ETIME=0 but ETIME is not 0
		else:
			if int(self.info["HISTORY_ETIME"][i]) == 0 and  int(self.info["ETIME"]) != 0:
				self.info["HISTORY_ETIME"][i]=self.info["ETIME"]
                self.createRecord(ct,stime,self.info["HISTORY_ETIME"][i],
                           self.info["HOSTNAME"][i],self.state,self.info['HISTORY_REASON'][i])
        else:
	    if not self.info.has_key('HISTORY_REASON'):
		reason=0
	    else:
		reason=self.info['HISTORY_REASON']
            if not self.info.has_key('HOSTNAME'):
                hostname=""
            else:
                hostname=self.info['HOSTNAME']

            self.createRecord(ct,self.info["HISTORY_STIME"],self.info["HISTORY_ETIME"],
                           hostname,self.state,reason)
                    
    def getRecords(self):
	return self.records
    def getLocalUserId(self):
        return self.user_name
        
    def getUserKeyInfo(self):
        if self.info.has_key("DN"):
            return self.dn
        else:
            return None
        
    def getLocalJobId(self):
            return self.jid
        
    def getJobName(self):
            return self.job_name
        
    def getNumOfJobs(self):
        return 1
    
    def getNumOfNodes(self):
        return 1;
    
    def getNumberOfCPU(self):
        return self.vcpu
    
    def getMemory(self):
        return int(self.memory)*1024
    def getMachineName(self):
        return self.ip
    def dump(self):
        print >> sys.stdout, "JobID: %s, Job_Name: %s, DN: %s, VCPU: %s, Memory: %s, User_Name: %s, State: %s, IP %s" % (self.jid,self.job_name,self.dn,self.vcpu,self.memory,self.user_name,self.state,self.ip)
	for r in self.records:
		r.dump()
