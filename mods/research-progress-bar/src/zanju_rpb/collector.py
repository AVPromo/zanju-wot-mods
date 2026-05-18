"""Collector helpers for research and tier-based field-mod progress."""
from __future__ import print_function, unicode_literals

import logging

try:
    from gui.prestige import prestige_helpers as _prestige_helpers
except Exception:
    _prestige_helpers = None
from gui.shared.gui_items import GUI_ITEM_TYPE_NAMES
from items import getTypeOfCompactDescr

from .constants import _TIER_FIELD_MOD_RULES, _UNLOCK_MARKER_TYPE_BY_GUI_NAME
from .utils import _extract_sequence_ints, _mapping_value, _to_int_or_none

_logger = logging.getLogger('zanju.researchprogressbar')


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
        'item_type': item_type,
        'name': _resolve_unlock_display_name(intcd, items),
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
    tier = _to_int_or_none(getattr(vehicle, 'level', None))
    if tier is not None:
        return tier

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
    """Build tier-based field-mod next-level plan and affordability checks."""
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
    plan['can_research_with_vehicle_xp'] = (
        (vehicle_xp >= next_level_cost) if next_level is not None else False
    )
    plan['can_research_with_total_xp'] = (
        (total_xp >= next_level_cost) if next_level is not None else False
    )
    return plan


def _collect_int_attr_candidates(objects, attr_names):
    values = []
    obj = None
    for obj in objects:
        value = _first_int_attr(obj, attr_names)
        if value is not None:
            values.append(value)
    return values


def _first_int_attr_from_objects(objects, attr_names):
    obj = None
    for obj in objects:
        value = _first_int_attr(obj, attr_names)
        if value is not None:
            return value
    return None


def _extract_elite_remaining_points(objects):
    obj = None
    for obj in objects:
        value = _first_int_attr(obj, ('remainingPoints', 'remainingPts', 'nextLevelPts', 'nextLvlPts'))
        if value is not None:
            return value

        sequence_items = _extract_sequence_ints(obj, 3)
        if len(sequence_items) >= 2:
            return sequence_items[1]

    return None


def _first_int_attr(obj, attr_names):
    attr_name = None
    for attr_name in attr_names:
        try:
            value = getattr(obj, attr_name, None)
        except Exception:
            value = None
        value = _to_int_or_none(value)
        if value is not None:
            return value
    return None


def _call_prestige_helper(helper_name, *args):
    if _prestige_helpers is None:
        return None

    try:
        helper = getattr(_prestige_helpers, helper_name, None)
    except Exception:
        helper = None
    if not callable(helper):
        return None

    candidates = []
    value = None
    for value in args:
        if value is None:
            continue
        candidates.append(value)
        value_int_cd = getattr(value, 'intCD', None)
        if value_int_cd is not None:
            candidates.append(value_int_cd)

    if not candidates:
        try:
            return helper()
        except TypeError:
            return None
        except Exception:
            return None

    candidate = None
    for candidate in candidates:
        try:
            return helper(candidate)
        except TypeError:
            continue
        except Exception:
            return None

    try:
        return helper()
    except TypeError:
        return None
    except Exception:
        return None


def _collect_elite_progression(vehicle):
    data = {
        'available': False,
        'current_level': None,
        'current_xp': None,
        'next_level_xp': None,
        'remaining_xp': None,
        'max_level': None,
    }

    if vehicle is None or not getattr(vehicle, 'isElite', False):
        return data

    has_vehicle_prestige = _call_prestige_helper('hasVehiclePrestige', vehicle)
    global_prestige_stats = _call_prestige_helper('getPrestigeStats')
    vehicle_points = _call_prestige_helper('getVehiclePoints', vehicle)
    prestige_stats = _call_prestige_helper('getPrestigeStats', vehicle_points, vehicle)
    if prestige_stats is None:
        prestige_stats = global_prestige_stats
    prestige_map = _call_prestige_helper('getVehiclePrestigeMap', prestige_stats, global_prestige_stats)
    mapped_prestige = _mapping_value(prestige_map, getattr(vehicle, 'intCD', None))
    prestige = _call_prestige_helper('getVehiclePrestige', vehicle)
    progress = _call_prestige_helper(
        'getCurrentProgress',
        mapped_prestige,
        prestige_stats,
        prestige,
        vehicle_points,
        vehicle,
    )
    if has_vehicle_prestige is False and prestige is None and prestige_stats is None and mapped_prestige is None:
        return data

    data['available'] = (
        bool(has_vehicle_prestige)
        or prestige is not None
        or prestige_stats is not None
        or mapped_prestige is not None
        or progress is not None
    )
    level_candidates = _collect_int_attr_candidates(
        (mapped_prestige, progress, prestige_stats, prestige),
        ('currentLevel', 'prestigeLevel', 'level'),
    )
    progress_sources = (progress, mapped_prestige, prestige_stats, prestige)
    if not level_candidates and all(source is None for source in progress_sources):
        return data

    if level_candidates:
        data['current_level'] = max(level_candidates)
    data['current_xp'] = _first_int_attr_from_objects(progress_sources, ('currentXP', 'currentXp'))
    data['next_level_xp'] = _first_int_attr_from_objects(
        progress_sources,
        ('nextLvlXP', 'nextLevelXP', 'nextLvlXp', 'nextLevelXp'),
    )
    remaining_points = _extract_elite_remaining_points(
        (progress, mapped_prestige, prestige_stats, prestige, vehicle_points)
    )
    if remaining_points is not None:
        data['remaining_xp'] = _call_prestige_helper('prestigePointsToXP', remaining_points)
        if data['remaining_xp'] is None:
            data['remaining_xp'] = remaining_points
    max_level_candidates = _collect_int_attr_candidates(
        (mapped_prestige, progress, prestige_stats, prestige),
        ('maxLevel',),
    )
    if max_level_candidates:
        data['max_level'] = max(max_level_candidates)
    if data['max_level'] is None:
        data['max_level'] = _first_int_attr(prestige, ('maxLevel',))
    if data['current_level'] is None:
        data['available'] = False

    return data


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


def _resolve_t11_step_xp_cost(step):
    """Safely resolves stable tier-11 node XP cost from getType()."""
    try:
        get_type = getattr(step, 'getType', None)
        if get_type is None or not callable(get_type):
            return None
        return _resolve_t11_xp_from_type(get_type())
    except Exception:
        return None


def _t11_action_node_sort_key(node):
    bucket_order = {
        'small_10k': 0,
        'big_20k': 1,
        'big_25k': 2,
        'unknown': 3,
    }
    return (
        bucket_order.get(node.get('bucket'), 99),
        _to_int_or_none(node.get('step_id')) or 0,
    )


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


def _make_empty_t11_bucket_counts():
    return {
        'small_10k': 0,
        'big_20k': 0,
        'big_25k': 0,
        'unknown': 0,
    }


def _collect_post_progression_step_metadata(pp, is_veh_skill_tree, vehicle, resolve_t11_action_marker_meta):
    total_steps = 0
    unique_level_count = 0
    step_id_to_level = {}
    step_meta = {}

    try:
        steps = list(pp.iterUnorderedSteps())
        total_steps = len(steps)

        unique_levels = set()
        step = None
        for step in steps:
            step_id = getattr(step, 'stepID', None)
            if step_id is None:
                step_id = getattr(step, 'id', None)

            level = getattr(step, 'level', None)
            if level is None and hasattr(step, 'getLevel'):
                try:
                    level = step.getLevel()
                except Exception:
                    level = None

            if step_id is not None:
                step_id_to_level[step_id] = level
                if is_veh_skill_tree:
                    step_xp_cost = _resolve_t11_step_xp_cost(step)
                    action_meta = None
                    if resolve_t11_action_marker_meta is not None:
                        action_meta = resolve_t11_action_marker_meta(step, step_id, vehicle)
                    step_meta[step_id] = {
                        'xp_cost': step_xp_cost,
                        'bucket': _make_t11_bucket(step_xp_cost),
                        'action_meta': action_meta,
                    }

            if level is not None:
                unique_levels.add(level)

        unique_level_count = len(unique_levels)
    except Exception:
        _logger.exception('Failed to read post-progression step metadata')

    return total_steps, unique_level_count, step_id_to_level, step_meta


def _normalize_t11_final_bucket(step_meta):
    if not step_meta:
        return

    meta = None
    for meta in step_meta.itervalues():
        if meta.get('bucket') == 'big_25k':
            return

    fallback_final_id = max(step_meta.keys())
    if step_meta[fallback_final_id].get('bucket') == 'unknown':
        step_meta[fallback_final_id]['bucket'] = 'big_25k'


def _collect_t11_unlock_data(step_meta, unlocked_step_ids):
    researched_action_nodes = []
    unresearched_action_nodes = []
    researched_buckets = _make_empty_t11_bucket_counts()
    unresearched_buckets = _make_empty_t11_bucket_counts()

    _normalize_t11_final_bucket(step_meta)

    step_id = None
    meta = None
    for step_id, meta in step_meta.iteritems():
        bucket = meta.get('bucket') or 'unknown'
        is_researched = step_id in unlocked_step_ids
        bucket_counts = researched_buckets if is_researched else unresearched_buckets
        bucket_counts[bucket] = bucket_counts.get(bucket, 0) + 1

        action_meta = meta.get('action_meta')
        if action_meta is None:
            continue

        action_node = {
            'step_id': step_id,
            'xp_cost': meta.get('xp_cost'),
            'bucket': bucket,
            'name': action_meta.get('name'),
            'tooltip_title': action_meta.get('tooltip_title'),
            'ui_localized_name': action_meta.get('ui_localized_name'),
            'localized_name': action_meta.get('localized_name'),
            'loc_name': action_meta.get('loc_name'),
            'tech_name': action_meta.get('tech_name'),
            'image_name': action_meta.get('image_name'),
            'slot_category': action_meta.get('slot_category'),
            'category': action_meta.get('category'),
        }
        if is_researched:
            researched_action_nodes.append(action_node)
        else:
            unresearched_action_nodes.append(action_node)

    return {
        't11_bucket_researched': researched_buckets,
        't11_bucket_unresearched': unresearched_buckets,
        't11_action_nodes_researched': sorted(researched_action_nodes, key=_t11_action_node_sort_key),
        't11_action_nodes_unresearched': sorted(unresearched_action_nodes, key=_t11_action_node_sort_key),
    }


def _collect_post_progression_unlock_state(pp, step_id_to_level, step_meta, is_veh_skill_tree):
    result = {
        'unlocked_steps': 0,
        'unique_unlocked_level_count': 0,
        't11_bucket_researched': _make_empty_t11_bucket_counts(),
        't11_bucket_unresearched': _make_empty_t11_bucket_counts(),
        't11_action_nodes_researched': [],
        't11_action_nodes_unresearched': [],
    }

    unlocked_step_ids = set()
    try:
        state = pp.getState(True)
        unlocks = getattr(state, 'unlocks', set()) or set()
        unlock = None
        for unlock in unlocks:
            unlocked_step_id = getattr(unlock, 'stepID', None)
            if unlocked_step_id is None:
                unlocked_step_id = getattr(unlock, 'id', None)
            if unlocked_step_id is None:
                unlocked_step_id = unlock

            try:
                if unlocked_step_id is not None:
                    unlocked_step_ids.add(unlocked_step_id)
            except Exception:
                pass

        result['unlocked_steps'] = len(unlocked_step_ids)

        unlocked_levels = set()
        unlocked_step_id = None
        for unlocked_step_id in unlocked_step_ids:
            level = step_id_to_level.get(unlocked_step_id)
            if level is not None:
                unlocked_levels.add(level)
        result['unique_unlocked_level_count'] = len(unlocked_levels)

        if is_veh_skill_tree and step_meta:
            result.update(_collect_t11_unlock_data(step_meta, unlocked_step_ids))
    except Exception:
        _logger.exception('Failed to read post-progression state/unlocks')

    return result


def _resolve_next_purchasable_post_progression_step_xp(pp, stats, vehicle, step_meta):
    next_purchasable_step_xp = None

    try:
        balance = stats.getMoneyExt(vehicle.intCD)
        step = pp.getFirstPurchasableStep(balance)
        if step is None:
            return None

        step_id = getattr(step, 'stepID', None) or getattr(step, 'id', None)
        if step_id is not None:
            step_meta_entry = step_meta.get(step_id)
            if step_meta_entry is not None:
                next_purchasable_step_xp = step_meta_entry.get('xp_cost')

        if next_purchasable_step_xp is None:
            next_purchasable_step_xp = _extract_xp_cost_lightweight(step)
    except Exception:
        _logger.exception('Failed to resolve next purchasable post-progression step')

    return next_purchasable_step_xp


def _collect_post_progression(vehicle, stats, resolve_t11_action_marker_meta=None):
    """Collect the production post-progression data used by the UI."""
    data = {
        'exists': False,
        'total_steps': 0,
        'unlocked_steps': 0,
        'is_veh_skill_tree': False,
        'unique_level_count': 0,
        'unique_unlocked_level_count': 0,
        'next_purchasable_step_xp': None,
        't11_bucket_researched': _make_empty_t11_bucket_counts(),
        't11_bucket_unresearched': _make_empty_t11_bucket_counts(),
        't11_action_nodes_researched': [],
        't11_action_nodes_unresearched': [],
    }

    try:
        data['exists'] = bool(getattr(vehicle, 'isPostProgressionExists', False))
    except Exception:
        _logger.exception('Failed to read vehicle post-progression flags')

    pp = getattr(vehicle, 'postProgression', None)
    if pp is None:
        return data

    try:
        data['is_veh_skill_tree'] = bool(pp.isVehSkillTree())
    except Exception:
        data['is_veh_skill_tree'] = False

    total_steps, unique_level_count, step_id_to_level, step_meta = _collect_post_progression_step_metadata(
        pp,
        data['is_veh_skill_tree'],
        vehicle,
        resolve_t11_action_marker_meta,
    )
    data['total_steps'] = total_steps
    data['unique_level_count'] = unique_level_count

    data.update(
        _collect_post_progression_unlock_state(
            pp,
            step_id_to_level,
            step_meta,
            data['is_veh_skill_tree'],
        )
    )

    if not data['is_veh_skill_tree']:
        return data

    data['next_purchasable_step_xp'] = _resolve_next_purchasable_post_progression_step_xp(
        pp,
        stats,
        vehicle,
        step_meta,
    )

    return data


def _collect_research_progress_data(vehicle, stats, items, resolve_t11_action_marker_meta=None):
    unlocks_set = stats.unlocks
    vehicle_tier = _get_vehicle_tier(vehicle)
    visible_unlocks = _collect_visible_unlocks(vehicle, unlocks_set, items)
    available_unlocks = _collect_available_unlocks(
        vehicle,
        unlocks_set,
        items,
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

    elite_progression = _collect_elite_progression(vehicle)

    # --- Field modifications / post-progression (per vehicle) ---
    field_mods = _collect_post_progression(vehicle, stats, resolve_t11_action_marker_meta)
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
        'elite_progression': elite_progression,
        'field_mods': {
            'exists': field_mods['exists'],
            'total_steps': field_mods['total_steps'],
            'unlocked_steps': field_mods['unlocked_steps'],
            'is_veh_skill_tree': field_mods['is_veh_skill_tree'],
            'unique_level_count': field_mods['unique_level_count'],
            'unique_unlocked_level_count': field_mods['unique_unlocked_level_count'],
            'next_purchasable_step_xp': field_mods['next_purchasable_step_xp'],
            't11_bucket_researched': field_mods['t11_bucket_researched'],
            't11_bucket_unresearched': field_mods['t11_bucket_unresearched'],
            't11_action_nodes_researched': field_mods['t11_action_nodes_researched'],
            't11_action_nodes_unresearched': field_mods['t11_action_nodes_unresearched'],
            'tier_plan': tier_plan,
        },
    }
