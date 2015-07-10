from pprint import pprint
from boto import ec2
#from boto import cloudwatch
import boto.ec2.cloudwatch
import datetime;
import boto3;
import sys
import os
import time

class spot_price:
	def __init__(self):
		self.ec2=boto3.client('ec2',region_name='us-west-2')
		
	def get_price(self,instid):
		resp=self.ec2.describe_instances(InstanceIds=[instid])
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
		StartTime=datetime.datetime.utcnow()
		print StartTime
		if(minu>StartTime.minute):
			StartTime=StartTime.replace(hour=(StartTime.hour-1))
		StartTime=StartTime.replace(minute=minu)
		print StartTime
		EndTime=StartTime
		#response = self.ec2.describe_spot_price_history(StartTime=datetime(2015,7,8,9,00,00),EndTime=datetime(2015,7,8,9,00,00),InstanceTypes=['m3.medium'],ProductDescription=['Linux/UNIX'],AvailabilityZone='us-west-2a',NextToken='abc')
		#pprint(response)
		print 'hello'
		resp1 = self.ec2.describe_spot_price_history(
                DryRun=False,
                StartTime=StartTime,
                EndTime=EndTime,
                InstanceTypes=[inst_type],
                ProductDescriptions=['Linux/UNIX'],
                Filters=[],
                AvailabilityZone=zone,
                MaxResults=1000,
                NextToken='')
		pprint(resp1)
		sphs=resp1['SpotPriceHistory']
		if len(sphs)==0:
			print "no spot price history as Instance is not of a spot Instance type"
			spotprice=0
		else:
			sph=sphs[0]
			spotprice=sph['SpotPrice']
		print spotprice
		print 'hello'
		return spotprice
		return StartTime
if __name__ == '__main__':
	try:
		sp=spot_price()
		value=sp.get_price('i-d0952f26')
		print value
	except IndexError:
		print "The instance is not a spot type instance and Hence there is no spot price history"
	except Exception, e:
      		print >> sys.stderr, str(e)
        	sys.exit(1)
   	sys.exit(0)
