# -*- coding: utf-8 -*-
"""Attaches the campaign widgets to the garage's Gameface document.

The widgets are plain HTML/JS running inside the game's own hangar document. Getting them
there means using `net.openwg.gameface`: its bootstrap runs in every Gameface document and
loads whatever a `ModInjectModel` on one of that document's SUB-views lists. We attach such a
model, plus our own data model (`zanjuCtWidgets`) carrying the campaign snapshot, which
widgets.js reads.

The banners are fixed beside the garage's vehicle name block, so no position is persisted. The
one thing they send back is a click: the JS reports which campaign was clicked and which keys
were held with it, and Python either opens the client's own screen for that campaign's mission
(see navigation) or pauses or resets it (see mission_actions).

The models ride on a child sub-view of the mod's own, which hangar_child adds to the random
garage. `gf_mod_inject` always writes to one fixed field, so a sub-view holds one mod at most. A
child of our own takes no sub-view that another mod could want, and no other mod writes to it.
The JS finds our data by scanning sub-views, so where the child sits does not matter to it.

The banners stand in the shared banner tray, on the side the config names. tray.js holds the
row arithmetic that this mod and crucible-tracker share.

See docs/reference/gameface-mod-widgets.md for the wider set of rules this follows.
"""
from __future__ import absolute_import, print_function, unicode_literals

import json
import logging

from frameworks.wulf import ViewModel

from .. import (collector, config, hangar_child, held_keys, mission_actions, mode_gate, navigation,
                route_gate)
from . import card_window
from ..constants import LOGGER_NAME
from ..localization import get_text as _loc

_MODULE_URL = 'coui://gui/gameface/mods/zanju_campaigns/widgets.js'
_STYLE_URL = 'coui://gui/gameface/mods/zanju_campaigns/widgets.css'
_INJECT_NAME = 'zanju_ct_widgets'
_DATA_PROPERTY = 'zanjuCtWidgets'
# Where the mod's own child sits among the children of the random garage view: 'ZNCT' in ASCII.
# Far above the client's resource IDs, which were near 136,000 on 2.4.0.2. Each of our mods has
# its own ID, listed in docs/reference/gameface-mod-widgets.md.
_POS_ID = 0x5A4E4354

_module_logger = logging.getLogger(LOGGER_NAME)

# Last campaign count reported to the log, so the payload build can report when the answer
# changes without writing a line on every tank switch. `None` means nothing logged yet.
_last_logged_count = None

# Client strings this mod reads instead of shipping its own. Written as the keys themselves
# rather than through `gui.Scaleform.locale`, because that module holds these very strings and
# the key is the half worth reading here. Each one names the same thing the widget names:
#
# - the two condition group headings, which the game's own mission card prints in that exact
#   place, and the separator it prints between two conditions of an "or" group
# - the state a mission is in once its primary objective is met and its secondary one is not
_KEY_PRIMARY = '#personal_missions:detailedView/conditionslabel'
_KEY_SECONDARY = '#personal_missions:detailedView/conditionsFullylabel'
_KEY_OR = '#personal_missions:conditions/orGroup'
_KEY_IMPROVING = '#ingame_gui:statistics/tab/quests/status/increaseResult'

_installed = []
# How many data models to keep, newest last. The client builds one hangar document at a time,
# so only the last entry is ever on screen. The others cover the frame or two that a rebuild
# can overlap in, and leave a margin for a mode that builds two.
_MAX_LIVE_MODELS = 4
# Every model this session ever attached. Only the log reads it. It is the number that made
# the growth below visible, so the trim must not hide it.
_attached_total = 0
# Live data models, so a change of tank or of mission progress can be pushed to whichever
# hangar views are currently carrying one.
#
# Nothing here can tell when a view dies. A torn-down view model takes an update and ignores
# it rather than refusing it, so the drop path in `_push` never runs, and `ViewModel` is not a
# `PyObjectEntity`, so it carries no `isBound` to ask instead. Measured on EU 2.3.1.3.
#
# The list is therefore trimmed by age, not by liveness. It used to grow with no bound at all,
# which cost one property set per dead entry on every refresh. A game.log from 2.4.0 shows 50
# entries after a few minutes of walking in and out of the garage, and `setSnapshot` carries
# the whole campaign snapshot as JSON. The sibling directives mod shares the pattern.
_models = []


class _WidgetsDataModel(ViewModel):
    """The campaign snapshot and whether to show it, read by widgets.js."""

    def __init__(self, payload):
        self._payload = payload
        # The counts reach the native view model, so they have to match what _initialize
        # actually adds: three properties, and two commands since the card window took its
        # hover reports through one of its own.
        super(_WidgetsDataModel, self).__init__(properties=3, commands=2)

    def _initialize(self):
        super(_WidgetsDataModel, self)._initialize()
        # The snapshot travels as JSON in a single string property: wulf arrays would need a
        # nested view model per row, and the widgets re-render wholesale anyway.
        self._addStringProperty('snapshot', self._payload)
        # Property indices are assigned in declaration order across every type, which is how
        # the setters below address them. This view is usually built before the lobby has
        # settled, so `visible` starts from whatever the two gates can answer at that point.
        self._addBoolProperty('visible', _widgets_visible())
        # Which modifier keys are held, as one string. Pushed on its own rather than folded
        # into the snapshot: a key change must not cost a rebuild of every card, and the
        # snapshot is far too big to resend for two booleans.
        self._addStringProperty('heldKeys', held_keys.text())
        # JS -> Python. `_addCommand` takes only the name and returns a Command; the handler
        # is bound to it with `+=` (it wraps an Event), which is how the game's own generated
        # view models declare theirs. A wulf command carries exactly one map argument.
        self.missionAction = self._addCommand('missionAction')
        self.missionAction += self.__onMissionAction
        # The hover card draws in a window of the mod's own, so the banners cannot open it with
        # CSS any more. They report which one the pointer is on, and where it sits.
        self.cardHover = self._addCommand('cardHover')
        self.cardHover += self.__onCardHover

    # Indices matching the declaration order in _initialize.
    _SNAPSHOT_INDEX = 0
    _VISIBLE_INDEX = 1
    _HELD_KEYS_INDEX = 2

    def setSnapshot(self, payload):
        self._payload = payload
        self._setString(self._SNAPSHOT_INDEX, payload)

    def setVisible(self, visible):
        self._setBool(self._VISIBLE_INDEX, bool(visible))

    def setHeldKeys(self, text):
        self._setString(self._HELD_KEYS_INDEX, text)

    def __onCardHover(self, *args):
        """The pointer entered or left a banner. An empty branch means it left."""
        arg = args[0] if args else None
        branch = _map_get(arg, 'branch')
        if not branch:
            _module_logger.debug('Hover left')
            card_window.hide(_module_logger)
            return
        _module_logger.debug('Hover on %s', branch)
        _show_card(branch, arg, _module_logger)

    def __onMissionAction(self, *args):
        """A banner was clicked. Which action it asks for depends on the keys held with it."""
        arg = args[0] if args else None
        branch = _map_get(arg, 'branch')
        if not branch:
            return
        action = _map_get(arg, 'action') or mission_actions.ACTION_OPEN
        if action == mission_actions.ACTION_OPEN:
            navigation.open_mission(branch, _module_logger)
            return

        # Resolved here rather than in `mission_actions`, which stays free of `collector` so
        # the two do not import each other. Resolved fresh on every click for the same reason
        # `navigation` does: the mission behind a banner can change between render and click.
        quest = collector.find_active_mission(branch, _module_logger)
        if quest is None:
            _module_logger.info('Campaign %s has no active mission to %s', branch, action)
            return
        mission_actions.perform(quest, action, _module_logger)


def _map_get(arg, key):
    """Read a key from the single map argument a wulf command carries.

    It may arrive as a plain dict or as a wrapped map exposing .get(); tolerate both, and
    treat anything unreadable as absent rather than raising inside a UI callback.
    """
    if isinstance(arg, dict):
        return arg.get(key)
    getter = getattr(arg, 'get', None)
    if callable(getter):
        try:
            return arg.get(key)
        except Exception:
            return None
    return None


def _build_payload(logger):
    """Snapshot plus its labels, as JSON for the widgets to render.

    The labels travel with the data so translation stays on the Python side, where the
    localization bundle lives; the JS only ever renders what it is handed.

    A snapshot with no campaigns in it is not an error and does not hide anything: the models
    are built well before the garage has finished assembling, so an empty first payload is the
    normal case, and every later refresh replaces it.
    """
    try:
        snapshot = collector.collect(logger)
        _log_payload_change(snapshot, logger)
        # Which side of the vehicle name the row stands on. widgets.js hands it to tray.js.
        snapshot['layout'] = {'side': config.tray_side()}
        snapshot['labels'] = {
            'noMission': _loc('LABEL_NO_MISSION'),
            'paused': _loc('LABEL_PAUSED'),
            # `_client_text` here and below: the client's own words, which spare a
            # translator four strings and give every language the game ships.
            'primaryConditions': _client_text(_KEY_PRIMARY, logger),
            'secondaryConditions': _client_text(_KEY_SECONDARY, logger),
            'or': _client_text(_KEY_OR, logger),
            'lockedVehicles': _loc('LABEL_LOCKED_VEHICLES'),
            'vehicleLocked': _loc('LABEL_VEHICLE_LOCKED'),
            'improving': _client_text(_KEY_IMPROVING, logger),
            'pawned': _loc('LABEL_PAWNED'),
            'hintOpen': _loc('LABEL_HINT_OPEN'),
            'hintPause': _loc('LABEL_HINT_PAUSE'),
            'hintResume': _loc('LABEL_HINT_RESUME'),
            'hintReset': _loc('LABEL_HINT_RESET'),
        }
        return json.dumps(snapshot)
    except Exception:
        logger.exception('Failed to serialise the campaign snapshot')
        return '{}'


def _client_text(key, logger, **format_kwargs):
    """A string the client already ships translated, or an empty string.

    An empty answer is the right failure here. The widget draws whatever it is handed, so a
    key the client drops leaves its line blank and costs nothing else. The secondary heading
    keeps its element even when empty, because that element carries the rule dividing the two
    condition groups, and losing the rule would read worse than losing the word.
    """
    try:
        from helpers import i18n
        return i18n.makeString(key, **format_kwargs)
    except Exception:
        logger.exception('Failed to read the client string %s', key)
        return ''


def _log_payload_change(snapshot, logger):
    """Report how many campaigns a snapshot found, when that number changes.

    The banners cannot appear before the client has the mission data, and how long that takes
    is not something this mod controls. Timing it is the only way to tell a slow client from a
    slow mod, so the first build is logged and every later change of the count -- which is what
    a reader of `game.log` needs to place the banners' arrival against the garage's.
    """
    global _last_logged_count
    try:
        count = len(snapshot.get('campaigns') or ())
    except Exception:
        return
    if count == _last_logged_count:
        return
    _last_logged_count = count
    logger.info('Snapshot has %d active campaign(s), vehicle in garage: %s',
                count, bool(snapshot.get('hasVehicle')))


def refresh(logger):
    """Rebuild the snapshot and push it to every live widget model."""
    if not _models:
        return
    payload = _build_payload(logger)
    _push(lambda model: model.setSnapshot(payload), logger)


def _show_card(branch, arg, logger):
    """Hand the card window the entry behind one banner, plus where that banner sits.

    The snapshot is rebuilt rather than cached: a hover is a rare event at human speed, and a
    cached copy would be the one thing on screen that could disagree with the banner above it.
    """
    try:
        snapshot = json.loads(_build_payload(logger))
    except Exception:
        logger.exception('Failed to read the snapshot for the hover card')
        return
    entry = None
    for row in snapshot.get('campaigns') or ():
        if row.get('branch') == branch:
            entry = row
            break
    if entry is None:
        card_window.hide(logger)
        return
    rect = (
        _int(_map_get(arg, 'x')), _int(_map_get(arg, 'y')),
        _int(_map_get(arg, 'w')), _int(_map_get(arg, 'h')),
    )
    card_window.show(branch, rect, entry, snapshot.get('labels') or {},
                     held_keys.text(), logger)


def _int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _apply_held_keys(logger):
    if not _widgets_visible():
        # The player is in battle, or on a screen drawn over the garage. No banner is on show,
        # and in battle every entry in `_models` belongs to a lobby the client destroyed long
        # ago. This runs inside the client's key dispatch on every modifier key of the session,
        # so it does as little as it can -- see held_keys for what that dispatch costs.
        return
    text = held_keys.text()
    _push(lambda model: model.setHeldKeys(text), logger)
    # The card draws its own hint lines now, so it needs the keys too.
    card_window.set_held_keys(text, logger)


def _on_held_keys_changed():
    _apply_held_keys(_module_logger)


def _widgets_visible():
    """The settings allow the banners, the garage is on screen, and the mode is one they belong to."""
    return config.is_enabled() and route_gate.is_visible() and mode_gate.is_visible()


def _apply_visibility(logger):
    visible = _widgets_visible()
    _push(lambda model: model.setVisible(visible), logger)
    if visible:
        # The player kept pressing keys while the widgets were off screen, and `_apply_held_keys`
        # dropped every one of those changes. Push the current keys before the banners are seen
        # again, or the first hint line they light is the one held when the garage went away.
        _apply_held_keys(logger)
        return
    # Leaving the garage does not move the pointer, so no banner reports a leave. Without
    # this the card would stay on screen over whatever replaced the garage.
    card_window.hide(logger)


def _push(action, logger):
    """Apply `action` to each model still alive, dropping any that refuses the update."""
    for model in list(_models):
        try:
            action(model)
        except Exception:
            # Not the teardown path: a torn-down view accepts updates and ignores them, so
            # nothing reaches here when one dies. This covers a model that fails for some
            # other reason, which has not been seen and is worth a line if it ever is.
            _forget(model)
            logger.info('Dropped a widgets model that refused an update (%d live)', len(_models))


def _forget(model):
    try:
        _models.remove(model)
    except ValueError:
        pass


def _on_mode_visibility(visible):
    """The player picked a different battle mode, and it changed the answer."""
    _module_logger.info('Random battles is the selected mode: %s', visible)
    _apply_visibility(_module_logger)


def _on_route_visibility(visible):
    _module_logger.info('Garage is the visible route: %s', visible)
    _apply_visibility(_module_logger)
    if visible:
        # The hangar view models are built before the garage is on screen, so the payload they
        # started with can already be stale by the time the player sees it -- the mission data
        # may have landed in between, and on a return from another lobby screen the tank may
        # have changed. Rebuilding here costs one snapshot and closes that gap.
        refresh(_module_logger)


def _bind_events(logger):
    """Refresh on the things that change what the widgets show.

    Called every time a hangar view is built rather than once per session, because the client
    throws our subscriptions away: `g_currentVehicle` clears its whole event manager in
    `destroy()`, which runs on every lobby teardown, so a handler attached once is silently
    gone afterwards.

    `Event.__iadd__` ignores a delegate it already holds, so re-binding costs nothing; the
    explicit membership test is only there to log when a subscription actually had to be
    replaced.
    """
    try:
        from CurrentVehicle import g_currentVehicle
        if _on_vehicle_changed not in g_currentVehicle.onChanged:
            g_currentVehicle.onChanged += _on_vehicle_changed
            logger.info('Subscribed to vehicle changes')
    except Exception:
        logger.exception('Failed to subscribe to vehicle changes')

    _bind_missions(logger)
    # The lobby state machine belongs to the lobby app, so it is a different object after every
    # teardown; `install` compares identity and only re-subscribes when it actually changed.
    route_gate.install(logger, _on_route_visibility)
    # The prebattle dispatcher is replaced on the same schedule, and for the same reason its
    # `install` is called here rather than once at load.
    mode_gate.install(logger, _on_mode_visibility)
    # Unlike the route gate, this subscribes to a module-level singleton that survives every
    # lobby teardown, so it is made once here and never retried.
    held_keys.install(logger, _on_held_keys_changed)


def _bind_missions(logger):
    """Follow the personal missions cache, which owns everything the banners show.

    `onPMSyncCompleted` fires when the cache has re-read the missions -- a mission selected or
    finished, a campaign switched, condition progress arriving after a battle. That is the one
    event that covers all of them, so it is the only mission subscription made here.

    `onSyncCompleted` on the same cache is deliberately not used. `EventsCache.update()` fires
    it immediately before `onPMSyncCompleted` on every path that reaches either, so listening
    to both only builds the same snapshot twice.
    """
    try:
        from helpers import dependency
        from skeletons.gui.server_events import IEventsCache
        events_cache = dependency.instance(IEventsCache)
        if _on_missions_synced not in events_cache.onPMSyncCompleted:
            events_cache.onPMSyncCompleted += _on_missions_synced
            logger.info('Subscribed to personal mission updates')
    except Exception:
        logger.exception('Failed to subscribe to personal mission updates')


def _unbind_events(logger):
    try:
        from CurrentVehicle import g_currentVehicle
        g_currentVehicle.onChanged -= _on_vehicle_changed
    except Exception:
        pass
    try:
        from helpers import dependency
        from skeletons.gui.server_events import IEventsCache
        dependency.instance(IEventsCache).onPMSyncCompleted -= _on_missions_synced
    except Exception:
        pass


def _on_vehicle_changed(*args):
    # A different tank falls in a different line, so every banner can change at once.
    refresh(_module_logger)


def _on_missions_synced(*args):
    refresh(_module_logger)


def install(logger):
    """Give the random garage a child view that carries the widgets. Returns True on success."""
    if _installed:
        return True

    # Almost certainly a no-op here -- neither the lobby app that owns the state machine nor
    # the prebattle dispatcher exists this early -- but both cost nothing, and `_bind_events`
    # retries them on every hangar build.
    route_gate.install(logger, _on_route_visibility)
    mode_gate.install(logger, _on_mode_visibility)
    # Unlike the route gate, this subscribes to a module-level singleton that survives every
    # lobby teardown, so it is made once here and never retried.
    held_keys.install(logger, _on_held_keys_changed)

    route = hangar_child.install(logger, _POS_ID, _INJECT_NAME, [_STYLE_URL], [_MODULE_URL],
                                 _DATA_PROPERTY, _build_data_model)
    if route is None:
        logger.warning('The garage child view could not be set up; the campaign widgets are disabled')
        return False
    _installed.append(route)
    logger.info('Campaign widgets installed (route %s)', route)
    return True


def _build_data_model():
    """The data model for one garage build. hangar_child calls this from the child's model."""
    global _attached_total
    # Subscribed before the snapshot is read, not after. A mission sync landing between the two
    # would otherwise be missed twice over: too early for the subscription to hear it, too late
    # for a payload that was already built.
    _bind_events(_module_logger)
    data_model = _WidgetsDataModel(_build_payload(_module_logger))
    _models.append(data_model)
    del _models[:-_MAX_LIVE_MODELS]
    _attached_total += 1
    _module_logger.info('Campaign widgets attached (%d built, %d kept)', _attached_total, len(_models))
    return data_model


def on_settings_changed(keys):
    """Mod Menu changed a setting. The side reaches the banners with the next snapshot."""
    refresh(_module_logger)
    _apply_visibility(_module_logger)


def uninstall(logger):
    del _installed[:]
    _unbind_events(logger)
    card_window.uninstall(logger)
    route_gate.uninstall(logger)
    mode_gate.uninstall(logger)
    held_keys.uninstall(logger)
    hangar_child.uninstall(logger)
    del _models[:]
