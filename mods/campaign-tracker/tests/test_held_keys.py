# -*- coding: utf-8 -*-
"""Tests for the rule that a fault in this module never reaches the client.

The regression these guard against: `_on_key` called the consumer's callback with no guard.
`gui.InputHandler` dispatches these events through `Event`, which raises the fault of a
delegate again after it logs it, and `game.handleKeyEvent` makes that call with no guard of
its own. One exception from the callback therefore skipped everything the client runs after
it for that key -- `GUI.handleKeyEvent`, which owns Escape and Tab, the messenger, and the
avatar's own input handler, which owns the radial menu and every battle command. A player
reported exactly that, after about an hour of play.

`Keys` is faked here rather than in the shared test environment, because a stub that answers
with plausible key codes for every mod is the kind of stub that turns a failing test green.
"""
from __future__ import absolute_import, print_function, unicode_literals

import sys
import types
import unittest

from zanju_ct import held_keys

_KEY_LSHIFT = 42
_KEY_RSHIFT = 54
_KEY_LCONTROL = 29
_KEY_RCONTROL = 157
_KEY_TAB = 15


class _Event(object):
    """One key event, carrying the two attributes `_read_key` asks it for."""

    def __init__(self, key, down):
        self.key = key
        self._down = down

    def isKeyDown(self):
        return self._down


class _Logger(object):
    """A logger that counts what it was asked to report."""

    def __init__(self):
        self.exceptions = []

    def info(self, message, *args):
        pass

    def exception(self, message, *args):
        self.exceptions.append(message)

    def drain(self):
        """Forget everything reported so far, and answer how much that was.

        `install` reports a fault of its own outside the game, because there is no client to
        subscribe to. A test that counts callback faults drains that first rather than matching
        on the wording of a log line.
        """
        count = len(self.exceptions)
        del self.exceptions[:]
        return count


class _HeldKeysTestCase(unittest.TestCase):
    def setUp(self):
        self._keys = types.ModuleType(str('Keys'))
        self._keys.KEY_LSHIFT = _KEY_LSHIFT
        self._keys.KEY_RSHIFT = _KEY_RSHIFT
        self._keys.KEY_LCONTROL = _KEY_LCONTROL
        self._keys.KEY_RCONTROL = _KEY_RCONTROL
        self._restore = sys.modules.get('Keys')
        sys.modules['Keys'] = self._keys
        self.logger = _Logger()

    def tearDown(self):
        held_keys.uninstall(self.logger)
        if self._restore is None:
            del sys.modules['Keys']
        else:
            sys.modules['Keys'] = self._restore


class CallbackFaultTest(_HeldKeysTestCase):
    def test_a_callback_that_raises_does_not_reach_the_client(self):
        # The bug: this exception left `_on_key` and took the rest of the key dispatch with it.
        def explode():
            raise ValueError('the lobby is gone')

        held_keys.install(self.logger, explode)
        held_keys._on_key(_Event(_KEY_LSHIFT, True))

    def test_the_fault_is_reported_once_and_no_more(self):
        # This runs on every modifier key of the session, so a fault that repeats must not
        # write a line every time.
        def explode():
            raise ValueError('the lobby is gone')

        held_keys.install(self.logger, explode)
        self.logger.drain()
        for down in (True, False, True, False, True):
            held_keys._on_key(_Event(_KEY_LCONTROL, down))
        self.assertEqual(len(self.logger.exceptions), 1)

    def test_a_later_install_reports_again(self):
        def explode():
            raise ValueError('the lobby is gone')

        held_keys.install(self.logger, explode)
        held_keys._on_key(_Event(_KEY_LSHIFT, True))
        held_keys.install(self.logger, explode)
        self.logger.drain()
        held_keys._on_key(_Event(_KEY_LSHIFT, False))
        self.assertEqual(len(self.logger.exceptions), 1)

    def test_the_keys_stay_tracked_after_a_fault(self):
        # The card reads `text()` when it is next built, so a fault must not lose the state.
        def explode():
            raise ValueError('the lobby is gone')

        held_keys.install(self.logger, explode)
        held_keys._on_key(_Event(_KEY_LSHIFT, True))
        self.assertEqual(held_keys.text(), 'shift')


class ReadKeyTest(_HeldKeysTestCase):
    def test_both_sides_of_the_keyboard_map_to_one_modifier(self):
        calls = []
        held_keys.install(self.logger, lambda: calls.append(held_keys.text()))
        held_keys._on_key(_Event(_KEY_RSHIFT, True))
        held_keys._on_key(_Event(_KEY_RCONTROL, True))
        self.assertEqual(calls, ['shift', 'shift ctrl'])

    def test_any_other_key_changes_nothing(self):
        calls = []
        held_keys.install(self.logger, lambda: calls.append(held_keys.text()))
        held_keys._on_key(_Event(_KEY_TAB, True))
        self.assertEqual(calls, [])
        self.assertEqual(held_keys.text(), '')

    def test_a_repeat_of_the_same_state_reports_nothing(self):
        calls = []
        held_keys.install(self.logger, lambda: calls.append(held_keys.text()))
        held_keys._on_key(_Event(_KEY_LSHIFT, True))
        held_keys._on_key(_Event(_KEY_LSHIFT, True))
        self.assertEqual(calls, ['shift'])


if __name__ == '__main__':
    unittest.main()
