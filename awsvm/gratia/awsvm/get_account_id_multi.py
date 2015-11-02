#!/usr/bin/env python
from pprint import pprint;
import datetime;
import boto3;
from boto3.session import Session
import sys
import os
import time
# ST --making this subroutine support multi-account and region
# should be able to pass session and client objects to the 
# subroutine but don't know how to do it.
# we are trying to get the AWS account number of the account
# we are using.  One documented way to do this is to 
# do ec2.describe_images() and grab the owner field from there.
# There may be better ways
# This assumes that there is at least one image owned in each region
# in each account.

class get_account_id:
	def __init__(self,acct,region):
		self.session=Session(profile_name=acct)
		self.ec2=self.session.client('ec2',region_name=region)

        def get_id(self):
                resp=self.ec2.describe_images(Owners=['self'])
                #pprint(resp)
                images=resp['Images']
		if len(images)<=0:
			myowner=""
			print "No images defined in this account and region"
			print "returning blank GlobalUsername"
			return myowner
                for image in images:
			myowner=image['OwnerId']
                        #as written this will return the last OwnerID
                        #but they should all be the same
		return myowner
