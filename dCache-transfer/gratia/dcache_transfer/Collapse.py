
"""
The Collapse module primarily exports one function, collapse, that aggregates
similar records (where each record is assumed to be a python dictionary
"""

from __future__ import absolute_import
from __future__ import print_function

import time
import random
import datetime
from . import TimeBinRange

"""
class RecordProxy:
   def __init__(self,record):
       self.record = record
       self.d = {}

   def __getitem__(self,name):
        if ( self.d.has_key(name) ):
           return self.d[name]
        return self.record[name]
 
   def __setitem__(self,name,value):
       self.d[name] = value
"""

def collapse(records,agg):
  """
  Aggregate together records based upon timebins using TimeBinRange.

  @param records: A list of records (dictionaries) to aggregate.
  @param agg: An aggregator (DictRecordAggregator) compatible with the records.
  @return: A list of aggregated records (usually aggregated by hour).
  """

  tr = TimeBinRange.TimeBinRange(agg)

  for r in records:
     r = dict(r)
     recordTime = int(time.mktime( r['datestamp'].timetuple() ))
     r.setdefault("njobs", 1)
     tr.add(recordTime, r)
      
  result = tr.list()
  for r in result:
      makeTransaction(r, agg)

  """
  no need for this code.  dCacheBillingAggregator stops fetching latest recorords at 75 min before now.
  now = int(time.time())
  while 1:
      if ( len(result) > 0  and result[-1]['tm'] > now - 2*TimeBinRange.RANGE_SIZE_SECS):
         del result[-1]
      else:
         break"""

  return result

def makeTransaction(record,agg):
   
   transaction = str(record['tm']/TimeBinRange.RANGE_SIZE_SECS)
   hashCode = 0
   for aggField in agg.aggFields:
      tupl = (hashCode, hash(record[aggField]))
      hashCode = hash(tupl)

   record['transaction'] = transaction + str(hashCode)
 
   record['datestamp'] = datetime.datetime.fromtimestamp(record['tm'])

def generateResult():

  """
  Generate a bunch of data; this is used to test the aggregation.
  """

  aggFields = { 'initiator' : [ 'I1' ,'I2','I3' ], 'client' : [  'C2' ,'C1','C3'] , 'protocol' : [ 'P1' ] , 'errorcode' :  [ 0 ] , 'isnew' : [ 0 ] }

  startTime = time.time() - 24*3600
  now = time.time() - 1
  results = []

  while startTime < now:
     r = {}
     r['datestamp'] =  datetime.datetime.fromtimestamp(startTime)
     for aggField in aggFields.keys():
        rN = random.randint(0,10000)
        aggFieldVal = aggFields[aggField][rN%len(aggFields[aggField])]
        r[aggField] = aggFieldVal

     r['njobs'] = 1
     r['transfersize'] = 1
     r['connectiontime'] = 1
     results.append(r)
     rN = random.randint(0,10000)
     startTime = startTime + 3+(rN%300)

  return results

def test():

   preResult = generateResult()
   result = collapse(preResult,TimeBinRange.DictRecordAggregator(['initiator','client', 'protocol','errorcode','isnew' ],['njobs','transfersize','connectiontime']))
   return result

if __name__ == "__main__":
   print("AAAA")
   for r in test():
      print(r)
