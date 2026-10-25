# -*- coding: utf-8 -*-
"""Tests for the settings: the two parts, the side, and how the file and the menu forms map."""
from __future__ import absolute_import, print_function, unicode_literals

import unittest

from zanju_crt import config


class ConfigTest(unittest.TestCase):

    def setUp(self):
        config._state.clear()
        config._state.update(config.DEFAULTS)

    def test_both_parts_are_on_and_the_banner_stands_right_by_default(self):
        self.assertTrue(config.garage_enabled())
        self.assertTrue(config.battle_enabled())
        self.assertEqual(config.tray_side(), 'right')

    def test_each_part_switches_off_on_its_own(self):
        config.apply({'garageEnabled': False})
        self.assertFalse(config.garage_enabled())
        self.assertTrue(config.battle_enabled())

    def test_the_master_switch_turns_both_parts_off(self):
        config.apply({'enabled': False})
        self.assertFalse(config.garage_enabled())
        self.assertFalse(config.battle_enabled())

    def test_an_unknown_side_or_key_is_dropped(self):
        self.assertEqual(config.sanitize({'traySide': 'up', 'other': 1}), {})

    def test_the_panel_shows_its_full_information_always_by_default(self):
        self.assertEqual(config.panel_details(), 'always')

    def test_an_unknown_panel_details_value_is_dropped(self):
        self.assertEqual(config.sanitize({'panelDetails': 'sometimes'}), {})
        self.assertEqual(config.sanitize({'panelDetails': 'alt'}), {'panelDetails': 'alt'})

    def test_the_menu_form_maps_both_ways(self):
        config.apply({'traySide': 'left', 'battleEnabled': False, 'panelDetails': 'never'})
        values = config.menu_values()
        self.assertEqual(values['traySide'], 1)
        self.assertEqual(values['panelDetails'], 2)
        self.assertFalse(values['battleEnabled'])
        menu_keys = dict((key, value) for key, value in config.sanitize(config.current()).items()
                         if key != 'panelPosition')
        self.assertEqual(config.from_menu(values), menu_keys)

    def test_the_template_carries_the_defaults(self):
        config.apply({'traySide': 'left', 'garageEnabled': False, 'panelDetails': 'alt'})
        template = config.menu_template()
        controls = dict((control['varName'], control['value'])
                        for column in ('column1', 'column2') for control in template[column])
        self.assertEqual(controls, {'garageEnabled': True, 'battleEnabled': True, 'panelDetails': 0, 'traySide': 0})

    def test_the_garage_and_the_battle_each_have_a_column_under_their_switch(self):
        template = config.menu_template()
        self.assertEqual([control['varName'] for control in template['column1']], ['garageEnabled', 'traySide'])
        self.assertEqual([control['varName'] for control in template['column2']], ['battleEnabled', 'panelDetails'])

    def test_the_details_choices_carry_the_labels_of_the_client(self):
        control = [c for c in config.menu_template()['column2'] if c['varName'] == 'panelDetails'][0]
        # Outside the client, the English text of the client's own setting stands in.
        self.assertEqual([option['label'] for option in control['options']],
                         ['Display always', 'Press Alt to display', 'Do not display'])

    def test_the_panel_has_no_saved_position_by_default(self):
        self.assertIsNone(config.panel_position())

    def test_a_saved_position_keeps_whole_pixels_and_its_screen_size(self):
        position = {'x': 812.6, 'y': 96, 'parentWidth': 1920, 'parentHeight': 1080}
        self.assertEqual(config.sanitize({'panelPosition': position})['panelPosition'],
                         {'x': 813, 'y': 96, 'parentWidth': 1920, 'parentHeight': 1080})

    def test_a_broken_position_puts_the_panel_back_in_its_default_place(self):
        for position in ({'x': 1, 'y': 2}, {'x': 1, 'y': 2, 'parentWidth': 0, 'parentHeight': 9}, 'top', None):
            self.assertIsNone(config.sanitize({'panelPosition': position})['panelPosition'])

    def test_a_menu_change_leaves_the_position_alone(self):
        position = {'x': 10, 'y': 20, 'parentWidth': 1920, 'parentHeight': 1080}
        config.apply({'panelPosition': position})
        config.apply(config.from_menu({'battleEnabled': False}))
        self.assertEqual(config.panel_position(), position)


if __name__ == '__main__':
    unittest.main()
