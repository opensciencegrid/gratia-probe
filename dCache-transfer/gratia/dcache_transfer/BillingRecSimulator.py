
from __future__ import absolute_import

import datetime
import time
import re
import random

from . import TestContainer
from . import Collapse
from . import TimeBinRange

def generateTableContent():

  """
  Generate a bunch of data; this is used to test the aggregation.
  """

  random.seed(0)

  aggFields = { 'initiator' : [ 'I1' ,'I2','I3' ], 'client' : [  'C2' ,'C1','C3'] , 'protocol' : [ 'P1' ] , 'errorcode' :  [ 0 ] , 'isnew' : [ 0 ] }

  startTime = TestContainer.StartTime
  now = TestContainer.EndTime
  results = []

  while startTime < now:
     r = {}
     r['datestamp'] =  datetime.datetime.fromtimestamp(startTime)
     r['transaction'] = str(random.randint(0,1000000))+str(time.time())
     r['tm'] = startTime
     for aggField in aggFields.keys():
        rN = random.randint(0,10000)
        aggFieldVal = aggFields[aggField][rN%len(aggFields[aggField])]
        r[aggField] = aggFieldVal

     r['transfersize'] = 1
     r['connectiontime'] = 1
     results.append(r)
     startTime = startTime + int(( len(results) % 2 ) == 0 )

  return results

sqlTableContent = None
reExp = re.compile(".*WHERE  *b.datestamp *>= '(..*)' *AND *b.datestamp *< *'(..*)'.*LIMIT  *([0-9][0-9]*) .*")


def execute(sqlQuery):

  global sqlTableContent

  if ( sqlTableContent == None ):
     sqlTableContent = generateTableContent()

  global reExp
 
  sqlQuery = sqlQuery.replace('\n',' ')
  dateMatch = reExp.match(sqlQuery)
  if dateMatch == None:
     raise Exception("Misspecified query argument:"+sqlQuery)

  startDateS = dateMatch.group(1)
  endDateS = dateMatch.group(2)
  limitS = dateMatch.group(3)
 
  startDate = DateStrToSecs(startDateS)
  endDate   = DateStrToSecs(endDateS)
  limit = int(limitS)

  results = []
  for r in sqlTableContent:
     recordTime = r['tm']

     if ( recordTime >= startDate and recordTime < endDate ):
         results.append(r.copy())
         if ( len(results) == limit ):
            break
  
  if ( len(results) != 0 ):
       TestContainer.sendInterrupt(300)

  return results

def DateStrToSecs(dateStr):
   format = "%Y-%m-%d %H:%M:%S"
   return time.mktime(time.strptime(dateStr,format))

