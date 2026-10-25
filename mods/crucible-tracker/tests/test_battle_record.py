# -*- coding: utf-8 -*-
"""Tests for the record of which battle type each vehicle went into."""
from __future__ import absolute_import, print_function, unicode_literals

import os
import shutil
import tempfile
import unittest

from zanju_crt import battle_record


class _Logger(object):
    def __init__(self):
        self.exceptions = []

    def exception(self, message, *args):
        self.exceptions.append(message)


class BattleRecordTest(unittest.TestCase):

    def setUp(self):
        self.base = tempfile.mkdtemp()
        self.saved_env = os.environ.get('APPDATA')
        os.environ['APPDATA'] = self.base
        self.logger = _Logger()

    def tearDown(self):
        if self.saved_env is None:
            os.environ.pop('APPDATA', None)
        else:
            os.environ['APPDATA'] = self.saved_env
        shutil.rmtree(self.base)

    def test_a_recorded_battle_reads_back_by_vehicle(self):
        self.assertTrue(battle_record.record(7, 5921, 1, 111, self.logger, now=1000))
        self.assertEqual(battle_record.load(7, self.logger, now=1001),
                         {5921: {'bonusType': 1, 'arena': 111, 'time': 1000}})

    def test_the_newest_battle_of_a_vehicle_wins(self):
        battle_record.record(7, 5921, 1, 111, self.logger, now=1000)
        battle_record.record(7, 5921, 32, 222, self.logger, now=2000)
        battle_record.record(7, 6177, 1, 333, self.logger, now=2000)
        records = battle_record.load(7, self.logger, now=2001)
        self.assertEqual(records[5921]['bonusType'], 32)
        self.assertEqual(records[6177]['bonusType'], 1)

    def test_a_record_too_old_for_a_running_battle_is_dropped(self):
        battle_record.record(7, 5921, 1, 111, self.logger, now=1000)
        self.assertEqual(battle_record.load(7, self.logger, now=1000 + 3 * 3600), {})

    def test_each_account_has_its_own_file(self):
        battle_record.record(7, 5921, 1, 111, self.logger, now=1000)
        self.assertEqual(battle_record.load(8, self.logger, now=1001), {})

    def test_a_reconnect_keeps_the_time_of_the_first_entry(self):
        battle_record.record(7, 5921, 1, 111, self.logger, now=1000)
        battle_record.record(7, 5921, 1, 111, self.logger, now=1400)
        self.assertEqual(battle_record.first_entry(7, 5921, 111, self.logger, now=1401), 1000)
        # Another arena is another battle, with an entry of its own.
        battle_record.record(7, 5921, 1, 222, self.logger, now=2000)
        self.assertEqual(battle_record.first_entry(7, 5921, 222, self.logger, now=2001), 2000)
        self.assertIsNone(battle_record.first_entry(7, 5921, 111, self.logger, now=2001))
        self.assertIsNone(battle_record.first_entry(7, 6177, 222, self.logger, now=2001))

    def test_no_account_or_no_vehicle_writes_nothing(self):
        self.assertFalse(battle_record.record(None, 5921, 1, 111, self.logger))
        self.assertFalse(battle_record.record(7, None, 1, 111, self.logger))


if __name__ == '__main__':
    unittest.main()
