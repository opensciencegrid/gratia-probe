from pprint import pprint
from boto import ec2
#from boto import cloudwatch
import boto.ec2.cloudwatch
import datetime
import boto3;

#AWS_ACCESS_KEY_ID = 'XXXXXXXXXXXXXXXXXX'
#AWS_SECRET_ACCESS_KEY = 'XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX'

'''
ec2conn = ec2.connect_to_region("us-west-2")
reservations = ec2conn.get_all_instances()
instances = [i for r in reservations for i in r.instances]
for i in instances:
    pprint(i.__dict__)
    print i.id
    break # remove this to list all instances

cw = boto.ec2.cloudwatch.connect_to_region("us-west-2")
met = cw.get_metric_statistics(
        300,
        datetime.datetime.utcnow() - datetime.timedelta(seconds=600),
        datetime.datetime.utcnow(),
        'CPUUtilization',
        'AWS/EC2',
        'Average',
        dimensions={'InstanceId':['i-fe3b7509']}
   )
#pprint(met)
print len(met)

met1=met[0]
print met1
print len(met1)
print met1['Average']
met2 = cw.get_metric_statistics(
        300,
        datetime.datetime.utcnow() - datetime.timedelta(seconds=600),
        datetime.datetime.utcnow(),
        'CPUUtilization',
        'AWS/EC2',
        'Maximum',
        dimensions={'InstanceId':['i-fe3b7509']}
   )
#pprint(met2)

'''
instid='i-3ff241f7';
ec2=boto3.client('ec2',region_name='us-west-2')
cw = boto3.client('cloudwatch',region_name='us-west-2')
resp=ec2.describe_instances(InstanceIds=[instid])
pprint(resp)
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



