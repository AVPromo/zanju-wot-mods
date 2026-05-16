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
from gui.impl import backport
try:
    from gui.impl.gen.resources import R
except Exception:
    R = None
try:
    from gui.prestige import prestige_helpers as _prestige_helpers
except Exception:
    _prestige_helpers = None
from gui.Scaleform.framework import ScopeTemplates, ViewSettings, g_entitiesFactories
from gui.Scaleform.framework.entities.View import View
from gui.Scaleform.framework.managers.loaders import SFViewLoadParams
from gui.shared.gui_items import GUI_ITEM_TYPE_NAMES
from gui.shared.personality import ServicesLocator
from helpers import dependency
from helpers import i18n
from items import getTypeOfCompactDescr
from .constants import (
    MOD_CONFIG_DIR_NAME,
    MOD_ID,
    MOD_VERSION,
    SCALEFORM_FILE_NAME,
    SCALEFORM_VIEW_ALIAS,
    _HANGAR_VIEW_ALIASES,
    _NAVIGATING_ROUTE_PREFIX,
    _TIER_FIELD_MOD_RULES,
    _UNLOCK_MARKER_TYPE_BY_GUI_NAME,
    _VISIBLE_ROUTE_PREFIX,
    _VISIBILITY_PROBE_DELAY,
)
from .localization import get_text as _loc
from .localization import make_tooltip as _loc_tooltip
from .localization import set_language_override as _set_language_override
from .scaleform_modes import build_scaleform_view_payload
from skeletons.gui.app_loader import GuiGlobalSpaceID as SPACE_ID
from skeletons.gui.shared import IItemsCache

_logger = logging.getLogger('zanju.researchprogressbar')
_lobby_state_logger = logging.getLogger('gui.lobby_state_machine.lobby_state_machine')

try:
    _STRING_TYPES = (basestring,)
except NameError:
    _STRING_TYPES = (str,)

# ---------------------------------------------------------------------------
# Config defaults — overridden by _load_config() at startup
# ---------------------------------------------------------------------------
_config = {
    'enabled': True,
    'language': 'auto',
    'showTechTree': True,
    'showFieldMods': True,
    'showUpgrades': True,
    'eliteMode': 'on',
    'scaleformPrototypeEnabled': True,
}

_CONFIG_PERSISTED_KEYS = (
    'enabled',
    'language',
    'showTechTree',
    'showFieldMods',
    'showUpgrades',
    'eliteMode',
    'scaleformPrototypeEnabled',
)

_MODS_SETTINGS_USER_KEYS = (
    'enabled',
    'showTechTree',
    'showFieldMods',
    'showUpgrades',
    'showEliteProgress',
)

_mods_settings_sync_in_progress = False

_ELITE_MODE_ON = 'on'
_ELITE_MODE_CUSTOMIZATION_ONLY = 'customization_only'
_ELITE_MODE_OFF = 'off'
_ELITE_MODE_VALUES = (
    _ELITE_MODE_ON,
    _ELITE_MODE_CUSTOMIZATION_ONLY,
    _ELITE_MODE_OFF,
)
_ELITE_MODE_INDEX_BY_VALUE = dict(
    (value, index) for index, value in enumerate(_ELITE_MODE_VALUES)
)
_MODS_SETTINGS_SCHEMA_VERSION = 6

_ROUTE_PATH_RE = re.compile(r'\((subScope/[^)]*)\)')

_T11_UI_NAME_HOOK_SPECS = (
    ('gui.impl.lobby.vehicle_hub.sub_presenters.veh_skill_tree.utils', 'fillNodeModel'),
    ('gui.impl.lobby.veh_skill_tree.utils', 'fillNodeModel'),
)

_t11_ui_name_cache = {}
_t11_ui_name_hook_records = []
_LAYOUT_REFRESH_VIEW_ALIASES = frozenset((
    'lobbyMenu',
    'settingsWindow',
    'simpleDialog',
))
_SCALEFORM_DISPOSE_SUB_VIEW_ALIASES = frozenset((
    'vehicleHub',
))
_SCALEFORM_DISPOSE_ROUTE_PREFIXES = (
    'subScope/subLayer/vehicleHub',
)


def _get_config_path():
    import os
    return os.path.join('mods', 'configs', MOD_CONFIG_DIR_NAME, 'config.json')


def _load_config():
    import io
    import json
    import os
    try:
        path = _get_config_path()
        if os.path.isfile(path):
            with io.open(path, 'r', encoding='utf-8') as fh:
                loaded = json.load(fh)
            if isinstance(loaded, dict):
                _config.update(loaded)
            _normalize_display_config()
            _logger.info('Config loaded from %s', path)
    except Exception:
        _logger.exception('Failed to load config, using defaults')
    _normalize_display_config()


def _normalize_elite_mode(value):
    if isinstance(value, bool):
        return _ELITE_MODE_ON if value else _ELITE_MODE_OFF
    if isinstance(value, Integral):
        index = int(value)
        if index >= 0 and index < len(_ELITE_MODE_VALUES):
            return _ELITE_MODE_VALUES[index]
        return _ELITE_MODE_ON
    if isinstance(value, _STRING_TYPES):
        normalized = value.strip().lower().replace('-', '_').replace(' ', '_')
        if normalized in _ELITE_MODE_INDEX_BY_VALUE:
            return normalized
        if normalized in ('customization', 'customisation', 'cosmetics_only'):
            return _ELITE_MODE_CUSTOMIZATION_ONLY
        if normalized in ('true', 'enabled'):
            return _ELITE_MODE_ON
        if normalized in ('false', 'disabled'):
            return _ELITE_MODE_OFF
    return _ELITE_MODE_ON


def _normalize_display_config():
    legacy_elite_value = _config.get('showEliteProgress', _config.get('eliteMode', _ELITE_MODE_ON))
    language = _config.get('language', 'auto')
    if not isinstance(language, _STRING_TYPES):
        language = 'auto'
    language = language.strip().lower().replace('-', '_') or 'auto'
    if language in ('client', 'default', 'system'):
        language = 'auto'
    _config['language'] = language
    for key in ('enabled', 'showTechTree', 'showFieldMods', 'showUpgrades'):
        _config[key] = bool(_config.get(key, True))
    _config['eliteMode'] = _normalize_elite_mode(_config.get('eliteMode', legacy_elite_value))
    _set_language_override(_config.get('language', 'auto'))


def _build_mode_preferences():
    return {
        'showResearch': bool(_config.get('showTechTree', True)),
        'showFieldMods': bool(_config.get('showFieldMods', True)),
        'showUpgrades': bool(_config.get('showUpgrades', True)),
        'eliteMode': _normalize_elite_mode(_config.get('eliteMode', _ELITE_MODE_ON)),
    }


def _save_config():
    import io
    import json
    import os

    path = _get_config_path()
    data = {}
    try:
        if os.path.isfile(path):
            with io.open(path, 'r', encoding='utf-8') as fh:
                existing = json.load(fh)
            if isinstance(existing, dict):
                data.update(existing)
    except Exception:
        _logger.exception('Failed to read existing config before save, rewriting %s', path)
        data = {}

    try:
        directory = os.path.dirname(path)
        if directory and not os.path.isdir(directory):
            os.makedirs(directory)

        data['configVersion'] = data.get('configVersion', 1)
        data.pop('showEliteProgress', None)
        for key in _CONFIG_PERSISTED_KEYS:
            data[key] = _config.get(key)

        payload = json.dumps(data, indent=4, sort_keys=False)
        if not payload.endswith('\n'):
            payload += '\n'

        with io.open(path, 'w', encoding='utf-8') as fh:
            fh.write(payload)

        _logger.info('Config saved to %s', path)
    except Exception:
        _logger.exception('Failed to save config to %s', path)


def _build_mod_settings_state():
    return {
        'enabled': bool(_config.get('enabled', True)),
        'showTechTree': bool(_config.get('showTechTree', True)),
        'showFieldMods': bool(_config.get('showFieldMods', True)),
        'showUpgrades': bool(_config.get('showUpgrades', True)),
        'showEliteProgress': _ELITE_MODE_INDEX_BY_VALUE.get(
            _normalize_elite_mode(_config.get('eliteMode', _ELITE_MODE_ON)),
            0,
        ),
    }


def _mods_settings_native(value):
    if type(value).__name__ == 'unicode':
        return value.encode('utf-8')
    if isinstance(value, list):
        return [_mods_settings_native(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_mods_settings_native(item) for item in value)
    if isinstance(value, dict):
        converted = {}
        try:
            items = value.iteritems()
        except AttributeError:
            items = value.items()
        for key, item in items:
            converted[_mods_settings_native(key)] = _mods_settings_native(item)
        return converted
    return value


def _build_mod_settings_template():
    settings = _build_mod_settings_state()
    return _mods_settings_native({
        'modDisplayName': _loc('MOD_NAME', "Zanju's Research Progress Bar"),
        'settingsVersion': _MODS_SETTINGS_SCHEMA_VERSION,
        'enabled': settings['enabled'],
        'column1': [
            {
                'type': 'CheckBox',
                'text': _loc('SETTING_RESEARCH', 'Research'),
                'tooltip': _loc_tooltip(
                    'TOOLTIP_RESEARCH_HEADER',
                    'TOOLTIP_RESEARCH_BODY',
                    'Research',
                    'Show XP progress toward the next researchable module or vehicle.',
                ),
                'value': settings['showTechTree'],
                'varName': 'showTechTree',
            },
            {
                'type': 'CheckBox',
                'text': _loc('SETTING_FIELD_MODS', 'Field Mods'),
                'tooltip': _loc_tooltip(
                    'TOOLTIP_FIELD_MODS_HEADER',
                    'TOOLTIP_FIELD_MODS_BODY',
                    'Field Mods',
                    'Show field modification progress for elite vehicles that support field modifications.',
                ),
                'value': settings['showFieldMods'],
                'varName': 'showFieldMods',
            },
            {
                'type': 'CheckBox',
                'text': _loc('SETTING_UPGRADES', 'Upgrades'),
                'tooltip': _loc_tooltip(
                    'TOOLTIP_UPGRADES_HEADER',
                    'TOOLTIP_UPGRADES_BODY',
                    'Upgrades',
                    'Show tier XI upgrade tree progress.',
                ),
                'value': settings['showUpgrades'],
                'varName': 'showUpgrades',
            },
            {
                'type': 'RadioButtonGroup',
                'text': _loc('SETTING_ELITE', 'Elite'),
                'tooltip': _loc_tooltip(
                    'TOOLTIP_ELITE_HEADER',
                    'TOOLTIP_ELITE_BODY',
                    'Elite',
                    '<b>On</b>: Show elite badges and tier XI customization elements.\n'
                    '<b>Customization only</b>: Show tier XI customization elements and hide elite badges.\n'
                    '<b>Off</b>: Hide elite progress entirely.',
                ),
                'options': [
                    {'label': _loc('SETTING_ELITE_OPTION_ON', 'On')},
                    {'label': _loc('SETTING_ELITE_OPTION_CUSTOMIZATION_ONLY', 'Customization only')},
                    {'label': _loc('SETTING_ELITE_OPTION_OFF', 'Off')},
                ],
                'value': settings['showEliteProgress'],
                'varName': 'showEliteProgress',
            },
        ],
    })


def _get_mods_settings_api():
    try:
        from gui.modsSettingsApi import g_modsSettingsApi
        return g_modsSettingsApi
    except Exception:
        return None


def _on_mod_settings_changed(linkage, new_settings):
    if linkage != MOD_ID or _mods_settings_sync_in_progress:
        return
    if not isinstance(new_settings, dict):
        return

    changed_keys = []
    for key in _MODS_SETTINGS_USER_KEYS:
        if key not in new_settings:
            continue
        config_key = key
        if key == 'showEliteProgress':
            config_key = 'eliteMode'
            new_value = _normalize_elite_mode(new_settings.get(key))
        else:
            new_value = bool(new_settings.get(key))
        if _config.get(config_key) != new_value:
            _config[config_key] = new_value
            changed_keys.append(config_key)

    if not changed_keys:
        return

    _save_config()
    _logger.info('Applied ModsSettingsApi changes: %s', ', '.join(changed_keys))
    if _mod is not None:
        _mod.on_external_config_changed(
            'mods_settings_api:{0}'.format(','.join(changed_keys))
        )


def _register_mod_settings():
    global _mods_settings_sync_in_progress

    api = _get_mods_settings_api()
    if api is None:
        _logger.info('ModsSettingsApi not found; in-game settings are unavailable')
        return False

    try:
        api.setModTemplate(MOD_ID, _build_mod_settings_template(), _on_mod_settings_changed)
        _mods_settings_sync_in_progress = True
        try:
            api.updateModSettings(MOD_ID, _mods_settings_native(_build_mod_settings_state()))
        finally:
            _mods_settings_sync_in_progress = False
        _logger.info('ModsSettingsApi integration registered')
        return True
    except Exception:
        _mods_settings_sync_in_progress = False
        _logger.exception('Failed to register ModsSettingsApi integration')
        return False


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


def _safe_method_text(step, method_name):
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


def _safe_attr_text(obj, attr_name, max_len=120):
    try:
        value = getattr(obj, attr_name, None)
    except Exception as exc:
        return '<error:{0}>'.format(_safe_text(exc, 80))
    return _safe_text(value, max_len)


def _clean_text_value(value):
    if value is None:
        return None
    text = _safe_text(value, 120).strip()
    if not text:
        return None
    if text[0] == '<' and text[-1] == '>':
        return None
    return text


def _safe_method_value(obj, method_name):
    ok, value_text = _safe_method_text(obj, method_name)
    if not ok:
        return None
    return _clean_text_value(value_text)


def _resolve_localized_action_name(action):
    for method_name in ('getLocSplitNameRes', 'getLocNameRes'):
        try:
            method = getattr(action, method_name, None)
            if method is None or not callable(method):
                continue
            resource = method()
            if resource is None or not callable(resource):
                continue
            text = _clean_text_value(backport.text(resource()))
            if text:
                return text
        except Exception:
            pass
    return None


def _is_generic_t11_action_name(name_text):
    if not name_text:
        return True
    normalized = name_text.strip().lower()
    return normalized in ('modification', 'upgrade', 'research item')


def _resolve_t11_tooltip_title(identifier):
    key = _clean_text_value(identifier)
    if not key:
        return None

    if R is not None:
        try:
            text = _clean_text_value(backport.text(R.strings.veh_skill_tree.tooltips.title(key)))
            if text and text != key:
                return text
        except Exception:
            pass

    try:
        resource_key = '#veh_skill_tree:tooltips/title/{0}'.format(key)
        text = _clean_text_value(i18n.makeString(resource_key))
        if text and text not in (key, resource_key):
            return text
    except Exception:
        pass

    return None


def _resolve_t11_tooltip_title_from_candidates(*identifiers):
    seen = set()
    for identifier in identifiers:
        key = _clean_text_value(identifier)
        if not key or key in seen:
            continue
        seen.add(key)
        text = _resolve_t11_tooltip_title(key)
        if text:
            return text
    return None


def _extract_t11_action_marker_meta(step, step_id, vehicle=None):
    """Builds best-effort marker metadata from a tier-11 step.action object."""
    try:
        action = getattr(step, 'action', None)
    except Exception:
        return None

    if action is None:
        return None

    descriptor = getattr(action, '_descriptor', None)
    vehicle_int_cd = getattr(vehicle, 'intCD', None) if vehicle is not None else None
    ui_localized_name = _get_cached_t11_ui_name(vehicle_int_cd, step_id)
    localized_name = _resolve_localized_action_name(action)
    tech_name = _safe_method_value(action, 'getTechName')
    loc_name = _safe_method_value(action, 'getLocName')
    image_name = _safe_method_value(action, 'getImageName')
    slot_category = _safe_method_value(action, 'getSlotCategory')
    descriptor_name = _clean_text_value(getattr(descriptor, 'name', None))
    descriptor_loc_name = _clean_text_value(getattr(descriptor, 'locName', None))
    descriptor_image_name = _clean_text_value(getattr(descriptor, 'imgName', None))
    descriptor_categories = getattr(descriptor, 'categories', None)
    descriptor_category = None
    if descriptor_categories is not None:
        try:
            if len(descriptor_categories) > 0:
                descriptor_category = _clean_text_value(descriptor_categories[0])
        except Exception:
            try:
                for category_value in descriptor_categories:
                    descriptor_category = _clean_text_value(category_value)
                    break
            except Exception:
                descriptor_category = _clean_text_value(descriptor_categories)

    tooltip_title = _resolve_t11_tooltip_title_from_candidates(
        ui_localized_name,
        loc_name,
        descriptor_loc_name,
        image_name,
        descriptor_image_name,
    )

    resolved_name = tooltip_title or localized_name or ui_localized_name
    if _is_generic_t11_action_name(resolved_name):
        resolved_name = (
            image_name
            or descriptor_image_name
            or loc_name
            or tech_name
            or descriptor_loc_name
            or descriptor_name
        )

    return {
        'step_id': step_id,
        'name': resolved_name,
        'tooltip_title': tooltip_title,
        'ui_localized_name': ui_localized_name,
        'localized_name': localized_name,
        'loc_name': loc_name or descriptor_loc_name,
        'tech_name': tech_name or descriptor_name,
        'image_name': image_name or descriptor_image_name,
        'slot_category': slot_category,
        'category': descriptor_category,
    }


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

    try:
        return int(value)
    except Exception:
        return None


def _mapping_value(mapping, key):
    if mapping is None or key is None:
        return None

    candidates = [key]
    try:
        candidates.append(str(key))
    except Exception:
        pass

    candidate = None
    for candidate in candidates:
        try:
            value = mapping.get(candidate)
        except Exception:
            value = None
        if value is not None:
            return value

        try:
            return mapping[candidate]
        except Exception:
            pass

    return None


def _collect_int_attr_candidates(objects, attr_names):
    values = []
    obj = None
    for obj in objects:
        value = _first_int_attr(obj, attr_names)
        if value is not None:
            values.append(value)
    return values


def _extract_sequence_ints(value, max_items):
    items = []
    if value is None or max_items <= 0 or isinstance(value, _STRING_TYPES):
        return items

    try:
        item_count = len(value)
    except Exception:
        return items

    limit = min(item_count, max_items)
    index = 0
    while index < limit:
        try:
            item = value[index]
        except Exception:
            break
        item = _to_int_or_none(item)
        if item is not None:
            items.append(item)
        index += 1
    return items


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


def _coerce_int_or_none(value):
    direct = _to_int_or_none(value)
    if direct is not None:
        return direct

    text = _clean_text_value(value)
    if text is None:
        return None

    try:
        return int(text)
    except Exception:
        return None


def _get_current_vehicle_int_cd():
    try:
        vehicle = g_currentVehicle.item
    except Exception:
        vehicle = None

    if vehicle is not None:
        return getattr(vehicle, 'intCD', None)
    return None


def _looks_like_t11_node_model(value):
    if value is None:
        return False
    return callable(getattr(value, 'getLocalizationName', None)) and callable(getattr(value, 'getId', None))


def _extract_t11_step_id(value):
    if value is None:
        return None

    step_id = _coerce_int_or_none(value)
    if step_id is not None:
        return step_id

    for method_name in ('getID', 'getId'):
        method = getattr(value, method_name, None)
        if callable(method):
            step_id = _coerce_int_or_none(method())
            if step_id is not None:
                return step_id

    for attr_name in ('stepID', 'stepId', 'step_id', 'id'):
        step_id = _coerce_int_or_none(getattr(value, attr_name, None))
        if step_id is not None:
            return step_id

    return None


def _normalize_t11_ui_step_id(vehicle_int_cd, step_id):
    vehicle_key = _coerce_int_or_none(vehicle_int_cd)
    step_key = _coerce_int_or_none(step_id)
    if vehicle_key is None or step_key is None:
        return step_key

    vehicle_text = str(vehicle_key)
    step_text = str(step_key)
    if step_text.startswith(vehicle_text) and len(step_text) > len(vehicle_text):
        suffix = step_text[len(vehicle_text):]
        try:
            normalized = int(suffix)
        except Exception:
            normalized = None
        if normalized is not None and normalized > 0:
            return normalized

    return step_key


def _get_cached_t11_ui_name(vehicle_int_cd, step_id):
    vehicle_key = _coerce_int_or_none(vehicle_int_cd)
    step_key = _normalize_t11_ui_step_id(vehicle_int_cd, step_id)
    if vehicle_key is None or step_key is None:
        return None
    return _t11_ui_name_cache.get((vehicle_key, step_key))


def _cache_t11_ui_name(vehicle_int_cd, step_id, localization_name, source_name):
    vehicle_key = _coerce_int_or_none(vehicle_int_cd)
    step_key = _normalize_t11_ui_step_id(vehicle_int_cd, step_id)
    name_text = _clean_text_value(localization_name)
    if vehicle_key is None or step_key is None or not name_text or _is_generic_t11_action_name(name_text):
        return False

    cache_key = (vehicle_key, step_key)
    previous = _t11_ui_name_cache.get(cache_key)
    if previous == name_text:
        return False

    _t11_ui_name_cache[cache_key] = name_text
    if _mod is not None and getattr(_mod, '_active', False):
        _mod._schedule_update('tier11_ui_name_capture')
    return True


def _capture_t11_ui_name_from_fill_node_model(args, kwargs, source_name):
    node_model = None
    step_id = None

    for value in list(args) + list(kwargs.values()):
        if node_model is None and _looks_like_t11_node_model(value):
            node_model = value
        if step_id is None:
            step_id = _extract_t11_step_id(value)

    if node_model is None:
        return False

    if step_id is None:
        step_id = _extract_t11_step_id(node_model)

    vehicle_int_cd = _get_current_vehicle_int_cd()
    localization_name = _safe_method_value(node_model, 'getLocalizationName')
    captured = _cache_t11_ui_name(
        vehicle_int_cd,
        step_id,
        localization_name,
        source_name,
    )
    return captured


def _wrap_t11_ui_name_hook(module_name, attr_name, original):
    def _wrapped(*args, **kwargs):
        result = original(*args, **kwargs)
        try:
            _capture_t11_ui_name_from_fill_node_model(
                args,
                kwargs,
                '{0}.{1}'.format(module_name, attr_name),
            )
        except Exception:
            _logger.exception('Failed to capture Tier-11 UI name from %s.%s', module_name, attr_name)
        return result

    _wrapped.__name__ = getattr(original, '__name__', attr_name)
    _wrapped.__doc__ = getattr(original, '__doc__', None)
    _wrapped._zanju_rpb_original = original
    return _wrapped


def _install_t11_ui_name_hooks():
    if _t11_ui_name_hook_records:
        return len(_t11_ui_name_hook_records)

    for module_name, attr_name in _T11_UI_NAME_HOOK_SPECS:
        try:
            module = __import__(module_name, fromlist=[attr_name])
        except Exception:
            continue

        original = getattr(module, attr_name, None)
        if not callable(original):
            continue
        if getattr(original, '_zanju_rpb_original', None) is not None:
            continue

        wrapped = _wrap_t11_ui_name_hook(module_name, attr_name, original)
        setattr(module, attr_name, wrapped)
        _t11_ui_name_hook_records.append((module, attr_name, original))
    return len(_t11_ui_name_hook_records)


def _uninstall_t11_ui_name_hooks():
    while _t11_ui_name_hook_records:
        module, attr_name, original = _t11_ui_name_hook_records.pop()
        try:
            setattr(module, attr_name, original)
        except Exception:
            _logger.exception('Failed to detach Tier-11 UI name hook: %s.%s', module.__name__, attr_name)


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
    """Collect the production post-progression data used by the UI."""
    data = {
        'exists': False,
        'total_steps': 0,
        'unlocked_steps': 0,
        'is_veh_skill_tree': False,
        'unique_level_count': 0,
        'unique_unlocked_level_count': 0,
        'next_purchasable_step_xp': None,
        't11_bucket_researched': {
            'small_10k': 0,
            'big_20k': 0,
            'big_25k': 0,
            'unknown': 0,
        },
        't11_bucket_unresearched': {
            'small_10k': 0,
            'big_20k': 0,
            'big_25k': 0,
            'unknown': 0,
        },
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

    step_id_to_level = {}
    step_meta = {}

    try:
        steps = list(pp.iterUnorderedSteps())
        data['total_steps'] = len(steps)

        unique_levels = set()
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
                if data['is_veh_skill_tree']:
                    step_xp_cost = _resolve_t11_step_xp_cost(step)
                    step_meta[sid] = {
                        'xp_cost': step_xp_cost,
                        'bucket': _make_t11_bucket(step_xp_cost),
                        'action_meta': _extract_t11_action_marker_meta(step, sid, vehicle),
                    }

            if level is not None:
                unique_levels.add(level)

        data['unique_level_count'] = len(unique_levels)
    except Exception:
        _logger.exception('Failed to read post-progression step metadata')

    unlocked_step_ids = set()
    try:
        state = pp.getState(True)
        unlocks = getattr(state, 'unlocks', set()) or set()
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

        data['unlocked_steps'] = len(unlocked_step_ids)

        unlocked_levels = set()
        for uid in unlocked_step_ids:
            level = step_id_to_level.get(uid)
            if level is not None:
                unlocked_levels.add(level)
        data['unique_unlocked_level_count'] = len(unlocked_levels)

        if data['is_veh_skill_tree'] and step_meta:
            explicit_final_ids = sorted([
                sid for sid, meta in step_meta.iteritems()
                if meta.get('bucket') == 'big_25k'
            ])
            if not explicit_final_ids:
                fallback_final_id = max(step_meta.keys())
                if step_meta[fallback_final_id].get('bucket') == 'unknown':
                    step_meta[fallback_final_id]['bucket'] = 'big_25k'

            researched_action_nodes = []
            unresearched_action_nodes = []
            for sid, meta in step_meta.iteritems():
                bucket = meta.get('bucket') or 'unknown'
                is_researched = sid in unlocked_step_ids
                bucket_counts = data['t11_bucket_researched'] if is_researched else data['t11_bucket_unresearched']
                bucket_counts[bucket] = bucket_counts.get(bucket, 0) + 1

                action_meta = meta.get('action_meta')
                if action_meta is None:
                    continue

                action_node = {
                    'step_id': sid,
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

            data['t11_action_nodes_researched'] = sorted(researched_action_nodes, key=_t11_action_node_sort_key)
            data['t11_action_nodes_unresearched'] = sorted(unresearched_action_nodes, key=_t11_action_node_sort_key)
    except Exception:
        _logger.exception('Failed to read post-progression state/unlocks')

    if not data['is_veh_skill_tree']:
        return data

    try:
        balance = stats.getMoneyExt(vehicle.intCD)
        step = pp.getFirstPurchasableStep(balance)
        if step is not None:
            step_id = getattr(step, 'stepID', None) or getattr(step, 'id', None)
            if step_id is not None:
                step_meta_entry = step_meta.get(step_id)
                if step_meta_entry is not None:
                    data['next_purchasable_step_xp'] = step_meta_entry.get('xp_cost')
            if data['next_purchasable_step_xp'] is None:
                data['next_purchasable_step_xp'] = _extract_xp_cost_lightweight(step)
    except Exception:
        _logger.exception('Failed to resolve next purchasable post-progression step')

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

    def as_refreshLayoutS(self):
        if self._isDAAPIInited():
            return self.flashObject.as_refreshLayout()
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

    def __init__(self):
        self._active = False
        self._pending_update_callback = None
        self._visibility_probe_callback = None
        self._update_in_progress = False
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
        self._last_scaleform_payload_log_key = None
        self._last_seen_sub_view_alias = None

    def _refresh_vehicle_change_hooks(self, reason):
        current_ok = False
        preview_ok = False

        try:
            try:
                g_currentVehicle.onChanged -= self._on_vehicle_changed
            except Exception:
                pass
            g_currentVehicle.onChanged += self._on_vehicle_changed
            current_ok = True
        except Exception:
            _logger.exception('Failed to refresh current vehicle hook (%s)', reason)

        try:
            try:
                g_currentPreviewVehicle.onChanged -= self._on_preview_vehicle_changed
            except Exception:
                pass
            g_currentPreviewVehicle.onChanged += self._on_preview_vehicle_changed
            preview_ok = True
        except Exception:
            _logger.exception('Failed to refresh preview vehicle hook (%s)', reason)

    # -- lifecycle -----------------------------------------------------------

    def start(self):
        self._active = True
        _install_t11_ui_name_hooks()
        self._attach_lobby_route_log_handler()
        self._start_scaleform_view()
        self._refresh_vehicle_change_hooks('start')
        # Avoid running heavy collection during early login/loading phase.
        # First update is triggered by onChanged once hangar vehicle selection settles.

    def stop(self):
        self._active = False
        self._cancel_pending_update()
        self._cancel_visibility_probe()
        self._detach_lobby_route_log_handler()
        _uninstall_t11_ui_name_hooks()
        g_currentPreviewVehicle.onChanged -= self._on_preview_vehicle_changed
        self._stop_scaleform_view()
        g_currentVehicle.onChanged -= self._on_vehicle_changed

    def on_external_config_changed(self, reason):
        if not self._active:
            return

        self._cancel_pending_update()
        self._cancel_visibility_probe()
        self._scaleform_payload = None

        if not _config.get('enabled', True):
            if self._scaleform_view is not None:
                self._set_scaleform_view_visible(False, reason)
            return

        self._schedule_update(reason)

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

        previous_route_path = self._current_lobby_route_path
        self._current_lobby_route_path = route_path
        if self._is_default_hangar_route(route_path) and not self._is_default_hangar_route(previous_route_path):
            self._last_seen_sub_view_alias = None
            if self._active:
                self._refresh_vehicle_change_hooks('enter_default_hangar')
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

    def _get_topmost_view_for_layer(self, layer):
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
                return get_topmost_view()

            view = None
            num_children = getattr(container, 'numChildren', 0)
            if callable(num_children):
                num_children = num_children()
            get_child_at = getattr(container, 'getChildAt', None)
            if view is None and callable(get_child_at) and num_children:
                view = get_child_at(num_children - 1)
            return view
        except Exception:
            _logger.exception('Failed to resolve topmost lobby view for layer=%s', layer)
            return None

    def _get_active_view_alias(self, layer):
        view = self._get_topmost_view_for_layer(layer)
        if view is None:
            return None
        return self._get_view_alias(view)

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

    def _get_layout_wulf_view_alias(self, view):
        alias = self._get_view_alias(view)
        if alias:
            return alias

        for candidate in (getattr(view, '_View__key', None), getattr(view, '_View__settings', None)):
            if candidate is None:
                continue
            for attr in ('alias', 'name'):
                value = getattr(candidate, attr, None)
                if value:
                    return value
            if isinstance(candidate, (list, tuple)) and candidate:
                first = candidate[0]
                if isinstance(first, _STRING_TYPES) and first:
                    return first

        return None

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
        if (
            self._current_lobby_route_path is not None
            and not self._is_default_hangar_route(self._current_lobby_route_path)
        ):
            return 'lobby_route={0}'.format(
                self._current_lobby_route_path
            )

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

        allow_missing_sub_view = effective_sub_view_alias is None and self._scaleform_view is not None
        if effective_sub_view_alias not in _HANGAR_VIEW_ALIASES and not allow_missing_sub_view:
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
            if is_visible:
                refresh_reason = 'visible:{0}'.format(reason)
                self._refresh_scaleform_layout(refresh_reason)
        except Exception:
            _logger.exception('Failed to set scaleform garage view visibility=%s (%s)', is_visible, reason)

    def _refresh_scaleform_layout(self, reason):
        if self._scaleform_view is None:
            return

        try:
            self._scaleform_view.as_refreshLayoutS()
            _logger.info('Scaleform garage view layout refresh (%s)', reason)
        except Exception:
            _logger.exception('Failed to refresh scaleform garage view layout (%s)', reason)

    def _dispose_scaleform_view(self, reason):
        if self._scaleform_view is None:
            return

        view = self._scaleform_view
        self._scaleform_view = None
        self._scaleform_view_visible = None
        self._scaleform_view_requested = False
        try:
            view.destroy()
            _logger.info('Disposed scaleform garage view (%s)', reason)
        except Exception:
            _logger.exception('Failed to dispose scaleform garage view (%s)', reason)

    def _should_dispose_scaleform_view_for_block(self, context):
        route_path = self._current_lobby_route_path or ''
        if route_path.startswith(_SCALEFORM_DISPOSE_ROUTE_PREFIXES):
            return True

        incoming_alias = context.get('incoming_alias')
        active_sub_view_alias = context.get('active_sub_view_alias')
        return (
            incoming_alias in _SCALEFORM_DISPOSE_SUB_VIEW_ALIASES
            or active_sub_view_alias in _SCALEFORM_DISPOSE_SUB_VIEW_ALIASES
        )

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
            if self._should_dispose_scaleform_view_for_block(context):
                self._dispose_scaleform_view('blocked:{0}'.format(reason))
            else:
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
        self._dispose_scaleform_view('lobby_exit')

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
        return build_scaleform_view_payload(vehicle, data, _build_mode_preferences())

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

    def _log_scaleform_payload_summary(self, vehicle):
        payload = self._scaleform_payload or {}
        modes = payload.get('modes') or []

        vehicle_name = (
            getattr(vehicle, 'userName', None)
            or getattr(vehicle, 'shortUserName', None)
            or getattr(vehicle, 'name', None)
            or '?'
        )
        vehicle_ref = '{0}:{1}'.format(getattr(vehicle, 'intCD', None), vehicle_name)
        mode_ids = []
        marker_counts = []
        for mode in modes:
            mode_id = str(mode.get('id') or '')
            mode_ids.append(mode_id)
            marker_counts.append('{0}:{1}'.format(mode_id, len(mode.get('markers') or [])))

        log_key = (
            vehicle_ref,
            payload.get('selectedModeId'),
            tuple(mode_ids),
            tuple(marker_counts),
        )
        if log_key == self._last_scaleform_payload_log_key:
            return

        self._last_scaleform_payload_log_key = log_key
        _logger.info(
            'Scaleform payload: vehicle=%s selected=%s modes=%s markers=%s',
            vehicle_ref,
            payload.get('selectedModeId'),
            ','.join(mode_ids),
            ', '.join(marker_counts) or 'none',
        )

    def _render_scaleform_view(self, vehicle, data):
        if not _config.get('scaleformPrototypeEnabled', True):
            return
        self._scaleform_payload = self._build_scaleform_payload(vehicle, data)
        self._log_scaleform_payload_summary(vehicle)
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

        had_pending = self._pending_update_callback is not None
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

        alias = self._get_view_alias(view)

        if alias in _LAYOUT_REFRESH_VIEW_ALIASES:
            self._refresh_scaleform_layout('view_added:{0}'.format(alias))

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

        elite_progression = _collect_elite_progression(vehicle)

        # --- Field modifications / post-progression (per vehicle) ---
        field_mods = _collect_post_progression(vehicle, stats)
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

    # -- rendering -----------------------------------------------------------

    def _render(self, vehicle, data):
        self._render_scaleform_view(vehicle, data)


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
        _register_mod_settings()
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
