# -*- coding: utf-8 -*-
"""Tests for the way back a banner click gives the campaign screen.

The client's back stack is stood in for here, with the same three calls the real one offers:
`getStateWithParamStack`, `pop` and `push`. Two things decide whether the result is right.

The first is how many steps a campaign takes. Campaign 3 sits a screen deeper than campaigns 1
and 2, so it records two states and they walk back out in order.

The second is where those entries go. Campaign 3 goes through a loading step which takes the
top entry back off once the sub-hangar is built. Entries written on top of that one would send
the player to the campaign map instead of the campaign.

Reaching the lobby state machine, and naming the states of each campaign, are functions of
their own in `back_navigation` so that these tests can stand in for them.
"""
from __future__ import absolute_import, print_function, unicode_literals

import unittest

from zanju_ct import back_navigation


class _Logger(object):
    def __init__(self):
        self.messages = []

    def info(self, message, *args):
        self.messages.append(message)

    def warning(self, message, *args):
        self.messages.append(message)

    def exception(self, message, *args):
        self.messages.append(message)


class _State(object):
    """A lobby state, named by the route the client reports for it."""

    def __init__(self, state_id):
        self.state_id = state_id

    def getStateID(self):
        return self.state_id


class _RecordedStates(object):
    """The three calls `back_navigation` makes on the client's own stack."""

    def __init__(self, entries=None):
        self.entries = list(entries or ())

    def getStateWithParamStack(self):
        return self.entries[:]

    def pop(self):
        return self.entries.pop()

    def push(self, state, params=None):
        self.entries.append((state, params if params is not None else {}))

    def states(self):
        return [state for state, _ in self.entries]


class _RouteInfo(object):
    def __init__(self, state):
        self.state = state


class _Machine(object):
    def __init__(self, route, recorded, states):
        self.visibleRouteInfo = _RouteInfo(_State(route)) if route else None
        self.states = states
        self.refreshed = 0
        self._LobbyStateMachine__recordedStates = recorded
        self._LobbyStateMachine__updateVisibleRoute = self._refresh

    def getStateByCls(self, state_class):
        return self.states.get(state_class)

    def _refresh(self):
        self.refreshed += 1


# Stands in for the client's own state classes. Only identity matters to `back_navigation`.
_SELECTOR_CLS = 'CampaignSelectorState'
_PM3_CLS = 'PersonalMissions3State'

_SELECTOR = _State('subScope/subLayer/campaignSelector')
_PM3 = _State('subScope/subLayer/personalMissions3Entry/personalMissions3')

_PAGE_ROUTE = 'subScope/subLayer/personalMissionsPage'
_MISSIONS_ROUTE = 'subScope/subLayer/personalMissions3Entry/personalMissions3/missions'
_LOADING_ROUTE = 'subScope/subLayer/personalMissions3Entry/personalMissions3/loading'


class RecordPathBackTest(unittest.TestCase):
    def setUp(self):
        self._real_machine = back_navigation._get_machine
        self._real_steps = back_navigation._steps_back
        back_navigation._steps_back = self._steps_back
        back_navigation._reported_failure = False

    def tearDown(self):
        back_navigation._get_machine = self._real_machine
        back_navigation._steps_back = self._real_steps
        back_navigation._reported_failure = False

    @staticmethod
    def _steps_back(route):
        """The real mapping, with the client's classes replaced by two plain names."""
        if back_navigation._is_inside(route, 'subScope/subLayer/personalMissions3Entry'):
            return (_SELECTOR_CLS, _PM3_CLS)
        if back_navigation._is_inside(route, _PAGE_ROUTE):
            return (_SELECTOR_CLS,)
        return ()

    def _machine(self, route=_PAGE_ROUTE, entries=None, states=None):
        if states is None:
            states = {_SELECTOR_CLS: _SELECTOR, _PM3_CLS: _PM3}
        machine = _Machine(route, _RecordedStates(entries), states)
        back_navigation._get_machine = lambda: machine
        return machine

    def _stack(self, machine):
        return machine._LobbyStateMachine__recordedStates

    def test_campaign_1_and_2_record_the_campaign_map_alone(self):
        # Their whole operation is one screen, so the map is the only step back.
        machine = self._machine(route=_PAGE_ROUTE)
        self.assertTrue(back_navigation.record_path_back(_Logger()))
        self.assertEqual(self._stack(machine).states(), [_SELECTOR])

    def test_campaign_3_records_the_campaign_under_the_map(self):
        # Two presses back, in the order the client's own path walks them: the campaign first,
        # then the campaign map.
        machine = self._machine(route=_MISSIONS_ROUTE)
        self.assertTrue(back_navigation.record_path_back(_Logger()))
        self.assertEqual(self._stack(machine).states(), [_SELECTOR, _PM3])

    def test_asks_the_client_to_redraw_the_back_button(self):
        # The button is drawn from a route change, and that already fired.
        machine = self._machine()
        back_navigation.record_path_back(_Logger())
        self.assertEqual(machine.refreshed, 1)

    def test_records_the_steps_under_the_loading_step_of_campaign_3(self):
        # The loading step takes the top entry back off when the sub-hangar is built. On top of
        # it, these entries would be taken off instead, and the campaign would never open.
        missions = _State(_MISSIONS_ROUTE)
        machine = self._machine(route=_LOADING_ROUTE, entries=[(missions, {'operationID': 9})])
        self.assertTrue(back_navigation.record_path_back(_Logger()))
        self.assertEqual(self._stack(machine).states(), [_SELECTOR, _PM3, missions])

    def test_keeps_the_params_of_the_entries_it_moves(self):
        missions = _State(_MISSIONS_ROUTE)
        params = {'operationID': 9, 'category': 'assault'}
        machine = self._machine(route=_LOADING_ROUTE, entries=[(missions, params)])
        back_navigation.record_path_back(_Logger())
        self.assertEqual(self._stack(machine).entries[-1], (missions, params))

    def test_lets_each_state_serialize_its_own_params(self):
        # The client's own push does the same, and campaign 3 reads its operation out of that.
        machine = self._machine(route=_MISSIONS_ROUTE)
        pushed = self._stack(machine).entries
        back_navigation.record_path_back(_Logger())
        self.assertEqual([params for _, params in pushed], [{}, {}])

    def test_records_nothing_when_the_player_is_still_in_the_garage(self):
        # Both client dispatchers refuse the navigation quietly when the screen cannot open.
        machine = self._machine(route='subScope/subLayer/hangar')
        logger = _Logger()
        self.assertFalse(back_navigation.record_path_back(logger))
        self.assertEqual(self._stack(machine).states(), [])
        self.assertEqual(machine.refreshed, 0)
        self.assertEqual(logger.messages, [])

    def test_records_nothing_outside_the_lobby(self):
        back_navigation._get_machine = lambda: None
        logger = _Logger()
        self.assertFalse(back_navigation.record_path_back(logger))
        self.assertEqual(logger.messages, [])

    def test_does_not_record_a_step_twice(self):
        machine = self._machine(route=_MISSIONS_ROUTE, entries=[(_PM3, {})])
        self.assertFalse(back_navigation.record_path_back(_Logger()))
        self.assertEqual(self._stack(machine).states(), [_PM3])
        self.assertEqual(machine.refreshed, 0)

    def test_leaves_the_stack_alone_when_the_client_renamed_the_back_stack(self):
        # Entries with no button to explain them would still change what Escape does.
        already_there = _State('other')
        machine = self._machine(entries=[(already_there, {})])
        del machine._LobbyStateMachine__updateVisibleRoute
        logger = _Logger()
        self.assertFalse(back_navigation.record_path_back(logger))
        self.assertEqual(self._stack(machine).states(), [already_there])
        self.assertEqual(len(logger.messages), 1)

    def test_leaves_the_stack_alone_when_one_step_is_missing(self):
        # Half a path back is worse than none: it would skip a screen without saying so.
        machine = self._machine(route=_MISSIONS_ROUTE, states={_SELECTOR_CLS: _SELECTOR})
        logger = _Logger()
        self.assertFalse(back_navigation.record_path_back(logger))
        self.assertEqual(self._stack(machine).states(), [])
        self.assertEqual(len(logger.messages), 1)

    def test_reports_a_missing_state_once(self):
        self._machine(states={})
        logger = _Logger()
        self.assertFalse(back_navigation.record_path_back(logger))
        self.assertFalse(back_navigation.record_path_back(logger))
        self.assertEqual(len(logger.messages), 1)

    def test_reports_a_failure_instead_of_raising(self):
        def _boom():
            raise ValueError('the client changed this call')

        back_navigation._get_machine = _boom
        logger = _Logger()
        self.assertFalse(back_navigation.record_path_back(logger))
        self.assertEqual(len(logger.messages), 1)


class StepsBackTest(unittest.TestCase):
    """The real mapping needs the client, so only its route matching is reachable here."""

    def test_a_screen_under_a_state_counts_as_that_state(self):
        self.assertTrue(back_navigation._is_inside(_MISSIONS_ROUTE,
                                                   'subScope/subLayer/personalMissions3Entry'))

    def test_the_state_itself_counts(self):
        self.assertTrue(back_navigation._is_inside(_PAGE_ROUTE, _PAGE_ROUTE))

    def test_a_name_that_only_starts_the_same_does_not_count(self):
        self.assertFalse(back_navigation._is_inside('subScope/subLayer/personalMissionsPageX',
                                                    _PAGE_ROUTE))


if __name__ == '__main__':
    unittest.main()
