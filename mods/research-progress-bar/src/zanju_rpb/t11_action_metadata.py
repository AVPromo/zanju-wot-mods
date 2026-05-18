from __future__ import print_function, unicode_literals

import logging

from CurrentVehicle import g_currentVehicle
from gui.impl import backport
try:
    from gui.impl.gen.resources import R
except Exception:
    R = None
from helpers import i18n

from . import utils as _utils_api

_logger = logging.getLogger('zanju.researchprogressbar')

_clean_text_value = _utils_api._clean_text_value
_coerce_int_or_none = _utils_api._coerce_int_or_none
_safe_text = _utils_api._safe_text

_T11_UI_NAME_HOOK_SPECS = (
    ('gui.impl.lobby.vehicle_hub.sub_presenters.veh_skill_tree.utils', 'fillNodeModel'),
    ('gui.impl.lobby.veh_skill_tree.utils', 'fillNodeModel'),
)

_t11_ui_name_cache = {}
_t11_ui_name_change_callback = None
_t11_ui_name_hook_records = []


def _safe_method_text(step, method_name):
    try:
        method = getattr(step, method_name, None)
        if method is None or not callable(method):
            return False, '<missing>'
        value = method()
        return True, _safe_text(value, 120)
    except Exception as exc:
        return False, '<error:{0}>'.format(_safe_text(exc, 80))


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
    if callable(_t11_ui_name_change_callback):
        try:
            _t11_ui_name_change_callback('tier11_ui_name_capture')
        except Exception:
            _logger.exception('Failed to react to Tier-11 UI name capture (%s)', source_name)
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


def _install_t11_ui_name_hooks(on_ui_name_capture=None):
    global _t11_ui_name_change_callback

    _t11_ui_name_change_callback = on_ui_name_capture
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
    global _t11_ui_name_change_callback

    _t11_ui_name_change_callback = None
    while _t11_ui_name_hook_records:
        module, attr_name, original = _t11_ui_name_hook_records.pop()
        try:
            setattr(module, attr_name, original)
        except Exception:
            _logger.exception('Failed to detach Tier-11 UI name hook: %s.%s', module.__name__, attr_name)
