# -*- coding: utf-8 -*-
"""Which battle type each vehicle went into, so the garage can tell which battles count.

The garage knows that a vehicle is still in a battle, but not in which kind. The client marks such
a vehicle with the inventory lock `LOCK_REASON.ON_ARENA`, and that lock carries no battle type:
there is one reason for every mode. A Crucible mission counts only random battles, so a vehicle
in an Onslaught battle must not raise the warning.

The mod runs in battle as well, so it records the facts itself. When a battle starts,
`onAvatarReady` gives the arena: its battle type, its unique ID, and the vehicle type of the
player. The record goes into a file per account, so it survives a restart of the client while
the vehicle is still in battle. The garage then reads it for each vehicle in battle.

A vehicle is in one battle at a time, so the record is keyed by vehicle and the newest one wins.
A record older than three hours is dropped: no battle runs that long.

A reconnect enters the same arena again. The record then keeps the time of the first entry, so
the battle panel can tell a reconnect from a first entry (see battle_session).

Every client import stays inside a function, so this module is importable outside the game.
"""
from __future__ import absolute_import, print_function, unicode_literals

import io
import json
import os
import time

from .constants import MOD_CONFIG_DIR_NAME
from .storage import atomic_write_text, resolve_mod_data_dir

_FILE_PATTERN = 'battles_{0}.json'
_MAX_AGE_SECONDS = 3 * 3600

_state = {'installed': False, 'logger': None}


def path_for(account_dbid):
    data_dir = resolve_mod_data_dir(MOD_CONFIG_DIR_NAME)
    if not data_dir or not account_dbid:
        return None
    return os.path.join(data_dir, _FILE_PATTERN.format(int(account_dbid)))


def prune(records, now):
    """The records that are not too old to belong to a battle still in progress."""
    return dict((key, value) for key, value in records.items()
                if isinstance(value, dict) and now - (value.get('time') or 0) < _MAX_AGE_SECONDS)


def load(account_dbid, logger, now=None):
    """{intCD: record} for this account. Each record holds `bonusType`, `arena` and `time`."""
    path = path_for(account_dbid)
    if not path or not os.path.isfile(path):
        return {}
    try:
        with io.open(path, 'r', encoding='utf-8') as handle:
            data = json.loads(handle.read())
    except Exception:
        logger.exception('Failed to read %s', path)
        return {}
    if not isinstance(data, dict):
        return {}
    records = {}
    for key, value in prune(data, time.time() if now is None else now).items():
        try:
            records[int(key)] = value
        except (TypeError, ValueError):
            continue
    return records


def bonus_types_by_vehicle(account_dbid, logger):
    """{intCD: battle type} for this account, the form `crucible.counted_in_battle` reads."""
    return dict((key, value.get('bonusType')) for key, value in load(account_dbid, logger).items())


def record(account_dbid, int_cd, bonus_type, arena_id, logger, now=None):
    """Note that this vehicle went into a battle of this type. Returns True when written.

    `time` is the first entry into this arena, so a reconnect keeps it.
    """
    path = path_for(account_dbid)
    if not path or not int_cd:
        return False
    now = time.time() if now is None else now
    records = dict((str(key), value) for key, value in load(account_dbid, logger, now).items())
    key = str(int(int_cd))
    before = records.get(key) or {}
    entered = before.get('time') if arena_id is not None and before.get('arena') == arena_id else None
    records[key] = {'bonusType': bonus_type, 'arena': arena_id, 'time': int(entered or now)}
    text = json.dumps(records, indent=2, sort_keys=True)
    if not isinstance(text, type(u'')):
        text = text.decode('ascii')
    return atomic_write_text(path, text, logger)


def first_entry(account_dbid, int_cd, arena_id, logger, now=None):
    """The time of the first entry of this vehicle into this arena, or None when there is none."""
    if arena_id is None or not int_cd:
        return None
    entry = load(account_dbid, logger, now).get(int(int_cd)) or {}
    return entry.get('time') if entry.get('arena') == arena_id else None


def install(logger):
    if _state['installed']:
        return
    from PlayerEvents import g_playerEvents
    g_playerEvents.onAvatarReady += _on_avatar_ready
    _state['installed'] = True
    _state['logger'] = logger


def uninstall(logger):
    if not _state['installed']:
        return
    try:
        from PlayerEvents import g_playerEvents
        g_playerEvents.onAvatarReady -= _on_avatar_ready
    except Exception:
        logger.exception('Failed to unsubscribe from onAvatarReady')
    _state['installed'] = False


def _on_avatar_ready(*args):
    # Runs inside the client's own event dispatch, so nothing may leave it.
    logger = _state['logger']
    try:
        _record_current_battle(logger)
    except Exception:
        logger.exception('Failed to record the battle type')


def current_battle():
    """(account, intCD of the vehicle, battle type, arena ID) of the battle now, or None."""
    import BigWorld
    from gui.shared.utils import getPlayerDatabaseID
    player = BigWorld.player()
    arena = getattr(player, 'arena', None)
    if arena is None:
        return None
    vehicle = arena.vehicles.get(player.playerVehicleID) or {}
    vehicle_type = vehicle.get('vehicleType')
    int_cd = vehicle_type.type.compactDescr if vehicle_type is not None else None
    return getPlayerDatabaseID(), int_cd, arena.bonusType, getattr(player, 'arenaUniqueID', None)


def _record_current_battle(logger):
    battle = current_battle()
    if battle is None:
        return
    account, int_cd, bonus_type, arena_id = battle
    if record(account, int_cd, bonus_type, arena_id, logger):
        logger.info('Battle recorded: vehicle %s in battle type %s', int_cd, bonus_type)
