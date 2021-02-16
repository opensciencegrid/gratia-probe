#===============================================================================
# This is a temporary class to read information stored in query_one log
#===============================================================================

from __future__ import absolute_import
from __future__ import print_function

import time
import sys
import os

from .VMRecord import VMRecord

class OneReader:
    def __init__(self,fn,verbose=False):
        self.fn=fn
        self.vms={}
        self.verbose=verbose
        self.start=time.time()
    def readFile(self):
        if not self.fn or not os.path.isfile(self.fn) or not os.access(self.fn, os.R_OK):
                raise Exception("One_query file, %s , does not exist." % self.fn)
        fd=open(self.fn,'r')
        tmp=eval(fd.read())
        for key,value in tmp.items():
            if self.verbose:
                print("Processing VM #%s: %s" % ( key, value), file=sys.stdout)
            vm=VMRecord(key,value)
            self.vms[key]=vm
    def getRecords(self):
        return self.vms       
    def dump(self):
        import pprint
        for key,vm in self.vms.items():
                vm.dump()

def parse_opts():
    import optparse
    parser = optparse.OptionParser(usage="%prog [options]")
    parser.add_option("-v", "--verbose", help="Enable verbose logging to stdout.",
        default=False, action="store_true", dest="verbose")
    parser.add_option("-f", "--one_query_file", help="Location of the OneVM query output file; "
        "defaults to /var/lib/gratia/data/query_one.log.", dest="one_query_file",
        default="/var/lib/gratia/data/query_one.log")
    opts, args = parser.parse_args()
    if not opts.one_query_file or not os.path.exists(opts.one_query_file):
        raise Exception("One_query file, %s , does not exist." % opts.one_query_file)
    return opts, args


if __name__ == "__main__":
   try:
      opts, dirs = parse_opts()
      reader=OneReader(opts.one_query_file,opts.verbose)
      reader.readFile()
      if opts.verbose:
        reader.dump()
   except Exception as e:
      print(e, file=sys.stderr)
      sys.exit(1)
   sys.exit(0)
            
            
        
