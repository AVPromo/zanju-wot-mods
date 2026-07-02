"""Read remaining Premium Account and WoT Plus time from the WoT client.

Two independent subscriptions are reported:

  * Premium Account - the classic WoT premium time (PREMIUM_TYPE.BASIC, plus the
    legacy "premium plus" account variant when present). Read from the account
    stats object; this surface is stable across client versions.

  * WoT Plus / WoT Plus Pro - the renewable subscription. The exact field names
    for this one have moved between client versions, so it is read through layered
    probes (controller -> stats -> player) with one-time discovery logging: if none
    of the known shapes match, the candidate attribute names are logged once so the
    correct field can be pinned without guesswork.

BigWorld scripting uses Python 2.7. Avoid Python-3-only syntax.
"""
# absolute_import is required: this module imports WoT's top-level ``constants`` module,
# which would otherwise resolve to this package's own constants.py under Py2.7's implicit
# relative import rules.
from __future__ import absolute_import, print_function, unicode_literals

KIND_PREMIUM_ACCOUNT = 'premium_account'
KIND_WOT_PLUS = 'wot_plus'

_SUBSCRIPTION_EXPIRY_KEYS = (
    'expiryTime',
    'endTime',
    'expiration',
    'expiresAt',
    'expiryTimestamp',
    'finishTime',
)
_SUBSCRIPTION_PRO_KEYS = (
    'isPro',
    'pro',
    'isWotPlusPro',
    'isProActive',
)


def collect_premium_status(items_cache, logger, discovery_state=None):
    """Return the current premium status as a normalized dict.

    Shape::

        {
            'now': <int epoch seconds>,
            'entries': [
                {
                    'kind': 'premium_account' | 'wot_plus',
                    'label_key': <localization key>,
                    'expiry': <int epoch seconds or None>,
                    'remaining': <int seconds or None>,
                    'active': <bool>,
                },
                ...
            ],
        }
    """
    now = _now()
    stats = _resolve_stats(items_cache, logger)

    premium_expiry = _read_premium_account_expiry(stats, logger)
    wot_plus_expiry, wot_plus_is_pro = _read_wot_plus(stats, logger, discovery_state)

    entries = [
        _build_entry(KIND_PREMIUM_ACCOUNT, 'LABEL_PREMIUM_ACCOUNT', premium_expiry, now),
        _build_wot_plus_entry(wot_plus_expiry, wot_plus_is_pro, now),
    ]
    return {'now': now, 'entries': entries}


def _build_entry(kind, label_key, expiry, now):
    remaining = None if expiry is None else int(expiry) - now
    return {
        'kind': kind,
        'label_key': label_key,
        'expiry': expiry,
        'remaining': remaining,
        'active': remaining is not None and remaining > 0,
    }


def _build_wot_plus_entry(expiry, is_pro, now):
    label_key = 'LABEL_WOT_PLUS_PRO' if is_pro else 'LABEL_WOT_PLUS'
    return _build_entry(KIND_WOT_PLUS, label_key, expiry, now)


# -- current time -----------------------------------------------------------

def _now():
    try:
        from helpers import time_utils
        timestamp = time_utils.getCurrentTimestamp()
        if timestamp:
            return int(timestamp)
    except Exception:
        pass

    import time
    return int(time.time())


# -- stats / premium account ------------------------------------------------

def _resolve_stats(items_cache, logger):
    try:
        return items_cache.stats
    except Exception:
        logger.exception('Failed to resolve account stats from items cache')
        return None


def _import_premium_type():
    try:
        from constants import PREMIUM_TYPE
        return PREMIUM_TYPE
    except Exception:
        return None


def _read_premium_account_expiry(stats, logger):
    if stats is None:
        return None

    # Current clients expose the active premium account expiry directly on stats.
    expiry = _coerce_timestamp(getattr(stats, 'activePremiumExpiryTime', 0))
    if not expiry:
        expiry = _coerce_timestamp(getattr(stats, 'totalPremiumExpiryTime', 0))
    if expiry:
        return expiry

    return _read_legacy_premium_expiry(stats, logger)


def _read_legacy_premium_expiry(stats, logger):
    expiry = 0
    premium_type = _import_premium_type()
    getter = getattr(stats, 'getPremiumExpiryTime', None)
    if callable(getter) and premium_type is not None:
        for attr in ('BASIC', 'PLUS'):
            type_value = getattr(premium_type, attr, None)
            if type_value is None:
                continue
            try:
                value = getter(type_value)
            except Exception:
                logger.exception('getPremiumExpiryTime(%s) failed', attr)
                continue
            expiry = max(expiry, _coerce_timestamp(value))

    if not expiry:
        expiry = _coerce_timestamp(getattr(stats, 'premiumExpiryTime', 0))

    return expiry or None


# -- WoT Plus subscription --------------------------------------------------

_WOT_PLUS_CONTROLLER_ACCESSORS = ('getExpiryTime', 'getEndTime', 'getExpiration', 'getState')


def _read_wot_plus(stats, logger, discovery_state):
    controller = _resolve_wot_plus_controller(logger)

    # When the controller exposes a known accessor it is authoritative: a zero/missing
    # expiry then genuinely means "no active subscription", not "could not read", so we
    # do not fall through to the noisier probes or the discovery log.
    if controller is not None and _controller_has_known_api(controller):
        expiry, is_pro = _read_wot_plus_from_controller(controller, logger)
        return expiry, bool(is_pro)

    for probe in (
        lambda: _read_wot_plus_from_stats(stats, logger),
        lambda: _read_wot_plus_from_player(logger),
    ):
        expiry, is_pro = probe()
        if expiry:
            return expiry, bool(is_pro)

    _log_wot_plus_discovery_once(controller, stats, logger, discovery_state)
    return None, False


def _controller_has_known_api(controller):
    for name in _WOT_PLUS_CONTROLLER_ACCESSORS:
        if callable(getattr(controller, name, None)):
            return True
    return False


def _resolve_wot_plus_controller(logger):
    try:
        from helpers import dependency
        from skeletons.gui.game_control import IWotPlusController
    except Exception:
        return None
    try:
        return dependency.instance(IWotPlusController)
    except Exception:
        logger.exception('Failed to resolve IWotPlusController')
        return None


def _read_wot_plus_from_controller(controller, logger):
    if controller is None:
        return None, None

    expiry = _first_timestamp(
        controller,
        getters=('getExpiryTime', 'getEndTime', 'getExpiration'),
        attrs=('expiryTime', 'endTime', 'expiration'),
    )
    is_pro = _first_bool(
        controller,
        getters=('isWotPlusProEnabled', 'isProEnabled', 'isPro'),
        attrs=('isPro', 'isProActive'),
    )
    if expiry:
        return expiry, is_pro

    # Some client versions wrap the data in a state/info object.
    for name in ('getState', 'getStateData', 'getSubscriptionInfo', 'getData'):
        getter = getattr(controller, name, None)
        if not callable(getter):
            continue
        try:
            info = getter()
        except Exception:
            continue
        info_expiry = _extract_subscription_expiry(info)
        if info_expiry:
            return info_expiry, _extract_subscription_pro(info) or is_pro
    return None, is_pro


def _read_wot_plus_from_stats(stats, logger):
    if stats is None:
        return None, None

    for name in ('getRenewableSubscriptionInfo', 'getWotPlusInfo'):
        getter = getattr(stats, name, None)
        if not callable(getter):
            continue
        try:
            info = getter()
        except Exception:
            continue
        expiry = _extract_subscription_expiry(info)
        if expiry:
            return expiry, _extract_subscription_pro(info)

    for name in ('renewableSubscription', 'wotPlus', 'wotPlusInfo'):
        info = getattr(stats, name, None)
        if info is not None:
            expiry = _extract_subscription_expiry(info)
            if expiry:
                return expiry, _extract_subscription_pro(info)

    expiry = _first_timestamp(
        stats,
        getters=(),
        attrs=('renewableSubscriptionExpiryTime', 'wotPlusExpiryTime'),
    )
    return expiry or None, None


def _read_wot_plus_from_player(logger):
    try:
        import BigWorld
        player = BigWorld.player()
    except Exception:
        return None, None

    info = getattr(player, 'renewableSubscription', None)
    if info is None:
        return None, None
    return _extract_subscription_expiry(info), _extract_subscription_pro(info)


# -- generic reflective helpers ---------------------------------------------

def _first_timestamp(obj, getters=(), attrs=()):
    if obj is None:
        return None
    for name in getters:
        getter = getattr(obj, name, None)
        if not callable(getter):
            continue
        try:
            value = getter()
        except Exception:
            continue
        timestamp = _coerce_timestamp(value)
        if timestamp:
            return timestamp
    for name in attrs:
        timestamp = _coerce_timestamp(getattr(obj, name, None))
        if timestamp:
            return timestamp
    return None


def _first_bool(obj, getters=(), attrs=()):
    if obj is None:
        return None
    for name in getters:
        getter = getattr(obj, name, None)
        if not callable(getter):
            continue
        try:
            return bool(getter())
        except Exception:
            continue
    for name in attrs:
        if hasattr(obj, name):
            return bool(getattr(obj, name))
    return None


def _extract_subscription_expiry(info):
    if info is None:
        return None
    for key in _SUBSCRIPTION_EXPIRY_KEYS:
        timestamp = _coerce_timestamp(_lookup(info, key))
        if timestamp:
            return timestamp
    return None


def _extract_subscription_pro(info):
    if info is None:
        return None
    for key in _SUBSCRIPTION_PRO_KEYS:
        value = _lookup(info, key)
        if value is not None:
            return bool(value)
    return None


def _lookup(info, key):
    if isinstance(info, dict):
        return info.get(key)
    return getattr(info, key, None)


def _coerce_timestamp(value):
    if value is None or isinstance(value, bool):
        return 0
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


# -- discovery logging ------------------------------------------------------

def _log_wot_plus_discovery_once(controller, stats, logger, discovery_state):
    if discovery_state is None or discovery_state.get('wot_plus_logged'):
        return
    discovery_state['wot_plus_logged'] = True

    controller_attrs = _candidate_attr_names(controller, ('expir', 'end', 'pro', 'state', 'enabled'))
    stats_attrs = _candidate_attr_names(stats, ('subscription', 'wotplus', 'renewable', 'premium'))
    logger.info(
        'WoT Plus expiry not resolved via known shapes. '
        'controller=%s candidate_controller_attrs=%s candidate_stats_attrs=%s',
        type(controller).__name__ if controller is not None else None,
        controller_attrs,
        stats_attrs,
    )


def _candidate_attr_names(obj, keywords):
    if obj is None:
        return []
    names = []
    try:
        attr_names = dir(obj)
    except Exception:
        return []
    for name in attr_names:
        lowered = name.lower()
        for keyword in keywords:
            if keyword in lowered:
                names.append(name)
                break
    return names
