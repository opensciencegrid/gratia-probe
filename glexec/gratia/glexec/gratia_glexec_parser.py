#
# This module will parge glexec_monitor log
# files and return gratia related information
#

import os,sys,stat
import time,calendar,string

# returns a dictionary
# where keys are (monitor_pid,glexec_uid)
# values are dictionaries
#   'start'            - Start utime
#   'jobuid'           - UID switched to
#   'DN','VO','FQAN'   - Used DN, VO, FQAN (optional)
#   'end'              - End utime (only for terminated jobs)
#   'usercpu','syscpu' - CPU seconds used in User and Kernel mode (only for terminated jobs)
def parse_log(logfile,time_limit):
    out={}
    fd=ReadBackFile(logfile)
    fd.open()
    try:
        while 1:
            try:
                line=fd.readline()
            except EOFError,e:
                break # no more data

            if line=="":
                continue # skip empty lines
            try:
                date,id,message=parse_line(line)
            except:
		#print "Can not parse, skipping ",line
                continue # skip malformed lines

            if out.has_key(id):
                el=out[id]
            else:
                el={}
                out[id]=el

            try:
                update_element(el,date,message)
            except:
                continue # skip malformed lines

            if el=={}:
                # ignore unrecognized entries
                del out[id]

            if date<time_limit:
                break # reached time limit 

        # remove entries that ended before the time limit
        for id in out.keys():
            el=out[id]
            if el.has_key('end'):
                if el['end']<time_limit:
                    del out[id]

        # nostart will a list of ids without a start section
        nostart=[]
        for id in out.keys():
            if not out[id].has_key("start"):
                nostart.append(id)

        while len(nostart)>0:
            try:
                line=fd.readline()
            except EOFError,e:
                break # no more data
            
            if line=="":
                continue # skip empty lines

            try:
                date,id,message=parse_line(line)
            except:
                continue # skip malformed lines

            if id in nostart:
                try:
                    update_element(out[id],date,message)
                except:
                    continue # skip malformed lines
                if out[id].has_key("start"):
                    nostart.remove(id)

    finally:
        fd.close()

    #remove elements without a start section, if any
    for id in nostart:
        del out[id]


    return out

#####################################################
#
# I N T E R N A L - Do not use
#
#####################################################

# This class mimics a File object
# but reads lines from back to the beginning
# it also automatically moves to filename.0 when
# finished with reading the first file
class ReadBackFile:
    def __init__(self,fname):
        self.fname=fname

    def open(self):
        self.mtime=os.stat(self.fname)[stat.ST_MTIME]
        self.fd=open(self.fname,"r")
        self.fd.seek(0,2) # go to EOF
        self.position=self.fd.tell()
        self.buffer=""

    def close(self):
        self.fd.close()
        del self.buffer

    # return the last line in the file
    def readline(self):
        # check if need to read more data
        if len(self.buffer)<512:
            self.readbuf(4096)
        if self.buffer=="":
            raise EOFError,"No more data"

        # find newline
        newline=self.buffer.rfind("\n")

        # save last line and shorten buffer
        if newline<0:
            # not found, send complete buffer
            out=self.buffer
            self.buffer=""
        else:
            out=self.buffer[(newline+1):]
            self.buffer=self.buffer[:newline]

        # return last line
        return out

    ###########################################
    # internal, read into buffer
    def readbuf(self,size):
        req_size=size
        if self.position>0:
            if size>self.position:
                size=self.position
            self.position=self.position-size
            self.fd.seek(self.position,0) # seek back from current position
            #print "Read at %i"%self.position
            part_buf=self.fd.read(size)
            self.buffer=part_buf+self.buffer

        if len(self.buffer)<size:
            new_name=self.fname+".0"
            #print "About to switch"
            if (os.access(new_name,os.R_OK) and
                (os.stat(new_name)[stat.ST_MTIME]<self.mtime)): # make sure it is an older file
                #print "switched"
                self.close()
                self.fname=new_name
                self.open()
                self.readbuf(req_size) # even if larger,better maintaing same granularity
        return
            
def parse_line_v1(line):
    # looking for [<date>#<monitor_id> <glexec_id>] Msg\n
    if line[0]!='[':
        raise RuntimeError,"Not starting with [ (%s)"%line
    header,message=string.split(line[1:],'] ',1)
    date,idstr=string.split(header,'#',1)
    mon_str,gl_str=string.split(idstr)

    return (long(date),(int(mon_str),int(gl_str)),message)

def parseISO8601_UTC(datestr):
    ts=time.strptime(datestr,"%Y-%m-%dT%H:%M:%SZ")
    t=calendar.timegm(ts)
    return t

def parseISO8601_Local(datestr):
    # first get the base time
    ts=time.strptime(datestr[:-6],"%Y-%m-%dT%H:%M:%S")
    t=calendar.timegm(ts)
    # then get the timezone
    tdstr=datestr[-6:]
    tdelta=(int(tdstr[1:3])*60+int(tdstr[4:6]))*60
    tdeltaWsign=tdelta*([-1,1][tdstr[0]=='-'])
    # put them together
    gmt=t+tdeltaWsign
    return gmt

def parseISO8601(datestr):
    if datestr[-1]=='Z':
      return parseISO8601_UTC(datestr)
    else:
      return parseISO8601_Local(datestr)

def parse_line_v3(line):
    import datetime
    #syslog type of message
    #<LOCAL_DATE> hostname glexec.mon[<monitor_id>#<glexec_id>]: message\n
    indx=line.find("glexec.mon[")
    tmp=line[:indx].strip().replace("  "," ")
    info = tmp.split(" ", 4)
    if len(tmp) >= 4:
        tmp = " ".join(info[:4])
    datestr=tmp[:tmp.rfind(" ")]
    #syslog doesn't have year, so we have to guess year ourselves 
    now=datetime.datetime.now()
    ts=time.strptime("%s %s"% (now.year,datestr.strip()),"%Y %b %d %H:%M:%S")
    if time.mktime(ts)>time.mktime(now.timetuple()):
	#we are in new year already, get a previous year
        ts=time.strptime("%s %s"% (now.year-1,datestr.strip()),"%Y %b %d %H:%M:%S")
    date=time.mktime(ts)
    tmp=line[indx:].strip()
    message=tmp[tmp.find(":")+1:].strip()
    tmp=line[indx+1:line.find("]:")]
    mon_str,gl_str=line[indx+len("glexec.mon["):(line[indx:].find("]:")+indx)].split("#")
    return (long(date),(int(mon_str),int(gl_str)),message)


def parse_line_v2(line):
    #looking for glemon[<monitor_id>#<glexec_id>]: <date> Msg\n
    if line[:7]!='glemon[':
       raise RuntimeError,"Not starting with glemon[ (%s)"%line  
    header,messageWdate=line[7:].split(']: ',1)
    mon_str,gl_str=header.split('#',1)
    datestr,message=messageWdate.split(' ',1)

    date=parseISO8601(datestr)

    return (long(date),(int(mon_str),int(gl_str)),message)

def parse_line(line):
    if line[0]=='[':
      return parse_line_v1(line)
    else:
      if line.find("glemon")==0:
      	return parse_line_v2(line)
      else:
      	return parse_line_v3(line)

	

def update_element(el,date,msg):
    msg7=msg[:7]
    if msg7=="Started":
        el["start"]=date
        if not el.has_key("useruid"):
            # do not overwrite, keep the newer one
            uididx=msg.rfind(" ")+1
            el["jobuid"]=int(msg[uididx:])
    elif msg7=="New uid":
        if not el.has_key("useruid"):
            # do not overwrite, keep the newer one
            uididx=msg.rfind(" ")+1
            el["jobuid"]=int(msg[uididx:])
    elif msg7=="Used DN":
        el["DN"]=msg[10:-1]
    elif msg7=="Used VO":
        el["VO"]=string.split(msg[10:],'"',1)[0]
    elif msg7=="Used FQ":
        el["FQAN"]=msg[12:-1] # if there are many listed, the oldest will prevail
    elif msg7=="Termina":
        el["end"]=date
        el["usercpu"]=1
        sysidx=msg.rfind(" ")+1
        el["syscpu"]=long(msg[sysidx:])
        useridx=msg.rfind(" ",0,sysidx-9)+1
        el["usercpu"]=long(msg[useridx:sysidx-8])
    return
    
