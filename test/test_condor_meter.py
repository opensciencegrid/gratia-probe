#!/bin/env python

import unittest
import classad

from condor import condor_meter


class CondorMeterTests(unittest.TestCase):
    """Unit tests for the HTCondor Gratia probe
    """

    def test_proc_attr_order(self):
        """get_num_procs() has an order of preferred attributes
        """
        jobad = classad.ClassAd()
        for attr, val in [('RequestCpus', 1),
                          ('MATCH_EXP_JOB_GLIDEIN_Cpus', 2),
                          ('MachineAttrCpus0', 3)]:
            jobad[attr] = val
            self.assertEquals(condor_meter.get_num_procs(jobad), val)

    def test_proc_expr(self):
        """get_num_procs() should be able to handle attributes set to ClassAd expressions
        """
        for attr in ['MachineAttrCpus0', 'MATCH_EXP_JOB_GLIDEIN_Cpus', 'RequestCpus']:
            jobad = classad.ClassAd()
            jobad[attr] = classad.ExprTree('2 + 2')
            procs = condor_meter.get_num_procs(jobad)
            self.assertEquals(procs, 4)

    def test_proc_int(self):
        """The Processors field should always return an integer
        """
        for attr in ['MachineAttrCpus0', 'MATCH_EXP_JOB_GLIDEIN_Cpus', 'RequestCpus']:
            jobad = classad.ClassAd()
            jobad[attr] = 'broken attribute'
            procs = condor_meter.get_num_procs(jobad)
            self.assertIsInstance(procs, int)
