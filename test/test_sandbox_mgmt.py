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
        prefix = 'test-prefix.'
        temp_dir = '/tmp'

        try:
            filename = sandbox_mgmt.GenerateFilename(prefix, temp_dir)
            self.assertTrue(os.path.exists(filename),
                            f'Failed to create temporary file ({filename})')
            self.assertEqual(temp_dir.rstrip('/'),
                             os.path.dirname(filename),
                             f'Temporary file {filename} placed in the wrong directory')
            self.assertRegex(filename,
                             rf'{temp_dir}/*{prefix}\d+\.{mock_config.return_value}__\w+',
                             'Unexpected file name format')
        finally:
            try:
                os.remove(filename)
            except FileNotFoundError:
                # don't need to clean up what's not there
                pass
