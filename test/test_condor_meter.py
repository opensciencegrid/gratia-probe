#!/bin/env python

import unittest
import classad

from condor import condor_meter

class CondorMeterTests(unittest.TestCase):
    """Unit tests for the HTCondor Gratia probe
    """

    def test_proc_expr(self):
        """get_num_procs() should be able to handle attributes set to ClassAd expressions
        """
        self.fail()

    def test_proc_int(self):
        """The Processors field should always return an integer
        """
        self.fail()
