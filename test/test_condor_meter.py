#!/bin/env python

import unittest
import classad

from condor_ap import condor_meter


class CondorMeterTests(unittest.TestCase):
    """Unit tests for the HTCondor Gratia probe
    """

    def test_proc_attr_order(self):
        """get_num_procs() has an order of preferred attributes
        """
        jobad = classad.ClassAd()
        for attr, val in [(x, condor_meter.PROC_ATTRS.index(x)) for x in reversed(condor_meter.PROC_ATTRS)]:
            jobad[attr] = val
            self.assertEqual(condor_meter.get_num_procs(jobad), val)

    def test_proc_expr(self):
        """get_num_procs() should be able to handle attributes set to ClassAd expressions
        """
        for attr in condor_meter.PROC_ATTRS:
            jobad = classad.ClassAd()
            jobad[attr] = classad.ExprTree('2 + 2')
            procs = condor_meter.get_num_procs(jobad)
            self.assertEqual(procs, 4)

    def test_proc_int(self):
        """The Processors field should always return an integer
        """
        for attr in condor_meter.PROC_ATTRS:
            jobad = classad.ClassAd()
            jobad[attr] = 'broken attribute'
            procs = condor_meter.get_num_procs(jobad)
            self.assertIsInstance(procs, int)
