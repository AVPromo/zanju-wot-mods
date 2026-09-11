# -*- coding: utf-8 -*-
"""Gives the screen a banner opens the same way back the client's own path gives it.

The client's own campaign screens carry a back button, and a screen opened from one of this
mod's banners does not get it. The game's own garage banner for the Fossa operation has the
same gap, so this improves on the client rather than repairing the mod.

The lobby back stack is not a history of screens. `recorded_states.pushRecordedTransitionSource`
records the source state of the transition the machine just took, and only when that transition
declares `record=True`. `gui/impl/lobby/personal_missions_30/state.py` puts those declarations
on `CampaignSelectorState`, one for each campaign screen. The button therefore appears only
when the player reached the screen from the campaign map. A jump straight out of the garage
takes the transition that hangs off `subScope/subLayer` instead, and that one records nothing.

The way back is not one step for every campaign. Campaign 3 sits a screen deeper: the map opens
the campaign, and the campaign opens the line. Two screens are recorded on the way in, so two
presses walk back out. Campaigns 1 and 2 keep their whole operation on one screen, so the map
is the only step. A client at 2.4.0.0 writes both presses of the campaign 3 path to `game.log`:

    Navigating to subScope/subLayer/personalMissions3Entry/personalMissions3
    Navigating to subScope/subLayer/campaignSelector

The first of those names `PersonalMissions3State`, which is the state to record, and not the
progression screen the player sees. The client records transition sources, and the transition
into the line list hangs off that parent state. Entering it lands on its initial child, which
is the progression screen, so recording the parent puts the player exactly where the client
does.

The missing entries have to be written after the navigation, never before it.
`pushRecordedTransitionSource` first drops every recorded state below the transition source,
and the source of that jump is the root of the whole garage subtree. Entries written before
the click are thrown away by the click itself.

They go under everything already recorded, not on top. Campaign 3 does not reach its screen in
one step. It enters a loading state while the sub-hangar builds, and that step records itself
and takes itself back off once the build finishes. An entry sitting on top of that one is the
entry it takes off, which drops the player on the campaign map instead of the campaign. Written
underneath, the stack matches what the natural path builds, step for step.

The button is drawn from `LobbyStateMachine.onVisibleRouteChanged`, which fired before the
entries were written, so the route has to be recomputed by hand. The client does the same
itself whenever a closed window prunes that stack.

What this costs the player: Escape walks the same path, so the garage is one press further away
for campaigns 1 and 2, and two for campaign 3. The client's own path costs exactly that,
because the back button and Escape both read this one stack.

Two of the names read below are private and name-mangled, so every call is guarded. A rename
upstream costs the back button and nothing else, which is where this mod stands today.

Every client import stays inside a function, so this module is importable outside the game.
"""
from __future__ import absolute_import, print_function, unicode_literals

# Whether a failure was already reported. It is reported once: a name this module cannot reach
# is missing for every later click as well, and the campaign screen still opened.
_reported_failure = False


def record_path_back(logger):
    """Record the screens the client's own path would have recorded, under the screen just opened.

    Returns True when the entries were written. Call this right after the navigation and only
    then. It reads where the player landed, and it does nothing unless that is a campaign
    screen.
    """
    try:
        machine = _get_machine()
        if machine is None:
            return False
        route = _visible_route(machine)
        classes = _steps_back(route) if route else ()
        if not classes:
            return False
        recorded = getattr(machine, '_LobbyStateMachine__recordedStates', None)
        refresh = getattr(machine, '_LobbyStateMachine__updateVisibleRoute', None)
        states = [machine.getStateByCls(state_class) for state_class in classes]
        if recorded is None or refresh is None or any(state is None for state in states):
            # Checked before the stack is touched. Entries with no button to explain them would
            # change what Escape does and show the player nothing.
            _report(logger, 'The lobby state machine no longer offers a back stack to write to')
            return False
        if not _insert_at_bottom(recorded, states):
            return False
        refresh()
        logger.info('Recorded the way back from %s: %s', route,
                    ', '.join(state.getStateID() for state in states))
        return True
    except Exception:
        # Worded to cover the redraw as well. A fault there leaves sound entries behind and
        # only costs the button, so a message naming the entries alone would misread.
        _report(logger, 'Failed to give the campaign screen a back button', failed=True)
        return False


def _steps_back(route):
    """The states the client's own path records for this screen, outermost first.

    Empty for any other route. Both client dispatchers refuse the navigation themselves when
    the screen cannot open, and they refuse it quietly. Without that answer a refused click
    would leave the entries behind and give the garage a back button to the campaign map.
    """
    from gui.Scaleform.daapi.view.lobby.missions.personal.state import PersonalMissionsPageState
    from gui.impl.lobby.personal_missions_30.state import (CampaignSelectorState,
                                                           PersonalMissions3EntryState,
                                                           PersonalMissions3State)
    if _is_inside(route, PersonalMissions3EntryState.STATE_ID):
        # The whole branch counts as arrival: the loading step, the progression screen and the
        # line list all live under this one state, and the way out is the same from each.
        return (CampaignSelectorState, PersonalMissions3State)
    if _is_inside(route, PersonalMissionsPageState.STATE_ID):
        return (CampaignSelectorState,)
    return ()


def _is_inside(route, state_id):
    """Whether this route is that state, or a screen under it."""
    return route == state_id or route.startswith(state_id + '/')


def _insert_at_bottom(recorded, states):
    """Write `states` under every entry already recorded. False when one is already there.

    `_RecordedStates` offers no insert, so the entries above are taken off and put back. They
    are put back in their own order, which leaves the stack exactly as it was with the new
    entries added at the bottom.
    """
    above = recorded.getStateWithParamStack()
    for recorded_state, _ in above:
        for state in states:
            if recorded_state is state:
                # A second copy would cost the player one more press of back for nothing.
                return False

    for _ in above:
        recorded.pop()
    for state in states:
        # No params given, so each state serializes its own, which is what the client's own
        # push does. Campaign 3 reads the operation it was opened with out of that.
        recorded.push(state)
    for recorded_state, params in above:
        recorded.push(recorded_state, params)
    return True


def _visible_route(machine):
    """The route the player is on, the same string the client writes to `game.log`."""
    info = machine.visibleRouteInfo
    state = info.state if info is not None else None
    return state.getStateID() if state is not None else None


def _get_machine():
    """The lobby's state machine, or None outside the lobby.

    Its own function so a test can stand in for it, the same way `route_gate` does.
    """
    from gui.Scaleform.lobby_entry import getLobbyStateMachine
    return getLobbyStateMachine()


def _report(logger, message, failed=False):
    global _reported_failure
    if _reported_failure:
        return
    _reported_failure = True
    if failed:
        logger.exception(message)
    else:
        logger.warning(message)
