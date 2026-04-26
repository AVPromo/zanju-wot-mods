"""
mod_crew_post_progression.py

Template mod for account-level crew post progression values.
Keeps global crew XP parsing separated from vehicle-specific research progress.
"""
from __future__ import print_function, unicode_literals

import logging

import BigWorld
from CurrentVehicle import g_currentVehicle
from helpers import dependency
from skeletons.gui.shared import IItemsCache

_logger = logging.getLogger('zanju.crewpostprogression')

MOD_ID = 'zanju.crewpostprogression'
MOD_VERSION = '0.1.0.0'

_config = {
    'enabled': True,
}


def _load_config():
    import json
    import os
    try:
        path = os.path.join('mods', 'configs', 'crew-post-progression', 'config.json')
        if os.path.isfile(path):
            with open(path, 'r') as fh:
                _config.update(json.load(fh))
            _logger.info('Config loaded from %s', path)
    except Exception:
        _logger.exception('Failed to load config, using defaults')


class CrewPostProgressionTemplate(object):
    itemsCache = dependency.descriptor(IItemsCache)

    def __init__(self):
        self._active = False

    def start(self):
        self._active = True
        g_currentVehicle.onChanged += self._on_vehicle_changed
        BigWorld.callback(0.5, self._deferred_update)

    def stop(self):
        self._active = False
        g_currentVehicle.onChanged -= self._on_vehicle_changed

    def _deferred_update(self):
        if self._active:
            self._log_global_pool()

    def _on_vehicle_changed(self):
        if self._active:
            self._log_global_pool()

    def _collect_global_xp_pool(self):
        stats = self.itemsCache.items.stats
        return getattr(stats, 'postProgressionXP', 0) or 0

    def _log_global_pool(self):
        if not _config.get('enabled'):
            return
        try:
            value = self._collect_global_xp_pool()
            _logger.info('Crew post-progression global XP pool=%d', value)
        except Exception:
            _logger.exception('Failed to collect crew post-progression global XP pool')


_mod = None


def init():
    global _mod
    _logger.info('%s v%s initializing', MOD_ID, MOD_VERSION)
    try:
        _load_config()
        _mod = CrewPostProgressionTemplate()
        _mod.start()
        _logger.info('%s initialized', MOD_ID)
    except Exception:
        _logger.exception('%s failed to initialize', MOD_ID)


def fini():
    global _mod
    try:
        if _mod is not None:
            _mod.stop()
            _mod = None
    except Exception:
        _logger.exception('%s error in fini', MOD_ID)
