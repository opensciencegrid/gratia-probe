#!/usr/bin/env python
from pprint import pprint
import datetime;
import boto3;
import sys
import os
import time

class cpuUtilization:
	def __init__(self):
		self.ec2=boto3.client('ec2',region_name='us-west-2')
	def getUtilPercent(self,instid):
		ec2=boto3.client('ec2',region_name='us-west-2')
		cw = boto3.client('cloudwatch',region_name='us-west-2')
		resp=ec2.describe_instances(InstanceIds=[instid])
		#pprint(resp)
		print 'hello'
		resv=resp['Reservations']
		for reservation in resv:
			#pprint(reservation)
			instances=reservation['Instances']
			for instance in instances:
				pprint(instance)
				print instance['LaunchTime']
				launchtime=instance['LaunchTime']
				zone=instance['Placement']['AvailabilityZone']
				print zone
				inst_type=instance['InstanceType']
				print inst_type
		print launchtime.hour
		minu=launchtime.minute
		print minu
		EndTime=datetime.datetime.utcnow()
		EndTime=EndTime.replace(minute=minu)
		StartTime=EndTime.replace(hour=(EndTime.hour-1))
		print StartTime
		print EndTime
		
		response = cw.get_metric_statistics(
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
		pprint(response)
		datapoints=response['Datapoints']
		if len(datapoints)==1:
			datapoint=datapoints[0]
			average=datapoint['Average']
			print average
			return average

