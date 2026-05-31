from __future__ import print_function, unicode_literals

import logging
import re

try:
    from CurrentVehicle import g_currentVehicle
except Exception:
    g_currentVehicle = None
try:
    from gui.Scaleform.daapi.view.lobby.veh_post_progression.veh_post_progression_vehicle import (
        g_postProgressionVehicle,
    )
except Exception:
    g_postProgressionVehicle = None

from . import utils as _utils_api

_logger = logging.getLogger('zanju.researchprogressbar')

_clean_text_value = _utils_api._clean_text_value
_coerce_int_or_none = _utils_api._coerce_int_or_none

try:
    _STRING_TYPES = (basestring,)
except NameError:
    _STRING_TYPES = (str,)

_ROLE_SLOT_TOOLTIP_HOOK_SPECS = (
    ('gui.impl.lobby.veh_post_progression.tooltips.role_slot_tooltip_view', 'RoleSlotTooltipView', '_onLoading'),
)

_role_slot_ui_cache = {}
_role_slot_ui_change_callback = None
_role_slot_ui_hook_records = []


def _get_current_vehicle_int_cd():
    if g_currentVehicle is None:
        return None

    try:
        vehicle = g_currentVehicle.item
    except Exception:
        vehicle = None
    return getattr(vehicle, 'intCD', None) if vehicle is not None else None


def _normalize_role_slot_category(value):
    cleaned = _clean_text_value(value)
    if cleaned is None:
        return None

    normalized = u'{0}'.format(cleaned).strip().lower()
    if not normalized:
        return None

    prefix = None
    for prefix in (
            '#tank_setup:categories/',
            'tank_setup:categories/',
            '#veh_post_progression:categories/',
            'veh_post_progression:categories/',
            'categories/'):
        if normalized.startswith(prefix):
            normalized = normalized[len(prefix):]
            break

    if '/' in normalized:
        parts = [part for part in normalized.split('/') if part]
        if parts:
            normalized = parts[-1]

    normalized = normalized.replace(' ', '_')
    if normalized == 'stealth':
        normalized = 'scouting'
    if normalized == 'reconnaissance':
        normalized = 'scouting'

    if normalized in ('special', 'universal', 'no_category', 'none', 'null', 'undefined'):
        return None

    if re.match(r'^[a-z_]+$', normalized) is None:
        return None
    return normalized


def _iter_role_slot_values(value, max_items=8):
    if value is None:
        return []
    if isinstance(value, _STRING_TYPES):
        return [value]

    if isinstance(value, dict):
        try:
            values = value.itervalues()
        except AttributeError:
            values = value.values()
        return [item for item in list(values)[:max_items] if item is not None]

    try:
        return [item for item in list(value)[:max_items] if item is not None]
    except Exception:
        return [value]


def _extract_role_slot_category_from_slot(slot):
    if slot is None:
        return None

    categories = getattr(slot, 'categories', None)
    if categories is not None:
        for category in _iter_role_slot_values(categories):
            normalized = _normalize_role_slot_category(category)
            if normalized:
                return normalized

    get_role = getattr(slot, 'getRole', None)
    if callable(get_role):
        normalized = _normalize_role_slot_category(get_role())
        if normalized:
            return normalized

    return _normalize_role_slot_category(slot)


def _extract_role_slot_ui_data_from_optional_devices(optional_devices):
    if optional_devices is None:
        return None

    available_categories = []
    seen = set()

    dyn_slot_type_options = getattr(optional_devices, 'dynSlotTypeOptions', None)
    for slot in _iter_role_slot_values(dyn_slot_type_options):
        normalized = _extract_role_slot_category_from_slot(slot)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        available_categories.append(normalized)

    if not available_categories:
        return None

    return {
        'available_categories': available_categories,
    }


def _extract_role_slot_ui_data_from_view_model(view_model):
    if view_model is None:
        return None

    available_categories = []
    seen = set()

    get_available_roles = getattr(view_model, 'getAvailableRoles', None)
    if callable(get_available_roles):
        for role_model in _iter_role_slot_values(get_available_roles()):
            normalized = _extract_role_slot_category_from_slot(role_model)
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            available_categories.append(normalized)

    if not available_categories:
        return None

    return {
        'available_categories': available_categories,
    }


def _merge_role_slot_ui_data(*data_sets):
    merged_categories = []
    seen = set()
    data_set = None

    for data_set in data_sets:
        if not isinstance(data_set, dict):
            continue
        category = None
        for category in data_set.get('available_categories') or []:
            normalized = _normalize_role_slot_category(category)
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            merged_categories.append(normalized)

    if not merged_categories:
        return None

    return {
        'available_categories': merged_categories,
    }


def _cache_role_slot_ui_data(vehicle_int_cd, level, ui_data, source_name):
    global _role_slot_ui_change_callback

    vehicle_key = _coerce_int_or_none(vehicle_int_cd)
    level_key = _coerce_int_or_none(level)
    merged_data = _merge_role_slot_ui_data(ui_data)
    if vehicle_key is None or merged_data is None:
        return False

    changed = False
    cache_keys = [(vehicle_key, level_key)]
    if level_key is not None:
        cache_keys.append((vehicle_key, None))

    cache_key = None
    for cache_key in cache_keys:
        if _role_slot_ui_cache.get(cache_key) == merged_data:
            continue
        _role_slot_ui_cache[cache_key] = dict(merged_data)
        changed = True

    if changed and callable(_role_slot_ui_change_callback):
        try:
            _role_slot_ui_change_callback('role_slot_ui_capture')
        except Exception:
            _logger.exception('Failed to react to role-slot UI capture (%s)', source_name)
    return changed


def _get_cached_role_slot_ui_data(vehicle_int_cd, level=None):
    vehicle_key = _coerce_int_or_none(vehicle_int_cd)
    level_key = _coerce_int_or_none(level)
    if vehicle_key is None:
        return None

    exact = _role_slot_ui_cache.get((vehicle_key, level_key))
    if exact is not None:
        return exact
    return _role_slot_ui_cache.get((vehicle_key, None))


def _resolve_live_role_slot_ui_data(vehicle_int_cd=None, level=None):
    if g_postProgressionVehicle is None:
        return None

    is_present = getattr(g_postProgressionVehicle, 'isPresent', None)
    if not callable(is_present):
        return None

    try:
        if not is_present():
            return None
    except Exception:
        return None

    current_vehicle_int_cd = _coerce_int_or_none(_get_current_vehicle_int_cd())
    requested_vehicle_int_cd = _coerce_int_or_none(vehicle_int_cd)
    if requested_vehicle_int_cd is not None and current_vehicle_int_cd is not None:
        if requested_vehicle_int_cd != current_vehicle_int_cd:
            return None

    try:
        default_item = getattr(g_postProgressionVehicle, 'defaultItem', None)
    except Exception:
        default_item = None

    optional_devices = getattr(default_item, 'optDevices', None)
    ui_data = _extract_role_slot_ui_data_from_optional_devices(optional_devices)
    vehicle_key = requested_vehicle_int_cd or current_vehicle_int_cd
    if ui_data is not None:
        _cache_role_slot_ui_data(vehicle_key, level, ui_data, 'live_opt_devices')
    return ui_data


def _resolve_vehicle_role_slot_ui_data(vehicle=None, level=None):
    if vehicle is None:
        return None

    vehicle_int_cd = _coerce_int_or_none(getattr(vehicle, 'intCD', None))
    optional_devices = getattr(vehicle, 'optDevices', None)
    ui_data = _extract_role_slot_ui_data_from_optional_devices(optional_devices)
    if ui_data is not None:
        _cache_role_slot_ui_data(vehicle_int_cd, level, ui_data, 'garage_opt_devices')
    return ui_data


def _extract_step_level(step):
    if step is None:
        return None

    level = getattr(step, 'level', None)
    if level is not None:
        return _coerce_int_or_none(level)

    get_level = getattr(step, 'getLevel', None)
    if callable(get_level):
        return _coerce_int_or_none(get_level())
    return None


def _capture_role_slot_ui_from_tooltip(view, step, source_name):
    vehicle_int_cd = _get_current_vehicle_int_cd()
    level = _extract_step_level(step)
    ui_data = _resolve_live_role_slot_ui_data(vehicle_int_cd, level)
    if ui_data is None:
        ui_data = _extract_role_slot_ui_data_from_view_model(getattr(view, 'viewModel', None))
        if ui_data is not None:
            _cache_role_slot_ui_data(vehicle_int_cd, level, ui_data, source_name)
    return ui_data


def _wrap_role_slot_tooltip_hook(module_name, owner_name, attr_name, original):
    def _wrapped(self, *args, **kwargs):
        result = original(self, *args, **kwargs)
        try:
            step = args[0] if args else kwargs.get('step')
            _capture_role_slot_ui_from_tooltip(
                self,
                step,
                '{0}.{1}.{2}'.format(module_name, owner_name, attr_name),
            )
        except Exception:
            _logger.exception(
                'Failed to capture role-slot UI metadata from %s.%s.%s',
                module_name,
                owner_name,
                attr_name,
            )
        return result

    _wrapped.__name__ = getattr(original, '__name__', attr_name)
    _wrapped.__doc__ = getattr(original, '__doc__', None)
    _wrapped._zanju_rpb_original = original
    return _wrapped


def _install_role_slot_ui_hooks(on_ui_capture=None):
    global _role_slot_ui_change_callback

    _role_slot_ui_change_callback = on_ui_capture
    if _role_slot_ui_hook_records:
        return len(_role_slot_ui_hook_records)

    module_name = None
    owner_name = None
    attr_name = None
    for module_name, owner_name, attr_name in _ROLE_SLOT_TOOLTIP_HOOK_SPECS:
        try:
            module = __import__(module_name, fromlist=[owner_name])
        except Exception:
            continue

        owner = getattr(module, owner_name, None)
        if owner is None:
            continue

        original = getattr(owner, attr_name, None)
        if not callable(original):
            continue
        if getattr(original, '_zanju_rpb_original', None) is not None:
            continue

        wrapped = _wrap_role_slot_tooltip_hook(module_name, owner_name, attr_name, original)
        setattr(owner, attr_name, wrapped)
        _role_slot_ui_hook_records.append((owner, attr_name, original))

    return len(_role_slot_ui_hook_records)


def _uninstall_role_slot_ui_hooks():
    global _role_slot_ui_change_callback

    _role_slot_ui_change_callback = None
    while _role_slot_ui_hook_records:
        owner, attr_name, original = _role_slot_ui_hook_records.pop()
        try:
            setattr(owner, attr_name, original)
        except Exception:
            _logger.exception('Failed to detach role-slot UI hook: %s.%s', owner.__name__, attr_name)


def _get_role_slot_ui_categories(vehicle=None, level=None):
    vehicle_int_cd = None
    if vehicle is not None:
        vehicle_int_cd = getattr(vehicle, 'intCD', None)

    garage_data = _resolve_vehicle_role_slot_ui_data(vehicle, level)
    live_data = _resolve_live_role_slot_ui_data(vehicle_int_cd, level)
    cached_data = _get_cached_role_slot_ui_data(vehicle_int_cd or _get_current_vehicle_int_cd(), level)
    merged_data = _merge_role_slot_ui_data(garage_data, live_data, cached_data)
    if merged_data is None:
        return []
    return merged_data.get('available_categories') or []
