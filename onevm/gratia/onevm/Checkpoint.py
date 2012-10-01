import time
import sys
import os

class Checkpoint:
    def __init__(self,fn,maxAge):
       self._fn=fn
       self._lastChecked=self.setLastCheckPoint(maxAge)
    def setLastCheckPoint(self,maxAge):
	lastChecked=time.time()-maxAge*24*60*60
	if os.path.isfile(self._fn):
		try:
			fd=open(self._fn,'r')
			lastChecked=float(fd.readline())
			fd.close()
		except:
			etype,value,trace=sys.exc_info()
			print "Failed to open file %s,%s,%s" % (etype,value,trace)
	return lastChecked
    def getLastCheckPoint(self):
	return self._lastChecked
    def createCheckPoint(self,tm):
	try:
		fd=open(self._fn,'w')
		fd.write(repr(tm))
		fd.close()
        except:
		etype,value,trace=sys.exc_info()
                print "Failed to write file %s,%s,%s" % (etype,value,trace)
	







	 
