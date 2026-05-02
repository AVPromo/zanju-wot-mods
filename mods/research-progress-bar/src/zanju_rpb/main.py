"""
zanju_rpb.main

Displays research progress for the currently selected vehicle in the hangar:
  - Module / next vehicle unlock progress  (tech tree XP)
  - Elite status progress                  (modules unlocked / total needed)
    - Field modification tree progress       (post-progression / "field mods")

BigWorld scripting uses Python 2.7. Avoid Python-3-only syntax.
"""
from __future__ import print_function, unicode_literals

import logging
import re
from numbers import Integral

import BigWorld
from CurrentVehicle import g_currentPreviewVehicle, g_currentVehicle
from frameworks.wulf import WindowLayer
from gui.Scaleform.framework import ScopeTemplates, ViewSettings, g_entitiesFactories
from gui.Scaleform.framework.entities.View import View
from gui.Scaleform.framework.managers.loaders import SFViewLoadParams
from gui.shared.gui_items import GUI_ITEM_TYPE_NAMES
from gui.shared.personality import ServicesLocator
from helpers import dependency
from items import getTypeOfCompactDescr
from .constants import (
    MOD_ID,
    MOD_VERSION,
    SCALEFORM_FILE_NAME,
    SCALEFORM_VIEW_ALIAS,
    _HANGAR_VIEW_ALIASES,
    _NAVIGATING_ROUTE_PREFIX,
    _TIER_FIELD_MOD_RULES,
    _UNLOCK_MARKER_LABEL_BY_TYPE,
    _UNLOCK_MARKER_TYPE_BY_GUI_NAME,
    _VISIBLE_ROUTE_PREFIX,
    _VISIBILITY_PROBE_DELAY,
)
from .scaleform_modes import build_scaleform_view_payload
from skeletons.gui.app_loader import GuiGlobalSpaceID as SPACE_ID
from skeletons.gui.game_control import IVehiclePostProgressionController
from skeletons.gui.shared import IItemsCache

_logger = logging.getLogger('zanju.researchprogressbar')
_lobby_state_logger = logging.getLogger('gui.lobby_state_machine.lobby_state_machine')

# ---------------------------------------------------------------------------
# Config defaults — overridden by _load_config() at startup
# ---------------------------------------------------------------------------
_config = {
    'enabled': True,
    'showTechTree': True,
    'showEliteProgress': True,
    'showFieldMods': True,
    # Emits verbose field-mod internals to python.log for parser tuning.
    # Keep disabled for normal use and enable only for targeted diagnostics.
    'debugFieldMods': False,
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
    # Try to read actual field-mod unlock tiers from post-progression settings.
    'parseNextStepXPFromSettings': False,
    # Try to resolve step XP from raw progression tree by step ID.
    'parseNextStepXPFromRawTree': False,
    # Extra tier-11 structural fingerprint probe (repr/dir), no method calls.
    'tier11WideNetProbe': True,
    # High-risk, gated method probe on tier-11 step objects.
    'tier11MethodProbeEnabled': False,
    'tier11MethodProbeName': 'getType',
    'tier11MethodProbeMaxStepsPerUpdate': 1,
    'scaleformPrototypeEnabled': True,
}

_ROUTE_PATH_RE = re.compile(r'\((subScope/[^)]*)\)')


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


def _next_available_unlock(vehicle, unlocks_set, available_unlocks=None):
    """
    Returns (xp_cost, intCD) for the most expensive currently researchable
    unlock whose prerequisites are met and which is not researched yet,
    or (None, None) if none.
    """
    if available_unlocks is None:
        available_unlocks = _collect_available_unlocks(vehicle, unlocks_set)
    if not available_unlocks:
        return None, None
    item = available_unlocks[-1]
    return item['xp_cost'], item['intcd']


def _resolve_unlock_item_type(intcd):
    """Maps an unlock compact descriptor to a stable research item type name."""
    try:
        gui_type_id = int(getTypeOfCompactDescr(intcd))
    except Exception:
        return 'unknown'

    try:
        gui_type_name = GUI_ITEM_TYPE_NAMES[gui_type_id]
    except Exception:
        return 'unknown'

    return _UNLOCK_MARKER_TYPE_BY_GUI_NAME.get(gui_type_name, 'unknown')


def _resolve_unlock_display_name(intcd, items=None):
    """Best-effort localized unlock name resolver for tooltip display."""
    if items is None:
        return None

    try:
        item = items.getItemByCD(intcd)
    except Exception:
        return None

    if item is None:
        return None

    for attr in ('userName', 'shortUserName', 'name'):
        value = getattr(item, attr, None)
        if value:
            return value

    return None


def _build_unlock_marker_ref(intcd, items=None):
    item_type = _resolve_unlock_item_type(intcd)
    return {
        'intcd': intcd,
        'item_type': item_type,
        'name': _resolve_unlock_display_name(intcd, items),
        'label': _UNLOCK_MARKER_LABEL_BY_TYPE.get(item_type, '?'),
    }


def _resolve_unlock_display_names(intcds, items=None):
    names = []
    for intcd in intcds:
        name = _resolve_unlock_display_name(intcd, items)
        if name is None:
            name = 'item {0}'.format(intcd)
        names.append(name)
    return names


def _build_unlock_marker(xp_cost, intcd, items=None, is_available=True, missing_prereq_intcds=()):
    item_type = _resolve_unlock_item_type(intcd)
    return {
        'xp_cost': xp_cost,
        'intcd': intcd,
        'item_type': item_type,
        'name': _resolve_unlock_display_name(intcd, items),
        'is_available': is_available,
        'missing_prereq_names': _resolve_unlock_display_names(missing_prereq_intcds, items),
        'missing_prereqs': [_build_unlock_marker_ref(prereq_intcd, items) for prereq_intcd in missing_prereq_intcds],
        'label': _UNLOCK_MARKER_LABEL_BY_TYPE.get(item_type, '?'),
    }


def _collect_visible_unlocks(vehicle, unlocks_set, items=None):
    """Returns sorted unlock dicts for all not-yet-researched tech-tree items."""
    visible = []
    for _idx, xp_cost, intcd, prereqs in vehicle.getUnlocksDescrs():
        if intcd in unlocks_set:
            continue
        try:
            cost = int(xp_cost)
        except Exception:
            continue
        missing_prereqs = sorted([p for p in prereqs if p not in unlocks_set])
        visible.append(
            _build_unlock_marker(
                cost,
                intcd,
                items=items,
                is_available=not missing_prereqs,
                missing_prereq_intcds=missing_prereqs,
            )
        )

    visible.sort(key=lambda item: (item['xp_cost'], item['intcd']))
    return visible


def _collect_available_unlocks(vehicle, unlocks_set, items=None, visible_unlocks=None):
    """Returns sorted unlock dicts for currently researchable items."""
    if visible_unlocks is None:
        visible_unlocks = _collect_visible_unlocks(vehicle, unlocks_set, items)
    return [item for item in visible_unlocks if item.get('is_available')]


def _get_vehicle_tier(vehicle):
    """Best-effort tier resolver for current vehicle (returns int or None)."""
    # Most vehicles expose tier as .level.
    tier = _to_int_or_none(getattr(vehicle, 'level', None))
    if tier is not None:
        return tier

    # Fallback to descriptor paths used by some entities.
    descriptor = getattr(vehicle, 'descriptor', None)
    if descriptor is not None:
        tier = _to_int_or_none(getattr(descriptor, 'level', None))
        if tier is not None:
            return tier

        type_descr = getattr(descriptor, 'type', None)
        if type_descr is not None:
            tier = _to_int_or_none(getattr(type_descr, 'level', None))
            if tier is not None:
                return tier

    return None


def _build_tier_field_mod_plan(vehicle_tier, unlocked_level_count, vehicle_xp, total_xp, is_veh_skill_tree):
    """Build tier-based field-mod next-level plan and affordability checks.

    Tier 11 remains under vehicle skill tree system and is not remapped.
    """
    plan = {
        'enabled': False,
        'reason': None,
        'max_level': None,
        'xp_per_level': None,
        'current_level': None,
        'next_level': None,
        'next_level_xp_cost': None,
        'can_research_with_vehicle_xp': None,
        'can_research_with_total_xp': None,
    }

    if vehicle_tier is None:
        plan['reason'] = 'unknown-tier'
        return plan

    if vehicle_tier <= 5:
        plan['reason'] = 'no-field-mods'
        return plan

    if vehicle_tier == 11 or is_veh_skill_tree:
        plan['reason'] = 'tier-11-skill-tree'
        return plan

    rules = _TIER_FIELD_MOD_RULES.get(vehicle_tier)
    if rules is None:
        plan['reason'] = 'no-tier-rules'
        return plan

    current_level = max(0, _to_int_or_none(unlocked_level_count) or 0)
    max_level = int(rules['max_level'])
    xp_per_level = int(rules['xp_per_level'])
    next_level = current_level + 1 if current_level < max_level else None
    next_level_cost = xp_per_level if next_level is not None else 0

    plan['enabled'] = True
    plan['reason'] = 'tier-rules'
    plan['max_level'] = max_level
    plan['xp_per_level'] = xp_per_level
    plan['current_level'] = current_level
    plan['next_level'] = next_level
    plan['next_level_xp_cost'] = next_level_cost
    plan['can_research_with_vehicle_xp'] = (vehicle_xp >= next_level_cost) if next_level is not None else False
    plan['can_research_with_total_xp'] = (total_xp >= next_level_cost) if next_level is not None else False
    return plan


def _classify_t11_step_size_from_xp(xp_cost):
    """Classify tier-11 upgrade node size from XP cost when available."""
    if xp_cost == 10000:
        return 'small'
    if xp_cost in (20000, 25000):
        return 'big'
    return 'unknown'


def _make_t11_bucket(xp_cost):
    if xp_cost == 10000:
        return 'small_10k'
    if xp_cost == 20000:
        return 'big_20k'
    if xp_cost == 25000:
        return 'big_25k'
    return 'unknown'


def _resolve_t11_xp_from_type(type_name):
    """Maps stable tier-11 getType values to known XP costs."""
    if type_name is None:
        return None

    value = str(type_name).strip().lower()
    if value == 'common':
        return 10000
    if value == 'special':
        return 10000
    if value == 'major':
        return 20000
    if value == 'final':
        return 25000
    return None


def _safe_t11_step_metadata(step):
    """Returns primitive metadata from step.__dict__ without method calls."""
    meta = {}
    try:
        raw = getattr(step, '__dict__', None)
        if isinstance(raw, dict):
            for key, value in raw.iteritems():
                if isinstance(value, (bool, Integral, float, str)):
                    meta[key] = value
    except Exception:
        pass
    return meta


def _safe_method_probe(step, method_name):
    """Calls one method on a step object in a fully-guarded way.

    Returns (ok, value_text).
    """
    try:
        method = getattr(step, method_name, None)
        if method is None or not callable(method):
            return False, '<missing>'
        value = method()
        return True, _safe_text(value, 120)
    except Exception as exc:
        return False, '<error:{0}>'.format(_safe_text(exc, 80))


def _get_t11_method_probe_cap(method_name):
    name = str(method_name or '')
    if name == 'getType':
        return 26
    if name == 'getPrice':
        return 1
    return 3


def _t11_meta_signature(meta):
    """Build a compact stable signature from primitive metadata keys/values."""
    if not meta:
        return '<empty>'

    parts = []
    for key in sorted(meta.keys()):
        value = meta[key]
        if isinstance(value, float):
            value = round(value, 4)
        value_text = str(value)
        if len(value_text) > 24:
            value_text = value_text[:24]
        parts.append('{0}={1}'.format(key, value_text))
    return '|'.join(parts)


def _safe_text(value, max_len=180):
    try:
        text = str(value)
    except Exception:
        return '<unprintable>'
    if len(text) > max_len:
        return text[:max_len]
    return text


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
def _collect_modification_price_tiers(settings):
    """Extracts unlock XP tier values from post-progression settings.

    Expected keys include Modification10000xp / Modification20000xp etc.
    """
    tiers = set()
    visited = set()

    def walk(node, depth):
        if depth > 8 or node is None:
            return
        try:
            node_id = id(node)
            if node_id in visited:
                return
            visited.add(node_id)
        except Exception:
            pass

        if isinstance(node, dict):
            for key, value in node.iteritems():
                try:
                    if isinstance(key, str):
                        m = re.match(r'^Modification(\d+)xp$', key)
                        if m is not None:
                            tiers.add(int(m.group(1)))
                except Exception:
                    pass
                walk(value, depth + 1)
            return

        if isinstance(node, (list, tuple, set)):
            for item in node:
                walk(item, depth + 1)
            return

        # Only inspect a narrow allow-list of container-like attributes.
        for attr in (
            'prices', 'price', 'costs', 'settings', 'config',
            'postProgressionConfig', 'vehicle_post_progression_config',
            '_data', '__dict__',
        ):
            try:
                child = getattr(node, attr, None)
                if child is not None and child is not node:
                    walk(child, depth + 1)
            except Exception:
                pass

    walk(settings, 0)
    return sorted(tiers)


def _resolve_next_step_xp_from_settings(level, pp_settings):
    if pp_settings is None or level is None:
        return None
    try:
        lvl = int(level)
    except Exception:
        return None

    tiers = _collect_modification_price_tiers(pp_settings)
    if not tiers:
        return None

    idx = max(0, min(lvl - 1, len(tiers) - 1))
    return tiers[idx]


def _resolve_next_step_xp_from_raw_tree(pp, step_id):
    if pp is None or step_id is None:
        return None

    try:
        raw_tree = pp.getRawTree()
    except Exception:
        return None

    visited = set()

    def walk(node, depth):
        if depth > 10 or node is None:
            return None
        try:
            node_id = id(node)
            if node_id in visited:
                return None
            visited.add(node_id)
        except Exception:
            pass

        # Dict path.
        if isinstance(node, dict):
            sid = node.get('stepID', node.get('id'))
            if sid == step_id:
                return _extract_xp_cost_lightweight(node)
            for value in node.itervalues():
                found = walk(value, depth + 1)
                if found is not None:
                    return found
            return None

        # Sequence path.
        if isinstance(node, (list, tuple, set)):
            for item in node:
                found = walk(item, depth + 1)
                if found is not None:
                    return found
            return None

        # Object path: match by id/stepID attrs, then check cost attrs.
        sid = getattr(node, 'stepID', None)
        if sid is None:
            sid = getattr(node, 'id', None)
        if sid == step_id:
            xp = _extract_xp_cost_lightweight(node)
            if xp is not None:
                return xp

        for attr in ('steps', 'items', 'nodes', 'actions', 'state', 'tree', '_data', '__dict__'):
            try:
                child = getattr(node, attr, None)
                if child is not None and child is not node:
                    found = walk(child, depth + 1)
                    if found is not None:
                        return found
            except Exception:
                pass

        return None

    return walk(raw_tree, 0)


def _resolve_next_research_step(pp, unlocked_step_ids, step_id_to_level):
    """Returns (step_id, level) for first not-yet-unlocked ordered step."""
    try:
        for step in pp.iterOrderedSteps():
            sid = getattr(step, 'stepID', None)
            if sid is None:
                sid = getattr(step, 'id', None)
            if sid is None or sid in unlocked_step_ids:
                continue

            lvl = step_id_to_level.get(sid)
            if lvl is None:
                lvl = getattr(step, 'level', None)
                if lvl is None and hasattr(step, 'getLevel'):
                    try:
                        lvl = step.getLevel()
                    except Exception:
                        lvl = None
            return sid, lvl
    except Exception:
        _logger.exception('Failed to resolve next research step from ordered post-progression steps')
    return None, None


def _collect_post_progression(vehicle, stats, pp_settings=None, method_probe_offset=0):
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
        'next_purchasable_step_level': None,
        'next_purchasable_step_xp_source': None,
        'next_purchasable_step_kind': None,
        'raw_unlock_count': 0,
        'unique_step_id_count': 0,
        'unique_level_count': 0,
        'unique_unlocked_step_id_count': 0,
        'unique_unlocked_level_count': 0,
        'next_purchasable_step_xp': None,
        'debug_step_preview': [],
        'debug_unlock_preview': [],
        'debug_level_price_preview': [],
        'debug_settings_price_tiers': [],
        't11_bucket_researched': {},
        't11_bucket_unresearched': {},
        't11_step_preview': [],
        't11_assumed_25k_step_id': None,
        't11_resolved_25k_step_id': None,
        't11_meta_signature_researched': {},
        't11_meta_signature_unresearched': {},
        't11_meta_keys': {},
        't11_widenet_step_repr': [],
        't11_widenet_step_dir_fingerprint': [],
        't11_widenet_unlock_repr': [],
        't11_method_probe_name': None,
        't11_method_probe_preview': [],
        't11_method_probe_hits': 0,
        't11_method_probe_next_offset': method_probe_offset,
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
    step_meta = {}
    steps_by_id = {}

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
                    steps_by_id[sid] = step

                if sid is not None:
                    step_meta_raw = _safe_t11_step_metadata(step)
                    step_repr = None
                    step_dir_fp = ''
                    if data['is_veh_skill_tree'] and _config.get('tier11WideNetProbe', True):
                        step_repr = _safe_text(repr(step))
                        try:
                            names = dir(step)
                        except Exception:
                            names = []
                        interesting = []
                        for name in names:
                            lname = name.lower()
                            if ('type' in lname
                                    or 'size' in lname
                                    or 'major' in lname
                                    or 'minor' in lname
                                    or 'perk' in lname
                                    or 'category' in lname
                                    or 'group' in lname
                                    or 'kind' in lname
                                    or 'branch' in lname
                                    or 'icon' in lname
                                    or 'slot' in lname
                                    or 'cost' in lname
                                    or 'price' in lname
                                    or 'xp' in lname):
                                interesting.append(name)
                        step_dir_fp = ','.join(sorted(interesting)[:40])

                    step_meta[sid] = {
                        'level': level,
                        # Keep normal probe modes safe: avoid deep step-cost introspection.
                        'xp_cost': None,
                        'size': 'unknown',
                        'meta': step_meta_raw,
                        'signature': _t11_meta_signature(step_meta_raw),
                        'repr': step_repr,
                        'dir_fp': step_dir_fp,
                    }

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

    unlocked_step_ids = set()

    if probe_mode in ('state-only', 'next-step-only', 'full'):
        try:
            state = pp.getState(True)
            unlocks = getattr(state, 'unlocks', set()) or set()
            data['raw_unlock_count'] = len(unlocks)

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

            if data['is_veh_skill_tree']:
                if _config.get('tier11MethodProbeEnabled', False):
                    method_name = str(_config.get('tier11MethodProbeName', 'getType') or 'getType')
                    max_steps = _to_int_or_none(_config.get('tier11MethodProbeMaxStepsPerUpdate', 1))
                    if max_steps is None or max_steps < 1:
                        max_steps = 1
                    max_steps = min(max_steps, _get_t11_method_probe_cap(method_name))

                    data['t11_method_probe_name'] = method_name
                    probed = 0
                    ordered_probe_ids = sorted(step_meta.keys())
                    if ordered_probe_ids:
                        start_idx = method_probe_offset % len(ordered_probe_ids)
                        ordered_probe_ids = ordered_probe_ids[start_idx:] + ordered_probe_ids[:start_idx]
                    for sid in ordered_probe_ids:
                        if probed >= max_steps:
                            break
                        step_obj = steps_by_id.get(sid)
                        if step_obj is None:
                            continue

                        ok, value_text = _safe_method_probe(step_obj, method_name)
                        data['t11_method_probe_preview'].append(
                            'sid={0},ok={1},value={2}'.format(sid, ok, value_text)
                        )
                        if ok:
                            data['t11_method_probe_hits'] += 1
                            step_meta[sid]['signature'] = '{0}:{1}'.format(method_name, value_text)
                            if method_name == 'getType':
                                xp_from_type = _resolve_t11_xp_from_type(value_text)
                                if xp_from_type is not None:
                                    step_meta[sid]['xp_cost'] = xp_from_type
                                    step_meta[sid]['size'] = _classify_t11_step_size_from_xp(xp_from_type)
                        probed += 1
                    data['t11_method_probe_next_offset'] = method_probe_offset + probed

                researched = {
                    'small_10k': 0,
                    'big_20k': 0,
                    'big_25k': 0,
                    'unknown': 0,
                }
                unresearched = {
                    'small_10k': 0,
                    'big_20k': 0,
                    'big_25k': 0,
                    'unknown': 0,
                }
                sig_researched = {}
                sig_unresearched = {}
                meta_keys = {}
                step_preview = []
                assumed_25k_step_id = max(step_meta.keys()) if step_meta else None
                data['t11_assumed_25k_step_id'] = assumed_25k_step_id
                has_explicit_25k = any(meta.get('xp_cost') == 25000 for meta in step_meta.itervalues())
                resolved_25k_step_id = None
                if has_explicit_25k:
                    explicit_25k_ids = sorted([
                        sid for sid, meta in step_meta.iteritems()
                        if meta.get('xp_cost') == 25000
                    ])
                    if explicit_25k_ids:
                        resolved_25k_step_id = explicit_25k_ids[0]
                else:
                    resolved_25k_step_id = assumed_25k_step_id
                data['t11_resolved_25k_step_id'] = resolved_25k_step_id

                for sid, meta in step_meta.iteritems():
                    xp_cost = meta.get('xp_cost')
                    level = meta.get('level')
                    size = meta.get('size')
                    signature = meta.get('signature') or '<empty>'
                    step_repr = meta.get('repr')
                    dir_fp = meta.get('dir_fp')
                    raw_meta = meta.get('meta') or {}
                    bucket = _make_t11_bucket(xp_cost)
                    if (not has_explicit_25k
                            and bucket == 'unknown'
                            and assumed_25k_step_id is not None
                            and sid == assumed_25k_step_id):
                        bucket = 'big_25k'
                        size = 'big_assumed_25k'

                    is_researched = sid in unlocked_step_ids

                    if is_researched:
                        researched[bucket] = researched.get(bucket, 0) + 1
                        sig_researched[signature] = sig_researched.get(signature, 0) + 1
                    else:
                        unresearched[bucket] = unresearched.get(bucket, 0) + 1
                        sig_unresearched[signature] = sig_unresearched.get(signature, 0) + 1

                    for key in raw_meta.keys():
                        meta_keys[key] = meta_keys.get(key, 0) + 1

                    if len(step_preview) < 40:
                        step_preview.append(
                            'sid={0},lvl={1},xp={2},size={3},researched={4},sig={5}'.format(
                                sid,
                                level,
                                xp_cost,
                                size,
                                is_researched,
                                signature,
                            )
                        )
                    if step_repr is not None and len(data['t11_widenet_step_repr']) < 40:
                        data['t11_widenet_step_repr'].append(
                            'sid={0},researched={1},repr={2}'.format(sid, is_researched, step_repr)
                        )
                    if dir_fp and len(data['t11_widenet_step_dir_fingerprint']) < 40:
                        data['t11_widenet_step_dir_fingerprint'].append(
                            'sid={0},researched={1},dir={2}'.format(sid, is_researched, dir_fp)
                        )

                data['t11_bucket_researched'] = researched
                data['t11_bucket_unresearched'] = unresearched
                data['t11_step_preview'] = step_preview
                data['t11_meta_signature_researched'] = sig_researched
                data['t11_meta_signature_unresearched'] = sig_unresearched
                data['t11_meta_keys'] = meta_keys

                if _config.get('tier11WideNetProbe', True):
                    unlock_preview = []
                    for unlock in unlocks:
                        if len(unlock_preview) >= 40:
                            break
                        unlock_preview.append(_safe_text(repr(unlock)))
                    data['t11_widenet_unlock_repr'] = unlock_preview
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

                if data['next_purchasable_step_id'] in step_id_to_level:
                    data['next_purchasable_step_level'] = step_id_to_level.get(data['next_purchasable_step_id'])
                data['next_purchasable_step_kind'] = 'purchasable'

                if data['is_veh_skill_tree'] and data['next_purchasable_step_id'] is not None:
                    step_meta_entry = step_meta.get(data['next_purchasable_step_id'])
                    if step_meta_entry is not None:
                        data['next_purchasable_step_xp'] = step_meta_entry.get('xp_cost')
                        if data['next_purchasable_step_xp'] is not None:
                            data['next_purchasable_step_xp_source'] = 'getType'

                if (_config.get('extractNextStepXPLightweight', True)
                        and data['next_purchasable_step_xp'] is None):
                    data['next_purchasable_step_xp'] = _extract_xp_cost_lightweight(step)
                    if data['next_purchasable_step_xp'] is not None:
                        data['next_purchasable_step_xp_source'] = 'lightweight'

                if probe_mode == 'full' and data['next_purchasable_step_xp'] is None:
                    data['next_purchasable_step_xp'] = _extract_xp_cost(step)
                    if data['next_purchasable_step_xp'] is not None:
                        data['next_purchasable_step_xp_source'] = 'full'

            if data['next_purchasable_step_id'] is None and not data['is_veh_skill_tree']:
                fallback_sid, fallback_lvl = _resolve_next_research_step(
                    pp,
                    unlocked_step_ids,
                    step_id_to_level,
                )
                if fallback_sid is not None:
                    data['next_purchasable_step_id'] = fallback_sid
                    data['next_purchasable_step_level'] = fallback_lvl
                    data['next_purchasable_step_kind'] = 'researchable'

            if (_config.get('parseNextStepXPFromSettings', True)
                    and not data['is_veh_skill_tree']
                    and data['next_purchasable_step_xp'] is None):
                tiers = _collect_modification_price_tiers(pp_settings)
                data['debug_settings_price_tiers'] = tiers[:24]
                if tiers and data['next_purchasable_step_level'] is not None:
                    lvl = int(data['next_purchasable_step_level'])
                    idx = max(0, min(lvl - 1, len(tiers) - 1))
                    data['next_purchasable_step_xp'] = tiers[idx]
                    data['next_purchasable_step_xp_source'] = 'settings'

            if (_config.get('parseNextStepXPFromRawTree', True)
                    and data['next_purchasable_step_xp'] is None
                    and data['next_purchasable_step_id'] is not None):
                xp_from_tree = _resolve_next_step_xp_from_raw_tree(
                    pp,
                    data['next_purchasable_step_id'],
                )
                if xp_from_tree is not None:
                    data['next_purchasable_step_xp'] = xp_from_tree
                    data['next_purchasable_step_xp_source'] = 'raw_tree'

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


class _ScaleformGarageView(View):
    def as_setContextS(self, data):
        if self._isDAAPIInited():
            return self.flashObject.as_setContext(data)
        return None

    def as_setVisibleS(self, is_visible):
        if self._isDAAPIInited():
            return self.flashObject.as_setVisible(is_visible)
        return None

    def as_setProgressS(self, value):
        if self._isDAAPIInited():
            return self.flashObject.as_setProgress(value)
        return None

    def as_pingS(self):
        if self._isDAAPIInited():
            return self.flashObject.as_ping()
        return None

    def _populate(self):
        super(_ScaleformGarageView, self)._populate()
        if _mod is not None:
            _mod._on_scaleform_view_populated(self)

    def _dispose(self):
        if _mod is not None:
            _mod._on_scaleform_view_disposed(self)
        super(_ScaleformGarageView, self)._dispose()


class _LobbyStateRouteLogHandler(logging.Handler):
    def emit(self, record):
        if _mod is None:
            return
        try:
            message = record.getMessage()
        except Exception:
            return
        _mod._on_lobby_route_log(message)


# ---------------------------------------------------------------------------
# Core mod class
# ---------------------------------------------------------------------------

class ResearchProgressBar(object):
    itemsCache = dependency.descriptor(IItemsCache)
    postProgressionCtrl = dependency.descriptor(IVehiclePostProgressionController)

    def __init__(self):
        self._active = False
        self._pending_update_callback = None
        self._visibility_probe_callback = None
        self._update_in_progress = False
        self._t11_method_probe_offsets = {}
        self._scaleform_view = None
        self._scaleform_payload = None
        self._scaleform_view_requested = False
        self._scaleform_settings_registered = False
        self._scaleform_hooks_registered = False
        self._scaleform_container_manager = None
        self._scaleform_view_visible = None
        self._lobby_route_log_handler = None
        self._current_lobby_route_path = None
        self._last_context_log_key = None
        self._last_seen_sub_view_alias = None

    # -- lifecycle -----------------------------------------------------------

    def start(self):
        self._active = True
        self._attach_lobby_route_log_handler()
        self._start_scaleform_view()
        g_currentVehicle.onChanged += self._on_vehicle_changed
        g_currentPreviewVehicle.onChanged += self._on_preview_vehicle_changed
        # Avoid running heavy collection during early login/loading phase.
        # First update is triggered by onChanged once hangar vehicle selection settles.

    def stop(self):
        self._active = False
        self._cancel_pending_update()
        self._cancel_visibility_probe()
        self._detach_lobby_route_log_handler()
        g_currentPreviewVehicle.onChanged -= self._on_preview_vehicle_changed
        self._stop_scaleform_view()
        g_currentVehicle.onChanged -= self._on_vehicle_changed

    def _start_scaleform_view(self):
        if not _config.get('scaleformPrototypeEnabled', True):
            return

        try:
            if not self._scaleform_settings_registered:
                g_entitiesFactories.addSettings(
                    ViewSettings(
                        SCALEFORM_VIEW_ALIAS,
                        _ScaleformGarageView,
                        SCALEFORM_FILE_NAME,
                        WindowLayer.WINDOW,
                        None,
                        ScopeTemplates.GLOBAL_SCOPE,
                    )
                )
                self._scaleform_settings_registered = True

            if not self._scaleform_hooks_registered:
                ServicesLocator.appLoader.onGUISpaceEntered += self._on_gui_space_entered
                ServicesLocator.appLoader.onGUISpaceLeft += self._on_gui_space_left
                self._scaleform_hooks_registered = True

            self._attach_scaleform_container_hooks()
            self._sync_scaleform_view('start')
        except Exception:
            _logger.exception('Failed to start scaleform garage view')

    def _stop_scaleform_view(self):
        self._detach_scaleform_container_hooks()
        self._scaleform_view_requested = False
        self._scaleform_payload = None
        self._current_lobby_route_path = None
        self._last_seen_sub_view_alias = None
        self._cancel_visibility_probe()

        if self._scaleform_view is not None:
            try:
                self._scaleform_view.destroy()
            except Exception:
                _logger.exception('Failed to destroy scaleform garage view')
            finally:
                self._scaleform_view = None
                self._scaleform_view_visible = None

        if self._scaleform_hooks_registered:
            try:
                ServicesLocator.appLoader.onGUISpaceEntered -= self._on_gui_space_entered
                ServicesLocator.appLoader.onGUISpaceLeft -= self._on_gui_space_left
            except Exception:
                _logger.exception('Failed to detach scaleform garage view hooks')
            finally:
                self._scaleform_hooks_registered = False

        if self._scaleform_settings_registered:
            try:
                g_entitiesFactories.removeSettings(SCALEFORM_VIEW_ALIAS)
            except Exception:
                _logger.exception('Failed to unregister scaleform garage view settings')
            finally:
                self._scaleform_settings_registered = False

    def _get_lobby_app(self):
        app_loader = ServicesLocator.appLoader
        app = None
        if hasattr(app_loader, 'getDefLobbyApp'):
            app = app_loader.getDefLobbyApp()
        if app is None and hasattr(app_loader, 'getApp'):
            app = app_loader.getApp()
        return app

    def _attach_lobby_route_log_handler(self):
        if self._lobby_route_log_handler is not None:
            return

        try:
            handler = _LobbyStateRouteLogHandler()
            handler.setLevel(logging.INFO)
            _lobby_state_logger.addHandler(handler)
            self._lobby_route_log_handler = handler
        except Exception:
            self._lobby_route_log_handler = None
            _logger.exception('Failed to attach lobby route log handler')

    def _detach_lobby_route_log_handler(self):
        handler = self._lobby_route_log_handler
        self._lobby_route_log_handler = None
        self._current_lobby_route_path = None
        if handler is None:
            return

        try:
            _lobby_state_logger.removeHandler(handler)
        except Exception:
            _logger.exception('Failed to detach lobby route log handler')

    def _extract_route_path(self, message):
        if message.startswith(_NAVIGATING_ROUTE_PREFIX):
            return message[len(_NAVIGATING_ROUTE_PREFIX):].strip()

        if message.startswith(_VISIBLE_ROUTE_PREFIX):
            match = _ROUTE_PATH_RE.search(message)
            if match is not None:
                return match.group(1)

        return None

    def _is_default_hangar_route(self, route_path):
        return route_path in ('subScope/subLayer/hangar', 'subScope/subLayer/hangar/{root}')

    def _on_lobby_route_log(self, message):
        route_path = self._extract_route_path(message)
        if route_path is None or route_path == self._current_lobby_route_path:
            return

        self._current_lobby_route_path = route_path
        if self._active:
            self._schedule_update('lobby_route_changed')

    def _attach_scaleform_container_hooks(self):
        app = self._get_lobby_app()
        container_manager = getattr(app, 'containerManager', None) if app is not None else None
        if container_manager is self._scaleform_container_manager:
            return

        self._detach_scaleform_container_hooks()
        if container_manager is None:
            return

        try:
            container_manager.onViewAddedToContainer += self._on_view_added_to_container
            self._scaleform_container_manager = container_manager
        except Exception:
            self._scaleform_container_manager = None
            _logger.exception('Failed to attach scaleform container hooks')

    def _detach_scaleform_container_hooks(self):
        if self._scaleform_container_manager is None:
            return

        try:
            self._scaleform_container_manager.onViewAddedToContainer -= self._on_view_added_to_container
        except Exception:
            _logger.exception('Failed to detach scaleform container hooks')
        finally:
            self._scaleform_container_manager = None

    def _get_active_view_alias(self, layer):
        container_manager = self._scaleform_container_manager
        if container_manager is None:
            app = self._get_lobby_app()
            container_manager = getattr(app, 'containerManager', None) if app is not None else None
        if container_manager is None:
            return None

        try:
            container = container_manager.getContainer(layer)
            if container is None:
                return None
            get_topmost_view = getattr(container, 'getTopmostView', None)
            if callable(get_topmost_view):
                view = get_topmost_view()
            else:
                view = None
                num_children = getattr(container, 'numChildren', 0)
                if callable(num_children):
                    num_children = num_children()
                get_child_at = getattr(container, 'getChildAt', None)
                if view is None and callable(get_child_at) and num_children:
                    view = get_child_at(num_children - 1)
            if view is None:
                return None
            return self._get_view_alias(view)
        except Exception:
            _logger.exception('Failed to resolve active lobby view alias for layer=%s', layer)
            return None

    def _get_view_alias(self, view):
        if view is None:
            return None

        alias = getattr(view, 'alias', None)
        if alias is None or isinstance(alias, Integral):
            config = getattr(view, 'as_config', None)
            if config is not None:
                config_alias = getattr(config, 'alias', None)
                if config_alias is not None:
                    alias = config_alias
        return alias

    def _get_scaleform_context(self, incoming_view=None):
        active_sub_view_alias = self._get_active_view_alias(WindowLayer.SUB_VIEW)
        if active_sub_view_alias is None:
            active_sub_view_alias = self._last_seen_sub_view_alias

        return {
            'active_sub_view_alias': active_sub_view_alias,
            'active_top_sub_view_alias': self._get_active_view_alias(WindowLayer.TOP_SUB_VIEW),
            'active_window_alias': self._get_active_view_alias(WindowLayer.WINDOW),
            'active_top_window_alias': self._get_active_view_alias(WindowLayer.TOP_WINDOW),
            'preview_present': g_currentPreviewVehicle.isPresent(),
            'vehicle_present': g_currentVehicle.item is not None,
            'incoming_alias': self._get_view_alias(incoming_view),
            'incoming_layer': getattr(incoming_view, 'layer', None) if incoming_view is not None else None,
        }

    def _get_scaleform_block_reason(self, context):
        if not self._active:
            return 'inactive'
        if not _config.get('scaleformPrototypeEnabled', True):
            return 'scaleform_disabled'
        if context['preview_present']:
            return 'preview_vehicle_present'
        if not context['vehicle_present']:
            return 'no_current_vehicle'
        if self._current_lobby_route_path is not None and not self._is_default_hangar_route(self._current_lobby_route_path):
            return 'lobby_route={0}'.format(self._current_lobby_route_path)

        incoming_alias = context['incoming_alias']
        incoming_layer = context['incoming_layer']
        effective_sub_view_alias = context['active_sub_view_alias']
        effective_top_sub_view_alias = context['active_top_sub_view_alias']
        if incoming_layer == WindowLayer.SUB_VIEW and incoming_alias is not None:
            effective_sub_view_alias = incoming_alias
        if incoming_layer == WindowLayer.TOP_SUB_VIEW and incoming_alias is not None:
            effective_top_sub_view_alias = incoming_alias

        if incoming_layer == WindowLayer.SUB_VIEW:
            if incoming_alias not in _HANGAR_VIEW_ALIASES and incoming_alias != SCALEFORM_VIEW_ALIAS:
                return 'incoming_sub_view={0}'.format(incoming_alias)
        if incoming_layer == WindowLayer.TOP_SUB_VIEW and incoming_alias != SCALEFORM_VIEW_ALIAS:
            return 'incoming_top_sub_view={0}'.format(incoming_alias)

        if effective_sub_view_alias not in _HANGAR_VIEW_ALIASES:
            return 'sub_view={0}'.format(effective_sub_view_alias)
        if effective_top_sub_view_alias not in (None, SCALEFORM_VIEW_ALIAS):
            return 'top_sub_view={0}'.format(effective_top_sub_view_alias)
        return None

    def _evaluate_scaleform_visibility(self, reason=None, incoming_view=None):
        context = self._get_scaleform_context(incoming_view)
        block_reason = self._get_scaleform_block_reason(context)
        if reason is not None:
            self._log_scaleform_context(reason, context, block_reason)
        return context, block_reason

    def _needs_visibility_probe(self, context, block_reason):
        if block_reason is None:
            return False

        incoming_layer = context['incoming_layer']
        if incoming_layer == WindowLayer.TOP_SUB_VIEW:
            return True
        if context['active_top_sub_view_alias'] not in (None, SCALEFORM_VIEW_ALIAS):
            return True
        return False

    def _log_scaleform_context(self, reason, context, block_reason):
        log_key = (
            block_reason is None,
            block_reason,
            self._current_lobby_route_path,
            context['active_sub_view_alias'],
            context['active_top_sub_view_alias'],
            context['preview_present'],
            context['vehicle_present'],
        )
        if log_key == self._last_context_log_key:
            return

        self._last_context_log_key = log_key
        _logger.info(
            'Garage view gate[%s]: visible=%s reason=%s route=%s sub=%s topSub=%s preview=%s vehicle=%s',
            reason,
            block_reason is None,
            block_reason or 'none',
            self._current_lobby_route_path,
            context['active_sub_view_alias'],
            context['active_top_sub_view_alias'],
            context['preview_present'],
            context['vehicle_present'],
        )

    def _should_show_scaleform_view(self, reason=None, incoming_view=None):
        _, block_reason = self._evaluate_scaleform_visibility(reason, incoming_view)
        return block_reason is None

    def _set_scaleform_view_visible(self, is_visible, reason):
        if self._scaleform_view is None:
            return
        if self._scaleform_view_visible is is_visible:
            return

        try:
            self._scaleform_view.as_setVisibleS(is_visible)
            self._scaleform_view_visible = is_visible
            _logger.info('Scaleform garage view visibility -> %s (%s)', is_visible, reason)
        except Exception:
            _logger.exception('Failed to set scaleform garage view visibility=%s (%s)', is_visible, reason)

    def _sync_scaleform_view(self, reason, incoming_view=None):
        context, block_reason = self._evaluate_scaleform_visibility(reason, incoming_view)
        if block_reason is None:
            self._cancel_visibility_probe()
            self._try_load_scaleform_view(reason)
            if self._scaleform_view is not None and self._scaleform_payload is not None:
                self._push_scaleform_payload()
                self._set_scaleform_view_visible(True, reason)
            return True

        if self._needs_visibility_probe(context, block_reason):
            self._schedule_visibility_probe(reason)
        else:
            self._cancel_visibility_probe()

        if self._scaleform_view is not None:
            self._set_scaleform_view_visible(False, reason)

        return False

    def _try_load_scaleform_view(self, reason):
        if not self._active or not _config.get('scaleformPrototypeEnabled', True):
            return
        if self._scaleform_view is not None or self._scaleform_view_requested:
            return

        try:
            app = self._get_lobby_app()
            if app is None:
                return

            params = SFViewLoadParams(SCALEFORM_VIEW_ALIAS)
            app.loadView(params)
            self._scaleform_view_requested = True
            _logger.info('Requested scaleform garage view load (%s)', reason)
        except Exception:
            self._scaleform_view_requested = False
            _logger.exception('Failed to request scaleform garage view load (%s)', reason)

    def _on_gui_space_entered(self, space_id):
        if not self._active:
            return
        if space_id == SPACE_ID.LOBBY:
            self._attach_scaleform_container_hooks()
            self._sync_scaleform_view('lobby_entered')

    def _on_gui_space_left(self, space_id):
        if space_id != SPACE_ID.LOBBY:
            return

        self._detach_scaleform_container_hooks()
        self._scaleform_view_requested = False
        if self._scaleform_view is not None:
            try:
                self._scaleform_view.destroy()
            except Exception:
                _logger.exception('Failed to dispose scaleform garage view on lobby exit')
            finally:
                self._scaleform_view = None
                self._scaleform_view_visible = None

    def _on_scaleform_view_populated(self, view):
        self._scaleform_view_requested = False
        self._scaleform_view = view
        self._scaleform_view_visible = None
        if not self._should_show_scaleform_view('populated', view):
            self._sync_scaleform_view('populated_outside_hangar', view)
            return
        if self._scaleform_payload is None:
            self._set_scaleform_view_visible(False, 'populated_no_modes')
            return
        try:
            ping_value = view.as_pingS()
            _logger.info('Scaleform garage view populated (%s)', ping_value)
        except Exception:
            _logger.exception('Scaleform garage view ping failed')
        self._push_scaleform_payload()
        self._set_scaleform_view_visible(True, 'populated')

    def _on_scaleform_view_disposed(self, view):
        if self._scaleform_view is view:
            self._scaleform_view = None
            self._scaleform_view_visible = None
        self._scaleform_view_requested = False
        _logger.info('Scaleform garage view disposed')

    def _build_scaleform_payload(self, vehicle, data):
        return build_scaleform_view_payload(vehicle, data)

    def _push_scaleform_payload(self):
        if self._scaleform_view is None or self._scaleform_payload is None:
            return

        try:
            self._scaleform_view.as_setContextS(self._scaleform_payload)
            progress = self._scaleform_payload.get('progress')
            if progress is not None:
                self._scaleform_view.as_setProgressS(progress)
        except Exception:
            _logger.exception('Failed to push data to scaleform garage view')

    def _render_scaleform_view(self, vehicle, data):
        if not _config.get('scaleformPrototypeEnabled', True):
            return
        self._scaleform_payload = self._build_scaleform_payload(vehicle, data)
        if self._scaleform_payload is None:
            if self._scaleform_view is not None:
                self._set_scaleform_view_visible(False, 'no_available_modes')
            return
        if self._sync_scaleform_view('data_update'):
            self._push_scaleform_payload()

    def _cancel_pending_update(self):
        callback_id = self._pending_update_callback
        self._pending_update_callback = None
        if callback_id is None:
            return
        try:
            BigWorld.cancelCallback(callback_id)
        except Exception:
            pass

    def _cancel_visibility_probe(self):
        callback_id = self._visibility_probe_callback
        self._visibility_probe_callback = None
        if callback_id is None:
            return
        try:
            BigWorld.cancelCallback(callback_id)
        except Exception:
            pass

    def _schedule_visibility_probe(self, reason):
        if not self._active or self._visibility_probe_callback is not None:
            return

        self._visibility_probe_callback = BigWorld.callback(
            _VISIBILITY_PROBE_DELAY,
            self._run_visibility_probe,
        )

    def _run_visibility_probe(self):
        self._visibility_probe_callback = None
        if not self._active:
            return

        if self._sync_scaleform_view('visibility_probe'):
            if self._scaleform_view is not None and self._scaleform_payload is not None:
                self._push_scaleform_payload()
            return

        self._schedule_visibility_probe('visibility_probe_retry')

    def _schedule_update(self, reason):
        if not self._active:
            return

        self._cancel_pending_update()

        # Keep deferred execution and callback coalescing, but run immediately.
        self._pending_update_callback = BigWorld.callback(0.0, self._deferred_update)

    # -- event handlers ------------------------------------------------------

    def _on_vehicle_changed(self):
        if not self._active:
            return
        self._schedule_update('vehicle_changed')

    def _on_preview_vehicle_changed(self):
        if not self._active:
            return
        self._schedule_update('preview_vehicle_changed')

    def _on_view_added_to_container(self, _container, view):
        if not self._active:
            return

        if getattr(view, 'layer', None) == WindowLayer.SUB_VIEW:
            self._last_seen_sub_view_alias = self._get_view_alias(view)

        if getattr(view, 'alias', None) == SCALEFORM_VIEW_ALIAS:
            return
        if self._should_show_scaleform_view('view_added_to_container', view):
            self._schedule_update('view_added_to_container')
        else:
            self._sync_scaleform_view('view_added_to_container', view)

    def _deferred_update(self):
        """Runs deferred work outside critical hangar-load callbacks."""
        self._pending_update_callback = None
        if self._active:
            try:
                self._update()
            except Exception:
                _logger.exception('Error in _deferred_update')

    # -- data collection -----------------------------------------------------

    def _update(self):
        if not _config.get('enabled'):
            return
        if not self._sync_scaleform_view('update_precheck'):
            return
        if self._update_in_progress:
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
        vehicle_tier = _get_vehicle_tier(vehicle)
        probe_offset = self._t11_method_probe_offsets.get(vehicle.intCD, 0)
        visible_unlocks = _collect_visible_unlocks(vehicle, unlocks_set, self.itemsCache.items)
        available_unlocks = _collect_available_unlocks(
            vehicle,
            unlocks_set,
            self.itemsCache.items,
            visible_unlocks=visible_unlocks,
        )

        # --- Tech tree XP progress ---
        veh_xp = stats.vehiclesXPs.get(vehicle.intCD, 0)
        free_xp = max(0, stats.freeXP)
        total_xp = veh_xp + free_xp

        next_cost, next_intcd = _next_available_unlock(vehicle, unlocks_set, available_unlocks)
        if next_cost and next_cost > 0:
            tt_pct = min(100, int(total_xp * 100 / next_cost))
        else:
            tt_pct = 100 if vehicle.isElite else 0

        can_research_with_vehicle_xp = bool(next_cost is not None and veh_xp >= next_cost)
        can_research_with_total_xp = bool(next_cost is not None and total_xp >= next_cost)

        # --- Elite module progress ---
        elite = vehicle.getEliteStatusProgress()
        elite_unlocked = len(elite.unlocked) if hasattr(elite, 'unlocked') else 0
        elite_total = len(elite.total) if hasattr(elite, 'total') else 0
        elite_pct = int(elite_unlocked * 100 / elite_total) if elite_total > 0 else 100

        # --- Field modifications / post-progression (per vehicle) ---
        pp_settings = None
        try:
            if self.postProgressionCtrl is not None:
                pp_settings = self.postProgressionCtrl.getSettings()
        except Exception:
            if _config.get('debugFieldMods'):
                _logger.exception('Failed to read post-progression controller settings')

        field_mods = _collect_post_progression(
            vehicle,
            stats,
            pp_settings,
            method_probe_offset=probe_offset,
        )
        self._t11_method_probe_offsets[vehicle.intCD] = field_mods.get('t11_method_probe_next_offset', probe_offset)
        tier_plan = _build_tier_field_mod_plan(
            vehicle_tier,
            field_mods['unique_unlocked_level_count'],
            veh_xp,
            total_xp,
            field_mods['is_veh_skill_tree'],
        )

        return {
            'vehicle': {
                'tier': vehicle_tier,
            },
            'tech_tree': {
                'vehicle_xp': veh_xp,
                'free_xp': free_xp,
                'total_xp': total_xp,
                'next_cost': next_cost,
                'next_intcd': next_intcd,
                'pct': tt_pct,
                'can_research_with_vehicle_xp': can_research_with_vehicle_xp,
                'can_research_with_total_xp': can_research_with_total_xp,
                'is_elite': vehicle.isElite,
                'is_fully_elite': vehicle.isFullyElite,
                'visible_unlocks': visible_unlocks,
                'locked_unlock_count': len(visible_unlocks) - len(available_unlocks),
                'available_unlocks': available_unlocks,
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
                'next_purchasable_step_level': field_mods['next_purchasable_step_level'],
                'next_purchasable_step_xp_source': field_mods['next_purchasable_step_xp_source'],
                'next_purchasable_step_kind': field_mods['next_purchasable_step_kind'],
                'raw_unlock_count': field_mods['raw_unlock_count'],
                'unique_step_id_count': field_mods['unique_step_id_count'],
                'unique_level_count': field_mods['unique_level_count'],
                'unique_unlocked_step_id_count': field_mods['unique_unlocked_step_id_count'],
                'unique_unlocked_level_count': field_mods['unique_unlocked_level_count'],
                'next_purchasable_step_xp': field_mods['next_purchasable_step_xp'],
                'debug_step_preview': field_mods['debug_step_preview'],
                'debug_unlock_preview': field_mods['debug_unlock_preview'],
                'debug_level_price_preview': field_mods['debug_level_price_preview'],
                'debug_settings_price_tiers': field_mods['debug_settings_price_tiers'],
                't11_bucket_researched': field_mods['t11_bucket_researched'],
                't11_bucket_unresearched': field_mods['t11_bucket_unresearched'],
                't11_step_preview': field_mods['t11_step_preview'],
                't11_assumed_25k_step_id': field_mods['t11_assumed_25k_step_id'],
                't11_resolved_25k_step_id': field_mods['t11_resolved_25k_step_id'],
                't11_meta_signature_researched': field_mods['t11_meta_signature_researched'],
                't11_meta_signature_unresearched': field_mods['t11_meta_signature_unresearched'],
                't11_meta_keys': field_mods['t11_meta_keys'],
                't11_widenet_step_repr': field_mods['t11_widenet_step_repr'],
                't11_widenet_step_dir_fingerprint': field_mods['t11_widenet_step_dir_fingerprint'],
                't11_widenet_unlock_repr': field_mods['t11_widenet_unlock_repr'],
                't11_method_probe_name': field_mods['t11_method_probe_name'],
                't11_method_probe_preview': field_mods['t11_method_probe_preview'],
                't11_method_probe_hits': field_mods['t11_method_probe_hits'],
                'tier_plan': tier_plan,
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
            '  Field mods DEBUG next step: id=%s kind=%s lvl=%s xp=%s source=%s',
            fm['next_purchasable_step_id'],
            fm['next_purchasable_step_kind'],
            fm['next_purchasable_step_level'],
            fm['next_purchasable_step_xp'],
            fm['next_purchasable_step_xp_source'],
        )
        if fm['debug_step_preview']:
            _logger.info('  Field mods DEBUG step preview: %s', '; '.join(fm['debug_step_preview']))
        if fm['debug_unlock_preview']:
            _logger.info('  Field mods DEBUG unlock preview: %s', ', '.join(fm['debug_unlock_preview']))
        if fm['debug_level_price_preview']:
            _logger.info('  Field mods DEBUG level price preview: %s', '; '.join(fm['debug_level_price_preview']))
        if fm['debug_settings_price_tiers']:
            _logger.info('  Field mods DEBUG settings xp tiers: %s', ', '.join([str(v) for v in fm['debug_settings_price_tiers']]))
        else:
            _logger.info('  Field mods DEBUG settings xp tiers: <none>')

        if fm['is_veh_skill_tree']:
            _logger.info('  Tier-11 DEBUG resolved 25k step id: %s', fm.get('t11_resolved_25k_step_id'))
            if fm.get('t11_method_probe_name'):
                _logger.info(
                    '  Tier-11 DEBUG method probe: name=%s hits=%d',
                    fm.get('t11_method_probe_name'),
                    fm.get('t11_method_probe_hits', 0),
                )
            if fm.get('t11_method_probe_preview'):
                _logger.info(
                    '  Tier-11 DEBUG method probe preview: %s',
                    '; '.join(fm['t11_method_probe_preview'][:12])
                )
            _logger.info(
                '  Tier-11 DEBUG researched buckets: small_10k=%d big_20k=%d big_25k=%d unknown=%d',
                fm['t11_bucket_researched'].get('small_10k', 0),
                fm['t11_bucket_researched'].get('big_20k', 0),
                fm['t11_bucket_researched'].get('big_25k', 0),
                fm['t11_bucket_researched'].get('unknown', 0),
            )
            _logger.info(
                '  Tier-11 DEBUG unresearched buckets: small_10k=%d big_20k=%d big_25k=%d unknown=%d',
                fm['t11_bucket_unresearched'].get('small_10k', 0),
                fm['t11_bucket_unresearched'].get('big_20k', 0),
                fm['t11_bucket_unresearched'].get('big_25k', 0),
                fm['t11_bucket_unresearched'].get('unknown', 0),
            )
            if fm['t11_step_preview']:
                _logger.info('  Tier-11 DEBUG step preview: %s', '; '.join(fm['t11_step_preview']))
            if fm.get('t11_meta_keys'):
                key_items = sorted(fm['t11_meta_keys'].items(), key=lambda item: item[0])
                _logger.info(
                    '  Tier-11 DEBUG metadata keys: %s',
                    '; '.join(['{0}={1}'.format(k, v) for k, v in key_items[:40]])
                )
            if fm.get('t11_meta_signature_researched'):
                sig_items = sorted(
                    fm['t11_meta_signature_researched'].items(),
                    key=lambda item: (-item[1], item[0]),
                )
                _logger.info(
                    '  Tier-11 DEBUG researched signatures: %s',
                    '; '.join(['{0} x{1}'.format(sig, cnt) for sig, cnt in sig_items[:12]])
                )
            if fm.get('t11_meta_signature_unresearched'):
                sig_items = sorted(
                    fm['t11_meta_signature_unresearched'].items(),
                    key=lambda item: (-item[1], item[0]),
                )
                _logger.info(
                    '  Tier-11 DEBUG unresearched signatures: %s',
                    '; '.join(['{0} x{1}'.format(sig, cnt) for sig, cnt in sig_items[:12]])
                )
            if fm.get('t11_widenet_step_dir_fingerprint'):
                _logger.info(
                    '  Tier-11 DEBUG widenet step dir: %s',
                    '; '.join(fm['t11_widenet_step_dir_fingerprint'][:20])
                )
            if fm.get('t11_widenet_step_repr'):
                _logger.info(
                    '  Tier-11 DEBUG widenet step repr: %s',
                    '; '.join(fm['t11_widenet_step_repr'][:20])
                )
            if fm.get('t11_widenet_unlock_repr'):
                _logger.info(
                    '  Tier-11 DEBUG widenet unlock repr: %s',
                    '; '.join(fm['t11_widenet_unlock_repr'][:20])
                )

    # -- rendering -----------------------------------------------------------

    def _render(self, vehicle, data):
        """
        Emit the active Scaleform garage UI and structured python.log output.
        """
        self._render_scaleform_view(vehicle, data)
        self._render_log(vehicle, data)

    def _render_log(self, vehicle, data):

        name = getattr(vehicle, 'userName', str(vehicle.intCD))
        tier = data.get('vehicle', {}).get('tier')
        if tier is not None:
            lines = ['Vehicle: {0} (Tier {1})'.format(name, tier)]
        else:
            lines = ['Vehicle: {0} (Tier unknown)'.format(name)]

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
                lines.append(
                    'Tech tree (max unlock): vehicleXP={0}, vehicle+freeXP={1}'.format(
                        tt['can_research_with_vehicle_xp'],
                        tt['can_research_with_total_xp'],
                    )
                )
            else:
                lines.append('Tech tree: no available unlocks')

        el = data['elite']
        if _config.get('showEliteProgress') and el['total'] > 0:
            lines.append('Elite mods: {0}% ({1}/{2})'.format(el['pct'], el['unlocked'], el['total']))

        vehicle_is_elite = bool(tt.get('is_elite'))
        fm = data['field_mods']
        if _config.get('showFieldMods'):
            if not vehicle_is_elite:
                lines.append('Field mods: requires elite vehicle status')
            elif not fm['exists']:
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

            if vehicle_is_elite and fm['is_veh_skill_tree']:
                lines.append('Tier-11 upgrades: skill tree progress shown by steps')

            if vehicle_is_elite and fm['next_purchasable_step_id'] is not None:
                if fm['next_purchasable_step_xp'] is not None:
                    lines.append(
                        'Field mods next: {0} XP required'.format(
                            fm['next_purchasable_step_xp'],
                        )
                    )
                else:
                    lines.append(
                        'Field mods next: step available at level {0}'.format(
                            fm['next_purchasable_step_level'],
                        )
                    )

            self._log_field_mods_debug(vehicle, fm)

            tier_plan = fm.get('tier_plan') or {}
            if not vehicle_is_elite:
                lines.append('Tier rules: unavailable until vehicle is elite')
            elif tier_plan.get('enabled'):
                if tier_plan.get('next_level') is not None:
                    lines.append(
                        'Tier rules: lvl {0}/{1}, next {2}, cost {3} XP'.format(
                            tier_plan.get('current_level'),
                            tier_plan.get('max_level'),
                            tier_plan.get('next_level'),
                            tier_plan.get('next_level_xp_cost'),
                        )
                    )
                    lines.append(
                        'Can research: vehicleXP={0}, vehicle+freeXP={1}'.format(
                            tier_plan.get('can_research_with_vehicle_xp'),
                            tier_plan.get('can_research_with_total_xp'),
                        )
                    )
                else:
                    lines.append(
                        'Tier rules: lvl {0}/{1} COMPLETE'.format(
                            tier_plan.get('current_level'),
                            tier_plan.get('max_level'),
                        )
                    )
            elif tier_plan.get('reason') == 'no-field-mods':
                lines.append('Tier rules: no field mods for this tier')


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
