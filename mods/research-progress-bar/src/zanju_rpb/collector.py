"""Collector helpers for research and tier-based field-mod progress."""
from __future__ import print_function, unicode_literals

import logging
import re

try:
    from gui.prestige import prestige_helpers as _prestige_helpers
except Exception:
    _prestige_helpers = None
try:
    from gui.impl import backport as _wg_backport
except Exception:
    _wg_backport = None
try:
    from gui.shared.gui_items import getKpiFormatDescription as _format_wg_kpi_description
except Exception:
    _format_wg_kpi_description = None
try:
    from gui.shared.items_parameters.param_name_helper import getVehicleParameterText as _wg_get_vehicle_parameter_text
except Exception:
    _wg_get_vehicle_parameter_text = None
try:
    from gui.shared.items_parameters.formatters import formatParameter as _wg_format_parameter_value
except Exception:
    _wg_format_parameter_value = None
try:
    import gui.shared.items_parameters.formatters as _wg_parameter_formatters
except Exception:
    _wg_parameter_formatters = None
from gui.shared.gui_items import GUI_ITEM_TYPE, GUI_ITEM_TYPE_NAMES
from items import getTypeOfCompactDescr
try:
    from post_progression_common import GROUP_ID_BY_FEATURE as _POST_PROGRESSION_GROUP_ID_BY_FEATURE
except Exception:
    _POST_PROGRESSION_GROUP_ID_BY_FEATURE = {
        'shells_consumables_switch': 1,
        'opt_dev_boosters_switch': 2,
    }

from .constants import _TIER_FIELD_MOD_RULES, _UNLOCK_MARKER_TYPE_BY_GUI_NAME
from .role_slot_ui_metadata import _get_role_slot_ui_categories
from .utils import _clean_text_value, _extract_sequence_ints, _mapping_value, _to_int_or_none

_logger = logging.getLogger('zanju.researchprogressbar')

try:
    _STRING_TYPES = (basestring,)
except NameError:
    _STRING_TYPES = (str,)

_HYPOTHETICAL_T11_XP_COST = 325000


def _resolve_post_progression_step_id(step):
    step_id = getattr(step, 'stepID', None)
    if step_id is None:
        step_id = getattr(step, 'id', None)
    return step_id


def _resolve_post_progression_step_level(step):
    level = getattr(step, 'level', None)
    if level is None and hasattr(step, 'getLevel'):
        try:
            level = step.getLevel()
        except Exception:
            level = None
    return level


def _resolve_post_progression_step_action(step):
    for attr_name in ('action', '_PostProgressionStepItem__action'):
        try:
            action = getattr(step, attr_name, None)
        except Exception:
            action = None
        if action is not None:
            return action
    return None


def _resolve_post_progression_step_reachable(step):
    """Whether an unresearched step is currently researchable -- its tree
    prerequisites are satisfied so the game would let you unlock it now.

    Uses the client's own per-step state machine. A step's state is one of
    RESTRICTED / LOCKED / UNLOCKED / RECEIVED, and the UNLOCKED state means "the
    node's unlockStrategy (any/all) is satisfied over its requiredUnlocks, but it
    is not yet bought" -- i.e. reachable. RECEIVED means already bought, LOCKED
    means no prerequisite path is unlocked yet. `step.isUnlocked()` is exactly the
    UNLOCKED test (note the name clash: the collector's "unlocked step ids" set is
    the RECEIVED/bought state, the opposite end of the lifecycle).

    Returns True/False, or None when the state cannot be read (older client), so
    callers can fall back to treating the node as reachable rather than hiding it.
    """
    method = getattr(step, 'isUnlocked', None)
    if not callable(method):
        return None
    try:
        return bool(method())
    except Exception:
        return None


def _extract_post_progression_repr_token(value, token_name):
    try:
        text = repr(value)
    except Exception:
        return None

    match = re.search(r'%s: ([^>,]+)' % re.escape(token_name), text)
    if match is None:
        return None

    token = match.group(1)
    if token is None:
        return None
    return token.strip()


def _resolve_post_progression_action_name(action):
    for attr_name in ('name', '_name', '_PostProgressionAction__name', '_PostProgressionModItem__name'):
        try:
            value = getattr(action, attr_name, None)
        except Exception:
            value = None
        if value:
            return value

    return _extract_post_progression_repr_token(action, 'name')


def _resolve_post_progression_action_category(action):
    if action is None:
        return None

    for method_name in ('getSlotCategory',):
        try:
            method = getattr(action, method_name, None)
        except Exception:
            method = None
        if callable(method):
            try:
                value = method()
            except Exception:
                value = None
            if value:
                return value

    for attr_name in (
            'category',
            '_category',
            '_RoleSlotModItem__category',
            '_RoleSlotModItem__slotCategory',
            '_RoleSlotModItem__slot_category'):
        try:
            value = getattr(action, attr_name, None)
        except Exception:
            value = None
        if value:
            return value

    return _extract_post_progression_repr_token(action, 'category')


def _normalize_post_progression_category(value):
    cleaned = _clean_text_value(value)
    if cleaned is None:
        return None

    normalized = cleaned.strip().lower()
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
    if normalized in ('', 'no_category', 'none', 'null', 'undefined'):
        return None

    if re.match(r'^[a-z_]+$', normalized) is None:
        return None

    return normalized


def _resolve_role_slot_available_categories(vehicle, level=None):
    ui_categories = _get_role_slot_ui_categories(vehicle, level)
    if not ui_categories:
        return []

    merged_categories = []
    seen = set()
    category = None
    for category in ui_categories:
        normalized = _normalize_post_progression_category(category)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        merged_categories.append(normalized)
    return merged_categories


def _resolve_post_progression_action_class_name(action):
    if action is None:
        return None
    return getattr(action, '__class__', type(action)).__name__


def _call_post_progression_method(pp, method_name, *args):
    try:
        method = getattr(pp, method_name, None)
    except Exception:
        method = None

    if not callable(method):
        return None

    try:
        return method(*args)
    except Exception:
        return None


def _call_post_progression_bool(pp, method_name, *args):
    value = _call_post_progression_method(pp, method_name, *args)
    if value is None:
        return None
    return bool(value)


def _call_post_progression_state_bool(state, method_name, *args):
    try:
        method = getattr(state, method_name, None)
    except Exception:
        method = None

    if not callable(method):
        return None

    try:
        return bool(method(*args))
    except Exception:
        return None


def _resolve_wg_resource_text(resource):
    if resource is None:
        return None

    if _wg_backport is not None:
        try:
            text = _wg_backport.text(resource)
        except Exception:
            text = None
        if text:
            return text

    if callable(resource):
        try:
            resource = resource()
        except Exception:
            return None

    if resource is None:
        return None
    return u'{0}'.format(resource)


def _normalize_post_progression_feature_identifier(value):
    text = _clean_text_value(value)
    if text is None:
        return None
    return re.sub(r'[^a-z0-9]+', '', text.lower())


def _resolve_post_progression_feature_group_id(action_name):
    normalized_action_name = _normalize_post_progression_feature_identifier(action_name)
    if not normalized_action_name:
        return None

    candidate_name = None
    candidate_group_id = None
    try:
        items = _POST_PROGRESSION_GROUP_ID_BY_FEATURE.iteritems()
    except AttributeError:
        items = _POST_PROGRESSION_GROUP_ID_BY_FEATURE.items()

    for candidate_name, candidate_group_id in items:
        if _normalize_post_progression_feature_identifier(candidate_name) == normalized_action_name:
            return _to_int_or_none(candidate_group_id)

    return None


def _normalize_t11_action_identifier(value):
    text = _clean_text_value(value)
    if text is None:
        return None
    return re.sub(r'[^a-z0-9]+', '', text.lower())


def _classify_t11_action_kind(action_name=None, image_name=None, action_class_name=None):
    if action_class_name == 'RoleSlotModItem':
        return 'role_slot'
    if action_class_name == 'FeatureModItem':
        return 'feature'

    identifier = None
    for identifier in (action_name, image_name):
        normalized_identifier = _normalize_t11_action_identifier(identifier)
        if normalized_identifier == 'roleslot':
            return 'role_slot'
        if normalized_identifier in (
                'shellsconsumablesswitch',
                'optdevboostersswitch',
                'shellsconsumablesoptdevboostersswitch'):
            return 'feature'

    return ''


def _resolve_post_progression_setup_switch_active(pp, state, vehicle, feature_group_id):
    if feature_group_id is None:
        return False

    # `isSetupSwitchActive()` only tells us the feature is available for the vehicle.
    # The actual per-loadout toggle state lives in the disabled-switch state.
    setup_switch_available = _call_post_progression_bool(
        pp,
        'isSetupSwitchActive',
        vehicle,
        feature_group_id,
    )
    if setup_switch_available is False:
        return False

    switch_disabled = _call_post_progression_state_bool(
        state,
        'isSwitchDisabled',
        feature_group_id,
    )
    if switch_disabled is None:
        switch_disabled = _call_post_progression_bool(
            pp,
            'isPrebattleSwitchDisabled',
            feature_group_id,
        )

    if switch_disabled is not None:
        return not switch_disabled

    return bool(setup_switch_available)


def _resolve_post_progression_selected_modification(action):
    if action is None:
        return None

    for method_name in ('getPurchasedModification',):
        try:
            method = getattr(action, method_name, None)
        except Exception:
            method = None
        if not callable(method):
            continue
        try:
            selected_modification = method()
        except Exception:
            selected_modification = None
        if selected_modification is not None:
            return selected_modification

    return None


def _call_post_progression_action_method(action, method_name, *args):
    if action is None:
        return None

    try:
        method = getattr(action, method_name, None)
    except Exception:
        method = None

    if not callable(method):
        return None

    try:
        return method(*args)
    except Exception:
        return None


def _normalize_post_progression_modification_collection(value):
    if value is None:
        return []

    if isinstance(value, dict):
        try:
            values = value.itervalues()
        except AttributeError:
            values = value.values()
        return [item for item in values if item is not None]

    try:
        items = list(value)
    except Exception:
        items = None

    if not isinstance(items, list):
        return []
    return [item for item in items if item is not None]


def _iter_post_progression_dual_modifications(action):
    method_name = None
    attr_name = None
    for method_name in ('getModifications', 'iterModifications', 'getAvailableModifications'):
        modifications = _normalize_post_progression_modification_collection(
            _call_post_progression_action_method(action, method_name)
        )
        if len(modifications) >= 2:
            return modifications

    for attr_name in ('modifications', '_modifications', '_MultiModsItem__modifications'):
        try:
            value = getattr(action, attr_name, None)
        except Exception:
            value = None
        modifications = _normalize_post_progression_modification_collection(value)
        if len(modifications) >= 2:
            return modifications

    return []


def _resolve_post_progression_dual_choice_index_from_name(modification_name):
    if not modification_name:
        return None

    match = re.search(r'_(1|2)$', u'{0}'.format(modification_name))
    if match is None:
        return None
    return int(match.group(1))


def _resolve_post_progression_dual_choice_index_from_modification(action, modification):
    if modification is None:
        return None

    modification_name = _resolve_post_progression_action_name(modification)
    derived_choice_index = _resolve_post_progression_dual_choice_index_from_name(modification_name)
    if derived_choice_index is not None:
        return derived_choice_index

    modifications = _iter_post_progression_dual_modifications(action)
    if not modifications:
        return None

    index = None
    candidate = None
    for index, candidate in enumerate(modifications[:2], 1):
        if candidate is modification:
            return index
        if modification_name and _resolve_post_progression_action_name(candidate) == modification_name:
            return index

    return None


def _resolve_post_progression_dual_selected_choice_index(action, raw_choice_index, selected_modification):
    normalized_choice_index = _to_int_or_none(raw_choice_index)
    if normalized_choice_index in (1, 2):
        return normalized_choice_index

    if normalized_choice_index is not None and normalized_choice_index > 0:
        derived_modification = _call_post_progression_action_method(
            action,
            'getModificationByID',
            normalized_choice_index,
        )
        derived_choice_index = _resolve_post_progression_dual_choice_index_from_modification(
            action,
            derived_modification,
        )
        if derived_choice_index is not None:
            return derived_choice_index

    if normalized_choice_index is not None and normalized_choice_index <= 0:
        return None

    return _resolve_post_progression_dual_choice_index_from_modification(action, selected_modification)


def _clean_post_progression_text(text):
    cleaned = _clean_text_value(text)
    if cleaned is None:
        return None

    cleaned = (
        cleaned.replace('&nbsp;', ' ')
        .replace('&lt;', '<')
        .replace('&gt;', '>')
        .replace('&amp;', '&')
    )
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned or None


def _clean_post_progression_kpi_label_text(text):
    cleaned = _clean_post_progression_text(text)
    if cleaned in (None, '0'):
        return None
    return cleaned


def _resolve_post_progression_parameter_label_text(parameter_name, is_positive, is_long=False):
    if _wg_get_vehicle_parameter_text is None or not parameter_name:
        return None

    try:
        return _clean_post_progression_kpi_label_text(
            _resolve_wg_resource_text(
                _wg_get_vehicle_parameter_text(
                    paramName=parameter_name,
                    isPositive=is_positive,
                    isLong=is_long,
                )
            )
        )
    except Exception:
        return None


def _resolve_post_progression_kpi_label_text(kpi_name, is_positive):
    return _resolve_post_progression_parameter_label_text(kpi_name, is_positive, is_long=False)


def _resolve_post_progression_preferred_label_text(parameter_name, is_positive):
    label = _resolve_post_progression_parameter_label_text(parameter_name, is_positive, is_long=False)
    if label:
        return label
    return _resolve_post_progression_parameter_label_text(parameter_name, is_positive, is_long=True)


def _resolve_post_progression_kpi_is_positive(kpi):
    if kpi is None:
        return None

    is_positive = _resolve_post_progression_is_positive(
        getattr(kpi, 'value', None),
        getattr(kpi, 'type', None),
    )
    if is_positive is None:
        return not bool(getattr(kpi, 'isDebuff', False))
    return is_positive


def _resolve_post_progression_is_positive(value, kpi_type):
    try:
        numeric_value = float(value)
    except Exception:
        return None

    cmp_value = 0.0 if kpi_type == 'add' else 1.0
    return numeric_value >= cmp_value


def _resolve_post_progression_kpi_numeric_values(value, kpi_type):
    try:
        numeric_value = float(value)
    except Exception:
        return None, None

    display_value = numeric_value
    if kpi_type == 'mul':
        display_value = (numeric_value - 1.0) * 100.0
    return numeric_value, display_value


def _resolve_post_progression_kpi_sign(display_value, force_positive=False):
    if display_value is None:
        return ''
    if force_positive:
        return '+'
    if display_value > 0:
        return '+'
    if display_value < 0:
        return '-'
    return ''


# \u2212 is the Unicode MINUS SIGN, which some WoT value formatters emit for negatives
# instead of the ASCII hyphen. The \u escape keeps this source file ASCII-only.
_LEADING_SIGN_STRIP_RE = re.compile(u'^\\s*[+\\-\u2212]\\s*')
_LEADING_SIGN_MATCH_RE = re.compile(u'^\\s*[+\\-\u2212]')


def _strip_post_progression_kpi_sign(text):
    cleaned = _clean_post_progression_text(text)
    if cleaned is None:
        return None
    cleaned = _LEADING_SIGN_STRIP_RE.sub('', cleaned)
    return cleaned or None


def _has_post_progression_kpi_sign(text):
    cleaned = _clean_post_progression_text(text)
    if cleaned is None:
        return False
    return _LEADING_SIGN_MATCH_RE.match(cleaned) is not None


def _replace_post_progression_fmt_in_text(text, original_fmt, adjusted_fmt):
    cleaned_text = _clean_post_progression_text(text)
    cleaned_original_fmt = _clean_post_progression_text(original_fmt)
    cleaned_adjusted_fmt = _clean_post_progression_text(adjusted_fmt)

    if cleaned_text is None or not cleaned_original_fmt or not cleaned_adjusted_fmt:
        return text
    if cleaned_original_fmt == cleaned_adjusted_fmt:
        return cleaned_text
    if cleaned_original_fmt not in cleaned_text:
        return cleaned_text

    return cleaned_text.replace(cleaned_original_fmt, cleaned_adjusted_fmt, 1)


def _adjust_post_progression_targeted_formatted_value_text(
        formatted_value_text,
        raw_value,
        kpi_type=None,
        force_mul_delta=False):
    cleaned_formatted_value_text = _clean_post_progression_text(formatted_value_text)
    if cleaned_formatted_value_text is None:
        return formatted_value_text

    try:
        numeric_value = float(raw_value)
    except Exception:
        return formatted_value_text

    if force_mul_delta and kpi_type == 'mul':
        if '%' not in cleaned_formatted_value_text:
            return formatted_value_text

        delta_percent = (numeric_value - 1.0) * 100.0
        return _format_post_progression_fallback_value_text(
            delta_percent,
            kpi_name='value',
            kpi_type='add',
        )

    return formatted_value_text


def _format_post_progression_fallback_value_text(display_value, kpi_name=None, kpi_type=None, force_positive=False):
    if display_value is None:
        return None

    magnitude = abs(display_value) if force_positive or display_value < 0 else display_value
    rounded_value = round(magnitude, 2)
    if int(rounded_value) == rounded_value:
        value_text = str(int(rounded_value))
    else:
        value_text = ('%.2f' % rounded_value).rstrip('0').rstrip('.')

    sign = _resolve_post_progression_kpi_sign(display_value, force_positive)
    if sign:
        value_text = sign + value_text

    cleaned_name = _clean_text_value(kpi_name)
    if kpi_type == 'mul' or cleaned_name == 'value':
        value_text += '%'
    return value_text


def _resolve_post_progression_kpi_formatted_value_text(kpi_name, value, kpi_type, force_positive=False):
    numeric_value, display_value = _resolve_post_progression_kpi_numeric_values(value, kpi_type)
    if numeric_value is None:
        return None

    formatted_value_text = None
    if _wg_format_parameter_value is not None and kpi_name:
        source_value = abs(numeric_value) if force_positive else numeric_value
        try:
            formatted_value_text = _clean_post_progression_text(
                _wg_format_parameter_value(
                    kpi_name,
                    round(source_value, 3),
                    None,
                    None,
                    None,
                    False,
                    True,
                )
            )
        except Exception:
            formatted_value_text = None

    if formatted_value_text and formatted_value_text != '--':
        if _has_post_progression_kpi_sign(formatted_value_text):
            return formatted_value_text
        stripped_text = _strip_post_progression_kpi_sign(formatted_value_text)
        sign = _resolve_post_progression_kpi_sign(display_value, force_positive)
        if stripped_text:
            return sign + stripped_text if sign else stripped_text

    return _format_post_progression_fallback_value_text(display_value, kpi_name, kpi_type, force_positive)


def _resolve_post_progression_regular_param_description(parameter_name, is_positive):
    return _resolve_post_progression_preferred_label_text(parameter_name, is_positive)


def _resolve_post_progression_regular_param_measure_unit_text(parameter_name, vehicle):
    if not parameter_name or vehicle is None or _wg_parameter_formatters is None:
        return None

    try:
        return _clean_post_progression_text(
            _wg_parameter_formatters.getMeasureUnitsForParameter(
                getattr(vehicle, 'descriptor', None),
                parameter_name,
            )
        )
    except Exception:
        return None


def _resolve_post_progression_regular_param_formatted_value_text(parameter_name, value, kpi_type, vehicle):
    if not parameter_name or vehicle is None:
        return None

    numeric_value, display_value = _resolve_post_progression_kpi_numeric_values(value, kpi_type)
    if numeric_value is None:
        return None

    if kpi_type == 'mul':
        return _format_post_progression_fallback_value_text(display_value, parameter_name, kpi_type)

    if _wg_parameter_formatters is None:
        return None

    raw_value = numeric_value
    try:
        settings = _wg_parameter_formatters.FORMAT_SETTINGS.get(
            parameter_name,
            _wg_parameter_formatters._listFormat,
        )
    except Exception:
        settings = None
    if not settings:
        return None

    formatted_value_text = None
    try:
        preprocessor = settings.get('preprocessor')
        parameter_state = None
        values = raw_value
        separator = None
        if preprocessor:
            values, separator, parameter_state = preprocessor(raw_value, None)

        if isinstance(values, (tuple, list)):
            if parameter_state is None:
                parameter_state = [None] * len(values)
            params = []
            current_value = None
            current_state = None
            for current_value, current_state in zip(values, parameter_state):
                params.append(
                    _wg_parameter_formatters._applyFormat(
                        current_value,
                        current_state,
                        settings,
                        False,
                        None,
                    )
                )
            separator = separator or settings.get('separator', '')
            formatted_value_text = separator.join(params)
        else:
            formatted_value_text = _wg_parameter_formatters._applyFormat(
                values,
                parameter_state,
                settings,
                False,
                None,
            )
    except Exception:
        formatted_value_text = None

    formatted_value_text = _clean_post_progression_text(formatted_value_text)
    if not formatted_value_text or formatted_value_text == '--':
        return None

    if _has_post_progression_kpi_sign(formatted_value_text):
        measure_unit_text = _resolve_post_progression_regular_param_measure_unit_text(parameter_name, vehicle)
        if measure_unit_text:
            return u'{0} {1}'.format(formatted_value_text, measure_unit_text)
        return formatted_value_text

    stripped_value_text = _strip_post_progression_kpi_sign(formatted_value_text)
    sign = _resolve_post_progression_kpi_sign(display_value)
    if stripped_value_text:
        formatted_value_text = sign + stripped_value_text if sign else stripped_value_text

    measure_unit_text = _resolve_post_progression_regular_param_measure_unit_text(parameter_name, vehicle)

    if measure_unit_text:
        return u'{0} {1}'.format(formatted_value_text, measure_unit_text)
    return formatted_value_text


def _resolve_post_progression_kpi_description(kpi, is_positive=None):
    if kpi is None:
        return None

    kpi_name = getattr(kpi, 'name', None)
    if not kpi_name:
        return None

    if is_positive is None:
        is_positive = _resolve_post_progression_kpi_is_positive(kpi)

    return _resolve_post_progression_preferred_label_text(kpi_name, is_positive)


def _resolve_post_progression_kpi_line(
        kpi,
        vehicle=None,
        parameter_name=None,
        force_mul_delta=False):
    if kpi is None:
        return None

    kpi_name = getattr(kpi, 'name', None)
    kpi_value = getattr(kpi, 'value', None)
    kpi_type = getattr(kpi, 'type', None)
    resolved_param_name = _clean_text_value(parameter_name)
    is_debuff = bool(getattr(kpi, 'isDebuff', False))
    positive_label = _resolve_post_progression_kpi_label_text(kpi_name, True)
    negative_label = _resolve_post_progression_kpi_label_text(kpi_name, False)
    description = None
    if resolved_param_name:
        description = _resolve_post_progression_regular_param_description(resolved_param_name, not is_debuff)
    if description is None:
        description = _clean_post_progression_text(
            _resolve_post_progression_kpi_description(kpi, is_positive=not is_debuff)
        )

    formatted_value_text = None
    if resolved_param_name:
        formatted_value_text = _resolve_post_progression_regular_param_formatted_value_text(
            resolved_param_name,
            kpi_value,
            kpi_type,
            vehicle,
        )
    if formatted_value_text is None:
        formatted_value_text = _resolve_post_progression_kpi_formatted_value_text(
            kpi_name,
            kpi_value,
            kpi_type,
        )

    original_formatted_value_text = formatted_value_text

    text = description
    if description and formatted_value_text:
        text = u'{0} {1}'.format(formatted_value_text, description)
    elif description is None:
        text = formatted_value_text

    formatted_value_text = _adjust_post_progression_targeted_formatted_value_text(
        original_formatted_value_text,
        kpi_value,
        kpi_type=kpi_type,
        force_mul_delta=force_mul_delta,
    )
    if formatted_value_text != original_formatted_value_text:
        text = _replace_post_progression_fmt_in_text(
            text,
            original_formatted_value_text,
            formatted_value_text,
        )

    if not text:
        return None

    return {
        'text': text,
        'is_debuff': is_debuff,
        'kpi_name': kpi_name,
        'kpi_value': kpi_value,
        'kpi_type': kpi_type,
        'param_name': resolved_param_name,
        'positive_label': positive_label,
        'negative_label': negative_label,
        'formatted_value_text': formatted_value_text,
    }


def _build_post_progression_kpi_lines(modification, vehicle):
    if modification is None or vehicle is None:
        return []

    try:
        kpis = modification.getKpi(vehicle) or []
    except Exception:
        return []

    lines = []
    index = None
    kpi = None
    for index, kpi in enumerate(kpis):
        line = _resolve_post_progression_kpi_line(
            kpi,
            vehicle=vehicle,
            force_mul_delta=True,
        )
        if not line:
            continue
        lines.append(line)

    return lines


def _build_post_progression_dual_available_choices(action, vehicle):
    modifications = _iter_post_progression_dual_modifications(action)
    choices = []
    position = None
    modification = None

    for position, modification in enumerate(modifications[:2], 1):
        choice_index = _resolve_post_progression_dual_choice_index_from_modification(action, modification)
        if choice_index not in (1, 2):
            choice_index = position
        choice_lines = _build_post_progression_kpi_lines(
            modification,
            vehicle,
        )
        choices.append({
            'choice_index': choice_index,
            'modification_id': _resolve_post_progression_modification_id(modification),
            'mod_name': _resolve_post_progression_action_name(modification),
            'lines': choice_lines,
        })

    return sorted(choices, key=lambda item: item.get('choice_index') or 99)


def _resolve_post_progression_modification_id(modification):
    """The modification's own id, as PURCHASE_POST_PROGRESSION_PAIR expects it.

    WG identifies a pair modification by its `actionID` (MultiModsItem.getPurchasedID
    returns `modifications[idx].actionID`, and getModificationByID keys on it).
    """
    value = getattr(modification, 'actionID', None)
    if value is None:
        value = getattr(modification, 'id', None)
    return _to_int_or_none(value)


def _normalize_post_progression_pairs(state):
    raw_pairs = None

    for attr_name in ('pairs', '_pairs'):
        try:
            raw_pairs = getattr(state, attr_name, None)
        except Exception:
            raw_pairs = None
        if raw_pairs is not None:
            break

    if not isinstance(raw_pairs, dict):
        return {}

    pairs = {}
    for step_id, choice_index in raw_pairs.iteritems():
        normalized_step_id = _to_int_or_none(step_id)
        normalized_choice_index = _to_int_or_none(choice_index)
        if normalized_step_id is None or normalized_choice_index is None:
            continue
        pairs[normalized_step_id] = normalized_choice_index
    return pairs


def _build_regular_field_mod_level_details(pp, state, vehicle=None):
    level_details = {}
    grouped_steps = {}
    state_pairs = _normalize_post_progression_pairs(state)
    role_slot_active = _call_post_progression_bool(pp, 'isRoleSlotActive', vehicle)

    try:
        steps = list(pp.iterUnorderedSteps())
    except Exception:
        _logger.exception('Failed to iterate regular post-progression steps')
        return level_details

    step = None
    for step in steps:
        level = _resolve_post_progression_step_level(step)
        step_id = _to_int_or_none(_resolve_post_progression_step_id(step))
        action = _resolve_post_progression_step_action(step)
        if level is None or step_id is None or action is None:
            continue

        grouped_steps.setdefault(level, []).append({
            'step_id': step_id,
            'action': action,
            'action_name': _resolve_post_progression_action_name(action),
            'action_class_name': _resolve_post_progression_action_class_name(action),
            'category': _resolve_post_progression_action_category(action),
        })

    level = None
    entries = None
    for level, entries in grouped_steps.iteritems():
        feature_entry = None
        role_slot_entry = None
        multi_entry = None
        leveled_entry = None

        entry = None
        for entry in entries:
            action_class_name = entry.get('action_class_name')
            if action_class_name == 'FeatureModItem':
                feature_entry = entry
            elif action_class_name == 'RoleSlotModItem':
                role_slot_entry = entry
            elif action_class_name == 'MultiModsItem':
                multi_entry = entry
            if action_class_name != 'MultiModsItem' and leveled_entry is None:
                leveled_entry = entry

        # A level's purchasable step is its LEVELED base step (SimpleModItem /
        # FeatureModItem / RoleSlotModItem, paid in XP). The MultiModsItem that
        # often shares the level is that step's free child holding the two
        # selectable variants -- it costs nothing and cannot be researched, so
        # it must never be the click target.
        research_step_id = leveled_entry.get('step_id') if leveled_entry else None

        if feature_entry is not None:
            feature_group_id = _resolve_post_progression_feature_group_id(feature_entry.get('action_name'))
            level_details[level] = {
                'kind': 'feature',
                'research_step_id': research_step_id,
                'feature_group_id': feature_group_id,
                'action_name': feature_entry.get('action_name'),
                'is_active': _resolve_post_progression_setup_switch_active(
                    pp,
                    state,
                    vehicle,
                    feature_group_id,
                ),
            }
            continue

        if role_slot_entry is not None:
            level_details[level] = {
                'kind': 'role_slot',
                'research_step_id': research_step_id,
                'action_name': role_slot_entry.get('action_name'),
                'category': role_slot_entry.get('category'),
                'categories': _resolve_role_slot_available_categories(vehicle, level),
                'is_active': bool(role_slot_active),
            }
            continue

        if multi_entry is not None:
            multi_action = multi_entry.get('action')
            selected_modification = _resolve_post_progression_selected_modification(multi_action)
            raw_selected_choice_index = state_pairs.get(multi_entry.get('step_id'))
            selected_mod_name = _resolve_post_progression_action_name(selected_modification)
            selected_choice_lines = _build_post_progression_kpi_lines(
                selected_modification,
                vehicle,
            )
            selected_choice_index = _resolve_post_progression_dual_selected_choice_index(
                multi_action,
                raw_selected_choice_index,
                selected_modification,
            )
            level_details[level] = {
                'kind': 'dual',
                'research_step_id': research_step_id,
                # The MultiModsItem's own step id, used to reach the action for a
                # PURCHASE_POST_PROGRESSION_PAIR pick (distinct from research_step_id,
                # which is the leveled base step researched to unlock the level).
                'pair_step_id': multi_entry.get('step_id'),
                'multi_action_name': multi_entry.get('action_name'),
                'selected_choice_index': selected_choice_index,
                'selected_mod_name': selected_mod_name,
                'selected_choice_lines': selected_choice_lines,
                'available_choices': _build_post_progression_dual_available_choices(multi_action, vehicle),
            }
            continue

        # Plain research levels have no special display data, but the marker click
        # action still needs their purchasable step id. Every tooltip/display
        # consumer treats the 'plain' kind the same as a missing detail entry.
        level_details[level] = {
            'kind': 'plain',
            'research_step_id': research_step_id,
        }

    return level_details


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


def _is_vehicle_module_unlock(intcd):
    """Whether tech-tree unlock `intcd` is a vehicle module (gun / turret / engine /
    chassis / radio) rather than a vehicle.

    Mirrors WG's own `itemTypeID in GUI_ITEM_TYPE.VEHICLE_MODULES` gate -- the game
    only offers a buy-and-mount dialog for modules, and its buy action rejects
    anything else. Vehicles (and any non-module unlock) return False.
    """
    try:
        return int(getTypeOfCompactDescr(intcd)) in GUI_ITEM_TYPE.VEHICLE_MODULES
    except Exception:
        return False


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


def _build_unlock_marker(
    xp_cost,
    intcd,
    items=None,
    is_available=True,
    missing_prereq_intcds=(),
    blueprint_info=None,
):
    item_type = _resolve_unlock_item_type(intcd)
    marker = {
        'xp_cost': xp_cost,
        'intcd': intcd,
        'item_type': item_type,
        'name': _resolve_unlock_display_name(intcd, items),
        'is_available': is_available,
        'missing_prereq_names': _resolve_unlock_display_names(missing_prereq_intcds, items),
        'missing_prereqs': [_build_unlock_marker_ref(prereq_intcd, items) for prereq_intcd in missing_prereq_intcds],
    }

    if blueprint_info:
        marker['blueprint_count'] = blueprint_info.get('count')
        marker['blueprint_total'] = blueprint_info.get('total')
        marker['blueprint_discount_percent'] = blueprint_info.get('discount_percent')

    return marker


def _resolve_unlock_vehicle_level(unlock_item):
    if unlock_item is None:
        return None

    level = _to_int_or_none(getattr(unlock_item, 'level', None))
    if level is not None:
        return level

    descriptor = getattr(unlock_item, 'descriptor', None)
    if descriptor is not None:
        level = _to_int_or_none(getattr(descriptor, 'level', None))
        if level is not None:
            return level

        type_descr = getattr(descriptor, 'type', None)
        if type_descr is not None:
            level = _to_int_or_none(getattr(type_descr, 'level', None))
            if level is not None:
                return level

    return None


def _extract_int_pair(value):
    values = _extract_sequence_ints(value, 2)
    if len(values) >= 2:
        return values[0], values[1]
    return None, None


def _resolve_vehicle_runtime_flag(vehicle, attr_names):
    attr_name = None
    for attr_name in attr_names:
        try:
            value = getattr(vehicle, attr_name, None)
        except Exception:
            value = None

        if callable(value):
            try:
                value = value()
            except Exception:
                value = None

        if value is not None:
            return bool(value)

    return None


def _normalize_vehicle_runtime_tag(value):
    cleaned_value = _clean_text_value(value)
    if cleaned_value is None:
        return None
    return re.sub(r'[^a-z0-9]+', '', cleaned_value.lower()) or None


def _resolve_vehicle_runtime_tags(vehicle):
    tags = set()
    sources = []

    descriptor = getattr(vehicle, 'descriptor', None)
    vehicle_type = getattr(descriptor, 'type', None) if descriptor is not None else None
    for source in (
            getattr(vehicle, 'tags', None),
            getattr(vehicle_type, 'tags', None),
            getattr(vehicle_type, 'typeTags', None)):
        if source is None or isinstance(source, _STRING_TYPES):
            continue
        sources.append(source)

    source = None
    for source in sources:
        try:
            values = list(source)
        except Exception:
            continue
        tag = None
        for tag in values:
            normalized_tag = _normalize_vehicle_runtime_tag(tag)
            if normalized_tag:
                tags.add(normalized_tag)

    return tags


def _resolve_hypothetical_t11_vehicle_probe(vehicle, vehicle_tier):
    if vehicle is None:
        return False

    vehicle_flags = {
        'is_premium': _resolve_vehicle_runtime_flag(vehicle, ('isPremium',)),
        'is_premium_igr': _resolve_vehicle_runtime_flag(vehicle, ('isPremiumIGR',)),
        'is_special': _resolve_vehicle_runtime_flag(vehicle, ('isSpecial',)),
        'is_reward': _resolve_vehicle_runtime_flag(vehicle, ('isReward',)),
        'is_collectible': _resolve_vehicle_runtime_flag(vehicle, ('isCollectible', 'isCollectibleVehicle')),
        'is_collector_vehicle': _resolve_vehicle_runtime_flag(vehicle, ('isCollectorVehicle',)),
    }
    vehicle_tags = _resolve_vehicle_runtime_tags(vehicle)

    is_collector = bool(
        vehicle_flags.get('is_collectible')
        or vehicle_flags.get('is_collector_vehicle')
        or vehicle_tags.intersection(frozenset(('collector', 'collectorvehicle')))
    )
    is_premium = bool(
        vehicle_flags.get('is_premium')
        or vehicle_flags.get('is_premium_igr')
        or vehicle_tags.intersection(frozenset(('premium', 'premiumigr')))
    )
    is_special = bool(
        vehicle_flags.get('is_special')
        or vehicle_tags.intersection(frozenset(('special',)))
    )
    return bool(vehicle_tier == 10 and not is_collector and not is_special and not is_premium)


def _has_real_tier11_vehicle_unlock(vehicle, items=None):
    if vehicle is None:
        return False

    try:
        unlock_descrs = list(vehicle.getUnlocksDescrs() or [])
    except Exception:
        return False

    unlock_entry = None
    for unlock_entry in unlock_descrs:
        if len(unlock_entry) < 4:
            continue

        intcd = unlock_entry[2]
        if _resolve_unlock_item_type(intcd) != 'vehicle':
            continue

        unlock_item = None
        if items is not None:
            try:
                unlock_item = items.getItemByCD(intcd)
            except Exception:
                unlock_item = None

        if _resolve_unlock_vehicle_level(unlock_item) == 11:
            return True

    return False


def _build_hypothetical_t11_unlock_marker():
    return {
        'xp_cost': _HYPOTHETICAL_T11_XP_COST,
        'intcd': -1,
        'item_type': 'vehicle',
        'name': None,
        'is_available': True,
        'missing_prereq_names': [],
        'missing_prereqs': [],
        'is_hypothetical_t11': True,
    }


def _append_hypothetical_t11_unlock(visible_unlocks, available_unlocks):
    hypothetical_unlock = _build_hypothetical_t11_unlock_marker()

    updated_visible_unlocks = list(visible_unlocks or [])
    updated_visible_unlocks.append(hypothetical_unlock)
    updated_visible_unlocks.sort(key=lambda item: (item['xp_cost'], item['intcd']))

    updated_available_unlocks = list(available_unlocks or [])
    updated_available_unlocks.append(hypothetical_unlock)
    updated_available_unlocks.sort(key=lambda item: (item['xp_cost'], item['intcd']))

    return updated_visible_unlocks, updated_available_unlocks


def _get_blueprints_requester(items):
    if items is None:
        return None

    try:
        return getattr(items, '_ItemsRequester__blueprints', None)
    except Exception:
        return None


def _get_blueprint_count_and_total(blueprints_requester, unlock_intcd, unlock_level):
    if blueprints_requester is None or unlock_level is None:
        return None, None

    try:
        value = blueprints_requester.getBlueprintCount(unlock_intcd, unlock_level)
    except Exception:
        return None, None

    return _extract_int_pair(value)


def _get_blueprint_discount_percent(blueprints_requester, unlock_intcd, unlock_level, blueprint_count):
    if blueprints_requester is None or unlock_level is None or blueprint_count is None:
        return None

    try:
        value = blueprints_requester.getBlueprintDiscount(unlock_intcd, unlock_level, blueprint_count)
    except Exception:
        return None

    return _to_int_or_none(value)


def _get_blueprint_discount_xp(blueprints_requester, unlock_intcd, unlock_level, raw_xp_cost):
    if blueprints_requester is None or unlock_level is None or raw_xp_cost is None:
        return None, None

    try:
        value = blueprints_requester.getFragmentDiscountAndCost(unlock_intcd, unlock_level, raw_xp_cost)
    except Exception:
        return None, None

    return _extract_int_pair(value)


def _resolve_unlock_research_state(intcd, raw_xp_cost, items=None):
    state = {
        'xp_cost': raw_xp_cost,
        'blueprint_info': None,
    }

    if items is None:
        return state

    try:
        unlock_item = items.getItemByCD(intcd)
    except Exception:
        return state

    unlock_level = _resolve_unlock_vehicle_level(unlock_item)
    if unlock_level is None:
        return state

    blueprints_requester = _get_blueprints_requester(items)
    if blueprints_requester is None:
        return state

    blueprint_count, blueprint_total = _get_blueprint_count_and_total(
        blueprints_requester,
        intcd,
        unlock_level,
    )
    if blueprint_total is None or blueprint_total <= 0:
        return state

    blueprint_count = _to_int_or_none(blueprint_count)
    if blueprint_count is None or blueprint_count < 0:
        blueprint_count = 0

    discount_percent = _get_blueprint_discount_percent(
        blueprints_requester,
        intcd,
        unlock_level,
        blueprint_count,
    )
    if discount_percent is None and blueprint_count == 1:
        discount_percent, _discount_xp = _get_blueprint_discount_xp(
            blueprints_requester,
            intcd,
            unlock_level,
            raw_xp_cost,
        )
    discount_percent = _to_int_or_none(discount_percent)
    if discount_percent is None or discount_percent < 0:
        discount_percent = 0

    state['blueprint_info'] = {
        'count': blueprint_count,
        'total': blueprint_total,
        'discount_percent': discount_percent,
    }

    if discount_percent <= 0:
        return state

    discount_xp = raw_xp_cost * discount_percent / 100

    state['xp_cost'] = max(0, raw_xp_cost - discount_xp)
    return state


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
        research_state = _resolve_unlock_research_state(intcd, cost, items)
        cost = research_state.get('xp_cost', cost)
        missing_prereqs = sorted([p for p in prereqs if p not in unlocks_set])
        unlock_marker = _build_unlock_marker(
            cost,
            intcd,
            items=items,
            is_available=not missing_prereqs,
            missing_prereq_intcds=missing_prereqs,
            blueprint_info=research_state.get('blueprint_info'),
        )
        unlock_marker['missing_prereq_intcds'] = missing_prereqs
        visible.append(unlock_marker)

    _assign_cost_with_prereqs(visible)

    visible.sort(key=lambda item: (item['xp_cost'], item['intcd']))
    return visible


def _assign_cost_with_prereqs(visible_unlocks):
    """Sum each unlock's own cost with its (direct, unresearched) prerequisites' costs.

    Missing prerequisites are themselves unresearched tech-tree nodes, so they appear in
    visible_unlocks with their own (discount-adjusted) xp_cost; we look those up rather than
    recomputing. Items with no missing prerequisites get a sum equal to their own cost.
    """
    cost_by_intcd = dict((marker['intcd'], marker['xp_cost']) for marker in visible_unlocks)
    for marker in visible_unlocks:
        prereq_cost = sum(
            cost_by_intcd.get(prereq_intcd, 0)
            for prereq_intcd in marker.get('missing_prereq_intcds', ())
        )
        marker['cost_with_prereqs_xp'] = marker['xp_cost'] + prereq_cost


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


def _collect_accelerate_crew_training_status(vehicle):
    data = {
        'available': False,
        'enabled': None,
    }

    if vehicle is None or not getattr(vehicle, 'isElite', False):
        return data

    data['available'] = True

    attr_name = None
    for attr_name in ('isXPToTman', 'isXPToTMan'):
        try:
            value = getattr(vehicle, attr_name, None)
        except Exception:
            value = None

        if value is None:
            continue

        if callable(value):
            try:
                value = value()
            except Exception:
                continue

        data['enabled'] = bool(value)
        return data

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
            step_id = _resolve_post_progression_step_id(step)
            level = _resolve_post_progression_step_level(step)
            action = _resolve_post_progression_step_action(step) if is_veh_skill_tree else None

            if step_id is not None:
                step_id_to_level[step_id] = level
                if is_veh_skill_tree:
                    step_xp_cost = _resolve_t11_step_xp_cost(step)
                    action_meta = None
                    if resolve_t11_action_marker_meta is not None:
                        action_meta = resolve_t11_action_marker_meta(step, step_id, vehicle)
                    step_meta[step_id] = {
                        'level': level,
                        'xp_cost': step_xp_cost,
                        'bucket': _make_t11_bucket(step_xp_cost),
                        'action': action,
                        'action_name': _resolve_post_progression_action_name(action),
                        'action_class_name': _resolve_post_progression_action_class_name(action),
                        'action_category': _resolve_post_progression_action_category(action),
                        'action_meta': action_meta,
                        'reachable': _resolve_post_progression_step_reachable(step),
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


def _build_t11_action_node(step_id, meta, pp, state, vehicle):
    action_meta = meta.get('action_meta')
    if action_meta is None:
        return None

    action = meta.get('action')
    action_name = meta.get('action_name')
    action_class_name = meta.get('action_class_name')
    image_name = action_meta.get('image_name')
    kind = _classify_t11_action_kind(action_name, image_name, action_class_name)

    action_node = {
        'step_id': step_id,
        'xp_cost': meta.get('xp_cost'),
        'bucket': meta.get('bucket') or 'unknown',
        'name': action_meta.get('name'),
        'tooltip_title': action_meta.get('tooltip_title'),
        'ui_localized_name': action_meta.get('ui_localized_name'),
        'localized_name': action_meta.get('localized_name'),
        'loc_name': action_meta.get('loc_name'),
        'tech_name': action_meta.get('tech_name'),
        'image_name': image_name,
        'action_name': action_name,
        'slot_category': action_meta.get('slot_category'),
        'category': action_meta.get('category'),
        'kind': kind,
    }

    kpi_lines = _build_post_progression_kpi_lines(
        action,
        vehicle,
    )
    if kpi_lines:
        action_node['kpi_lines'] = kpi_lines

    if kind == 'feature':
        feature_group_id = _resolve_post_progression_feature_group_id(action_name or image_name)
        action_node['is_active'] = _resolve_post_progression_setup_switch_active(
            pp,
            state,
            vehicle,
            feature_group_id,
        )
    elif kind == 'role_slot':
        action_node['is_active'] = bool(_call_post_progression_bool(pp, 'isRoleSlotActive', vehicle))
        current_category = _normalize_post_progression_category(
            meta.get('action_category')
            or action_meta.get('slot_category')
            or action_meta.get('category')
            or _resolve_post_progression_action_category(action)
        )
        if current_category:
            action_node['slot_category'] = current_category

        available_categories = _resolve_role_slot_available_categories(vehicle, meta.get('level'))
        if available_categories:
            action_node['available_categories'] = available_categories

    return action_node


def _collect_t11_unlock_data(pp, state, vehicle, step_meta, unlocked_step_ids):
    researched_action_nodes = []
    unresearched_action_nodes = []
    researched_buckets = _make_empty_t11_bucket_counts()
    unresearched_buckets = _make_empty_t11_bucket_counts()
    # Per bucket, how many still-unresearched nodes are currently researchable
    # (tree prerequisites satisfied). reachability_known stays False until at least
    # one unresearched node reports a definite state, so an older client that can't
    # report step states leaves every bucket treated as reachable (never grayed).
    unresearched_reachable_buckets = _make_empty_t11_bucket_counts()
    reachability_known = False

    _normalize_t11_final_bucket(step_meta)

    step_id = None
    meta = None
    for step_id, meta in step_meta.iteritems():
        bucket = meta.get('bucket') or 'unknown'
        is_researched = step_id in unlocked_step_ids
        bucket_counts = researched_buckets if is_researched else unresearched_buckets
        bucket_counts[bucket] = bucket_counts.get(bucket, 0) + 1

        if not is_researched:
            reachable = meta.get('reachable')
            if reachable is not None:
                reachability_known = True
                if reachable:
                    unresearched_reachable_buckets[bucket] = unresearched_reachable_buckets.get(bucket, 0) + 1

        action_node = _build_t11_action_node(step_id, meta, pp, state, vehicle)
        if action_node is None:
            continue
        if is_researched:
            researched_action_nodes.append(action_node)
        else:
            unresearched_action_nodes.append(action_node)

    return {
        't11_bucket_researched': researched_buckets,
        't11_bucket_unresearched': unresearched_buckets,
        't11_bucket_unresearched_reachable': unresearched_reachable_buckets,
        't11_reachability_known': reachability_known,
        't11_action_nodes_researched': sorted(researched_action_nodes, key=_t11_action_node_sort_key),
        't11_action_nodes_unresearched': sorted(unresearched_action_nodes, key=_t11_action_node_sort_key),
    }


def _collect_post_progression_unlock_state(pp, step_id_to_level, step_meta, is_veh_skill_tree, vehicle=None):
    result = {
        'unlocked_steps': 0,
        'unique_unlocked_level_count': 0,
        'level_details': {},
        't11_bucket_researched': _make_empty_t11_bucket_counts(),
        't11_bucket_unresearched': _make_empty_t11_bucket_counts(),
        't11_bucket_unresearched_reachable': _make_empty_t11_bucket_counts(),
        't11_reachability_known': False,
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

        if not is_veh_skill_tree:
            result['level_details'] = _build_regular_field_mod_level_details(pp, state, vehicle)

        if is_veh_skill_tree and step_meta:
            result.update(_collect_t11_unlock_data(pp, state, vehicle, step_meta, unlocked_step_ids))
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
        'level_details': {},
        'next_purchasable_step_xp': None,
        't11_bucket_researched': _make_empty_t11_bucket_counts(),
        't11_bucket_unresearched': _make_empty_t11_bucket_counts(),
        't11_bucket_unresearched_reachable': _make_empty_t11_bucket_counts(),
        't11_reachability_known': False,
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
            vehicle,
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


def _collect_research_progress_data(
        vehicle,
        stats,
        items,
        resolve_t11_action_marker_meta=None,
        include_hypothetical_t11=False):
    unlocks_set = stats.unlocks
    vehicle_tier = _get_vehicle_tier(vehicle)
    visible_unlocks = _collect_visible_unlocks(vehicle, unlocks_set, items)
    available_unlocks = _collect_available_unlocks(
        vehicle,
        unlocks_set,
        items,
        visible_unlocks=visible_unlocks,
    )
    real_available_unlocks = list(available_unlocks)
    can_show_hypothetical_t11 = _resolve_hypothetical_t11_vehicle_probe(vehicle, vehicle_tier)

    if (include_hypothetical_t11
            and can_show_hypothetical_t11
            and not _has_real_tier11_vehicle_unlock(vehicle, items)):
        visible_unlocks, available_unlocks = _append_hypothetical_t11_unlock(
            visible_unlocks,
            available_unlocks,
        )

    # --- Tech tree XP progress ---
    veh_xp = stats.vehiclesXPs.get(vehicle.intCD, 0)
    free_xp = max(0, stats.freeXP)
    total_xp = veh_xp + free_xp

    next_cost, next_intcd = _next_available_unlock(vehicle, unlocks_set, real_available_unlocks)
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
    accelerate_crew_training = _collect_accelerate_crew_training_status(vehicle)

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
        'accelerate_crew_training': accelerate_crew_training,
        'field_mods': {
            'exists': field_mods['exists'],
            'total_steps': field_mods['total_steps'],
            'unlocked_steps': field_mods['unlocked_steps'],
            'is_veh_skill_tree': field_mods['is_veh_skill_tree'],
            'unique_level_count': field_mods['unique_level_count'],
            'unique_unlocked_level_count': field_mods['unique_unlocked_level_count'],
            'level_details': field_mods['level_details'],
            'next_purchasable_step_xp': field_mods['next_purchasable_step_xp'],
            't11_bucket_researched': field_mods['t11_bucket_researched'],
            't11_bucket_unresearched': field_mods['t11_bucket_unresearched'],
            't11_bucket_unresearched_reachable': field_mods['t11_bucket_unresearched_reachable'],
            't11_reachability_known': field_mods['t11_reachability_known'],
            't11_action_nodes_researched': field_mods['t11_action_nodes_researched'],
            't11_action_nodes_unresearched': field_mods['t11_action_nodes_unresearched'],
            'tier_plan': tier_plan,
        },
    }
