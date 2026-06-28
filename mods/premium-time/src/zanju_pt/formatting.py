"""Remaining-time formatting helpers for premium-time.

Pure functions: no WoT imports here so the formatting is trivially testable and reused by
both the runtime collector and the Scaleform payload builder.
"""
from __future__ import print_function, unicode_literals

from .localization import get_text as _loc

_SECONDS_PER_MINUTE = 60
_SECONDS_PER_HOUR = 60 * 60
_SECONDS_PER_DAY = 24 * 60 * 60


def format_remaining(seconds):
    """Format a remaining-seconds count as a compact localized duration.

    Returns a short string such as "23d 4h", "4h 12m", or "8m". Sub-minute and
    non-positive inputs collapse to the "less than a minute" label; callers decide
    whether a non-positive remainder means "expired / inactive" before calling here.
    """
    try:
        total = int(seconds)
    except (TypeError, ValueError):
        return _loc('DURATION_UNKNOWN', '--')

    if total < _SECONDS_PER_MINUTE:
        return _loc('DURATION_LESS_THAN_MINUTE', '<1m')

    days = total // _SECONDS_PER_DAY
    hours = (total % _SECONDS_PER_DAY) // _SECONDS_PER_HOUR
    minutes = (total % _SECONDS_PER_HOUR) // _SECONDS_PER_MINUTE

    day_unit = _loc('UNIT_DAY_SHORT', 'd')
    hour_unit = _loc('UNIT_HOUR_SHORT', 'h')
    minute_unit = _loc('UNIT_MINUTE_SHORT', 'm')

    if days >= 1:
        return '{0}{1} {2}{3}'.format(days, day_unit, hours, hour_unit)
    if hours >= 1:
        return '{0}{1} {2}{3}'.format(hours, hour_unit, minutes, minute_unit)
    return '{0}{1}'.format(minutes, minute_unit)


def remaining_severity(seconds):
    """Classify how urgent a remaining-time value is, for colouring in the widget.

    Returns one of: "expired", "critical" (< 1 day), "warning" (< 3 days), "normal".
    """
    try:
        total = int(seconds)
    except (TypeError, ValueError):
        return 'normal'

    if total <= 0:
        return 'expired'
    if total < _SECONDS_PER_DAY:
        return 'critical'
    if total < 3 * _SECONDS_PER_DAY:
        return 'warning'
    return 'normal'
