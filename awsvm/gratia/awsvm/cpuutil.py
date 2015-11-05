#!/usr/bin/env python
from pprint import pprint
import datetime
import boto3

from gratia.common.Gratia import DebugPrint

class CpuUtilization(object):
    def __init__(self, session=None, region=None):
        if session is None and region is None:
            DebugPrint(1,"ERROR: need either a session (with default region) or region specified")

        try:
            if session is None:
                self.ec2 = boto3.resource('ec2',region)
                self.cw = boto3.client('cloudwatch',region)
            else:
                self.ec2 = session.resource('ec2',region)
                self.cw = session.client('cloudwatch',region)
        except Exception as e:
            DebugPrint(1,'ERROR: Unable to create ec2 or cloudwatch clients')
            DebugPrint(4,e)

    def getUtilPercent(self, instid):
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
        startTime=endTime.replace(hour=(endTime.hour-1))

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
