#!/usr/bin/env python
from pprint import pprint
import datetime;
import boto3;
from boto3.session import Session
import sys
import os
import time
# modifying this class to support multiple accounts/profiles and regions
# Should be able to pass the session and client objects through to
# the subroutine but not sure how.
class cpuUtilization:
	def __init__(self,acct,region):
# should trap exceptions here
		self.session = Session(profile_name = acct)
		self.ec2=self.session.client('ec2',region_name=region)
                self.cw=self.session.client('cloudwatch', region_name=region)
	def getUtilPercent(self,instid):
#		ec2=boto3.client('ec2',region_name='us-west-2')
#		cw = boto3.client('cloudwatch',region_name='us-west-2')
		resp=self.ec2.describe_instances(InstanceIds=[instid])
		#pprint(resp)
		#print 'hello'
		resv=resp['Reservations']
		for reservation in resv:
			#pprint(reservation)
			instances=reservation['Instances']
			for instance in instances:
				#pprint(instance)
				#print instance['LaunchTime']
				launchtime=instance['LaunchTime']
				zone=instance['Placement']['AvailabilityZone']
				#print zone
				inst_type=instance['InstanceType']
				print inst_type
		#print launchtime.hour
		minu=launchtime.minute
		#print minu
		EndTime=datetime.datetime.utcnow()
		EndTime=EndTime.replace(minute=minu)
		StartTime=EndTime.replace(hour=(EndTime.hour-1))
		print StartTime
		print EndTime
		# should trap exceptions here		
		response = self.cw.get_metric_statistics(
		    Namespace='AWS/EC2',
		    MetricName='CPUUtilization',
		    Dimensions=[
        		{
		            'Name': 'InstanceId',
		            'Value': instid
		        },
		    ],
		    StartTime=StartTime,
		    EndTime=EndTime,
		    Period=3600,
		    Statistics=['Average','Minimum','Maximum'],
		    Unit='Percent')
		#pprint(response)
		datapoints=response['Datapoints']
		if len(datapoints)==1:
			datapoint=datapoints[0]
			average=datapoint['Average']
			#print average
			return average

