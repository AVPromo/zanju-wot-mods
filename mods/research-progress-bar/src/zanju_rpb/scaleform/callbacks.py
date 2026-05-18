from __future__ import print_function, unicode_literals

import BigWorld
from frameworks.wulf import WindowLayer

from . import runtime as _scaleform_runtime_api
from . import views as _scaleform_views_api

_push_scaleform_payload = _scaleform_runtime_api._push_scaleform_payload
_refresh_scaleform_layout = _scaleform_runtime_api._refresh_scaleform_layout
_get_view_alias = _scaleform_views_api._get_view_alias


def _cancel_callback(callback_id):
    if callback_id is None:
        return None

    try:
        BigWorld.cancelCallback(callback_id)
    except Exception:
        pass
    return None


def _schedule_unique_callback(is_active, current_callback_id, delay, callback_fn):
    if not is_active or current_callback_id is not None:
        return current_callback_id
    return BigWorld.callback(delay, callback_fn)


def _reschedule_immediate_callback(is_active, current_callback_id, callback_fn):
    if not is_active:
        return current_callback_id

    current_callback_id = _cancel_callback(current_callback_id)
    return BigWorld.callback(0.0, callback_fn)


def _run_visibility_probe_callback(
    is_active,
    scaleform_view,
    scaleform_payload,
    sync_scaleform_view,
    schedule_visibility_probe,
    logger,
):
    if not is_active:
        return

    if sync_scaleform_view('visibility_probe'):
        if scaleform_view is not None and scaleform_payload is not None:
            _push_scaleform_payload(scaleform_view, scaleform_payload, logger)
        return

    schedule_visibility_probe('visibility_probe_retry')


def _handle_view_added_to_container_callback(
    is_active,
    view,
    last_seen_sub_view_alias,
    scaleform_view_alias,
    layout_refresh_view_aliases,
    scaleform_view,
    should_show_scaleform_view,
    schedule_update,
    sync_scaleform_view,
    logger,
):
    if not is_active:
        return last_seen_sub_view_alias

    if getattr(view, 'layer', None) == WindowLayer.SUB_VIEW:
        last_seen_sub_view_alias = _get_view_alias(view)

    if getattr(view, 'alias', None) == scaleform_view_alias:
        return last_seen_sub_view_alias

    alias = _get_view_alias(view)

    if alias in layout_refresh_view_aliases:
        _refresh_scaleform_layout(scaleform_view, 'view_added:{0}'.format(alias), logger)

    if should_show_scaleform_view('view_added_to_container', view):
        schedule_update('view_added_to_container')
    else:
        sync_scaleform_view('view_added_to_container', view)

    return last_seen_sub_view_alias


def _run_deferred_update_callback(is_active, update_fn, logger):
    if not is_active:
        return

    try:
        update_fn()
    except Exception:
        logger.exception('Error in _deferred_update')
