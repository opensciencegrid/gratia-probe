from boto3.session import Session

session = Session(aws_access_key_id='AKIAIV5EZ7QTHZEGIIQQ',
aws_secret_access_key='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',
region_name='us-west-2')

ec2 = session.resource('ec2')
ec2_us_west_2 = session.resource('ec2', region_name='us-west-2')

# List all of my EC2 instances in my default region.
print('Default region:')
for instance in ec2.instances.all():
	print(instance.id)
