#!/usr/bin/env python
from pprint import pprint;
import datetime;
import boto3;
import sys
import os
import time

class get_account_id:
	def __init__(self):
		self.ec2=boto3.client('ec2',region_name='us-west-2')

        def get_id(self):
		myec2=boto3.client('ec2',region_name='us-west-2')
                resp=myec2.describe_images(Owners=['self'])
                #pprint(resp)
                images=resp['Images']
                for image in images:
			myowner=image['OwnerId']
                        #as written this will return the last OwnerID
                        #but they should all be the same
		return myowner
