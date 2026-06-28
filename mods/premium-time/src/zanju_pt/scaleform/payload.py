"""Build the Scaleform payload pushed into the premium-time widget."""
from __future__ import print_function, unicode_literals

from ..collector import KIND_PREMIUM_ACCOUNT, KIND_WOT_PLUS
from ..formatting import format_remaining, remaining_severity
from ..localization import get_text as _loc


def build_premium_payload(status, prefs):
    """Turn collected premium status into a widget payload, or None to hide the widget.

    Returns None when there is nothing to show (every subscription is filtered out by
    the user's settings, or all are inactive while "hide when inactive" is enabled).
    """
    entries = (status or {}).get('entries') or []
    show_by_kind = {
        KIND_PREMIUM_ACCOUNT: bool(prefs.get('showPremiumAccount', True)),
        KIND_WOT_PLUS: bool(prefs.get('showWotPlus', True)),
    }
    hide_when_inactive = bool(prefs.get('hideWhenInactive', False))

    lines = []
    for entry in entries:
        if not show_by_kind.get(entry.get('kind'), True):
            continue
        if hide_when_inactive and not entry.get('active'):
            continue
        lines.append(_build_line(entry))

    if not lines:
        return None

    return {
        'title': _loc('WIDGET_TITLE', 'Premium Time'),
        'corner': prefs.get('corner', 'top_right'),
        'lines': lines,
    }


def _build_line(entry):
    label = _loc(entry.get('label_key'), entry.get('default_label') or entry.get('label_key'))
    if entry.get('active'):
        value = format_remaining(entry.get('remaining'))
        severity = remaining_severity(entry.get('remaining'))
    else:
        value = _loc('VALUE_INACTIVE', 'Inactive')
        severity = 'inactive'
    return {'label': label, 'value': value, 'severity': severity}


def summarize_payload(payload):
    """Compact, log-friendly summary of a payload for change-detection logging."""
    if payload is None:
        return None
    lines = payload.get('lines') or []
    return tuple((line.get('label'), line.get('value'), line.get('severity')) for line in lines)
