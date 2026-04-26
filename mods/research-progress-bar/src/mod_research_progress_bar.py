"""
mod_research_progress_bar.py

Displays research progress for the currently selected vehicle in the hangar:
  - Module / next vehicle unlock progress  (tech tree XP)
  - Elite status progress                  (modules unlocked / total needed)
    - Field modification tree progress       (post-progression / "field mods")

BigWorld scripting uses Python 2.7. Avoid Python-3-only syntax.
"""
from __future__ import print_function, unicode_literals

import logging
from numbers import Integral

import BigWorld
from CurrentVehicle import g_currentVehicle
from helpers import dependency
from skeletons.gui.shared import IItemsCache

_logger = logging.getLogger('zanju.researchprogressbar')

MOD_ID = 'zanju.researchprogressbar'
MOD_VERSION = '0.1.0.0'

# ---------------------------------------------------------------------------
# Config defaults — overridden by _load_config() at startup
# ---------------------------------------------------------------------------
_config = {
    'enabled': True,
    'showTechTree': True,
    'showEliteProgress': True,
    'showFieldMods': True,
    # Emits extra field-mod internals to python.log for parser tuning.
    'debugFieldMods': True,
    # Crash-isolation mode for field-mod collection.
    #   off: skip postProgression API access, keep vehicle-level flags only
    #   flags-only: read only vehicle-level availability/active flags
    #   completion-only: flags + postProgression completion/isVehSkillTree
    #   steps-only: completion-only + iterUnorderedSteps() metadata only
    #   state-only: steps-only + getState(True) unlock extraction
    #   next-step-only: state-only + getFirstPurchasableStep() id only
    #   full: include postProgression tree/state/step inspection + XP extraction
    'fieldModsProbeMode': 'next-step-only',
    # In safer modes, try only shallow next-step XP extraction (no method calls).
    'extractNextStepXPLightweight': False,
    # Options: log | ui
    'displayMode': 'log',
    # Approximate normalized screen position for the UI text widget.
    'panelPosX': 0.0,
    'panelPosY': 0.0,
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


def _to_int_or_none(value):
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, Integral):
        return int(value)
    if isinstance(value, float):
        return int(value)
    return None


def _extract_xp_cost(value):
    """Best-effort extraction of XP-like cost from WoT progression objects."""
    direct = _to_int_or_none(value)
    if direct is not None:
        return direct

    if isinstance(value, dict):
        for key in ('xp', 'xpCost', 'requiredXP', 'unlockXP', 'costXP', 'researchCost', 'neededXP'):
            if key in value:
                nested = _extract_xp_cost(value.get(key))
                if nested is not None:
                    return nested
        return None

    if isinstance(value, (list, tuple)):
        for item in value:
            nested = _extract_xp_cost(item)
            if nested is not None:
                return nested
        return None

    for attr in ('xpCost', 'xp', 'requiredXP', 'unlockXP', 'costXP', 'researchCost', 'neededXP'):
        try:
            nested = _extract_xp_cost(getattr(value, attr, None))
            if nested is not None:
                return nested
        except Exception:
            pass

    for method in ('getPrice', 'getCost', 'getXPCost', 'getXP'):
        try:
            if hasattr(value, method):
                raw = getattr(value, method)()
                nested = _extract_xp_cost(raw)
                if nested is not None:
                    return nested
        except Exception:
            pass

    return None


def _extract_xp_cost_lightweight(value):
    """Safer XP extraction variant: no method invocation on runtime objects."""
    direct = _to_int_or_none(value)
    if direct is not None:
        return direct

    if isinstance(value, dict):
        for key in ('xp', 'xpCost', 'requiredXP', 'unlockXP', 'costXP', 'researchCost', 'neededXP'):
            if key in value:
                nested = _extract_xp_cost_lightweight(value.get(key))
                if nested is not None:
                    return nested
        return None

    if isinstance(value, (list, tuple)):
        for item in value:
            nested = _extract_xp_cost_lightweight(item)
            if nested is not None:
                return nested
        return None

    for attr in ('xpCost', 'xp', 'requiredXP', 'unlockXP', 'costXP', 'researchCost', 'neededXP'):
        try:
            nested = _extract_xp_cost_lightweight(getattr(value, attr, None))
            if nested is not None:
                return nested
        except Exception:
            pass

    return None


def _collect_post_progression(vehicle, stats):
    """Collect per-vehicle field-mod / post-progression status."""
    data = {
        'exists': False,
        'active': False,
        'completion': None,
        'completion_name': 'UNKNOWN',
        'total_steps': 0,
        'unlocked_steps': 0,
        'is_veh_skill_tree': False,
        'next_purchasable_step_id': None,
        'raw_unlock_count': 0,
        'unique_step_id_count': 0,
        'unique_level_count': 0,
        'unique_unlocked_step_id_count': 0,
        'unique_unlocked_level_count': 0,
        'next_purchasable_step_xp': None,
        'debug_step_preview': [],
        'debug_unlock_preview': [],
        'debug_level_price_preview': [],
    }

    try:
        # These flags are read directly from vehicle-level properties.
        data['exists'] = bool(getattr(vehicle, 'isPostProgressionExists', False))
        data['active'] = bool(getattr(vehicle, 'isPostProgressionActive', False))
    except Exception:
        _logger.exception('Failed to read vehicle post-progression flags')

    probe_mode = str(_config.get('fieldModsProbeMode', 'completion-only')).lower()

    if probe_mode == 'off':
        return data

    pp = getattr(vehicle, 'postProgression', None)
    if pp is None:
        return data

    if probe_mode in ('completion-only', 'steps-only', 'state-only', 'next-step-only', 'full'):
        try:
            completion = pp.getCompletion()
            data['completion'] = completion
            data['completion_name'] = str(completion)
        except Exception:
            _logger.exception('Failed to read post-progression completion')

        try:
            data['is_veh_skill_tree'] = bool(pp.isVehSkillTree())
        except Exception:
            pass

    step_id_to_level = {}

    if probe_mode in ('steps-only', 'state-only', 'next-step-only', 'full'):
        try:
            steps = list(pp.iterUnorderedSteps())
            data['total_steps'] = len(steps)

            unique_levels = set()
            step_preview = []

            for step in steps:
                sid = getattr(step, 'stepID', None)
                if sid is None:
                    sid = getattr(step, 'id', None)

                level = getattr(step, 'level', None)
                if level is None and hasattr(step, 'getLevel'):
                    try:
                        level = step.getLevel()
                    except Exception:
                        level = None

                if sid is not None:
                    step_id_to_level[sid] = level
                if level is not None:
                    unique_levels.add(level)

                if len(step_preview) < 24:
                    step_preview.append('sid={0},lvl={1},type={2}'.format(
                        sid,
                        level,
                        type(step).__name__,
                    ))

            data['unique_step_id_count'] = len(step_id_to_level)
            data['unique_level_count'] = len(unique_levels)
            data['debug_step_preview'] = step_preview
        except Exception:
            _logger.exception('Failed to read post-progression step metadata')

    if probe_mode in ('state-only', 'next-step-only', 'full'):
        try:
            state = pp.getState(True)
            unlocks = getattr(state, 'unlocks', set()) or set()
            data['raw_unlock_count'] = len(unlocks)

            unlocked_step_ids = set()
            unlock_preview = []
            for unlock in unlocks:
                uid = getattr(unlock, 'stepID', None)
                if uid is None:
                    uid = getattr(unlock, 'id', None)
                if uid is None:
                    uid = unlock

                try:
                    if uid is not None:
                        unlocked_step_ids.add(uid)
                except Exception:
                    pass

                if len(unlock_preview) < 24:
                    unlock_preview.append('{0}'.format(uid))

            data['unlocked_steps'] = len(unlocked_step_ids)
            data['unique_unlocked_step_id_count'] = len(unlocked_step_ids)

            unlocked_levels = set()
            for uid in unlocked_step_ids:
                if uid in step_id_to_level:
                    lvl = step_id_to_level[uid]
                    if lvl is not None:
                        unlocked_levels.add(lvl)
            data['unique_unlocked_level_count'] = len(unlocked_levels)

            data['debug_unlock_preview'] = unlock_preview
        except Exception:
            _logger.exception('Failed to read post-progression state/unlocks')

    if probe_mode in ('next-step-only', 'full'):
        try:
            balance = stats.getMoneyExt(vehicle.intCD)
            step = pp.getFirstPurchasableStep(balance)
            if step is not None:
                data['next_purchasable_step_id'] = (
                    getattr(step, 'stepID', None)
                    or getattr(step, 'id', None)
                )

                if _config.get('extractNextStepXPLightweight', True):
                    data['next_purchasable_step_xp'] = _extract_xp_cost_lightweight(step)

                if probe_mode == 'full' and data['next_purchasable_step_xp'] is None:
                    data['next_purchasable_step_xp'] = _extract_xp_cost(step)
        except Exception:
            _logger.exception('Failed to resolve next purchasable post-progression step')

    if probe_mode != 'full':
        return data

    try:
        # Count all tree steps and current unlocks for this specific vehicle.
        steps = list(pp.iterUnorderedSteps())
        data['total_steps'] = len(steps)

        state = pp.getState(True)
        unlocks = getattr(state, 'unlocks', set()) or set()
        data['unlocked_steps'] = len(unlocks)
        data['raw_unlock_count'] = len(unlocks)

        unlocked_step_ids = set()
        unlock_preview = []
        for unlock in unlocks:
            uid = getattr(unlock, 'stepID', None)
            if uid is None:
                uid = getattr(unlock, 'id', None)
            if uid is None:
                uid = unlock

            try:
                if uid is not None:
                    unlocked_step_ids.add(uid)
            except Exception:
                pass

            if len(unlock_preview) < 24:
                unlock_preview.append('{0}'.format(uid))

        step_id_to_level = {}
        unique_levels = set()
        step_preview = []
        level_price_total = {}
        level_price_unlocked = {}

        for step in steps:
            sid = getattr(step, 'stepID', None)
            if sid is None:
                sid = getattr(step, 'id', None)

            level = getattr(step, 'level', None)
            if level is None and hasattr(step, 'getLevel'):
                try:
                    level = step.getLevel()
                except Exception:
                    level = None

            if sid is not None:
                step_id_to_level[sid] = level
            if level is not None:
                unique_levels.add(level)

            step_xp = _extract_xp_cost(step)
            if level is not None and step_xp is not None:
                level_price_total[level] = level_price_total.get(level, 0) + step_xp
                if sid in unlocked_step_ids:
                    level_price_unlocked[level] = level_price_unlocked.get(level, 0) + step_xp

            if len(step_preview) < 24:
                step_preview.append('sid={0},lvl={1},xp={2},unlocked={3},type={4}'.format(
                    sid,
                    level,
                    step_xp,
                    sid in unlocked_step_ids,
                    type(step).__name__,
                ))

        unlocked_levels = set()
        for uid in unlocked_step_ids:
            if uid in step_id_to_level:
                lvl = step_id_to_level[uid]
                if lvl is not None:
                    unlocked_levels.add(lvl)

        data['unique_step_id_count'] = len(step_id_to_level)
        data['unique_level_count'] = len(unique_levels)
        data['unique_unlocked_step_id_count'] = len(unlocked_step_ids)
        data['unique_unlocked_level_count'] = len(unlocked_levels)
        data['debug_step_preview'] = step_preview
        data['debug_unlock_preview'] = unlock_preview

        level_keys = sorted(unique_levels)
        level_price_preview = []
        for lvl in level_keys[:24]:
            total = level_price_total.get(lvl)
            unlocked_total = level_price_unlocked.get(lvl, 0)
            level_price_preview.append('lvl={0},xp_unlocked={1},xp_total={2}'.format(lvl, unlocked_total, total))
        data['debug_level_price_preview'] = level_price_preview
    except Exception:
        _logger.exception('Failed to read post-progression steps/state')

    try:
        balance = stats.getMoneyExt(vehicle.intCD)
        step = pp.getFirstPurchasableStep(balance)
        if step is not None:
            data['next_purchasable_step_id'] = (
                getattr(step, 'stepID', None)
                or getattr(step, 'id', None)
            )
            data['next_purchasable_step_xp'] = _extract_xp_cost(step)
    except Exception:
        # Optional hint only; ignore if unavailable.
        pass

    return data


class _OverlayPanel(object):
    """Minimal persistent overlay text panel in hangar."""

    def __init__(self):
        self._gui = None
        self._text = None
        self._failed = False

    def _attach_root(self, comp):
        if hasattr(self._gui, 'addRoot'):
            self._gui.addRoot(comp)
            return True
        return False

    def _detach_root(self, comp):
        if hasattr(self._gui, 'delRoot'):
            self._gui.delRoot(comp)
            return True
        if hasattr(self._gui, 'removeRoot'):
            self._gui.removeRoot(comp)
            return True
        return False

    def ensure(self):
        if self._failed:
            return False
        if self._text is not None:
            return True

        try:
            import GUI
            self._gui = GUI

            if not hasattr(GUI, 'Text'):
                _logger.error('GUI.Text is unavailable in this client')
                self._failed = True
                return False

            text = GUI.Text('')
            text.visible = True
            text.multiline = True
            text.wrap = True
            text.colourFormatting = False
            text.text = ''
            text.horizontalAnchor = 'LEFT'
            text.verticalAnchor = 'TOP'
            text.position = (
                float(_config.get('panelPosX', 0.0)),
                float(_config.get('panelPosY', 0.0)),
                0.3,
            )

            if not self._attach_root(text):
                _logger.error('Unable to attach overlay panel to GUI root')
                self._failed = True
                return False

            self._text = text
            _logger.info('Overlay panel attached')
            return True
        except Exception:
            self._failed = True
            _logger.exception('Failed to initialize overlay panel')
            return False

    def update_lines(self, lines):
        if not self.ensure():
            return False
        try:
            header = 'Research Progress'
            body = '\n'.join(lines)
            self._text.text = '{0}\n{1}'.format(header, body)
            return True
        except Exception:
            self._failed = True
            _logger.exception('Failed to update overlay panel text')
            return False

    def destroy(self):
        if self._text is None or self._gui is None:
            return
        try:
            self._detach_root(self._text)
        except Exception:
            _logger.exception('Failed to detach overlay panel')
        finally:
            self._text = None
            self._gui = None


# ---------------------------------------------------------------------------
# Core mod class
# ---------------------------------------------------------------------------

class ResearchProgressBar(object):
    itemsCache = dependency.descriptor(IItemsCache)

    def __init__(self):
        self._active = False
        self._panel = None
        self._ui_failed = False
        self._pending_update_callback = None
        self._update_in_progress = False

    # -- lifecycle -----------------------------------------------------------

    def start(self):
        self._active = True
        self._ui_failed = False
        self._panel = _OverlayPanel()
        g_currentVehicle.onChanged += self._on_vehicle_changed
        self._schedule_update('startup')

    def stop(self):
        self._active = False
        self._cancel_pending_update()
        if self._panel is not None:
            self._panel.destroy()
            self._panel = None
        g_currentVehicle.onChanged -= self._on_vehicle_changed

    def _cancel_pending_update(self):
        callback_id = self._pending_update_callback
        self._pending_update_callback = None
        if callback_id is None:
            return
        try:
            BigWorld.cancelCallback(callback_id)
        except Exception:
            pass

    def _schedule_update(self, reason):
        if not self._active:
            return

        self._cancel_pending_update()

        # Keep deferred execution and callback coalescing, but run immediately.
        _logger.info('Scheduling research update immediately (%s)', reason)
        self._pending_update_callback = BigWorld.callback(0.0, self._deferred_update)

    # -- event handlers ------------------------------------------------------

    def _on_vehicle_changed(self):
        if not self._active:
            return
        self._schedule_update('vehicle_changed')

    def _deferred_update(self):
        """Runs deferred work outside critical hangar-load callbacks."""
        self._pending_update_callback = None
        if self._active:
            try:
                _logger.info('Running scheduled research update')
                self._update()
            except Exception:
                _logger.exception('Error in _deferred_update')

    # -- data collection -----------------------------------------------------

    def _update(self):
        if not _config.get('enabled'):
            return
        if self._update_in_progress:
            _logger.info('Skipping research update because one is already in progress')
            return

        self._update_in_progress = True
        try:
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
        finally:
            self._update_in_progress = False

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

        # --- Field modifications / post-progression (per vehicle) ---
        field_mods = _collect_post_progression(vehicle, stats)

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
                'exists': field_mods['exists'],
                'active': field_mods['active'],
                'completion': field_mods['completion'],
                'completion_name': field_mods['completion_name'],
                'total_steps': field_mods['total_steps'],
                'unlocked_steps': field_mods['unlocked_steps'],
                'is_veh_skill_tree': field_mods['is_veh_skill_tree'],
                'next_purchasable_step_id': field_mods['next_purchasable_step_id'],
                'raw_unlock_count': field_mods['raw_unlock_count'],
                'unique_step_id_count': field_mods['unique_step_id_count'],
                'unique_level_count': field_mods['unique_level_count'],
                'unique_unlocked_step_id_count': field_mods['unique_unlocked_step_id_count'],
                'unique_unlocked_level_count': field_mods['unique_unlocked_level_count'],
                'next_purchasable_step_xp': field_mods['next_purchasable_step_xp'],
                'debug_step_preview': field_mods['debug_step_preview'],
                'debug_unlock_preview': field_mods['debug_unlock_preview'],
                'debug_level_price_preview': field_mods['debug_level_price_preview'],
            },
        }

    def _log_field_mods_debug(self, vehicle, fm):
        if not _config.get('debugFieldMods'):
            return

        name = getattr(vehicle, 'userName', str(vehicle.intCD))
        _logger.info(
            '  Field mods DEBUG [%s]: exists=%s active=%s isVehSkillTree=%s completion=%s',
            name,
            fm['exists'],
            fm['active'],
            fm['is_veh_skill_tree'],
            fm['completion_name'],
        )
        _logger.info(
            '  Field mods DEBUG counts: total_steps=%d raw_unlocks=%d unique_step_ids=%d unique_levels=%d unlocked_step_ids=%d unlocked_levels=%d',
            fm['total_steps'],
            fm['raw_unlock_count'],
            fm['unique_step_id_count'],
            fm['unique_level_count'],
            fm['unique_unlocked_step_id_count'],
            fm['unique_unlocked_level_count'],
        )
        _logger.info(
            '  Field mods DEBUG next step: id=%s xp=%s',
            fm['next_purchasable_step_id'],
            fm['next_purchasable_step_xp'],
        )
        if fm['debug_step_preview']:
            _logger.info('  Field mods DEBUG step preview: %s', '; '.join(fm['debug_step_preview']))
        if fm['debug_unlock_preview']:
            _logger.info('  Field mods DEBUG unlock preview: %s', ', '.join(fm['debug_unlock_preview']))
        if fm['debug_level_price_preview']:
            _logger.info('  Field mods DEBUG level price preview: %s', '; '.join(fm['debug_level_price_preview']))

    # -- rendering -----------------------------------------------------------

    def _render(self, vehicle, data):
        """
        Phase 1: structured log output.
        Phase 2: persistent overlay panel in hangar.
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
        if _config.get('showFieldMods'):
            if not fm['exists']:
                _logger.info('  Field mods: not available for this vehicle')
            else:
                # Tier-11 skill trees keep step-based view; classic field mods use level-based progress.
                if fm['is_veh_skill_tree']:
                    total_units = fm['total_steps']
                    unlocked_units = fm['unlocked_steps']
                    unit_label = 'steps'
                else:
                    total_units = fm['unique_level_count']
                    unlocked_units = fm['unique_unlocked_level_count']
                    unit_label = 'levels'

                if total_units > 0:
                    pct = int(unlocked_units * 100 / total_units)
                    _logger.info(
                        '  Field mods: %s  (%d / %d %s, completion=%s, active=%s)',
                        _make_text_bar(pct),
                        unlocked_units,
                        total_units,
                        unit_label,
                        fm['completion_name'],
                        fm['active'],
                    )
                else:
                    _logger.info(
                        '  Field mods: available but no steps resolved (completion=%s, active=%s)',
                        fm['completion_name'],
                        fm['active'],
                    )

                if fm['is_veh_skill_tree']:
                    _logger.info('  Tier-11 style: vehicle skill tree mode detected (isVehSkillTree=True)')

                if fm['next_purchasable_step_id'] is not None:
                    if fm['next_purchasable_step_xp'] is not None:
                        _logger.info(
                            '  Field mods: next purchasable step id=%s xp=%s',
                            fm['next_purchasable_step_id'],
                            fm['next_purchasable_step_xp'],
                        )
                    else:
                        _logger.info('  Field mods: next purchasable step id=%s', fm['next_purchasable_step_id'])

                self._log_field_mods_debug(vehicle, fm)

    def _render_ui(self, vehicle, data):
        if self._ui_failed:
            self._render_log(vehicle, data)
            return

        if self._panel is None:
            self._panel = _OverlayPanel()

        name = getattr(vehicle, 'userName', str(vehicle.intCD))
        lines = ['Vehicle: {0}'.format(name)]

        tt = data['tech_tree']
        if _config.get('showTechTree'):
            if tt['is_fully_elite']:
                lines.append('Tech tree: COMPLETE (fully elite)')
            elif tt['next_cost']:
                lines.append(
                    'Tech tree: {0}% ({1}/{2} XP, free {3})'.format(
                        tt['pct'], tt['total_xp'], tt['next_cost'], tt['free_xp']
                    )
                )
            else:
                lines.append('Tech tree: no available unlocks')

        el = data['elite']
        if _config.get('showEliteProgress') and el['total'] > 0:
            lines.append('Elite mods: {0}% ({1}/{2})'.format(el['pct'], el['unlocked'], el['total']))

        fm = data['field_mods']
        if _config.get('showFieldMods'):
            if not fm['exists']:
                lines.append('Field mods: not available for this vehicle')
            elif fm['is_veh_skill_tree'] and fm['total_steps'] > 0:
                pct = int(fm['unlocked_steps'] * 100 / fm['total_steps'])
                lines.append(
                    'Field mods: {0}% ({1}/{2}, completion={3})'.format(
                        pct, fm['unlocked_steps'], fm['total_steps'], fm['completion_name']
                    )
                )
            elif (not fm['is_veh_skill_tree']) and fm['unique_level_count'] > 0:
                pct = int(fm['unique_unlocked_level_count'] * 100 / fm['unique_level_count'])
                lines.append(
                    'Field mods: {0}% ({1}/{2} levels, completion={3})'.format(
                        pct,
                        fm['unique_unlocked_level_count'],
                        fm['unique_level_count'],
                        fm['completion_name'],
                    )
                )
            else:
                lines.append('Field mods: available but no steps resolved')

            if fm['is_veh_skill_tree']:
                lines.append('Tier-11 style: vehicle skill tree mode detected')

            self._log_field_mods_debug(vehicle, fm)

        if not self._panel.update_lines(lines):
            self._ui_failed = True
            _logger.error('UI panel unavailable, falling back to log mode')
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
