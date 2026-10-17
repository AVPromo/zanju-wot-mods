# -*- coding: utf-8 -*-
"""Tests for the hover card window: where it hangs, and what it does with no window standing.

The window itself needs the client. These tests cover the parts that do not.
"""
from __future__ import absolute_import, print_function, unicode_literals

import unittest

from mods_common import card_window


class _Logger(object):
    def __init__(self):
        self.exceptions = []

    def exception(self, message, *args):
        self.exceptions.append(message)

    def warning(self, message, *args):
        pass


class _MapArg(object):
    """A Wulf command argument: a map with `get`, not a dict."""

    def __init__(self, values):
        self._values = values

    def get(self, key):
        return self._values.get(key)


class PlaceTest(unittest.TestCase):

    def test_the_card_hangs_centred_under_the_banner(self):
        # A banner at x 900, 60 wide, 80 high; a card 380 wide; the gap is 6.
        self.assertEqual(card_window.place_under((900, 100, 60, 80), (380, 300), (1920, 1080)), (740, 186))

    def test_a_card_near_an_edge_stays_on_screen(self):
        self.assertEqual(card_window.place_under((1880, 100, 40, 80), (380, 300), (1920, 1080)), (1540, 186))
        self.assertEqual(card_window.place_under((0, 900, 40, 80), (380, 300), (1920, 1080)), (0, 780))


class ArgTest(unittest.TestCase):

    def test_a_command_argument_reads_as_a_dict_or_a_map(self):
        self.assertEqual(card_window.read_arg({'token': '3'}, 'token'), '3')
        self.assertEqual(card_window.read_arg(_MapArg({'width': 400}), 'width'), 400)
        self.assertIsNone(card_window.read_arg(None, 'width'))
        self.assertIsNone(card_window.read_arg('text', 'width'))


class NoWindowTest(unittest.TestCase):

    def setUp(self):
        self.card = card_window.CardWindow(('mods', 'zanju', 'test', 'views', 'Card'), 'ZanjuTestCard',
                                           'zanju.test.json')
        self.logger = _Logger()

    def test_with_no_window_the_card_is_not_alive(self):
        self.assertFalse(self.card.is_alive())

    def test_an_update_or_a_hide_with_no_window_does_nothing(self):
        self.card.update({'heldKeys': 'shift'}, self.logger)
        self.card.hide(self.logger)
        self.card.uninstall(self.logger)
        self.assertEqual(self.logger.exceptions, [])
        self.assertEqual(self.card.key, '')

    def test_a_size_for_another_card_is_ignored(self):
        self.card._on_sized(self.logger, {'token': '99', 'width': 10, 'height': 10})
        self.assertIsNone(self.card._size)
        self.assertEqual(self.logger.exceptions, [])


if __name__ == '__main__':
    unittest.main()
