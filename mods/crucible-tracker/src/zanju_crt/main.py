"""
zanju_crt.main

Shows a garage banner for the Crucible, the client's sets of demanding missions. The banner
names the active series, its current mission and the shields left, or, with no active series,
how many series are still open. Its hover card lists every available series with its state, and
the conditions of the current mission.

In battle, a panel shows the progress of each condition of the current mission. The garage
writes the facts that a battle needs about the active series (see transport), and the battle
session reads them back (see battle_session).

BigWorld scripting uses Python 2.7. Avoid Python-3-only syntax.
"""
from __future__ import absolute_import, print_function, unicode_literals

import logging

from . import battle_record, battle_session, config
from .constants import LOGGER_NAME, MOD_ID
from .gameface import widgets_inject

_logger = logging.getLogger(LOGGER_NAME)


def init():
    # A failure inside init() that raises AttributeError disappears with no log line, so the
    # mod logs its own traceback. See docs/debugging.md.
    _logger.info('%s initializing', MOD_ID)
    try:
        config.load(_logger)
        # Recorded in every battle, so the garage can tell which vehicles in battle count.
        battle_record.install(_logger)
        widgets_inject.install(_logger)
        battle_session.install(_logger)
        config.register_menu(MOD_ID, _logger, _on_settings_changed)
        _logger.info('%s initialized', MOD_ID)
    except Exception:
        _logger.exception('%s failed to initialize', MOD_ID)


def _on_settings_changed(keys):
    widgets_inject.on_settings_changed(keys)
    battle_session.on_settings_changed(keys)


def fini():
    try:
        battle_session.uninstall(_logger)
        widgets_inject.uninstall(_logger)
        battle_record.uninstall(_logger)
    except Exception:
        _logger.exception('%s error in fini', MOD_ID)
