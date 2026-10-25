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
            os.path.join('C', 'Users', 'player', 'AppData', 'Roaming', 'Wargaming.net', 'WorldOfTanks', 'mods',
                         'Zanju', 'directives-helper'))

    def test_falls_back_to_the_user_profile(self):
        os.environ['USERPROFILE'] = os.path.join('C', 'Users', 'player')
        self.assertEqual(
            storage.resolve_mod_data_dir('research-progress-bar'),
            os.path.join('C', 'Users', 'player', 'AppData', 'Roaming', 'Wargaming.net', 'WorldOfTanks', 'mods',
                         'Zanju', 'research-progress-bar'))

    def test_ignores_a_blank_variable(self):
        os.environ['APPDATA'] = '   '
        os.environ['LOCALAPPDATA'] = os.path.join('C', 'Local')
        self.assertEqual(
            storage.resolve_mod_data_dir('x'),
            os.path.join('C', 'Local', 'Wargaming.net', 'WorldOfTanks', 'mods', 'Zanju', 'x'))

    def test_answers_none_without_any_home(self):
        self.assertIsNone(storage.resolve_mod_data_dir('directives-helper'))


class LegacyCopyTest(_Environment):
    """Earlier releases kept the folders in AppData/zanju_wot_mods_cache/."""

    def setUp(self):
        super(LegacyCopyTest, self).setUp()
        self.root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.root)
        os.environ['APPDATA'] = self.root
        self.old_dir = os.path.join(self.root, 'zanju_wot_mods_cache', 'campaign-tracker')

    def _write(self, path, text):
        if not os.path.isdir(os.path.dirname(path)):
            os.makedirs(os.path.dirname(path))
        with open(path, 'wb') as fh:
            fh.write(text.encode('utf-8'))

    def _read(self, path):
        with open(path, 'rb') as fh:
            return fh.read().decode('utf-8')

    def test_the_old_folder_is_copied_to_the_new_place_and_stays(self):
        self._write(os.path.join(self.old_dir, 'config.json'), '{"traySide": "left"}')
        new_dir = storage.resolve_mod_data_dir('campaign-tracker')
        self.assertEqual(self._read(os.path.join(new_dir, 'config.json')), '{"traySide": "left"}')
        self.assertTrue(os.path.isfile(os.path.join(self.old_dir, 'config.json')))

    def test_a_new_folder_that_exists_is_never_overwritten(self):
        self._write(os.path.join(self.old_dir, 'config.json'), '{"old": true}')
        new_dir = os.path.join(self.root, 'Wargaming.net', 'WorldOfTanks', 'mods', 'Zanju', 'campaign-tracker')
        self._write(os.path.join(new_dir, 'config.json'), '{"new": true}')
        self.assertFalse(storage.copy_legacy_dir(self.old_dir, new_dir))
        self.assertEqual(self._read(os.path.join(new_dir, 'config.json')), '{"new": true}')

    def test_no_old_folder_means_nothing_to_copy(self):
        new_dir = storage.resolve_mod_data_dir('crucible-tracker')
        self.assertFalse(os.path.exists(new_dir))


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
