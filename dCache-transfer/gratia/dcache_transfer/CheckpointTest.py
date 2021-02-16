# Copyright 2007 Cornell University, Ithaca, NY. All rights reserved.
#
# Author:  Gregory J. Sharp
#
# This program performs some basic unit tests on the Checkpoint module.

from __future__ import absolute_import
from __future__ import print_function

import os
import sys
import stat
from datetime import datetime

from .Checkpoint import Checkpoint

TestFileName = "chkpt_test"
stmp4 = datetime( 2006, 1, 1, 1, 0, 0, 2, None )
txn4 = "85432"


def checkok( testid, c, stamp, txn ):
    if c.lastDateStamp() != stamp or c.lastTransaction() != txn:
        print("ERROR " + testid + ": expected stamp = ", stamp, \
              " current stamp = ", c.lastDateStamp())
        print("ERROR " + testid + ": txn = ", txn, \
              " current txn = ", c.lastTransaction())
        sys.exit(1) # stop trying - something is wrong
    else:
        print("Test " + testid + ": passed")

def deleteTestFile():
    """ Get rid of extant test file file """
    if os.path.exists( TestFileName ):
        os.chmod( TestFileName, stat.S_IWRITE )
        os.unlink( TestFileName )

def phase1():
    # TEST 0
    # Make sure an uninitialized checkpoint has the default date and
    # transaction values.
    stmp0 = datetime( 1990, 1, 1, 0, 0, 0, 0, None )
    c = Checkpoint( TestFileName )
    checkok( "0", c, stmp0, "" )

    # TEST 1
    # Update the checkpoint and see if it now remembers the correct values.
    stmp1 = datetime( 2004, 1, 1, 0, 0, 0, 0, None )
    txn1 = "12345"
    c.createPending( stmp1, txn1 )
    c.commit()
    checkok( "1", c, stmp1, txn1 )

    # TEST 2
    # Make sure that the old timestamp is still valid until the commit
    stmp2 = datetime( 2004, 1, 1, 0, 0, 0, 1, None )
    txn2 = "12346"
    c.createPending( stmp2, txn2 )
    checkok( "2", c, stmp1, txn1 )

    # TEST 3
    # Do the commit and make sure it updated everything.
    c.commit()
    checkok( "3", c, stmp2, txn2 )

    # TEST 4
    txn4a = "12347"
    stmp4a = datetime( 2005, 1, 1, 1, 0, 0, 1, None )

    c.createPending( stmp4a, txn4a )
    # Don't commit - just press on with the next one.
    c.createPending( stmp4, txn4 )
    c.commit()
    checkok( "4", c, stmp4, txn4)

def phase2():
    """
    At this point we create a new checkpoint object and make sure
    That the checkpoint file holds the last values we think we wrote
    to it, which should be stmp4 and txn4.
    """
    c = Checkpoint( TestFileName )
    checkok( "5", c, stmp4, txn4 )


# Remove the test file - leave things as we found them.
if __name__ == '__main__':
    deleteTestFile()
    phase1()
    phase2()
    deleteTestFile()
    sys.exit(0)
