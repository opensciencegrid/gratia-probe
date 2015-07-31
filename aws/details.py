import boto3;
from pprint import pprint;
import datetime

#ec2 = boto3.resource('ec2', region_name='us-west-2')
#client = ec2.meta.client
#desc=client.describe_instances()
#print desc


ec2=boto3.client('ec2',region_name='us-west-2')
cwatch = boto3.client('cloudwatch',region_name='us-west-2')
response = ec2.describe_instances()
#pprint(response)
resv=response['Reservations']
#print resv
i=0
#pprint(resv)


for reservation in resv:
	#pprint(reservation)
	instances=reservation['Instances']
	for instance in instances:
		#print instance['InstanceId']
		#print instance['InstanceType']
		tags=instance['Tags']
		#print "the tags are"
		for tag in tags:
			#print tag['Key'],
			#print tag['Value']
		response=cwatch.list_metrics()
		#pprint(response)
		response1 = cwatch.get_metric_statistics(
		Namespace='AWS/EC2',MetricName='CPUUtilization',
		Dimensions=[
		{
            	'Name': 'InstanceId',
           	'Value': instance['InstanceId']
        	},
    		],
    		StartTime='2015-06-25T09:00:00.000',
    		EndTime='2015-06-25T10:00:00.000',
    		Period=3600,
    		Statistics=['Average'],
    		Unit='Percent'
		)
		#pprint(response1)
		
	break


