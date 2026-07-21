#!/bin/env python

import os
import unittest
from unittest.mock import patch, PropertyMock

from common.gratia.common import sandbox_mgmt

class SandboxMgmtTests(unittest.TestCase):

    @patch('gratia.common.config.ConfigProxy.get_GratiaExtension', create=True, return_value='test-extension')
    def test_GenerateFilename(self, mock_config):
        """GenerateFilename creates a temporary file and returns the path to the file
        """
        prefix = 'test-prefix'
        temp_dir = '/tmp'

        try:
            with sandbox_mgmt.GenerateFilename(prefix, temp_dir) as filename:
                self.assertTrue(os.path.exists(filename.name),
                                f'Failed to create temporary file ({filename.name})')
                self.assertEqual(temp_dir.rstrip('/'),
                                 os.path.dirname(filename.name),
                                 f'Temporary file {filename.name} placed in the wrong directory')
                self.assertRegex(filename.name,
                                 rf'{temp_dir}/*{prefix}\.\d+\.{mock_config.return_value}__\w+',
                                 'Unexpected file name format')
        finally:
            try:
                filename.close()
                os.remove(filename.name)
            except (FileNotFoundError, NameError):
                # don't need to clean up what's not there
                pass
