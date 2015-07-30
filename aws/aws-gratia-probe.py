#!/usr/bin/env python
import gratia.common.Gratia as Gratia
import gratia.common.GratiaCore as GratiaCore
import gratia.common.GratiaWrapper as GratiaWrapper
from gratia.common.Gratia import DebugPrint
import boto3;
from pprint import pprint;
import datetime
from time import mktime
import time
import sys
import spot_price
import cpuutil
import inst_hardware
import os

class Awsgratiaprobe:
	def __init__(self):
		GratiaCore.Config.set_DebugLevel(5)
	        
	
	def process(self):
		ec2=boto3.client('ec2',region_name='us-west-2')	
		response = ec2.describe_instances()
		#pprint(response)
		resv=response['Reservations']
		for reservation in resv:
			#pprint(reservation)
			instances=reservation['Instances']
			for instance in instances:
				pprint(instance)
				print instance['InstanceId']
				print instance['InstanceType']
				tags=instance['Tags']
				print "the tags are"
				for tag in tags:
					print tag['Key'],
					print tag['Value']
					
				r = Gratia.UsageRecord()
				user="aws account user"
				for tag in tags:
					if tag['Key'].lower() == 'user'.lower():
			                	user=tag['Value']	
				r.LocalUserId(user)
		                #Public Ip address is retrieved if instance is running"
				try:
					ipaddr=instance['PublicIpAddress']
					r.MachineName(instance['PublicIpAddress'],instance['ImageId'])	
				except KeyError:
					r.MachineName("no Public ip as instance has been stopped",instance['ImageId'])


		                r.LocalJobId(instance['InstanceId'])
		                r.GlobalJobId(instance['InstanceId']+"#"+repr(time.time()))
				print 'hello1'
				for tag in tags:
					if tag['Key'].lower() == 'name'.lower():               
						r.JobName(tag['Value'])
				#status,description=recs[i].getStatus()
				
				state=instance['State']
				print state['Name']
				status=1
				if state['Name']=="running":
					print status
					status=0
				else:
					status=1
				#print 'hello'
				print status
				pprint(r)
				print instance['StateTransitionReason']
				description=instance['StateTransitionReason']	
		                print description
				r.Status(status,description)
				
				#r.ProcessorDescription(instance['InstanceType'])
				#r.MachineNameDescription(instance['ImageId'])
				
				try:
					ipaddr=instance['PrivateIpAddress']
					r.Host(instance['PrivateIpAddress'],False,instance['Placement']['AvailabilityZone'])
					r.SubmitHost(instance['PrivateIpAddress'],instance['Placement']['AvailabilityZone'])	
				except KeyError:
					r.SubmitHost("no Private ip as instance has been terminated")
				except Exception as e:
					print e
				print 'setting site name'
				
				#GratiaCore.Config.setSiteName('aws'+instance['Placement']['AvailabilityZone'])
				print 'done setting'
				#r.ReportedSiteName('aws'+instance['Placement']		['AvailabilityZone'])
				r.ResourceType('aws')
				project="aws-no project name given"
				for tag in tags:
					if tag['Key'].lower() == 'project'.lower():               
						project=tag['Value']		
				r.ProjectName(project)
		                r.Njobs(1,"The no of jobs running at a time")
		                r.NodeCount(1) # default to total
				hardwdet=GratiaCore.Config.getConfigAttribute("HardwareDetails")
				instdet=inst_hardware.insthardware(hardwdet)
				types=instdet.gettypedetails()
				pprint(types)
				processor='1'
				memory=''
				price=0.0
				for t in types:
					if t['instance-type'] == instance['InstanceType']:
						processor=t['vcpu']
						memory=t['ram']
						price=t['price']
				print memory," the value of memory"	
				cpu=float(processor)
		                r.Processors(cpu,0,"total",instance['InstanceType'])
		               	r.Memory(float(memory))
		                # Spot price is retrieved using instance id as the charge per hour of that instance in the last hour
				print instance['InstanceId']
				if "'SpotInstanceRequestId" in instance.keys():
					sp=spot_price.spot_price()
					value=sp.get_price(instance['InstanceId'])
					print value
					price=value
				r.Charge(str(price),"$","$/instance hr","The spot price charged in last hour corresponding to launch time")
				# The Time period for which the spot price and other values are calculated is noted down
				launchtime=instance['LaunchTime']
				print launchtime.hour
				print 'hello3'
				minu=launchtime.minute
				print minu
				
				currtime=time.time()
			
								
				EndTime=datetime.datetime.now()
				print type(EndTime)
				EndTime=EndTime.replace(minute=minu)
				StartTime=EndTime.replace(hour=(EndTime.hour-1))
				print StartTime
				print EndTime
				print 'starttime'
				t=StartTime.date()
				#print GratiaCore.TimeToString(time.mktime(t.timetuple()))
				print 'convert'
				stime=time.mktime(StartTime.timetuple())
		                r.StartTime(stime)
		                
		                et=EndTime.date()
				etime=time.mktime(EndTime.timetuple())
				r.EndTime(etime)
				print 'hello123'
				print etime-stime," the diff"
		                r.WallDuration(etime-stime)
				Cpu=cpuutil.cpuUtilization()
				aver=Cpu.getUtilPercent(instance['InstanceId'])
				print aver," average in percentage"
				print type(aver)
				print type(cpu)
				if aver is None:
					cpuUtil=0.0
					print "The CPU Utilization value is NULL as the instance was not running in the last hour"
					r.CpuDuration(0,'user')
				else:
					cpuUtil=aver
					r.CpuDuration((etime-stime)*float(aver)*cpu/100,'user')
				r.CpuDuration(0,'system')
		                r.ResourceType("AWSVM")
				r.AdditionalInfo("Version","1.0")
		
				print r
				print 'done'	
				Gratia.Send(r)
				
			


if __name__ == '__main__':
	try:
	    	Gratia.Initialize('/etc/gratia/onevm/ProbeConfig')
		GratiaWrapper.CheckPreconditions()
		vmProbe=Awsgratiaprobe()
		Filelock="filelock"
		conf=GratiaCore.Config
		duplicatelock=conf.getConfigAttribute("ExemptDuplicates")
		filelock=conf.getConfigAttribute("DuplicateFilelock")
		if  duplicatelock == "True":
	    		if os.path.isfile(Filelock):
        			fl=open(Filelock, 'r+')
	        		date=datetime.datetime.now()
	        		line=fl.readline()
	        		print line
	        		prevdate = datetime.datetime.strptime(line, "%Y-%m-%d %H:%M:%S.%f")
	        		print prevdate
	        		currtime=time.mktime(date.timetuple())
	        		prevtime=time.mktime(prevdate.timetuple())
	        		diff=currtime-prevtime
        			print diff
	        		if diff>=3599.0:
	                		fl.seek(0, 0)
        	        		fl.truncate()
	                		fl.write(str(date));
	                		t = os.path.getmtime(Filelock)
	                		print t
	                		print datetime.datetime.fromtimestamp(t)
	                		fl.close()
					vmProbe.process()	
	        		else:
			                print "hour is not over yet"
			                fl.close()
			else:
			        fl=open(Filelock,'w+')
			        date=str(datetime.datetime.now())
			        fl.write(date);
			        fl.close()
				vmProbe.process()
		else:
			vmProbe.process()
	except Exception, e:
	      	print >> sys.stderr, str(e)
	        sys.exit(1)
	sys.exit(0)	

