"""Scaleform payload builders for the research progress bar."""
from __future__ import print_function, unicode_literals


MODE_REGULAR_RESEARCH = 'regular_research'
MODE_FIELD_MODS = 'field_mods'
MODE_TIER11_UPGRADES = 'tier11_upgrades'


def build_scaleform_view_payload(vehicle, data):
    """Builds the full Scaleform payload or None when no mode is available."""
    modes = []

    research_mode = _build_regular_research_mode(data)
    if research_mode is not None:
        modes.append(research_mode)

    field_mods_mode = _build_field_mods_mode(data)
    if field_mods_mode is not None:
        modes.append(field_mods_mode)

    tier11_mode = _build_tier11_mode(data)
    if tier11_mode is not None:
        modes.append(tier11_mode)

    if not modes:
        return None

    return {
        'vehicleLabel': _build_vehicle_label(vehicle, data),
        'selectedModeId': modes[0]['id'],
        'modes': modes,
    }


def _build_vehicle_label(vehicle, data):
    name = getattr(vehicle, 'userName', str(vehicle.intCD))
    tier = (data.get('vehicle') or {}).get('tier')
    if tier is None:
        return '{0} (Tier unknown)'.format(name)
    return '{0} (Tier {1})'.format(name, tier)


def _build_regular_research_mode(data):
    tech_tree = data.get('tech_tree') or {}
    visible_unlocks = tech_tree.get('visible_unlocks') or []
    available_unlocks = tech_tree.get('available_unlocks') or []
    locked_unlock_count = _to_int(tech_tree.get('locked_unlock_count')) or 0

    if not visible_unlocks:
        return None

    max_requirement_xp = max([1] + [int(item['xp_cost']) for item in visible_unlocks])
    vehicle_xp = min(_to_int(tech_tree.get('vehicle_xp')) or 0, max_requirement_xp)
    free_xp = min(
        _to_int(tech_tree.get('free_xp')) or 0,
        max(0, max_requirement_xp - vehicle_xp),
    )

    if available_unlocks:
        right_caption = 'Total XP'
        right_text = _format_percent(vehicle_xp + free_xp, max_requirement_xp)
    elif locked_unlock_count > 0:
        right_caption = 'Locked'
        right_text = str(locked_unlock_count)
    else:
        right_caption = 'Total XP'
        right_text = _format_percent(vehicle_xp + free_xp, max_requirement_xp)

    return _make_mode(
        MODE_REGULAR_RESEARCH,
        'Research',
        max_requirement_xp,
        vehicle_xp,
        free_xp,
        _format_percent(vehicle_xp, max_requirement_xp),
        'Vehicle XP',
        right_text,
        right_caption,
        markers=[_build_research_marker(item) for item in visible_unlocks],
    )


def _build_field_mods_mode(data):
    field_mods = data.get('field_mods') or {}
    tier_plan = field_mods.get('tier_plan') or {}
    tech_tree = data.get('tech_tree') or {}

    if not _is_field_mods_mode_enabled(field_mods, tier_plan, tech_tree):
        return None

    max_level = _to_int(tier_plan.get('max_level')) or _to_int(field_mods.get('unique_level_count')) or 0
    current_level = _to_int(tier_plan.get('current_level'))
    if current_level is None:
        current_level = _to_int(field_mods.get('unique_unlocked_level_count')) or 0
    current_level = max(0, min(current_level, max_level))

    next_level = _to_int(tier_plan.get('next_level'))
    next_level_xp_cost = _to_int(tier_plan.get('next_level_xp_cost'))
    if next_level_xp_cost is None:
        next_level_xp_cost = _to_int(field_mods.get('next_purchasable_step_xp'))
    xp_per_level = _to_int(tier_plan.get('xp_per_level'))

    vehicle_xp = _to_int(tech_tree.get('vehicle_xp')) or 0
    free_xp = _to_int(tech_tree.get('free_xp')) or 0
    total_xp = _to_int(tech_tree.get('total_xp'))
    if total_xp is None:
        total_xp = vehicle_xp + free_xp

    remaining_levels = range(current_level + 1, max_level + 1)

    if next_level is None or current_level >= max_level:
        primary_value = float(max_level)
        secondary_value = 0.0
        completed_value = 0.0
        bar_max_value = max_level
        left_text = '100%'
        left_caption = 'Vehicle XP'
        right_text = '100%'
        right_caption = 'Total XP'
        markers = []
    elif xp_per_level is not None and xp_per_level > 0 and remaining_levels:
        total_cost = xp_per_level * max_level
        completed_total_cost = xp_per_level * current_level
        remaining_total_cost = xp_per_level * len(remaining_levels)
        primary_value = min(vehicle_xp, remaining_total_cost)
        secondary_value = min(free_xp, max(0, remaining_total_cost - primary_value))
        completed_value = completed_total_cost
        left_text = _format_percent(completed_total_cost + vehicle_xp, total_cost)
        left_caption = 'Vehicle XP'
        right_text = _format_percent(completed_total_cost + total_xp, total_cost)
        right_caption = 'Total XP'
        bar_max_value = total_cost
        markers = _build_field_mod_markers(
            current_level,
            max_level,
            xp_per_level,
            vehicle_xp,
            total_xp,
        )
    else:
        primary_value, secondary_value = _build_fractional_fill(
            current_level,
            max_level,
            next_level_xp_cost,
            vehicle_xp,
            total_xp,
        )
        completed_value = 0.0
        left_text = _format_percent(vehicle_xp, next_level_xp_cost)
        left_caption = 'Vehicle XP'
        right_text = _format_percent(total_xp, next_level_xp_cost)
        right_caption = 'Total XP'
        bar_max_value = max_level
        markers = []

    return _make_mode(
        MODE_FIELD_MODS,
        'Field Mods',
        bar_max_value,
        primary_value,
        secondary_value,
        left_text,
        left_caption,
        right_text,
        right_caption,
        markers=markers,
        completed_value=completed_value,
    )


def _build_tier11_mode(data):
    field_mods = data.get('field_mods') or {}
    tech_tree = data.get('tech_tree') or {}
    if not _is_tier11_mode_enabled(field_mods, tech_tree):
        return None

    total_steps = _to_int(field_mods.get('total_steps')) or 0
    unlocked_steps = _to_int(field_mods.get('unlocked_steps')) or 0
    unlocked_steps = max(0, min(unlocked_steps, total_steps))

    next_step_xp_cost = _to_int(field_mods.get('next_purchasable_step_xp'))
    vehicle_xp = _to_int(tech_tree.get('vehicle_xp')) or 0
    free_xp = _to_int(tech_tree.get('free_xp')) or 0
    total_xp = _to_int(tech_tree.get('total_xp'))
    if total_xp is None:
        total_xp = vehicle_xp + free_xp

    if unlocked_steps >= total_steps:
        primary_value = float(total_steps)
        secondary_value = 0.0
        right_text = 'Done'
        right_caption = 'Status'
    elif next_step_xp_cost:
        primary_value, secondary_value = _build_fractional_fill(
            unlocked_steps,
            total_steps,
            next_step_xp_cost,
            vehicle_xp,
            total_xp,
        )
        right_text = _format_percent(total_xp, next_step_xp_cost)
        right_caption = 'Next Upgrade'
    else:
        primary_value = float(unlocked_steps)
        secondary_value = 0.0
        right_text = _format_percent(unlocked_steps, total_steps)
        right_caption = 'Progress'

    return _make_mode(
        MODE_TIER11_UPGRADES,
        'Tier 11',
        total_steps,
        primary_value,
        secondary_value,
        '{0}/{1}'.format(unlocked_steps, total_steps),
        'Steps',
        right_text,
        right_caption,
        markers=[],
    )


def _build_research_marker(item):
    return {
        'id': 'unlock_{0}'.format(item['intcd']),
        'positionValue': item['xp_cost'],
        'costXp': item['xp_cost'],
        'itemType': item['item_type'],
        'isAvailable': item.get('is_available', True),
        'missingPrereqNames': item.get('missing_prereq_names', []),
        'missingPrereqs': item.get('missing_prereqs', []),
        'name': item.get('name'),
        'label': item['label'],
    }


def _build_field_mod_markers(current_level, max_level, xp_per_level, vehicle_xp, total_xp):
    markers = []
    cumulative_total_cost = 0

    for level in range(1, max_level + 1):
        cumulative_total_cost += xp_per_level
        remaining_cost = max(0, (level - current_level) * xp_per_level)
        roman_level = _to_roman(level)
        markers.append({
            'id': 'field_mod_{0}'.format(level),
            'positionValue': cumulative_total_cost,
            'costXp': xp_per_level if level <= current_level else remaining_cost,
            'itemType': 'unknown',
            'isAvailable': True,
            'name': 'Level {0}'.format(roman_level),
            'label': roman_level,
            'hideTooltipIcon': True,
            'markerState': _resolve_field_mod_marker_state(
                level,
                current_level,
                remaining_cost,
                vehicle_xp,
                total_xp,
            ),
        })

    return markers


def _resolve_field_mod_marker_state(level, current_level, remaining_cost, vehicle_xp, total_xp):
    if level <= current_level:
        return 'completed'
    if remaining_cost <= max(0, vehicle_xp):
        return 'reachable_vehicle'
    if remaining_cost <= max(0, total_xp):
        return 'reachable_total'
    return 'locked'


def _make_mode(
        mode_id,
        button_label,
        bar_max_value,
        primary_value,
        secondary_value,
        left_counter_text,
        left_counter_caption,
        right_counter_text,
        right_counter_caption,
        markers=None,
        completed_value=0.0):
    bar_max = max(1.0, float(bar_max_value or 0))
    completed = _clamp(float(completed_value or 0), 0.0, bar_max)
    primary = _clamp(float(primary_value or 0), 0.0, bar_max - completed)
    secondary = _clamp(float(secondary_value or 0), 0.0, bar_max - completed - primary)

    return {
        'id': mode_id,
        'buttonLabel': button_label,
        'barMaxValue': bar_max,
        'completedValue': completed,
        'primaryValue': primary,
        'secondaryValue': secondary,
        'leftCounterText': left_counter_text,
        'leftCounterCaption': left_counter_caption,
        'rightCounterText': right_counter_text,
        'rightCounterCaption': right_counter_caption,
        'markers': markers or [],
        'progress': int(min(100, (completed + primary + secondary) * 100.0 / bar_max)),
    }


def _build_fractional_fill(base_units, max_units, step_cost, vehicle_xp, total_xp):
    if max_units <= 0:
        return 0.0, 0.0

    primary_value = float(max(0, min(base_units, max_units)))
    secondary_value = 0.0

    if step_cost is None or step_cost <= 0 or primary_value >= float(max_units):
        return primary_value, secondary_value

    vehicle_fraction = min(1.0, float(max(0, vehicle_xp)) / float(step_cost))
    total_fraction = min(1.0, float(max(0, total_xp)) / float(step_cost))
    secondary_fraction = max(0.0, total_fraction - vehicle_fraction)

    primary_value = min(float(max_units), primary_value + vehicle_fraction)
    secondary_value = min(float(max_units) - primary_value, secondary_fraction)
    return primary_value, secondary_value


def _is_field_mods_mode_enabled(field_mods, tier_plan, tech_tree):
    if not tech_tree.get('is_elite'):
        return False
    if not field_mods.get('exists'):
        return False
    if field_mods.get('is_veh_skill_tree'):
        return False

    if tier_plan.get('enabled'):
        return tier_plan.get('next_level') is not None

    unique_level_count = _to_int(field_mods.get('unique_level_count')) or 0
    unique_unlocked_level_count = _to_int(field_mods.get('unique_unlocked_level_count')) or 0
    if unique_level_count <= 0:
        return False
    return unique_unlocked_level_count < unique_level_count


def _is_tier11_mode_enabled(field_mods, tech_tree):
    if not tech_tree.get('is_elite'):
        return False
    if not field_mods.get('is_veh_skill_tree'):
        return False
    total_steps = _to_int(field_mods.get('total_steps')) or 0
    return total_steps > 0


def _format_percent(current_value, target_value):
    target = _to_int(target_value)
    if target is None or target <= 0:
        return '0%'
    current = max(0, _to_int(current_value) or 0)
    return '{0}%'.format(int(min(100, current * 100 / target)))


def _to_roman(value):
    number = _to_int(value)
    if number is None or number <= 0:
        return str(value)

    parts = []
    numerals = (
        (1000, 'M'),
        (900, 'CM'),
        (500, 'D'),
        (400, 'CD'),
        (100, 'C'),
        (90, 'XC'),
        (50, 'L'),
        (40, 'XL'),
        (10, 'X'),
        (9, 'IX'),
        (5, 'V'),
        (4, 'IV'),
        (1, 'I'),
    )

    for numeral_value, numeral_text in numerals:
        while number >= numeral_value:
            parts.append(numeral_text)
            number -= numeral_value

    return ''.join(parts)


def _to_int(value):
    try:
        if value is None:
            return None
        return int(value)
    except Exception:
        return None


def _clamp(value, min_value, max_value):
    if value < min_value:
        return min_value
    if value > max_value:
        return max_value
    return value