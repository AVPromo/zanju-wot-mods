"""Lightweight runtime localization loader for research-progress-bar."""
from __future__ import print_function, unicode_literals

import io
import json
import logging
import os

from .constants import MOD_CONFIG_DIR_NAME, MOD_ID

try:
    from helpers import i18n as _wg_i18n
except Exception:
    _wg_i18n = None


_logger = logging.getLogger('zanju.researchprogressbar.i18n')
_DEFAULT_LANGUAGE = 'en'
_AUTO_LANGUAGE = 'auto'
_language_override = _AUTO_LANGUAGE
_bundle_cache = {}


def set_language_override(value):
    global _language_override

    normalized = _normalize_language_code(value)
    if normalized != _language_override:
        _language_override = normalized
        _bundle_cache.clear()


def get_text(key, default=None, **format_kwargs):
    text = _get_active_bundle().get(key)
    if text is None:
        text = _resolve_packaged_text(key)
    if text is None:
        text = default if default is not None else key

    if format_kwargs:
        try:
            text = text.format(**format_kwargs)
        except Exception:
            _logger.exception('Failed to format localized text for key %s', key)
    return text


def make_tooltip(header_key, body_key, header_default, body_default):
    return (
        '{HEADER}'
        + get_text(header_key, header_default)
        + '{/HEADER}{BODY}'
        + get_text(body_key, body_default)
        + '{/BODY}'
    )


def _get_active_bundle():
    language_codes = tuple(_iter_candidate_languages())
    bundle = _bundle_cache.get(language_codes)
    if bundle is not None:
        return bundle

    bundle = {}
    for language_code in language_codes:
        bundle.update(_load_bundle(language_code))
    _bundle_cache[language_codes] = bundle
    return bundle


def _iter_candidate_languages():
    yielded = set()

    for language_code in (_DEFAULT_LANGUAGE,) + tuple(_detect_requested_languages()):
        normalized = _normalize_language_code(language_code)
        if not normalized or normalized == _AUTO_LANGUAGE or normalized in yielded:
            continue
        yielded.add(normalized)
        yield normalized


def _detect_requested_languages():
    if _language_override != _AUTO_LANGUAGE:
        return _expand_language_candidates(_language_override)

    candidates = []
    if _wg_i18n is not None:
        for attr_name in ('getLanguageCode', 'getCurrentLanguage', 'getUILanguageCode'):
            getter = getattr(_wg_i18n, attr_name, None)
            if not callable(getter):
                continue
            try:
                candidates.extend(_expand_language_candidates(getter()))
            except Exception:
                continue

        for attr_name in ('LANGUAGE_CODE', 'CURRENT_LANGUAGE', 'languageCode', 'currentLanguage'):
            candidates.extend(_expand_language_candidates(getattr(_wg_i18n, attr_name, None)))

    for env_name in ('WOT_LANGUAGE', 'LANGUAGE', 'LC_ALL', 'LANG'):
        candidates.extend(_expand_language_candidates(os.environ.get(env_name)))

    unique = []
    seen = set()
    for language_code in candidates:
        if language_code in seen or language_code == _DEFAULT_LANGUAGE:
            continue
        seen.add(language_code)
        unique.append(language_code)
    return unique


def _expand_language_candidates(value):
    normalized = _normalize_language_code(value)
    if not normalized or normalized == _AUTO_LANGUAGE:
        return []

    candidates = [normalized]
    if '_' in normalized:
        base_language = normalized.split('_', 1)[0]
        if base_language and base_language not in candidates:
            candidates.append(base_language)
    return candidates


def _normalize_language_code(value):
    if value is None:
        return _AUTO_LANGUAGE

    try:
        text = '{0}'.format(value)
    except Exception:
        return _AUTO_LANGUAGE

    normalized = text.strip().lower().replace('-', '_')
    if not normalized:
        return _AUTO_LANGUAGE
    if '.' in normalized:
        normalized = normalized.split('.', 1)[0]
    if normalized in ('auto', 'default', 'client', 'system'):
        return _AUTO_LANGUAGE
    return normalized


def _load_bundle(language_code):
    merged = {}
    for base_dir in _iter_i18n_directories():
        file_path = os.path.join(base_dir, '{0}.yml'.format(language_code))
        if not os.path.isfile(file_path):
            continue
        try:
            with io.open(file_path, 'r', encoding='utf-8') as fh:
                merged.update(_parse_flat_yaml(fh.read()))
        except Exception:
            _logger.exception('Failed to load localization file %s', file_path)
    return merged


def _iter_i18n_directories():
    yield os.path.join('mods', 'configs', MOD_CONFIG_DIR_NAME, 'i18n')


def _parse_flat_yaml(text):
    data = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith('#') or ':' not in line:
            continue

        key, raw_value = line.split(':', 1)
        key = key.strip()
        value = raw_value.strip()
        if not key:
            continue
        if not value:
            data[key] = ''
            continue

        if value.startswith('"') and value.endswith('"'):
            try:
                data[key] = json.loads(value)
                continue
            except Exception:
                pass

        if value.startswith("'") and value.endswith("'"):
            data[key] = value[1:-1]
            continue

        data[key] = value
    return data


def _resolve_packaged_text(key):
    if _wg_i18n is None:
        return None

    resource_keys = (
        '#{0}:{1}'.format(MOD_ID, key),
        '#mods:{0}/{1}'.format(MOD_ID, key),
        '#mods:{0}:{1}'.format(MOD_ID, key),
    )
    for resource_key in resource_keys:
        try:
            resolved = _wg_i18n.makeString(resource_key)
        except Exception:
            continue
        if resolved and resolved not in (resource_key, key):
            return resolved
    return None