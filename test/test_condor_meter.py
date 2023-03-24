#!/bin/env python

import unittest
from unittest.mock import patch
import classad

from condor_ap import condor_meter


class ProcessorCountTests(unittest.TestCase):
    """Tests for processor counting logic
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


class BecomeCondorTests(unittest.TestCase):
    """Unit tests for the become_condor function
    """

    def setUp(self):
        self.mock_getpwnam = patch('pwd.getpwnam').start()
        self.mock_setgid = patch('os.setgid').start()
        self.mock_setuid = patch('os.setuid').start()

        # specific pwd.struct_passwd instance
        self.mock_user = self.mock_getpwnam.return_value
        self.mock_user.pw_gid = 9618
        self.mock_user.pw_uid = 9619

    def tearDown(self):
        self.mock_getpwnam.stop()
        self.mock_setgid.stop()
        self.mock_setuid.stop()

    def test_success(self):
        """Everything is as expected
        """
        condor_meter.become_condor()

        self.mock_getpwnam.assert_called_once_with('condor')
        self.mock_setgid.assert_called_once_with(self.mock_user.pw_gid)
        self.mock_setuid.assert_called_once_with(self.mock_user.pw_uid)

    def test_no_condor_user(self):
        """There is no 'condor' user
        """
        self.mock_getpwnam.configure_mock(side_effect=KeyError)

        with self.assertRaises(condor_meter.utils.InternalError):
            condor_meter.become_condor()

        self.mock_getpwnam.assert_called_once_with('condor')
        self.mock_setgid.assert_not_called()
        self.mock_setuid.assert_not_called()

    def test_fail_drop_gid(self):
        """Can't setgid
        """
        self.mock_setgid.configure_mock(side_effect=PermissionError)

        with self.assertRaises(condor_meter.utils.InternalError):
            condor_meter.become_condor()

        self.mock_getpwnam.assert_called_once_with('condor')
        self.mock_setgid.assert_called_once_with(self.mock_user.pw_gid)
        self.mock_setuid.assert_not_called()

    def test_fail_drop_uid(self):
        """Can't setgid
        """
        self.mock_setuid.configure_mock(side_effect=PermissionError)

        with self.assertRaises(condor_meter.utils.InternalError):
            condor_meter.become_condor()

        self.mock_getpwnam.assert_called_once_with('condor')
        self.mock_setgid.assert_called_once_with(self.mock_user.pw_gid)
        self.mock_setuid.assert_called_once_with(self.mock_user.pw_uid)
