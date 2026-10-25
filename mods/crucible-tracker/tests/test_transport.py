# -*- coding: utf-8 -*-
"""Tests for the battle transport file: one per account, written only on a change."""
from __future__ import absolute_import, print_function, unicode_literals

import os
import shutil
import tempfile
import unittest

from zanju_crt import transport


class _Logger(object):
    def __init__(self):
        self.exceptions = []

    def exception(self, message, *args):
        self.exceptions.append(message)


class TransportTest(unittest.TestCase):

    def setUp(self):
        self.base = tempfile.mkdtemp()
        self.saved_env = os.environ.get('APPDATA')
        os.environ['APPDATA'] = self.base
        transport._written.clear()
        transport._remembered.clear()
        self.logger = _Logger()

    def tearDown(self):
        if self.saved_env is None:
            os.environ.pop('APPDATA', None)
        else:
            os.environ['APPDATA'] = self.saved_env
        shutil.rmtree(self.base)

    def test_the_file_is_per_account_under_the_mod_folder(self):
        path = transport.path_for(500725877)
        self.assertTrue(path.endswith(os.path.join('crucible-tracker', 'battle_500725877.json')))
        self.assertIsNone(transport.path_for(None))

    def test_a_saved_transport_reads_back(self):
        data = {'version': 1, 'savedAt': 10, 'active': {'questID': 'challenge:57:2'}}
        self.assertTrue(transport.save(1, data, self.logger))
        self.assertEqual(transport.load(1, self.logger), data)

    def test_a_new_save_time_alone_writes_nothing(self):
        transport.save(1, {'version': 1, 'savedAt': 10, 'active': {'questID': 'a'}}, self.logger)
        self.assertFalse(transport.save(1, {'version': 1, 'savedAt': 20, 'active': {'questID': 'a'}}, self.logger))
        self.assertTrue(transport.save(1, {'version': 1, 'savedAt': 30, 'active': {'questID': 'b'}}, self.logger))

    def test_no_active_series_is_written_as_such(self):
        transport.save(1, None, self.logger)
        self.assertEqual(transport.load(1, self.logger), {'active': None})

    def test_a_missing_file_reads_as_none(self):
        self.assertIsNone(transport.load(2, self.logger))
        self.assertEqual(self.logger.exceptions, [])

    def test_the_last_save_of_each_account_stays_in_memory(self):
        transport.save(1, {'version': 1, 'savedAt': 10, 'active': {'questID': 'a'}}, self.logger)
        transport.save(1, {'version': 1, 'savedAt': 20, 'active': {'questID': 'a'}}, self.logger)
        transport.save(2, None, self.logger)
        self.assertEqual(transport.remembered(1)['savedAt'], 20)
        self.assertEqual(transport.remembered(2), {'active': None})
        self.assertIsNone(transport.remembered(3))
        self.assertIsNone(transport.remembered(None))


if __name__ == '__main__':
    unittest.main()
