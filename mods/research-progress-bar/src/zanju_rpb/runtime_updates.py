from __future__ import print_function, unicode_literals

from .scaleform import callbacks as _scaleform_callbacks_api
from .scaleform import gate as _scaleform_gate_api
from .scaleform import hooks as _scaleform_hooks_api
from .constants import _VISIBILITY_PROBE_DELAY

_cancel_callback = _scaleform_callbacks_api._cancel_callback
_extract_route_path = _scaleform_gate_api._extract_route_path
_is_default_hangar_route = _scaleform_gate_api._is_default_hangar_route
_refresh_vehicle_change_hooks = _scaleform_hooks_api._refresh_vehicle_change_hooks
_reschedule_immediate_callback = _scaleform_callbacks_api._reschedule_immediate_callback
_run_deferred_update_callback = _scaleform_callbacks_api._run_deferred_update_callback
_run_visibility_probe_callback = _scaleform_callbacks_api._run_visibility_probe_callback
_schedule_unique_callback = _scaleform_callbacks_api._schedule_unique_callback


def _handle_lobby_route_log(mod, message, logger):
    route_path = _extract_route_path(message)
    if route_path is None or route_path == mod._current_lobby_route_path:
        return

    previous_route_path = mod._current_lobby_route_path
    mod._current_lobby_route_path = route_path
    if _is_default_hangar_route(route_path) and not _is_default_hangar_route(previous_route_path):
        mod._last_seen_sub_view_alias = None
        if mod._active:
            _refresh_vehicle_change_hooks(
                mod._on_vehicle_changed,
                mod._on_preview_vehicle_changed,
                'enter_default_hangar',
                logger,
            )
    if mod._active:
        mod._schedule_update('lobby_route_changed')


def _cancel_pending_update(mod):
    mod._pending_update_callback = _cancel_callback(mod._pending_update_callback)


def _cancel_visibility_probe(mod):
    mod._visibility_probe_callback = _cancel_callback(mod._visibility_probe_callback)


def _schedule_visibility_probe(mod, reason=None):
    mod._visibility_probe_callback = _schedule_unique_callback(
        mod._active,
        mod._visibility_probe_callback,
        _VISIBILITY_PROBE_DELAY,
        mod._run_visibility_probe,
    )


def _run_visibility_probe(mod, logger):
    mod._visibility_probe_callback = None
    _run_visibility_probe_callback(
        mod._active,
        mod._scaleform_view,
        mod._scaleform_payload,
        mod._sync_scaleform_view,
        mod._schedule_visibility_probe,
        logger,
    )


def _schedule_update(mod, reason=None):
    mod._pending_update_callback = _reschedule_immediate_callback(
        mod._active,
        mod._pending_update_callback,
        mod._deferred_update,
    )


def _handle_vehicle_changed(mod):
    if not mod._active:
        return
    mod._schedule_update('vehicle_changed')


def _handle_preview_vehicle_changed(mod):
    if not mod._active:
        return
    mod._schedule_update('preview_vehicle_changed')


def _run_deferred_update(mod, logger):
    mod._pending_update_callback = None
    _run_deferred_update_callback(mod._active, mod._update, logger)
