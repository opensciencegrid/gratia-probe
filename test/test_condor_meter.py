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

        # ridiculous looking nonsense to be able to mock out htcondor.param['FOO']
        self.htcondor_config = {}
        self.mock_htcondor_param = patch('htcondor.param',
                                         **{'__getitem__.side_effect': self.htcondor_config.__getitem__}).start()

        # specific pwd.struct_passwd instance
        self.mock_user = self.mock_getpwnam.return_value
        self.mock_user.pw_gid = 9618
        self.mock_user.pw_uid = 9619

    def tearDown(self):
        self.mock_getpwnam.stop()
        self.mock_setgid.stop()
        self.mock_setuid.stop()
        self.mock_htcondor_param.stop()

    def test_condor_user_success(self):
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

    def test_condor_ids(self):
        """Test privilege drop when admins specify CONDOR_IDS
        """
        self.htcondor_config['CONDOR_IDS'] = '1.2'

        condor_meter.become_condor()

        self.mock_setgid.assert_called_once_with(2)
        self.mock_setuid.assert_called_once_with(1)

    def test_malformed_condor_ids(self):
        """Test error handling for malformed CONDOR_IDS configuration
        """
        for bad_id in ('i love condor', '', '100', '2.gratia', 'garbage.50'):
            self.htcondor_config['CONDOR_IDS'] = bad_id
            with self.assertRaises(condor_meter.utils.InternalError):
                condor_meter.become_condor()

    @patch('htcondor.reload_config')
    @patch('os.environ.setdefault')
    def test_htcondor_ce_ids(self, mock_environ, mock_reload):
        """Test privilege drop when an HTCondor-CE admin specifies CONDOR_IDS
        """
        self.htcondor_config['CONDOR_IDS'] = '1.2'

        condor_meter.become_condor('htcondor-ce')

        mock_environ.assert_called_once_with('CONDOR_CONFIG', '/etc/condor-ce/condor_config')
        mock_reload.assert_called_once()
        self.mock_setgid.assert_called_once_with(2)
        self.mock_setuid.assert_called_once_with(1)
