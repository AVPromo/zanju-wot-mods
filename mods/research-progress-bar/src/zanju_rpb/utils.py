"""Small tolerant helpers used across research-progress-bar runtime code."""
from __future__ import print_function, unicode_literals

from numbers import Integral

try:
    _STRING_TYPES = (basestring,)
except NameError:
    _STRING_TYPES = (str,)


def _safe_text(value, max_len=180):
    try:
        text = str(value)
    except Exception:
        return '<unprintable>'
    if len(text) > max_len:
        return text[:max_len]
    return text


def _clean_text_value(value):
    if value is None:
        return None
    text = _safe_text(value, 120).strip()
    if not text:
        return None
    if text[0] == '<' and text[-1] == '>':
        return None
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
