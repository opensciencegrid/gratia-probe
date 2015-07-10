#!/usr/bin/env python
import gratia.common.Gratia as Gratia
import gratia.common.GratiaCore as GratiaCore
import gratia.common.GratiaWrapper as GratiaWrapper
from gratia.common.Gratia import DebugPrint
import boto3;
from pprint import pprint;
import datetime
import spot_price

ec2=boto3.client('ec2',region_name='us-west-2')

response = ec2.describe_instances()
pprint(response)
resv=response['Reservations']
for reservation in resv:
	#pprint(reservation)
	instances=reservation['Instances']
	for instance in instances:
		print instance['InstanceId']
		print instance['InstanceType']
		tags=instance['Tags']
		print "the tags are"
		for tag in tags:
			print tag['Key'],
			print tag['Value']

		r = Gratia.UsageRecord()
		for tag in tags:
			if tag['Key'].lower == 'user'.lower:
	                	r.LocalUserId(tag['Value'])
                keyInfo=vmr.getUserKeyInfo()
                if vmr.getMachineName():
                    r.MachineName(vmr.getMachineName())
		try:
			ipaddr=instance['PublicIpAddress']
			r.MachineName(instance['PublicIpAddress'])	
		except KeyError:
			r.MachineName("no Public ip as instance has stopped")
			
                '''if  keyInfo:
                    r.UserKeyInfo(vmr.getUserKeyInfo())
			we can put the key name used to access
		'''
                r.LocalJobId(instance['InstanceId'])
                r.GlobalJobId(instance['InstanceId']+"#"+repr(time.time()))
		for tag in tags:
			if tag['Key'].lower == 'name'.lower:               
				r.JobName(tag['Value'])
		#status,description=recs[i].getStatus()
		state=instance['State']
		if state['Name'].lower=='running':
			status=1
		else:
			status=0
		description=instance['StateReason']['Code']	
                r.Status(status,description)
		r.ProcessorDescription(instance['InstanceType'])
		r.MachineNameDescription(instance['ImageId'])
		r.Host(instance['PrivateIpAddress'])
		r.ReportedSiteName('aws'+instance['Placement']['AvailabilityZone'])
		r.ResourceType('aws')
		for tag in tags:
			if tag['Key'].lower == 'project'.lower:               
				r.ProjectName(tag['Value'])
			else:
				r.ProjectName('aws')		
		
                r.Njobs(1,"")
                #r.Memory(vmr.getMemory(),"KB")
                r.NodeCount(1) # default to total
		
		instdet=inst_hardware.insthardware()
		types=instdet.gettypedetails()
		pprint(types)
		for t in types:
			if t['instance-type'] == instance['InstanceType']:
				processor=t['vcpu']
				memory=t['ram']
		
                r.Processors(processor,0,"total")
               
                # Spot price is retrieved using instance id as the charge per hour of that instance in the last hour
		print instance['InstanceId']
		sp=spot_price.spot_price()
		value=sp.get_price(instance['InstanceId'])
		print value
		r.Charge(value)
		r.ChargeUnit("$/instance Hr")
		r.ChargeDescription()
		r.ChargeFormula()
		# The Time period for which the spot price and other values are calculated is noted down
		launchtime=instance['LaunchTime']
		print launchtime.hour
		minu=launchtime.minute
		print minu
		EndTime=datetime.datetime.utcnow()
		EndTime=EndTime.replace(minute=minu)
		StartTime=EndTime.replace(hour=(EndTime.hour-1))
		print StartTime
		print EndTime
		
                r.StartTime(StartTime)
                #etime=current_time
                #if float(recs[i].getEndTime())>0:
                #    etime=float(recs[i].getEndTime())
                r.EndTime(EndTime)
                r.WallDuration(EndTime-StartTime)
		
		cpu=cpuutil.cpuUtilization()
		aver=cpu.getUtilPercent(instance['InstanceId'])
		print aver
		cpuUtil=aver
		
                r.CpuDuration(etime-stime,'user')
                r.CpuDuration(0,'system')
		if recs[i].getSubmitHost() != None:
                	r.SubmitHost(recs[i].getSubmitHost())
                r.ProjectName(self.project)
                r.ResourceType(self.resourceType)
		r.AdditionalInfo("Version",self.version)

		pprint(r)

		break
	break
