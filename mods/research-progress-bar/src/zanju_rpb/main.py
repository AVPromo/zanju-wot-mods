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
from skeletons.gui.game_control import IVehiclePostProgressionController
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

_CONFIG_PERSISTED_KEYS = (
    'enabled',
    'language',
    'showTechTree',
    'showFieldMods',
    'showUpgrades',
    'eliteMode',
    'debugFieldMods',
    'fieldModsProbeMode',
    'extractNextStepXPLightweight',
    'parseNextStepXPFromSettings',
    'parseNextStepXPFromRawTree',
    'tier11WideNetProbe',
    'tier11MethodProbeEnabled',
    'tier11MethodProbeName',
    'tier11MethodProbeMaxStepsPerUpdate',
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
_T11_CATEGORY_HINT_RE = re.compile(
    r'(firepower|survivability|mobility|scouting|mechanic|special|category|speciali[sz]ation|icon|slot)',
    re.I,
)

_T11_CATEGORY_PROBE_ATTRS = (
    'settings', 'config', 'postProgressionConfig', 'vehicle_post_progression_config',
    'tree', 'state', 'nodes', 'steps', 'items', 'children', 'groups', 'slots',
    'branches', 'category', 'categories', 'specialization', 'specializations',
    'icon', 'iconPath', '_data', '__dict__',
)

_T11_UI_NAME_HOOK_SPECS = (
    ('gui.impl.lobby.vehicle_hub.sub_presenters.veh_skill_tree.utils', 'fillNodeModel'),
    ('gui.impl.lobby.veh_skill_tree.utils', 'fillNodeModel'),
)

_t11_ui_name_cache = {}
_t11_ui_name_hook_records = []
_t11_ui_name_probe_miss_count = 0
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
    import io, json, os
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
    import io, json, os

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


def _resolve_t11_step_xp_cost(step):
    """Safely resolves stable tier-11 node XP cost from getType()."""
    try:
        get_type = getattr(step, 'getType', None)
        if get_type is None or not callable(get_type):
            return None
        return _resolve_t11_xp_from_type(get_type())
    except Exception:
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


def _safe_attr_text(obj, attr_name, max_len=120):
    try:
        value = getattr(obj, attr_name, None)
    except Exception as exc:
        return '<error:{0}>'.format(_safe_text(exc, 80))
    return _safe_text(value, max_len)


def _clean_probe_text(value):
    if value is None:
        return None
    text = _safe_text(value, 120).strip()
    if not text:
        return None
    if text[0] == '<' and text[-1] == '>':
        return None
    return text


def _safe_method_value(obj, method_name):
    ok, value_text = _safe_method_probe(obj, method_name)
    if not ok:
        return None
    return _clean_probe_text(value_text)


def _resolve_localized_action_name(action):
    for method_name in ('getLocSplitNameRes', 'getLocNameRes'):
        try:
            method = getattr(action, method_name, None)
            if method is None or not callable(method):
                continue
            resource = method()
            if resource is None or not callable(resource):
                continue
            text = _clean_probe_text(backport.text(resource()))
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
    key = _clean_probe_text(identifier)
    if not key:
        return None

    if R is not None:
        try:
            text = _clean_probe_text(backport.text(R.strings.veh_skill_tree.tooltips.title(key)))
            if text and text != key:
                return text
        except Exception:
            pass

    try:
        resource_key = '#veh_skill_tree:tooltips/title/{0}'.format(key)
        text = _clean_probe_text(i18n.makeString(resource_key))
        if text and text not in (key, resource_key):
            return text
    except Exception:
        pass

    return None


def _resolve_t11_tooltip_title_from_candidates(*identifiers):
    seen = set()
    for identifier in identifiers:
        key = _clean_probe_text(identifier)
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
    descriptor_name = _clean_probe_text(getattr(descriptor, 'name', None))
    descriptor_loc_name = _clean_probe_text(getattr(descriptor, 'locName', None))
    descriptor_image_name = _clean_probe_text(getattr(descriptor, 'imgName', None))
    descriptor_categories = getattr(descriptor, 'categories', None)
    descriptor_category = None
    if descriptor_categories is not None:
        try:
            if len(descriptor_categories) > 0:
                descriptor_category = _clean_probe_text(descriptor_categories[0])
        except Exception:
            try:
                for category_value in descriptor_categories:
                    descriptor_category = _clean_probe_text(category_value)
                    break
            except Exception:
                descriptor_category = _clean_probe_text(descriptor_categories)

    tooltip_title = _resolve_t11_tooltip_title_from_candidates(
        ui_localized_name,
        loc_name,
        descriptor_loc_name,
        image_name,
        descriptor_image_name,
    )

    resolved_name = tooltip_title or localized_name or ui_localized_name
    if _is_generic_t11_action_name(resolved_name):
        resolved_name = image_name or descriptor_image_name or loc_name or tech_name or descriptor_loc_name or descriptor_name

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


def _collect_t11_action_probe(step, step_id):
    """Collects low-risk debug metadata from a tier-11 step.action object."""
    try:
        action = getattr(step, 'action', None)
    except Exception as exc:
        return 'sid={0},action=<error:{1}>'.format(step_id, _safe_text(exc, 80)), []

    if action is None:
        return 'sid={0},action=<missing>'.format(step_id), []

    _ok, tech_name = _safe_method_probe(action, 'getTechName')
    _ok, loc_name = _safe_method_probe(action, 'getLocName')
    _ok, image_name = _safe_method_probe(action, 'getImageName')
    _ok, slot_category = _safe_method_probe(action, 'getSlotCategory')

    descriptor = getattr(action, '_descriptor', None)
    preview = (
        'sid={0},aclass={1},atype={2},tech={3},loc={4},img={5},slot={6},'
        'dname={7},dloc={8},dimg={9}'
    ).format(
        step_id,
        type(action).__name__,
        _safe_attr_text(action, 'actionType', 40),
        tech_name,
        loc_name,
        image_name,
        slot_category,
        _safe_attr_text(descriptor, 'name', 80),
        _safe_attr_text(descriptor, 'locName', 80),
        _safe_attr_text(descriptor, 'imgName', 80),
    )

    hits = _probe_t11_category_hints(action, 'step[{0}].action'.format(step_id))
    if descriptor is not None:
        hits.extend(
            _probe_t11_category_hints(
                descriptor,
                'step[{0}].action._descriptor'.format(step_id),
            )
        )

    deduped_hits = []
    seen = set()
    for hit in hits:
        if hit in seen:
            continue
        seen.add(hit)
        deduped_hits.append(hit)

    return preview, deduped_hits


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


def _looks_like_t11_category_hint(value):
    if value is None:
        return False
    return _T11_CATEGORY_HINT_RE.search(_safe_text(value, 240)) is not None


def _is_string_like(value):
    return isinstance(value, str) or type(value).__name__ == 'unicode'


def _probe_t11_category_hints(root, root_name):
    hits = []
    seen = set()
    visited = set()

    def add_hit(path, value):
        text = _safe_text(value, 180)
        item = '{0}={1}'.format(path, text)
        if item in seen:
            return
        seen.add(item)
        hits.append(item)

    def walk(node, path, depth):
        if node is None or depth > 8 or len(hits) >= 40:
            return

        try:
            node_id = id(node)
            if node_id in visited:
                return
            visited.add(node_id)
        except Exception:
            pass

        if _is_string_like(node):
            if _looks_like_t11_category_hint(node):
                add_hit(path, node)
            return

        if isinstance(node, dict):
            sid = node.get('stepID', node.get('id'))
            for key, value in node.iteritems():
                key_text = _safe_text(key, 48)
                child_path = '{0}.{1}'.format(path, key_text)
                if _looks_like_t11_category_hint(key):
                    add_hit('{0}::<key>'.format(child_path), key)
                if sid is not None and _is_string_like(value) and _looks_like_t11_category_hint(value):
                    add_hit('{0}[step={1}]'.format(child_path, sid), value)
                walk(value, child_path, depth + 1)
                if len(hits) >= 40:
                    return
            return

        if isinstance(node, (list, tuple, set)):
            for index, item in enumerate(node):
                walk(item, '{0}[{1}]'.format(path, index), depth + 1)
                if len(hits) >= 40:
                    return
            return

        sid = getattr(node, 'stepID', None)
        if sid is None:
            sid = getattr(node, 'id', None)

        attr_names = list(_T11_CATEGORY_PROBE_ATTRS)
        try:
            slots = getattr(type(node), '__slots__', None)
            if _is_string_like(slots):
                slots = [slots]
            if isinstance(slots, (list, tuple)):
                for slot_name in slots[:40]:
                    if slot_name not in attr_names:
                        attr_names.append(slot_name)
        except Exception:
            pass

        for attr in attr_names:
            try:
                child = getattr(node, attr, None)
            except Exception:
                continue
            if child is None or child is node:
                continue

            child_path = '{0}.{1}'.format(path, attr)
            if _looks_like_t11_category_hint(attr):
                add_hit('{0}::<attr>'.format(child_path), attr)
            if sid is not None and _is_string_like(child) and _looks_like_t11_category_hint(child):
                add_hit('{0}[step={1}]'.format(child_path, sid), child)
            walk(child, child_path, depth + 1)
            if len(hits) >= 40:
                return

    walk(root, root_name, 0)
    return hits


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


def _call_prestige_helper(helper_name, *values):
    if _prestige_helpers is None:
        return None

    helper = getattr(_prestige_helpers, helper_name, None)
    if not callable(helper):
        return None

    candidates = []
    for value in values:
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
            if _config.get('debugFieldMods'):
                _logger.exception('Failed prestige helper %s without args', helper_name)
            return None

    for candidate in candidates:
        try:
            return helper(candidate)
        except TypeError:
            continue
        except Exception:
            if _config.get('debugFieldMods'):
                _logger.exception('Failed prestige helper %s for values=%s', helper_name, candidates)
            return None

    try:
        return helper()
    except TypeError:
        return None
    except Exception:
        if _config.get('debugFieldMods'):
            _logger.exception('Failed prestige helper %s without args after candidate fallback', helper_name)
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


def _extract_sequence_ints(value, max_items=4):
    items = []
    if value is None or isinstance(value, (str, unicode)):
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


def _debug_prestige_value_summary(value):
    if value is None:
        return 'None'

    parts = ['type={0}'.format(type(value).__name__)]
    for attr_name in ('currentLevel', 'prestigeLevel', 'level', 'currentXP', 'nextLvlXP', 'maxLevel', 'remainingPoints', 'remainingPts', 'nextLevelPts'):
        attr_value = _first_int_attr(value, (attr_name,))
        if attr_value is not None:
            parts.append('{0}={1}'.format(attr_name, attr_value))

    sequence_items = _extract_sequence_ints(value)
    if sequence_items:
        parts.append('items={0}'.format(sequence_items))

    try:
        if hasattr(value, '__len__') and not isinstance(value, (str, unicode)):
            parts.append('len={0}'.format(len(value)))
    except Exception:
        pass

    return ','.join(parts)


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

    data['available'] = bool(has_vehicle_prestige) or prestige is not None or prestige_stats is not None or mapped_prestige is not None or progress is not None
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
    remaining_points = _extract_elite_remaining_points((progress, mapped_prestige, prestige_stats, prestige, vehicle_points))
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

    if _config.get('debugFieldMods'):
        vehicle_name = getattr(vehicle, 'userName', getattr(vehicle, 'intCD', 'unknown'))
        _logger.info(
            '  Elite DEBUG [%s]: has=%s globalStats=(%s) points=(%s) stats=(%s) mapEntry=(%s) prestige=(%s) progress=(%s) levelCandidates=%s chosenLevel=%s currentXP=%s nextXP=%s remainingXP=%s maxLevel=%s',
            vehicle_name,
            has_vehicle_prestige,
            _debug_prestige_value_summary(global_prestige_stats),
            _debug_prestige_value_summary(vehicle_points),
            _debug_prestige_value_summary(prestige_stats),
            _debug_prestige_value_summary(mapped_prestige),
            _debug_prestige_value_summary(prestige),
            _debug_prestige_value_summary(progress),
            level_candidates,
            data['current_level'],
            data['current_xp'],
            data['next_level_xp'],
            data['remaining_xp'],
            data['max_level'],
        )

    return data


def _coerce_int_or_none(value):
    direct = _to_int_or_none(value)
    if direct is not None:
        return direct

    text = _clean_probe_text(value)
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
    name_text = _clean_probe_text(localization_name)
    if vehicle_key is None or step_key is None or not name_text or _is_generic_t11_action_name(name_text):
        return False

    cache_key = (vehicle_key, step_key)
    previous = _t11_ui_name_cache.get(cache_key)
    if previous == name_text:
        return False

    _t11_ui_name_cache[cache_key] = name_text
    if _config.get('debugFieldMods'):
        _logger.info(
            'Tier-11 UI name cache captured: intCD=%s sid=%s source=%s name=%s',
            vehicle_key,
            step_key,
            source_name,
            name_text,
        )
    if _mod is not None and getattr(_mod, '_active', False):
        _mod._schedule_update('tier11_ui_name_capture')
    return True


def _capture_t11_ui_name_from_fill_node_model(args, kwargs, source_name):
    global _t11_ui_name_probe_miss_count

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
    if not captured and _config.get('debugFieldMods') and _t11_ui_name_probe_miss_count < 12:
        _t11_ui_name_probe_miss_count += 1
        _logger.info(
            'Tier-11 UI name capture miss: intCD=%s sid=%s nodeId=%s source=%s loc=%s argTypes=%s',
            _coerce_int_or_none(vehicle_int_cd),
            step_id,
            _safe_method_value(node_model, 'getId'),
            source_name,
            localization_name,
            ','.join([type(value).__name__ for value in list(args) + list(kwargs.values())[:6]]),
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
            if _config.get('debugFieldMods'):
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

    if _config.get('debugFieldMods') and _t11_ui_name_hook_records:
        _logger.info(
            'Tier-11 UI name hooks attached: %s',
            ', '.join([
                '{0}.{1}'.format(module.__name__, attr_name)
                for module, attr_name, _original in _t11_ui_name_hook_records
            ])
        )
    return len(_t11_ui_name_hook_records)


def _uninstall_t11_ui_name_hooks():
    while _t11_ui_name_hook_records:
        module, attr_name, original = _t11_ui_name_hook_records.pop()
        try:
            setattr(module, attr_name, original)
        except Exception:
            if _config.get('debugFieldMods'):
                _logger.exception('Failed to detach Tier-11 UI name hook: %s.%s', module.__name__, attr_name)


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
        't11_action_nodes_researched': [],
        't11_action_nodes_unresearched': [],
        't11_action_probe_preview': [],
        't11_action_probe_hits': [],
        't11_settings_probe_hits': [],
        't11_raw_tree_probe_hits': [],
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
                    step_xp_cost = None
                    step_size = 'unknown'
                    action_meta = None
                    if data['is_veh_skill_tree']:
                        step_xp_cost = _resolve_t11_step_xp_cost(step)
                        if step_xp_cost is not None:
                            step_size = _classify_t11_step_size_from_xp(step_xp_cost)
                        action_meta = _extract_t11_action_marker_meta(step, sid, vehicle)
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

                    if data['is_veh_skill_tree'] and _config.get('debugFieldMods'):
                        action_preview, action_hits = _collect_t11_action_probe(step, sid)
                        if len(data['t11_action_probe_preview']) < 40:
                            data['t11_action_probe_preview'].append(action_preview)
                        for hit in action_hits:
                            if len(data['t11_action_probe_hits']) >= 80:
                                break
                            if hit not in data['t11_action_probe_hits']:
                                data['t11_action_probe_hits'].append(hit)

                    step_meta[sid] = {
                        'level': level,
                        'xp_cost': step_xp_cost,
                        'size': step_size,
                        'meta': step_meta_raw,
                        'signature': _t11_meta_signature(step_meta_raw),
                        'action_meta': action_meta,
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
                researched_action_nodes = []
                unresearched_action_nodes = []
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

                    if meta.get('action_meta') is not None:
                        action_node = {
                            'step_id': sid,
                            'xp_cost': xp_cost,
                            'bucket': bucket,
                            'name': meta['action_meta'].get('name'),
                            'tooltip_title': meta['action_meta'].get('tooltip_title'),
                            'ui_localized_name': meta['action_meta'].get('ui_localized_name'),
                            'localized_name': meta['action_meta'].get('localized_name'),
                            'loc_name': meta['action_meta'].get('loc_name'),
                            'tech_name': meta['action_meta'].get('tech_name'),
                            'image_name': meta['action_meta'].get('image_name'),
                            'slot_category': meta['action_meta'].get('slot_category'),
                            'category': meta['action_meta'].get('category'),
                        }
                        if is_researched:
                            researched_action_nodes.append(action_node)
                        else:
                            unresearched_action_nodes.append(action_node)

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
                data['t11_action_nodes_researched'] = sorted(researched_action_nodes, key=_t11_action_node_sort_key)
                data['t11_action_nodes_unresearched'] = sorted(unresearched_action_nodes, key=_t11_action_node_sort_key)

                if _config.get('tier11WideNetProbe', True):
                    unlock_preview = []
                    for unlock in unlocks:
                        if len(unlock_preview) >= 40:
                            break
                        unlock_preview.append(_safe_text(repr(unlock)))
                    data['t11_widenet_unlock_repr'] = unlock_preview

                if _config.get('debugFieldMods'):
                    data['t11_settings_probe_hits'] = _probe_t11_category_hints(pp_settings, 'settings')
                    try:
                        raw_tree = pp.getRawTree()
                    except Exception:
                        raw_tree = None
                    data['t11_raw_tree_probe_hits'] = _probe_t11_category_hints(raw_tree, 'rawTree')
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
        self._last_scaleform_payload_log_key = None
        self._last_seen_sub_view_alias = None
        self._bound_current_vehicle_holder_id = None
        self._bound_current_vehicle_event_id = None
        self._bound_preview_vehicle_holder_id = None
        self._bound_preview_vehicle_event_id = None

    def _record_vehicle_binding_targets(self):
        current_event = getattr(g_currentVehicle, 'onChanged', None)
        preview_event = getattr(g_currentPreviewVehicle, 'onChanged', None)
        self._bound_current_vehicle_holder_id = id(g_currentVehicle)
        self._bound_current_vehicle_event_id = id(current_event) if current_event is not None else None
        self._bound_preview_vehicle_holder_id = id(g_currentPreviewVehicle)
        self._bound_preview_vehicle_event_id = id(preview_event) if preview_event is not None else None

    def _clear_vehicle_binding_targets(self):
        self._bound_current_vehicle_holder_id = None
        self._bound_current_vehicle_event_id = None
        self._bound_preview_vehicle_holder_id = None
        self._bound_preview_vehicle_event_id = None

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

        if current_ok or preview_ok:
            self._record_vehicle_binding_targets()
            self._log_control_debug(
                'vehicle_hooks_refreshed',
                'reason={0} current={1} preview={2}'.format(reason, current_ok, preview_ok),
            )

    def _format_control_identity(self, value):
        if value is None:
            return 'None'
        return '0x{0:x}'.format(int(value))

    def _format_vehicle_item(self, item):
        if item is None:
            return 'none'

        name = (
            getattr(item, 'userName', None)
            or getattr(item, 'shortUserName', None)
            or getattr(item, 'name', None)
            or '?'
        )
        return '{0}:{1}'.format(getattr(item, 'intCD', None), name)

    def _describe_vehicle_binding(self, holder, bound_holder_id, bound_event_id):
        event = getattr(holder, 'onChanged', None)
        live_holder_id = id(holder)
        live_event_id = id(event) if event is not None else None
        present = 'n/a'
        is_present = getattr(holder, 'isPresent', None)
        if callable(is_present):
            try:
                present = is_present()
            except Exception:
                present = 'err'

        is_match = bound_holder_id == live_holder_id and bound_event_id == live_event_id
        return 'bind={0}/{1} live={2}/{3} ok={4} present={5} item={6}'.format(
            self._format_control_identity(bound_holder_id),
            self._format_control_identity(bound_event_id),
            self._format_control_identity(live_holder_id),
            self._format_control_identity(live_event_id),
            is_match,
            present,
            self._format_vehicle_item(getattr(holder, 'item', None)),
        )

    def _log_control_debug(self, reason, extra=None):
        if not _config.get('debugFieldMods'):
            return

        payload = self._scaleform_payload if isinstance(self._scaleform_payload, dict) else {}
        extra_text = '' if extra is None else ' | {0}'.format(extra)
        _logger.info(
            '  Control DEBUG [%s]: cv[%s] pv[%s] route=%s lastSub=%s view=%s req=%s vis=%s pending=%s updating=%s payload=%s%s',
            reason,
            self._describe_vehicle_binding(
                g_currentVehicle,
                self._bound_current_vehicle_holder_id,
                self._bound_current_vehicle_event_id,
            ),
            self._describe_vehicle_binding(
                g_currentPreviewVehicle,
                self._bound_preview_vehicle_holder_id,
                self._bound_preview_vehicle_event_id,
            ),
            self._current_lobby_route_path,
            self._last_seen_sub_view_alias,
            self._scaleform_view is not None,
            self._scaleform_view_requested,
            self._scaleform_view_visible,
            self._pending_update_callback is not None,
            self._update_in_progress,
            payload.get('vehicleLabel'),
            extra_text,
        )

    # -- lifecycle -----------------------------------------------------------

    def start(self):
        self._active = True
        _install_t11_ui_name_hooks()
        self._attach_lobby_route_log_handler()
        self._start_scaleform_view()
        self._refresh_vehicle_change_hooks('start')
        self._log_control_debug('start', 'hooks_attached=True')
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
        self._log_control_debug('stop', 'hooks_attached=False')
        self._clear_vehicle_binding_targets()

    def on_external_config_changed(self, reason):
        if not self._active:
            return

        self._cancel_pending_update()
        self._cancel_visibility_probe()
        self._scaleform_payload = None
        self._log_control_debug('config_changed', 'reason={0}'.format(reason))

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
            self._log_control_debug('gui_space_entered', 'space={0}'.format(space_id))
            self._attach_scaleform_container_hooks()
            self._sync_scaleform_view('lobby_entered')

    def _on_gui_space_left(self, space_id):
        if space_id != SPACE_ID.LOBBY:
            return

        self._log_control_debug('gui_space_left', 'space={0}'.format(space_id))

        self._detach_scaleform_container_hooks()
        self._scaleform_view_requested = False
        self._dispose_scaleform_view('lobby_exit')

    def _on_scaleform_view_populated(self, view):
        self._scaleform_view_requested = False
        self._scaleform_view = view
        self._scaleform_view_visible = None
        self._log_control_debug('scaleform_populated', 'alias={0}'.format(self._get_view_alias(view)))
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
        self._log_control_debug('scaleform_disposed', 'alias={0}'.format(self._get_view_alias(view)))
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
            self._log_control_debug(
                'push_scaleform_payload',
                'selected={0}'.format(self._scaleform_payload.get('selectedModeId')),
            )
            self._log_scaleform_payload_debug()
        except Exception:
            _logger.exception('Failed to push data to scaleform garage view')

    def _log_scaleform_payload_debug(self):
        if not _config.get('debugFieldMods'):
            return

        payload = self._scaleform_payload or {}
        modes = payload.get('modes') or []
        if not modes:
            return

        mode_ids = []
        tier11_mode = None
        for mode in modes:
            mode_id = str(mode.get('id') or '')
            mode_ids.append(mode_id)
            if mode_id == 'tier11_upgrades':
                tier11_mode = mode

        if tier11_mode is None:
            return

        markers = tier11_mode.get('markers') or []
        marker_bits = []
        marker_key = []
        for marker in markers:
            marker_id = str(marker.get('id') or '')
            position_value = _to_int_or_none(marker.get('positionValue'))
            marker_state = str(marker.get('markerState') or '')
            marker_item_type = str(marker.get('itemType') or '')
            marker_category = str(marker.get('debugCategory') or '')
            marker_bar_type = str(marker.get('barItemType') or '')
            marker_hide_bar_icon = bool(marker.get('hideBarIcon'))
            marker_bits.append(
                '%s@%s[%s]{item=%s cat=%s bar=%s hide=%s}' % (
                    marker_id,
                    position_value,
                    marker_state,
                    marker_item_type,
                    marker_category,
                    marker_bar_type,
                    marker_hide_bar_icon,
                )
            )
            marker_key.append((marker_id, position_value, marker_state))

        log_key = (
            tuple(mode_ids),
            payload.get('selectedModeId'),
            _to_int_or_none(tier11_mode.get('barMaxValue')),
            _to_int_or_none(tier11_mode.get('completedValue')),
            _to_int_or_none(tier11_mode.get('primaryValue')),
            _to_int_or_none(tier11_mode.get('secondaryValue')),
            tuple(marker_bits),
        )
        if log_key == self._last_scaleform_payload_log_key:
            return

        self._last_scaleform_payload_log_key = log_key
        _logger.info(
            '  Scaleform DEBUG tier11 payload: selected=%s modes=%s barMax=%s completed=%s primary=%s secondary=%s markers=%s',
            payload.get('selectedModeId'),
            ','.join(mode_ids),
            tier11_mode.get('barMaxValue'),
            tier11_mode.get('completedValue'),
            tier11_mode.get('primaryValue'),
            tier11_mode.get('secondaryValue'),
            '; '.join(marker_bits) or 'none',
        )

    def _render_scaleform_view(self, vehicle, data):
        if not _config.get('scaleformPrototypeEnabled', True):
            return
        self._scaleform_payload = self._build_scaleform_payload(vehicle, data)
        self._log_control_debug(
            'render_scaleform_payload',
            'vehicle={0} selected={1}'.format(
                self._format_vehicle_item(vehicle),
                None if self._scaleform_payload is None else self._scaleform_payload.get('selectedModeId'),
            ),
        )
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
        self._log_control_debug('schedule_update', 'reason={0} hadPending={1}'.format(reason, had_pending))

    # -- event handlers ------------------------------------------------------

    def _on_vehicle_changed(self):
        if not self._active:
            self._log_control_debug('vehicle_changed_ignored', 'active=False')
            return
        self._log_control_debug('vehicle_changed_signal')
        self._schedule_update('vehicle_changed')

    def _on_preview_vehicle_changed(self):
        if not self._active:
            self._log_control_debug('preview_vehicle_changed_ignored', 'active=False')
            return
        self._log_control_debug('preview_vehicle_changed_signal')
        self._schedule_update('preview_vehicle_changed')

    def _on_view_added_to_container(self, _container, view):
        if not self._active:
            return

        if getattr(view, 'layer', None) == WindowLayer.SUB_VIEW:
            self._last_seen_sub_view_alias = self._get_view_alias(view)

        if getattr(view, 'alias', None) == SCALEFORM_VIEW_ALIAS:
            return

        alias = self._get_view_alias(view)

        self._log_control_debug(
            'view_added_to_container',
            'alias={0} layer={1}'.format(alias, getattr(view, 'layer', None)),
        )

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
                self._log_control_debug('deferred_update_start')
                self._update()
                self._log_control_debug('deferred_update_end')
            except Exception:
                _logger.exception('Error in _deferred_update')

    # -- data collection -----------------------------------------------------

    def _update(self):
        if not _config.get('enabled'):
            return
        self._log_control_debug('update_begin')
        if not self._sync_scaleform_view('update_precheck'):
            self._log_control_debug('update_blocked_precheck')
            return
        if self._update_in_progress:
            self._log_control_debug('update_skipped_in_progress')
            return

        self._update_in_progress = True
        try:
            vehicle = g_currentVehicle.item
            if vehicle is None:
                self._log_control_debug('update_no_vehicle')
                return

            try:
                stats = self.itemsCache.items.stats
            except Exception:
                _logger.exception('itemsCache not ready')
                self._log_control_debug('update_no_stats')
                return

            self._log_control_debug('update_collect', 'vehicle={0}'.format(self._format_vehicle_item(vehicle)))
            data = self._collect(vehicle, stats)
            self._render(vehicle, data)
            self._log_control_debug('update_rendered', 'vehicle={0}'.format(self._format_vehicle_item(vehicle)))
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

        elite_progression = _collect_elite_progression(vehicle)

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
            'elite_progression': elite_progression,
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
                't11_action_nodes_researched': field_mods['t11_action_nodes_researched'],
                't11_action_nodes_unresearched': field_mods['t11_action_nodes_unresearched'],
                't11_action_probe_preview': field_mods['t11_action_probe_preview'],
                't11_action_probe_hits': field_mods['t11_action_probe_hits'],
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
            if fm.get('t11_action_probe_preview'):
                _logger.info(
                    '  Tier-11 DEBUG action probe: %s',
                    '; '.join(fm['t11_action_probe_preview'][:16])
                )
            if fm.get('t11_action_probe_hits'):
                _logger.info(
                    '  Tier-11 DEBUG action hints: %s',
                    '; '.join(fm['t11_action_probe_hits'][:20])
                )
            else:
                _logger.info('  Tier-11 DEBUG action hints: <none>')
            if fm.get('t11_settings_probe_hits'):
                _logger.info(
                    '  Tier-11 DEBUG settings hints: %s',
                    '; '.join(fm['t11_settings_probe_hits'][:20])
                )
            else:
                _logger.info('  Tier-11 DEBUG settings hints: <none>')
            if fm.get('t11_raw_tree_probe_hits'):
                _logger.info(
                    '  Tier-11 DEBUG raw-tree hints: %s',
                    '; '.join(fm['t11_raw_tree_probe_hits'][:20])
                )
            else:
                _logger.info('  Tier-11 DEBUG raw-tree hints: <none>')

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
        mode_preferences = _build_mode_preferences()
        if mode_preferences.get('showResearch'):
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
        elite_mode = mode_preferences.get('eliteMode')
        if elite_mode != _ELITE_MODE_OFF and el['total'] > 0:
            if elite_mode == _ELITE_MODE_CUSTOMIZATION_ONLY:
                lines.append('Elite: customization milestones only')
            else:
                lines.append('Elite mods: {0}% ({1}/{2})'.format(el['pct'], el['unlocked'], el['total']))

        vehicle_is_elite = bool(tt.get('is_elite'))
        fm = data['field_mods']
        show_field_mods = mode_preferences.get('showFieldMods')
        show_upgrades = mode_preferences.get('showUpgrades')
        if show_field_mods:
            if not vehicle_is_elite:
                lines.append('Field mods: requires elite vehicle status')
            elif not fm['exists']:
                lines.append('Field mods: not available for this vehicle')
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

            if (not fm['is_veh_skill_tree']) and vehicle_is_elite and fm['next_purchasable_step_id'] is not None:
                if fm['next_purchasable_step_xp'] is not None:
                    lines.append(
                        'Field mods next: {0} XP required'.format(
                            fm['next_purchasable_step_xp']
                        )
                    )
                else:
                    lines.append(
                        'Field mods next: step available at level {0}'.format(
                            fm['next_purchasable_step_level']
                        )
                    )

        if show_upgrades:
            if fm['is_veh_skill_tree'] and fm['total_steps'] > 0:
                pct = int(fm['unlocked_steps'] * 100 / fm['total_steps'])
                lines.append(
                    'Upgrades: {0}% ({1}/{2}, completion={3})'.format(
                        pct, fm['unlocked_steps'], fm['total_steps'], fm['completion_name']
                    )
                )
                lines.append('Upgrades: skill tree progress shown by steps')
            elif fm['is_veh_skill_tree']:
                lines.append('Upgrades: available but no steps resolved')

            if fm['is_veh_skill_tree'] and fm['next_purchasable_step_id'] is not None:
                if fm['next_purchasable_step_xp'] is not None:
                    lines.append(
                        'Upgrades next: {0} XP required'.format(
                            fm['next_purchasable_step_xp']
                        )
                    )
                else:
                    lines.append(
                        'Upgrades next: step available at level {0}'.format(
                            fm['next_purchasable_step_level']
                        )
                    )

        if show_field_mods or show_upgrades:
            self._log_field_mods_debug(vehicle, fm)

            tier_plan = fm.get('tier_plan') or {}
            if fm['is_veh_skill_tree']:
                pass
            elif not vehicle_is_elite:
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
