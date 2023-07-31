#!/bin/env python

import os
import shutil
import tempfile
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

class CompressOutboxTests(unittest.TestCase):
    def setUp(self):
        #provision test environment
        self.probe_dir = tempfile.mkdtemp()
        self.outbox = os.path.join(self.probe_dir, 'outbox')
        os.makedirs(self.outbox, exist_ok=True)
        self.outfiles = ['testfile1', 'testfile2']
        # add content to the files
        for fname in self.outfiles:
            with open(os.path.join(self.outbox, fname), 'w') as f:
                f.write('test content')

    def tearDown(self):
        #Remove probe_dir after test
        shutil.rmtree(self.probe_dir)

    @patch('gratia.common.config.ConfigProxy.get_GratiaExtension', create=True, return_value ='test-extension')
    @patch('gratia.common.config.ConfigProxy.getFilenameFragment', create=True, return_value ='test-filename')
    def test_compress_outbox(self, mock_gratia_ext, mock_file_frag):
        """CompressOutbox compresses the files in the outbox directory
            and stores the resulting tarball in probe_dir/staged.
        """
        #Parameters for function
        probe_dir = self.probe_dir
        outbox = self.outbox
        outfiles = self.outfiles

        #Assert that CompressOutbox returns True
        result = sandbox_mgmt.CompressOutbox(probe_dir, outbox, outfiles)
        self.assertTrue(result)
