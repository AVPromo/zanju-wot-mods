"""Scaleform payload builders for the research progress bar."""
from __future__ import print_function, unicode_literals

from ..localization import get_text as _loc


MODE_REGULAR_RESEARCH = 'regular_research'
MODE_FIELD_MODS = 'field_mods'
MODE_TIER11_UPGRADES = 'tier11_upgrades'
MODE_ELITE_PROGRESSION = 'elite_progression'

ELITE_MODE_ON = 'on'
ELITE_MODE_CUSTOMIZATION_ONLY = 'customization_only'
ELITE_MODE_OFF = 'off'

ELITE_MAX_LEVEL = 350
ELITE_LEVEL_XP_SEGMENTS = (
    (1, 5, 1000),
    (5, 20, 1500),
    (20, 150, 2500),
    (150, 250, 3000),
    (250, ELITE_MAX_LEVEL, 4000),
)
ELITE_COLOR_MARKERS = (
    ('metal', 'ELITE_BADGE_METAL', 'Metal Badge', 1),
    ('bronze', 'ELITE_BADGE_BRONZE', 'Bronze Badge', 20),
    ('silver', 'ELITE_BADGE_SILVER', 'Silver Badge', 70),
    ('gold', 'ELITE_BADGE_GOLD', 'Gold Badge', 150),
    ('red_gold', 'ELITE_BADGE_RED_GOLD', 'Red Gold Badge', 250),
    ('prestige_elite', 'ELITE_BADGE_PRESTIGE', 'Prestige Elite Badge', ELITE_MAX_LEVEL),
)
ELITE_T11_COSMETIC_MARKERS = (
    ('stat_tracker', 'ELITE_REWARD_STAT_TRACKER', 'Stat Tracker', 35),
    ('volumetric_style', 'ELITE_REWARD_VOLUMETRIC_STYLE', 'Volumetric Style', 75),
    ('gun_sleeve', 'ELITE_REWARD_GUN_SLEEVE', 'Gun Sleeve', 155),
)

T11_CATEGORY_SORT_ORDER = {
    'firepower': 0,
    'survivability': 1,
    'scouting': 2,
    'mobility': 3,
    'special': 4,
    'mechanics': 5,
}


def build_scaleform_view_payload(vehicle, data, mode_preferences=None):
    """Builds the full Scaleform payload or None when no mode is available."""
    preferences = _normalize_mode_preferences(mode_preferences)
    modes = []

    if preferences['showResearch']:
        research_mode = _build_regular_research_mode(data)
        if research_mode is not None:
            modes.append(research_mode)

    if preferences['showFieldMods']:
        field_mods_mode = _build_field_mods_mode(data)
        if field_mods_mode is not None:
            modes.append(field_mods_mode)

    if preferences['showUpgrades']:
        tier11_mode = _build_tier11_mode(data)
        if tier11_mode is not None:
            modes.append(tier11_mode)

    elite_mode = _build_elite_mode(data, preferences['eliteMode'])
    if elite_mode is not None:
        modes.append(elite_mode)

    if not modes:
        return None

    return {
        'vehicleLabel': _build_vehicle_label(vehicle, data),
        'selectedModeId': modes[0]['id'],
        'modes': modes,
    }


def _normalize_mode_preferences(mode_preferences):
    preferences = dict(mode_preferences or {})
    elite_mode = preferences.get('eliteMode') or ELITE_MODE_ON
    if elite_mode not in (ELITE_MODE_ON, ELITE_MODE_CUSTOMIZATION_ONLY, ELITE_MODE_OFF):
        elite_mode = ELITE_MODE_ON

    return {
        'showResearch': bool(preferences.get('showResearch', True)),
        'showFieldMods': bool(preferences.get('showFieldMods', True)),
        'showUpgrades': bool(preferences.get('showUpgrades', True)),
        'eliteMode': elite_mode,
    }


def _build_vehicle_label(vehicle, data):
    name = getattr(vehicle, 'userName', str(vehicle.intCD))
    tier = (data.get('vehicle') or {}).get('tier')
    if tier is None:
        return _loc('VEHICLE_LABEL_TIER_UNKNOWN_FORMAT', '{name} (Tier unknown)', name=name)
    return _loc('VEHICLE_LABEL_TIER_FORMAT', '{name} (Tier {tier})', name=name, tier=tier)


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
        right_caption = _loc('CAPTION_TOTAL_XP', 'Total XP')
        right_text = _format_percent(vehicle_xp + free_xp, max_requirement_xp)
    elif locked_unlock_count > 0:
        right_caption = _loc('CAPTION_LOCKED', 'Locked')
        right_text = str(locked_unlock_count)
    else:
        right_caption = _loc('CAPTION_TOTAL_XP', 'Total XP')
        right_text = _format_percent(vehicle_xp + free_xp, max_requirement_xp)

    return _make_mode(
        MODE_REGULAR_RESEARCH,
        _loc('MODE_RESEARCH', 'Research'),
        max_requirement_xp,
        vehicle_xp,
        free_xp,
        _format_percent(vehicle_xp, max_requirement_xp),
        _loc('CAPTION_VEHICLE_XP', 'Vehicle XP'),
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
        left_caption = _loc('CAPTION_VEHICLE_XP', 'Vehicle XP')
        right_text = '100%'
        right_caption = _loc('CAPTION_TOTAL_XP', 'Total XP')
        markers = []
    elif xp_per_level is not None and xp_per_level > 0 and remaining_levels:
        total_cost = xp_per_level * max_level
        completed_total_cost = xp_per_level * current_level
        remaining_total_cost = xp_per_level * len(remaining_levels)
        primary_value = min(vehicle_xp, remaining_total_cost)
        secondary_value = min(free_xp, max(0, remaining_total_cost - primary_value))
        completed_value = completed_total_cost
        left_text = _format_percent(completed_total_cost + vehicle_xp, total_cost)
        left_caption = _loc('CAPTION_VEHICLE_XP', 'Vehicle XP')
        right_text = _format_percent(completed_total_cost + total_xp, total_cost)
        right_caption = _loc('CAPTION_TOTAL_XP', 'Total XP')
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
        left_caption = _loc('CAPTION_VEHICLE_XP', 'Vehicle XP')
        right_text = _format_percent(total_xp, next_level_xp_cost)
        right_caption = _loc('CAPTION_TOTAL_XP', 'Total XP')
        bar_max_value = max_level
        markers = []

    return _make_mode(
        MODE_FIELD_MODS,
        _loc('MODE_FIELD_MODS', 'Field Mods'),
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

    display_layout = _build_t11_display_layout(field_mods)
    total_cost = display_layout['total_cost']

    if total_cost > 0:
        remaining_cost = display_layout['remaining_cost']
        if remaining_cost <= 0:
            return None
        primary_value = min(vehicle_xp, remaining_cost)
        secondary_value = min(free_xp, max(0, remaining_cost - primary_value))
        completed_value = display_layout['completed_cost']
        left_text = _format_percent(completed_value + vehicle_xp, total_cost)
        left_caption = _loc('CAPTION_VEHICLE_XP', 'Vehicle XP')
        right_text = _format_percent(completed_value + total_xp, total_cost)
        right_caption = _loc('CAPTION_TOTAL_XP', 'Total XP')
        bar_max_value = total_cost
        markers = _build_t11_markers(
            display_layout,
            vehicle_xp,
            total_xp,
        )
    elif next_step_xp_cost:
        primary_value, secondary_value = _build_fractional_fill(
            unlocked_steps,
            total_steps,
            next_step_xp_cost,
            vehicle_xp,
            total_xp,
        )
        completed_value = 0.0
        left_text = _format_percent(vehicle_xp, next_step_xp_cost)
        left_caption = _loc('CAPTION_VEHICLE_XP', 'Vehicle XP')
        right_text = _format_percent(total_xp, next_step_xp_cost)
        right_caption = _loc('CAPTION_TOTAL_XP', 'Total XP')
        bar_max_value = total_steps
        markers = []
    else:
        primary_value = float(unlocked_steps)
        secondary_value = 0.0
        completed_value = 0.0
        left_text = '0%'
        left_caption = _loc('CAPTION_VEHICLE_XP', 'Vehicle XP')
        right_text = _format_percent(unlocked_steps, total_steps)
        right_caption = _loc('CAPTION_TOTAL_XP', 'Total XP')
        bar_max_value = total_steps
        markers = []

    return _make_mode(
        MODE_TIER11_UPGRADES,
        _loc('MODE_UPGRADES', 'Upgrades'),
        bar_max_value,
        primary_value,
        secondary_value,
        left_text,
        left_caption,
        right_text,
        right_caption,
        markers=markers,
        completed_value=completed_value,
        side_counter_text='{0}/{1}'.format(unlocked_steps, total_steps),
        side_counter_caption=_loc('CAPTION_UNLOCKED', 'Unlocked'),
    )


def _build_elite_mode(data, elite_mode=ELITE_MODE_ON):
    if elite_mode == ELITE_MODE_OFF:
        return None

    tech_tree = dict(data.get('tech_tree') or {})
    field_mods = data.get('field_mods') or {}
    vehicle_data = data.get('vehicle') or {}
    tech_tree['vehicle_tier'] = vehicle_data.get('tier')
    elite_progression = data.get('elite_progression') or {}
    if not _is_elite_progression_mode_enabled(tech_tree, elite_progression):
        return None

    include_t11_cosmetics = _is_tier11_mode_enabled(field_mods, tech_tree)
    if elite_mode == ELITE_MODE_CUSTOMIZATION_ONLY and not include_t11_cosmetics:
        return None

    progress_cap = _elite_total_required_xp()
    if elite_mode == ELITE_MODE_CUSTOMIZATION_ONLY:
        progress_cap = _elite_customization_total_required_xp()

    current_level = _to_int(elite_progression.get('current_level'))
    if current_level is None:
        return None

    current_level = max(1, min(current_level, ELITE_MAX_LEVEL))
    current_xp_value = _to_int(elite_progression.get('current_xp'))
    current_xp = max(0, current_xp_value or 0)
    next_level_xp = _to_int(elite_progression.get('next_level_xp'))
    remaining_xp = _to_int(elite_progression.get('remaining_xp'))
    if current_level >= ELITE_MAX_LEVEL:
        total_progress = _elite_total_required_xp()
        current_xp = _elite_required_xp_for_level(ELITE_MAX_LEVEL - 1)
        next_level_xp = current_xp
    else:
        if next_level_xp is None or next_level_xp <= 0:
            next_level_xp = _elite_required_xp_for_level(current_level)
        if current_xp_value is None and remaining_xp is not None and next_level_xp > 0:
            current_xp = min(remaining_xp, next_level_xp)
        current_xp = min(current_xp, next_level_xp)
        total_progress = min(
            _elite_total_required_xp(),
            _elite_cumulative_xp_to_level(current_level) + current_xp,
        )
    total_progress = min(progress_cap, total_progress)

    return _make_mode(
        MODE_ELITE_PROGRESSION,
        _loc('MODE_ELITE', 'Elite'),
        progress_cap,
        0.0,
        0.0,
        _loc('ELITE_LEVEL_FORMAT', 'Elite Level {level}', level=current_level),
        _loc('ELITE_BASE_XP_PROGRESS_FORMAT', '{current} / {target} Base XP', current=current_xp, target=next_level_xp),
        _format_percent(total_progress, progress_cap),
        _loc('CAPTION_BASE_XP', 'Base XP'),
        markers=_build_elite_markers(
            total_progress,
            include_badges=(elite_mode == ELITE_MODE_ON),
            include_t11_cosmetics=include_t11_cosmetics,
        ),
        completed_value=total_progress,
        counter_layout='elite_status',
        bar_fill_mode='completed_only',
    )


def _build_elite_markers(current_total_xp, include_badges=True, include_t11_cosmetics=False):
    markers = []
    if include_badges:
        for marker_key, marker_label_key, marker_default_name, level in ELITE_COLOR_MARKERS:
            if level <= 1:
                continue
            position_value = _elite_cumulative_xp_to_level(level)
            if level >= ELITE_MAX_LEVEL:
                position_value = _elite_total_required_xp()
            markers.append({
                'id': 'elite_{0}'.format(marker_key),
                'positionValue': position_value,
                'costXp': position_value,
                'itemType': 'unknown',
                'name': _loc(marker_label_key, marker_default_name),
                'level': level,
                'label': '',
                'iconCacheKey': 'elite:{0}'.format(marker_key),
                'hideTooltipIcon': False,
                'hideBarIcon': False,
                'markerState': 'completed' if position_value <= current_total_xp else 'locked',
                'singleProgressRow': True,
                'progressLabel': _loc('CAPTION_BASE_XP', 'Base XP'),
                'isAvailable': True,
            })

    if include_t11_cosmetics:
        for marker_key, marker_label_key, marker_default_name, level in ELITE_T11_COSMETIC_MARKERS:
            position_value = _elite_cumulative_xp_to_level(level)
            markers.append({
                'id': 'elite_t11_{0}'.format(marker_key),
                'positionValue': position_value,
                'costXp': position_value,
                'itemType': 'unknown',
                'name': _loc(marker_label_key, marker_default_name),
                'level': level,
                'label': '',
                'iconCacheKey': 'elite:t11_cosmetic',
                'hideTooltipIcon': False,
                'hideBarIcon': False,
                'markerState': 'completed' if position_value <= current_total_xp else 'locked',
                'singleProgressRow': True,
                'progressLabel': _loc('CAPTION_BASE_XP', 'Base XP'),
                'isAvailable': True,
            })
    return markers


def _elite_total_required_xp():
    return _elite_cumulative_xp_to_level(ELITE_MAX_LEVEL)


def _elite_customization_total_required_xp():
    max_marker_level = max([level for _, _, _, level in ELITE_T11_COSMETIC_MARKERS] or [ELITE_MAX_LEVEL])
    return _elite_cumulative_xp_to_level(max_marker_level)


def _elite_required_xp_for_level(level):
    current_level = _to_int(level) or 0
    if current_level >= ELITE_MAX_LEVEL:
        return 0

    for start_level, next_level, xp_required in ELITE_LEVEL_XP_SEGMENTS:
        if current_level >= start_level and current_level < next_level:
            return xp_required

    return 0


def _elite_cumulative_xp_to_level(level):
    target_level = _to_int(level) or 0
    if target_level <= 1:
        return 0
    if target_level > ELITE_MAX_LEVEL:
        target_level = ELITE_MAX_LEVEL

    total_xp = 0
    for start_level, next_level, xp_required in ELITE_LEVEL_XP_SEGMENTS:
        if target_level <= start_level:
            break
        total_xp += max(0, min(target_level, next_level) - start_level) * xp_required
    return total_xp


def _build_research_marker(item):
    blueprint_count = item.get('blueprint_count')
    blueprint_total = item.get('blueprint_total')
    blueprint_discount_percent = item.get('blueprint_discount_percent')

    return {
        'id': 'unlock_{0}'.format(item['intcd']),
        'positionValue': item['xp_cost'],
        'costXp': item['xp_cost'],
        'itemType': item['item_type'],
        'progressLabel': _loc('CAPTION_VEHICLE_XP', 'Vehicle XP'),
        'totalProgressLabel': _loc('CAPTION_TOTAL_XP', 'Total XP'),
        'isAvailable': item.get('is_available', True),
        'missingPrereqNames': item.get('missing_prereq_names', []),
        'missingPrereqs': item.get('missing_prereqs', []),
        'name': item.get('name'),
        'blueprintCount': blueprint_count,
        'blueprintTotal': blueprint_total,
        'blueprintDiscountPercent': blueprint_discount_percent,
        'blueprintTooltipText': _build_blueprint_tooltip_text(
            blueprint_count,
            blueprint_total,
            blueprint_discount_percent,
        ),
    }


def _build_blueprint_tooltip_text(count, total, discount_percent):
    if count is None or total is None or discount_percent is None:
        return None

    return _loc(
        'BLUEPRINT_TOOLTIP_FORMAT',
        '<count>{count}</count>/<total>{total}</total> Blueprints (<discount>{discount}%</discount> discount)',
        count=count,
        total=total,
        discount=discount_percent,
    )


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
            'showBarLabel': True,
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


def _build_t11_markers(display_layout, vehicle_xp, total_xp):
    completed_minor_nodes = display_layout['completed_minor_nodes']
    completed_major_nodes = display_layout['completed_major_nodes']
    remaining_minor_nodes = display_layout['remaining_minor_nodes']
    remaining_major_nodes = display_layout['remaining_major_nodes']
    remaining_final_nodes = display_layout['remaining_final_nodes']
    remaining_minor_count = display_layout['remaining_minor_count']
    remaining_major_count = display_layout['remaining_major_count']
    remaining_final_count = display_layout['remaining_final_count']
    markers = _build_t11_completed_markers(completed_minor_nodes, completed_major_nodes)
    completed_cost = display_layout['completed_cost']

    if remaining_minor_count > 0:
        minor_marker = _make_t11_marker(
            marker_id='t11_minor_upgrade',
            position_value=completed_cost + 10000,
            cost_xp=10000,
            name=_loc('UPGRADE_MINOR', 'Minor Upgrade'),
            remaining_cost=10000,
            vehicle_xp=vehicle_xp,
            total_xp=total_xp,
            action_node=_first_t11_action_node(remaining_minor_nodes),
        )
        minor_marker['itemType'] = 'minor_upgrade'
        minor_marker['barItemType'] = 'minor_upgrade'
        minor_marker['iconPaths'] = []
        minor_marker['iconCacheKey'] = 'minor_upgrade'
        minor_marker['hideTooltipIcon'] = False
        minor_marker['name'] = _loc('UPGRADE_MINOR', 'Minor Upgrade')
        markers.append(minor_marker)

    if remaining_major_count > 0:
        major_marker = _make_t11_marker(
            marker_id='t11_major_upgrade',
            position_value=completed_cost + 20000,
            cost_xp=20000,
            name=_loc('UPGRADE_MAJOR', 'Major Upgrade'),
            remaining_cost=20000,
            vehicle_xp=vehicle_xp,
            total_xp=total_xp,
            action_node=_first_t11_action_node(remaining_major_nodes),
        )
        major_marker['itemType'] = 'major_upgrade'
        major_marker['barItemType'] = 'major_upgrade'
        major_marker['iconPaths'] = []
        major_marker['iconCacheKey'] = 'major_upgrade'
        major_marker['hideTooltipIcon'] = False
        major_marker['name'] = _loc('UPGRADE_MAJOR', 'Major Upgrade')
        markers.append(major_marker)

    if remaining_final_count > 0:
        final_node = _first_t11_action_node(remaining_final_nodes)
        final_available = remaining_minor_count == 0 and remaining_major_count == 0
        if final_available:
            final_state = _resolve_remaining_cost_marker_state(25000, vehicle_xp, total_xp)
        else:
            final_state = 'locked'
        final_marker = {
            'id': 't11_final_upgrade',
            'positionValue': display_layout['total_cost'],
            'costXp': 25000,
            'itemType': 'unknown',
            'isAvailable': final_available,
            'missingPrereqNames': [_loc('UPGRADE_ALL_OTHER_NODES', 'All Other Nodes')] if not final_available else [],
            'missingPrereqs': [],
            'name': _resolve_t11_action_node_name(final_node, _loc('UPGRADE_FINAL', 'Final Upgrade')),
            'label': '',
            'hideTooltipIcon': True,
            'markerState': final_state,
        }
        markers.append(_apply_t11_bar_icon(_apply_t11_action_metadata(final_marker, final_node), True))

    return markers


def _build_t11_completed_markers(completed_minor_count, completed_major_count):
    markers = []
    var_minor_nodes = completed_minor_count or []
    var_major_nodes = completed_major_count or []

    for index in range(len(var_minor_nodes)):
        minor_node = var_minor_nodes[index]
        markers.append(_make_t11_completed_marker(
            marker_id='t11_completed_minor_{0}'.format(index + 1),
            position_value=(index + 1) * 10000,
            cost_xp=10000,
            name=_resolve_t11_action_node_name(minor_node, _loc('UPGRADE_MINOR', 'Minor Upgrade')),
            action_node=minor_node,
        ))

    completed_minor_cost = len(var_minor_nodes) * 10000
    for index in range(len(var_major_nodes)):
        major_node = var_major_nodes[index]
        markers.append(_make_t11_completed_marker(
            marker_id='t11_completed_major_{0}'.format(index + 1),
            position_value=completed_minor_cost + ((index + 1) * 20000),
            cost_xp=20000,
            name=_resolve_t11_action_node_name(major_node, _loc('UPGRADE_MAJOR', 'Major Upgrade')),
            action_node=major_node,
        ))

    return markers


def _build_t11_display_layout(field_mods):
    researched = field_mods.get('t11_bucket_researched') or {}
    unresearched = field_mods.get('t11_bucket_unresearched') or {}
    researched_action_nodes = field_mods.get('t11_action_nodes_researched') or []

    unresearched_action_nodes = field_mods.get('t11_action_nodes_unresearched') or []
    completed_minor_count = _to_int(researched.get('small_10k')) or 0
    completed_major_count = _to_int(researched.get('big_20k')) or 0
    remaining_minor_count = _to_int(unresearched.get('small_10k')) or 0
    remaining_major_count = _to_int(unresearched.get('big_20k')) or 0
    remaining_final_count = _to_int(unresearched.get('big_25k')) or 0
    completed_minor_nodes = _pad_t11_action_nodes(
        _sort_t11_action_nodes_by_category(_filter_t11_action_nodes(researched_action_nodes, 10000)),
        completed_minor_count,
        _loc('UPGRADE_MINOR', 'Minor Upgrade')
    )
    completed_major_nodes = _pad_t11_action_nodes(
        _sort_t11_action_nodes_by_category(_filter_t11_action_nodes(researched_action_nodes, 20000)),
        completed_major_count,
        _loc('UPGRADE_MAJOR', 'Major Upgrade')
    )
    remaining_minor_nodes = _sort_t11_action_nodes_by_category(
        _filter_t11_action_nodes(unresearched_action_nodes, 10000)
    )
    remaining_major_nodes = _sort_t11_action_nodes_by_category(
        _filter_t11_action_nodes(unresearched_action_nodes, 20000)
    )
    remaining_final_nodes = _sort_t11_action_nodes_by_category(
        _filter_t11_action_nodes(unresearched_action_nodes, 25000)
    )
    completed_minor_cost = (_to_int(researched.get('small_10k')) or 0) * 10000
    completed_major_cost = (_to_int(researched.get('big_20k')) or 0) * 20000
    remaining_minor_cost = remaining_minor_count * 10000
    remaining_major_cost = remaining_major_count * 20000
    remaining_final_cost = remaining_final_count * 25000
    completed_cost = completed_minor_cost + completed_major_cost
    total_cost = completed_cost + remaining_minor_cost + remaining_major_cost + remaining_final_cost

    return {
        'completed_minor_count': completed_minor_count,
        'completed_major_count': completed_major_count,
        'completed_minor_nodes': completed_minor_nodes,
        'completed_major_nodes': completed_major_nodes,
        'remaining_minor_nodes': remaining_minor_nodes,
        'remaining_major_nodes': remaining_major_nodes,
        'remaining_final_nodes': remaining_final_nodes,
        'remaining_minor_count': remaining_minor_count,
        'remaining_major_count': remaining_major_count,
        'remaining_final_count': remaining_final_count,
        'completed_minor_cost': completed_minor_cost,
        'completed_major_cost': completed_major_cost,
        'completed_cost': completed_cost,
        'remaining_minor_cost': remaining_minor_cost,
        'remaining_major_cost': remaining_major_cost,
        'remaining_final_cost': remaining_final_cost,
        'remaining_cost': remaining_minor_cost + remaining_major_cost + remaining_final_cost,
        'total_cost': total_cost,
    }


def _make_t11_marker(
    marker_id,
    position_value,
    cost_xp,
    name,
    remaining_cost,
    vehicle_xp,
    total_xp,
    action_node=None,
    show_bar_icon=True,
):
    marker = {
        'id': marker_id,
        'positionValue': position_value,
        'costXp': cost_xp,
        'itemType': 'unknown',
        'isAvailable': True,
        'name': name,
        'label': '',
        'hideTooltipIcon': True,
        'markerState': _resolve_remaining_cost_marker_state(remaining_cost, vehicle_xp, total_xp),
    }
    marker = _apply_t11_action_metadata(marker, action_node)
    return _apply_t11_bar_icon(marker, show_bar_icon)


def _make_t11_completed_marker(marker_id, position_value, cost_xp, name, action_node=None, show_bar_icon=True):
    marker = {
        'id': marker_id,
        'positionValue': position_value,
        'costXp': cost_xp,
        'itemType': 'unknown',
        'isAvailable': True,
        'name': name,
        'label': '',
        'hideTooltipIcon': True,
        'markerState': 'completed',
    }
    marker = _apply_t11_action_metadata(marker, action_node)
    return _apply_t11_bar_icon(marker, show_bar_icon)


def _filter_t11_action_nodes(nodes, xp_cost):
    filtered = []
    for node in nodes:
        if _to_int((node or {}).get('xp_cost')) == xp_cost:
            filtered.append(node)
    return filtered


def _normalize_t11_category(category):
    if not category:
        return ''
    normalized = u'{0}'.format(category).strip().lower()
    if normalized == 'reconnaissance':
        return 'scouting'
    if normalized == 'mechanic':
        return 'mechanics'
    return normalized


def _sort_t11_action_nodes_by_category(nodes):
    if not nodes:
        return []

    def sort_key(node):
        normalized_category = _normalize_t11_category((node or {}).get('category'))
        return (
            T11_CATEGORY_SORT_ORDER.get(normalized_category, len(T11_CATEGORY_SORT_ORDER)),
            normalized_category,
            _resolve_t11_action_node_name(node, ''),
        )

    return sorted(nodes, key=sort_key)


def _pad_t11_action_nodes(nodes, expected_count, fallback_name):
    padded = list(nodes or [])
    expected = max(0, _to_int(expected_count) or 0)
    while len(padded) < expected:
        padded.append({'name': fallback_name})
    return padded[:expected]


def _first_t11_action_node(nodes):
    return nodes[0] if nodes else None


def _resolve_t11_action_node_name(action_node, fallback_name):
    if action_node is None:
        return fallback_name
    for key in ('tooltip_title', 'name', 'localized_name', 'ui_localized_name', 'image_name', 'loc_name', 'tech_name'):
        value = action_node.get(key)
        if value:
            return value
    return fallback_name


def _build_t11_action_icon_paths(action_node):
    if action_node is None:
        return []

    bucket = action_node.get('bucket')
    category = action_node.get('category')
    image_name = action_node.get('image_name')
    if not image_name:
        return []

    ordered_branches = []
    if bucket == 'small_10k':
        ordered_branches.extend(['special'] if category == 'special' else [])
        ordered_branches.extend(['common', 'special'])
    elif bucket == 'big_20k':
        ordered_branches.append('major')
    elif bucket == 'big_25k':
        ordered_branches.append('final')

    for branch in ('common', 'major', 'final', 'special'):
        if branch not in ordered_branches:
            ordered_branches.append(branch)

    paths = []
    for branch in ordered_branches:
        for size in ('small', 'large'):
            paths.append(
                '../maps/icons/skillTree/tree/perks/{0}/skills/{1}/{2}.png'.format(
                    branch,
                    size,
                    image_name,
                )
            )
            paths.append(
                'img://gui/maps/icons/skillTree/tree/perks/{0}/skills/{1}/{2}.png'.format(
                    branch,
                    size,
                    image_name,
                )
            )

    for size in ('120x80', '192x120'):
        paths.append(
            '../maps/icons/vehPostProgression/actionItems/modificationWithFeature/{0}/{1}.png'.format(
                size,
                image_name,
            )
        )
        paths.append(
            'img://gui/maps/icons/vehPostProgression/actionItems/modificationWithFeature/{0}/{1}.png'.format(
                size,
                image_name,
            )
        )

    return paths


def _apply_t11_action_metadata(marker, action_node):
    if action_node is None:
        return marker

    image_name = action_node.get('image_name')
    category = _normalize_t11_category(action_node.get('category'))
    if category:
        marker['itemType'] = category
    icon_paths = _build_t11_action_icon_paths(action_node)
    if icon_paths:
        marker['iconPaths'] = icon_paths
        if category:
            marker['iconCacheKey'] = 't11:{0}:{1}'.format(category, image_name)
        else:
            marker['iconCacheKey'] = 't11:{0}'.format(image_name)
        marker['hideTooltipIcon'] = False
    return marker


def _resolve_t11_bar_item_type(marker):
    category = _normalize_t11_category(marker.get('itemType'))
    if category in ('firepower', 'survivability', 'mobility', 'scouting', 'stealth'):
        return category
    return ''


def _apply_t11_bar_icon(marker, show_bar_icon=True):
    bar_item_type = _resolve_t11_bar_item_type(marker)
    if not show_bar_icon:
        marker['hideBarIcon'] = True
        return marker

    if bar_item_type:
        marker['barItemType'] = bar_item_type

    return marker


def _resolve_field_mod_marker_state(level, current_level, remaining_cost, vehicle_xp, total_xp):
    if level <= current_level:
        return 'completed'
    return _resolve_remaining_cost_marker_state(remaining_cost, vehicle_xp, total_xp)


def _resolve_remaining_cost_marker_state(remaining_cost, vehicle_xp, total_xp):
    if remaining_cost <= max(0, vehicle_xp):
        return 'reachable_vehicle'
    if remaining_cost <= max(0, total_xp):
        return 'reachable_total'
    return 'locked'


def _sum_t11_bucket_costs(buckets):
    if buckets is None:
        return 0

    return (
        (_to_int(buckets.get('small_10k')) or 0) * 10000
        + (_to_int(buckets.get('big_20k')) or 0) * 20000
        + (_to_int(buckets.get('big_25k')) or 0) * 25000
    )


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
        completed_value=0.0,
        side_counter_text='',
        side_counter_caption='',
        counter_layout='',
        bar_fill_mode=''):
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
        'sideCounterText': side_counter_text,
        'sideCounterCaption': side_counter_caption,
        'markers': markers or [],
        'counterLayout': counter_layout,
        'barFillMode': bar_fill_mode,
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
    if not field_mods.get('is_veh_skill_tree'):
        return False
    total_steps = _to_int(field_mods.get('total_steps')) or 0
    return total_steps > 0


def _is_elite_progression_mode_enabled(tech_tree, elite_progression):
    vehicle_tier = _to_int(tech_tree.get('vehicle_tier'))
    if not tech_tree.get('is_elite'):
        return False
    if vehicle_tier is not None and vehicle_tier < 5:
        return False
    if not elite_progression.get('available'):
        return False
    return _to_int(elite_progression.get('current_level')) is not None


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
