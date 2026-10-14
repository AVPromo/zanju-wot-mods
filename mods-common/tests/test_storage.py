# -*- coding: utf-8 -*-
"""Tests for where a mod keeps its files in AppData, and how it writes them.

The folder decides where the player's settings are. A change to it loses them without a word,
so the path is worth pinning literally.
"""
from __future__ import absolute_import, print_function, unicode_literals

import logging
import os
import shutil
import tempfile
import unittest

from mods_common import storage

_ENV_NAMES = ('APPDATA', 'LOCALAPPDATA', 'USERPROFILE')


class _Environment(unittest.TestCase):

    def setUp(self):
        saved = dict((name, os.environ.get(name)) for name in _ENV_NAMES)
        self.addCleanup(self._restore, saved)
        for name in _ENV_NAMES:
            os.environ.pop(name, None)

    @staticmethod
    def _restore(saved):
        for name, value in saved.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value


class ResolveModDataDirTest(_Environment):

    def test_puts_each_mod_in_its_own_folder_under_the_shared_parent(self):
        os.environ['APPDATA'] = os.path.join('C', 'Users', 'player', 'AppData', 'Roaming')
        self.assertEqual(
            storage.resolve_mod_data_dir('directives-helper'),
            os.path.join('C', 'Users', 'player', 'AppData', 'Roaming', 'zanju_wot_mods_cache',
                         'directives-helper'))

    def test_falls_back_to_the_user_profile(self):
        os.environ['USERPROFILE'] = os.path.join('C', 'Users', 'player')
        self.assertEqual(
            storage.resolve_mod_data_dir('research-progress-bar'),
            os.path.join('C', 'Users', 'player', 'AppData', 'Roaming', 'zanju_wot_mods_cache',
                         'research-progress-bar'))

    def test_ignores_a_blank_variable(self):
        os.environ['APPDATA'] = '   '
        os.environ['LOCALAPPDATA'] = os.path.join('C', 'Local')
        self.assertEqual(
            storage.resolve_mod_data_dir('x'), os.path.join('C', 'Local', 'zanju_wot_mods_cache', 'x'))

    def test_answers_none_without_any_home(self):
        self.assertIsNone(storage.resolve_mod_data_dir('directives-helper'))


class AtomicWriteTextTest(unittest.TestCase):

    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.root)
        self.logger = logging.getLogger('test.storage')

    def _read(self, path):
        with open(path, 'rb') as fh:
            return fh.read().decode('utf-8')

    def test_creates_missing_folders(self):
        path = os.path.join(self.root, 'a', 'b', 'state.json')
        self.assertTrue(storage.atomic_write_text(path, '{}', self.logger))
        self.assertEqual(self._read(path), '{}')

    def test_replaces_an_existing_file_and_leaves_no_temp_file(self):
        path = os.path.join(self.root, 'state.json')
        storage.atomic_write_text(path, 'old', self.logger)
        self.assertTrue(storage.atomic_write_text(path, 'new', self.logger))
        self.assertEqual(self._read(path), 'new')
        self.assertEqual(os.listdir(self.root), ['state.json'])


if __name__ == '__main__':
    unittest.main()
