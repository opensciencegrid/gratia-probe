#!/usr/bin/env python
from pprint import pprint
import datetime
import boto3

from gratia.common.Gratia import DebugPrint

class Ec2Util(object):
    def __init__(self, session=None, region=None):
        if session is None and region is None:
            DebugPrint(1,"ERROR: need either a session (with default region) or region specified")

        try:
            if session is None:
                self.ec2 = boto3.resource('ec2',region)
                self.ec2_client = boto3.client('ec2',region)
                self.cw = boto3.client('cloudwatch',region)
            else:
                self.ec2 = session.resource('ec2',region)
                self.ec2_client = session.client('ec2',region)
                self.cw = session.client('cloudwatch',region)
        except Exception as e:
            DebugPrint(1,'ERROR: Unable to create ec2 or cloudwatch clients')
            DebugPrint(4,e)

    def cpu_utilization(self, instid):
        try:
            instance = self.ec2.Instance(instid)
            launchtime = instance.launch_time
            zone = instance.placement['AvailabilityZone']
            inst_type = instance.instance_type
        except Exception as e:
            DebugPrint(1,'ERROR: Error getting data for instance %s from ec2'%instid)
            DebugPrint(4,e)
            return None

        minu=launchtime.minute
        endTime=datetime.datetime.utcnow()
        endTime=endTime.replace(minute=minu)
        startTime=endTime - datetime.timedelta(hours=1)

        try:
            response = self.cw.get_metric_statistics(
                Namespace='AWS/EC2',
                MetricName='CPUUtilization',
                Dimensions=[
                    {
                        'Name': 'InstanceId',
                        'Value': instid
                    },
                ],
                StartTime=startTime,
                EndTime=endTime,
                Period=3600,
                Statistics=['Average','Minimum','Maximum'],
                Unit='Percent')
        except Exception as e:
            DebugPrint(1,'ERROR: Error getting data for instance %s from cloudwatch'%instid)
            DebugPrint(4,e)
            return None

        datapoints=response['Datapoints']
        if len(datapoints) > 0:
            datapoint=datapoints[0]
            average=datapoint['Average']
            return average
        
        return None

    def spot_price(self,instid):
        try:
            instance = self.ec2.Instance(instid)
            launchtime = instance.launch_time
            zone = instance.placement['AvailabilityZone']
            inst_type = instance.instance_type
        except Exception as e:
            DebugPrint(1,'ERROR: Error getting data for instance %s from ec2'%instid)
            DebugPrint(4,e)
            return None

        minu=launchtime.minute
        startTime=datetime.datetime.utcnow()
        if(minu>startTime.minute):
            startTime=startTime - datetime.timedelta(hours=1)
        startTime=startTime.replace(minute=minu)
        endTime=startTime
        resp1 = self.ec2_client.describe_spot_price_history(
            DryRun=False,
            StartTime=startTime,
            EndTime=endTime,
            InstanceTypes=[inst_type],
            ProductDescriptions=['Linux/UNIX'],
            Filters=[],
            AvailabilityZone=zone,
            MaxResults=1000,
            NextToken='')
        sphs=resp1['SpotPriceHistory']
        if len(sphs)==0:
            DebugPrint(2,"WARNING: no spot price history for instance %s"%instid)
            spotprice=0
        else:
            sph=sphs[0]
            spotprice=sph['SpotPrice']
        return spotprice
