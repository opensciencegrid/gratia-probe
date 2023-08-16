#!/bin/env python

import glob
import os
import shutil
import tarfile
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
        # provision test environment
        gratia_ex = patch('gratia.common.config.ConfigProxy.get_GratiaExtension',
                          create=True, return_value='test-extension')
        file_frag = patch('gratia.common.config.ConfigProxy.getFilenameFragment',
                          create=True, return_value='test-filename')

        self.mock_gratia_ex = gratia_ex.start()
        self.mock_file_frag = file_frag.start()

        self.probe_dir = tempfile.mkdtemp()
        self.outbox = os.path.join(self.probe_dir, 'outbox')
        os.makedirs(self.outbox, exist_ok=True)
        self.outfiles = ['testfile1', 'testfile2']

        # add content to the files
        for testfile in self.outfiles:
            content = testfile + ' contains this content'
            with open(os.path.join(self.outbox, testfile), 'w', encoding="utf-8") as test:
                test.write(content)

        self.addCleanup(gratia_ex.stop)
        self.addCleanup(file_frag.stop)

    def tearDown(self):
        # Remove probe_dir after test
        shutil.rmtree(self.probe_dir)

    def test_compress_outbox(self):
        """CompressOutbox compresses the files in the outbox directory
        and stores the resulting tarball in probe_dir/staged.
        """
        # Assert that CompressOutbox returns True
        result = sandbox_mgmt.CompressOutbox(self.probe_dir, self.outbox, self.outfiles)
        self.assertTrue(result)

    def test_tarball_creation(self):
        """
        Assert that tarball is created in the correct location
        """
        sandbox_mgmt.CompressOutbox(self.probe_dir, self.outbox, self.outfiles)

        path_to_tarball = f'{self.probe_dir}/staged/store'

        # Finds exactly one tarball that matches GenerateFilename function output
        tarball = glob.glob("tz.*.test-extension__*", root_dir=path_to_tarball)
        tarball_location = os.path.join(f'{path_to_tarball}', tarball[0])
        # Counts files in the directory that the tarball should be in
        tarball_count = len((tarball))

        self.assertTrue(os.path.exists(tarball_location),
                        'Tarball not created in correct location')
        self.assertEqual(tarball_count, 1,
                         f'Expected 1 tarball, found {tarball_count}')

    def test_tarball_contents(self):
        """
        Assert that unpacked tarball contains files from outfiles
        """
        sandbox_mgmt.CompressOutbox(self.probe_dir, self.outbox, self.outfiles)
        path_to_tarball = f'{self.probe_dir}/staged/store'

        # Finds tarball that matches GenerateFilename() output
        tarball = glob.glob("tz.*.test-extension__*", root_dir=path_to_tarball)
        # Where tarball exists
        tarball_location = os.path.join(f'{path_to_tarball}', tarball[0])

        # Gets names of files within tarball
        with tarfile.open(tarball_location, "r") as names:

            # Names of files in tarball
            namelist = names.getnames()

            # Sort both lists to ensure order-independent comparison
            namelist.sort()
            self.outfiles.sort()

            # Open files in outfiles
            expected_files1 = open(os.path.join(f'{self.outbox}/{self.outfiles[0]}'), 'rb')
            expected_files2 = open(os.path.join(f'{self.outbox}/{self.outfiles[1]}'), 'rb')

            # Extract the contents from testfile1
            file1 = names.extractfile(namelist[0])
            file1_contents = file1.readlines()
            expected_results_f1 = expected_files1.readlines()

            # Extract the contents from testfile2
            file2 = names.extractfile(namelist[1])
            file2_contents = file2.readlines()
            expected_results_f2 = expected_files2.readlines()

            self.assertListEqual(namelist, self.outfiles,
                                 'Unexpected file names in tarball')
            self.assertEqual(file1_contents, expected_results_f1,
                             'Unexpected content in file1')
            self.assertEqual(file2_contents, expected_results_f2,
                             'Unexpected content in file2')
