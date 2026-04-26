"""
mod_research_progress_bar.py

Displays research progress for the currently selected vehicle in the hangar:
  - Module / next vehicle unlock progress  (tech tree XP)
  - Elite status progress                  (modules unlocked / total needed)
  - Field modification XP pool             (post-progression / "field mods")
  - Prestige / tier-11 milestones          (prestige system)

BigWorld scripting uses Python 2.7. Avoid Python-3-only syntax.
"""
from __future__ import print_function, unicode_literals

import logging

import BigWorld
from CurrentVehicle import g_currentVehicle
from helpers import dependency
from skeletons.gui.shared import IItemsCache

_logger = logging.getLogger('com.zanju.researchprogressbar')

MOD_ID = 'com.zanju.researchprogressbar'
MOD_VERSION = '0.1.0.0'

# ---------------------------------------------------------------------------
# Config defaults — overridden by _load_config() at startup
# ---------------------------------------------------------------------------
_config = {
    'enabled': True,
    'showTechTree': True,
    'showEliteProgress': True,
    'showFieldMods': True,
    'showPrestige': True,
    # Phase 2: set to 'ui' when a Flash/HTML overlay is implemented
    'displayMode': 'log',
}


def _load_config():
    import json, os
    try:
        path = os.path.join(
            'mods', 'configs', 'research-progress-bar', 'config.json'
        )
        if os.path.isfile(path):
            with open(path, 'r') as fh:
                _config.update(json.load(fh))
            _logger.info('Config loaded from %s', path)
    except Exception:
        _logger.exception('Failed to load config, using defaults')


# ---------------------------------------------------------------------------
# Progress data helpers
# ---------------------------------------------------------------------------

def _make_text_bar(pct, width=20):
    """Returns an ASCII progress bar, e.g. [========------------] 40%"""
    filled = int(width * max(0, min(100, pct)) / 100)
    return '[{0}{1}] {2}%'.format('=' * filled, '-' * (width - filled), pct)


def _next_available_unlock(vehicle, unlocks_set):
    """
    Returns (xp_cost, intCD) for the cheapest unlock whose prerequisites are
    all met but which has not been researched yet, or (None, None) if none.
    """
    best_cost = None
    best_intcd = None
    for _idx, xp_cost, intcd, prereqs in vehicle.getUnlocksDescrs():
        if intcd in unlocks_set:
            continue
        if any(p not in unlocks_set for p in prereqs):
            continue
        if best_cost is None or xp_cost < best_cost:
            best_cost = xp_cost
            best_intcd = intcd
    return best_cost, best_intcd


# ---------------------------------------------------------------------------
# Core mod class
# ---------------------------------------------------------------------------

class ResearchProgressBar(object):
    itemsCache = dependency.descriptor(IItemsCache)

    def __init__(self):
        self._active = False

    # -- lifecycle -----------------------------------------------------------

    def start(self):
        self._active = True
        g_currentVehicle.onChanged += self._on_vehicle_changed
        # Fire immediately so the hangar shows progress on startup
        BigWorld.callback(0.5, self._deferred_update)

    def stop(self):
        self._active = False
        g_currentVehicle.onChanged -= self._on_vehicle_changed

    # -- event handlers ------------------------------------------------------

    def _on_vehicle_changed(self):
        if not self._active:
            return
        try:
            self._update()
        except Exception:
            _logger.exception('Error in _on_vehicle_changed')

    def _deferred_update(self):
        """Called 0.5 s after init to let itemsCache finish its first sync."""
        if self._active:
            try:
                self._update()
            except Exception:
                _logger.exception('Error in _deferred_update')

    # -- data collection -----------------------------------------------------

    def _update(self):
        if not _config.get('enabled'):
            return
        vehicle = g_currentVehicle.item
        if vehicle is None:
            return

        try:
            stats = self.itemsCache.items.stats
        except Exception:
            _logger.exception('itemsCache not ready')
            return

        data = self._collect(vehicle, stats)
        self._render(vehicle, data)

    def _collect(self, vehicle, stats):
        unlocks_set = stats.unlocks

        # --- Tech tree XP progress ---
        veh_xp = stats.vehiclesXPs.get(vehicle.intCD, 0)
        free_xp = max(0, stats.freeXP)
        total_xp = veh_xp + free_xp

        next_cost, next_intcd = _next_available_unlock(vehicle, unlocks_set)
        if next_cost and next_cost > 0:
            tt_pct = min(100, int(total_xp * 100 / next_cost))
        else:
            tt_pct = 100 if vehicle.isElite else 0

        # --- Elite module progress ---
        elite = vehicle.getEliteStatusProgress()
        elite_unlocked = len(elite.unlocked) if hasattr(elite, 'unlocked') else 0
        elite_total = len(elite.total) if hasattr(elite, 'total') else 0
        elite_pct = int(elite_unlocked * 100 / elite_total) if elite_total > 0 else 100

        # --- Field modifications XP pool ---
        pp_xp = getattr(stats, 'postProgressionXP', 0) or 0

        # --- Prestige / tier-11 milestones ---
        # prestigeMilestonesAchieved maps intCD -> milestone count (or dict of levels)
        prestige_raw = getattr(stats, 'prestigeMilestonesAchieved', {}) or {}
        prestige_milestones = prestige_raw.get(vehicle.intCD, 0)

        return {
            'tech_tree': {
                'vehicle_xp': veh_xp,
                'free_xp': free_xp,
                'total_xp': total_xp,
                'next_cost': next_cost,
                'next_intcd': next_intcd,
                'pct': tt_pct,
                'is_elite': vehicle.isElite,
                'is_fully_elite': vehicle.isFullyElite,
            },
            'elite': {
                'unlocked': elite_unlocked,
                'total': elite_total,
                'pct': elite_pct,
            },
            'field_mods': {
                'xp': pp_xp,
                # TODO (Phase 2): query IVehiclePostProgressionController for
                # this vehicle's field mod unlock costs and per-slot progress.
                # Inject via: dependency.descriptor(IVehiclePostProgressionController)
            },
            'prestige': {
                'milestones': prestige_milestones,
            },
        }

    # -- rendering -----------------------------------------------------------

    def _render(self, vehicle, data):
        """
        Phase 1: structured log output.
        Phase 2: replace _render_ui() stub below with a Flash/HTML overlay.
        """
        if _config.get('displayMode') == 'ui':
            self._render_ui(vehicle, data)
        else:
            self._render_log(vehicle, data)

    def _render_log(self, vehicle, data):
        name = getattr(vehicle, 'userName', str(vehicle.intCD))
        _logger.info('--- Research Progress: %s ---', name)

        tt = data['tech_tree']
        if _config.get('showTechTree'):
            if tt['is_fully_elite']:
                _logger.info('  Tech tree:  COMPLETE (fully elite)')
            elif tt['next_cost']:
                _logger.info(
                    '  Tech tree:  %s  (%d / %d XP, free XP: %d)',
                    _make_text_bar(tt['pct']),
                    tt['total_xp'], tt['next_cost'], tt['free_xp'],
                )
            else:
                _logger.info('  Tech tree:  no available unlocks found')

        el = data['elite']
        if _config.get('showEliteProgress') and el['total'] > 0:
            _logger.info(
                '  Elite mods: %s  (%d / %d modules)',
                _make_text_bar(el['pct']),
                el['unlocked'], el['total'],
            )

        fm = data['field_mods']
        if _config.get('showFieldMods') and fm['xp'] > 0:
            _logger.info('  Field mods: %d XP in pool (Phase 2: unlock costs pending)', fm['xp'])

        pr = data['prestige']
        if _config.get('showPrestige') and pr['milestones']:
            _logger.info('  Prestige:   %s milestones achieved', pr['milestones'])

    def _render_ui(self, vehicle, data):
        """
        Phase 2 stub — replace with Flash/HTML overlay logic.
        Until implemented, falls back to log output.
        """
        # TODO: push 'data' to a Flash or GameFace component.
        # Flash: inject via BigWorld.flashCallback / scaleform panel
        # GameFace: register a Python→HTML bridge method
        self._render_log(vehicle, data)


# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------

_mod = None


def init():
    global _mod
    _logger.info('%s v%s initializing', MOD_ID, MOD_VERSION)
    try:
        _load_config()
        _mod = ResearchProgressBar()
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
