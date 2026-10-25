# -*- coding: utf-8 -*-
"""Tests for the Mod Menu glue: register, declare the defaults, push, and drop the echo."""
from __future__ import absolute_import, print_function, unicode_literals

import sys
import types
import unittest

from mods_common import mod_menu


class _Logger(object):
    def __init__(self):
        self.exceptions = []

    def info(self, message, *args):
        pass

    def exception(self, message, *args):
        self.exceptions.append(message)


class _Api(object):
    """Mod Menu as the mods see it. It calls the change callback for every update, the echo too."""

    def __init__(self, with_defaults=True):
        self.templates = {}
        self.callbacks = {}
        self.values = {}
        self.defaults = {}
        if not with_defaults:
            self.setModDefaults = None

    def setModTemplate(self, linkage, template, callback):
        self.templates[linkage] = template
        self.callbacks[linkage] = callback

    def setModDefaults(self, linkage, defaults):
        self.defaults[linkage] = defaults

    def updateModSettings(self, linkage, values):
        self.values[linkage] = values
        self.callbacks[linkage](linkage, values)


class ModMenuTest(unittest.TestCase):

    def setUp(self):
        self.saved = dict(sys.modules)
        self.api = _Api()
        module = types.ModuleType(str('gui.aslainMenu'))
        module.g_modsSettingsApi = self.api
        sys.modules[str('gui.aslainMenu')] = module
        self.logger = _Logger()
        self.changes = []

    def tearDown(self):
        sys.modules.clear()
        sys.modules.update(self.saved)

    def _register(self):
        return mod_menu.register('zanju.test', {'enabled': True}, {'side': 0}, {'side': 1},
                                 self.changes.append, self.logger)

    def test_register_sets_the_template_the_defaults_and_the_values(self):
        self.assertTrue(self._register())
        linkage = mod_menu.native_key('zanju.test')
        self.assertEqual(self.api.templates[linkage], {mod_menu.native('enabled'): True})
        self.assertEqual(self.api.defaults[linkage], {mod_menu.native('side'): 0})
        self.assertEqual(self.api.values[linkage], {mod_menu.native('side'): 1})

    def test_the_echo_of_a_push_is_not_a_change(self):
        self._register()
        self.assertEqual(self.changes, [])

    def test_a_change_by_the_player_reaches_the_mod(self):
        self._register()
        linkage = mod_menu.native_key('zanju.test')
        self.api.callbacks[linkage](linkage, {'side': 0})
        self.assertEqual(self.changes, [{'side': 0}])

    def test_a_change_for_another_mod_is_ignored(self):
        self._register()
        linkage = mod_menu.native_key('zanju.test')
        self.api.callbacks[linkage](mod_menu.native_key('zanju.other'), {'side': 0})
        self.assertEqual(self.changes, [])

    def test_an_older_menu_without_declared_defaults_still_registers(self):
        self.api.setModDefaults = None
        self.assertTrue(self._register())
        self.assertEqual(self.logger.exceptions, [])

    def test_no_menu_means_the_config_file_alone(self):
        del sys.modules[str('gui.aslainMenu')]
        sys.modules[str('gui.aslainMenu')] = None
        self.assertFalse(self._register())

    def test_a_failing_handler_is_logged_and_not_raised(self):
        def broken(settings):
            raise RuntimeError('no')

        mod_menu.register('zanju.test', {}, {}, {}, broken, self.logger)
        linkage = mod_menu.native_key('zanju.test')
        self.api.callbacks[linkage](linkage, {'side': 0})
        self.assertEqual(len(self.logger.exceptions), 1)


if __name__ == '__main__':
    unittest.main()
