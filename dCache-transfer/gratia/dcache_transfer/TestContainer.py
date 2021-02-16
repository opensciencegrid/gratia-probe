"""
This module generates and executes a test of the dCache-transfer probe.

We simulate the results of a DB query and make sure that it gets properly
aggregated.
"""

from __future__ import absolute_import
from __future__ import print_function

import re
import time
import random
import datetime

from . import TimeBinRange
from . import Collapse
from . import BillingRecSimulator

class SimInterrupt:
    pass

# test clean area
# generate 6 hours worth of records
# aggegated records should overlap between seconds
# parse out query time stamp
# return list of rows sorted by time
# route A: record limit is not hit 
# A1 report total transferred
# A2 aggregate and report transfferrred
# assertion : total transferred should be the same
# route B: record limit is hit
# reshufle sorted list randomly
# interrupt probe at random times
# assertion check - total transferred should be the same as in route A

TEST = 0
StartTime = 1272314919 - 24*3600
EndTime = StartTime + 4*3600 + 700

recordsToSend = []
addedTransactions = {}

def isTest():
    return TEST

def getMaxAge():
    return  (time.time() - StartTime)/(3600*24)

def getEndDateTime():
    return datetime.datetime.fromtimestamp(EndTime + 3600)

def sendInterrupt(freq):
    """
    Randomly raises an interrupt exception
    """
    if TEST:
        if random.randint(0,freq) == 0:
            raise SimInterrupt()

def processRow(dbRow,log):
   if ( dbRow['transaction'] not in addedTransactions):
      recordsToSend.append(dbRow)
      addedTransactions[dbRow['transaction']] = 1
   else:
      log.info("Duplicate detected, discarding")
   return dbRow['njobs']

def createStatistics(records):
   overall = countBy(records,None,None)
   initiator = countBy(records,"initiator","I1")
   errorcode = countBy(records,"errorcode",0)
   totalRecords = len(records)

   return overall,initiator,errorcode,totalRecords

def countBy(records, fieldName, fieldValue):
    sum = 0
    for r in records: 
        if fieldName != None and fieldValue != None:
            if r[fieldName] == fieldValue:
                sum = sum + r['transfersize']
        else:
            sum = sum + r['transfersize']

    return sum

def dumpStatistics(log):
   global recordsToSend
   if ( not TEST ):
      return
   log.info("Send to gratia:")
   dump(log,createStatistics(recordsToSend))

   log.info("Generated:")
   dump(log,createStatistics(BillingRecSimulator.sqlTableContent))
    
def dump(log, infos):
   (overall,initiator,errorcode,totalRecords) = infos
   log.info("Overall %s" % overall)
   log.info("initiator %s"% initiator)
   log.info("errorcode %s" % errorcode)
   log.info("num records %s" % totalRecords)


if __name__ == "__main__":

  recordsToSend = BillingRecSimulator.generateTableContent() 
  print("Pre aggregation")
  print(createStatistics(recordsToSend))

  recordsToSend = Collapse.collapse(recordsToSend,TimeBinRange.DictRecordAggregator(['initiator','client', 'protocol','errorcode','isnew' ],['njobs','transfersize','connectiontime']))
  print("Post Aggregation")
  print(createStatistics(recordsToSend))

