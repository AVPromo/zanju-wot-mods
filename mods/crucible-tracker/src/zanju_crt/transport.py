# -*- coding: utf-8 -*-
"""The facts about the active Crucible series, carried from the garage into battle.

A battle cannot ask the client about the Crucible. The client drops the active series when the
account entity goes away, which is what happens when a battle starts (`onAccountBecomeNonPlayer`
in ChallengesController). So the garage writes the facts to a file, one per account, and the
battle reads them back. The file also covers a reconnect into a battle after a restart of the
client, where no garage ran in between. The third-party tracker `crusable_progress_tracker` uses
the same route.

The file is written only when its content changes. The save time is left out of the comparison,
so a garage that refreshes ten times writes it once. The last transport of each account also
stays in memory, and a battle reads that copy first. The file is for a battle that no garage of
this session came before.
"""
from __future__ import absolute_import, print_function, unicode_literals

import io
import json
import os

from .constants import MOD_CONFIG_DIR_NAME
from .storage import atomic_write_text, resolve_mod_data_dir

_FILE_PATTERN = 'battle_{0}.json'

# The text last written for each account, so an unchanged transport is not written again.
_written = {}
# The last transport of each account in this session.
_remembered = {}


def path_for(account_dbid):
    data_dir = resolve_mod_data_dir(MOD_CONFIG_DIR_NAME)
    if not data_dir or not account_dbid:
        return None
    return os.path.join(data_dir, _FILE_PATTERN.format(int(account_dbid)))


def save(account_dbid, data, logger):
    """Write the transport for this account. `data` None means no series is active.

    Returns True when the file changed.
    """
    data = {'active': None} if data is None else data
    if account_dbid:
        _remembered[int(account_dbid)] = data
    path = path_for(account_dbid)
    if not path:
        return False
    key = _encode(_comparable(data))
    if _written.get(path) == key:
        return False
    if atomic_write_text(path, _encode(data), logger):
        _written[path] = key
        return True
    return False


def remembered(account_dbid):
    """The last transport that this session saved for this account, or None."""
    if not account_dbid:
        return None
    return _remembered.get(int(account_dbid))


def load(account_dbid, logger):
    """The transport for this account from its file, or None when there is none or it cannot be
    read."""
    path = path_for(account_dbid)
    if not path or not os.path.isfile(path):
        return None
    try:
        with io.open(path, 'r', encoding='utf-8') as handle:
            data = json.loads(handle.read())
    except Exception:
        logger.exception('Failed to read %s', path)
        return None
    return data if isinstance(data, dict) else None


def _comparable(data):
    # The save time changes on every write, so it would make every write a change.
    return dict((key, value) for key, value in data.items() if key != 'savedAt')


def _encode(data):
    text = json.dumps(data, indent=2, sort_keys=True)
    if not isinstance(text, type(u'')):
        text = text.decode('ascii')
    return text
