from __future__ import print_function, unicode_literals

from . import config as _config_api
from .scaleform import hooks as _scaleform_hooks_api
from .scaleform import runtime as _scaleform_runtime_api
from . import t11_action_metadata as _t11_action_metadata_api

_config = _config_api._config
_load_config = _config_api._load_config
_register_mod_settings = _config_api._register_mod_settings
_attach_lobby_route_log_handler = _scaleform_hooks_api._attach_lobby_route_log_handler
_configure_scaleform_runtime_callbacks = _scaleform_hooks_api._configure_scaleform_runtime_callbacks
_detach_vehicle_change_hooks = _scaleform_hooks_api._detach_vehicle_change_hooks
_detach_lobby_route_log_handler = _scaleform_hooks_api._detach_lobby_route_log_handler
_LobbyStateRouteLogHandler = _scaleform_hooks_api._LobbyStateRouteLogHandler
_hide_scaleform_view = _scaleform_runtime_api._hide_scaleform_view
_install_t11_ui_name_hooks = _t11_action_metadata_api._install_t11_ui_name_hooks
_refresh_vehicle_change_hooks = _scaleform_hooks_api._refresh_vehicle_change_hooks
_uninstall_t11_ui_name_hooks = _t11_action_metadata_api._uninstall_t11_ui_name_hooks


def _handle_registered_mod_settings_change(mod, reason):
    if mod is not None:
        mod.on_external_config_changed(reason)


def _initialize_runtime(
    mod,
    mod_factory,
    mod_id,
    mod_version,
    on_registered_mod_settings_changed,
    logger,
):
    logger.info('%s v%s initializing', mod_id, mod_version)
    try:
        _load_config()
        mod = mod_factory()
        mod._load_mode_state(logger)
        _register_mod_settings(mod_id, on_registered_mod_settings_changed)
        mod.start()
        logger.info('%s initialized', mod_id)
    except Exception:
        logger.exception('%s failed to initialize', mod_id)
    return mod


def _finalize_runtime(mod, mod_id, logger):
    try:
        if mod is not None:
            mod.stop()
            mod = None
    except Exception:
        logger.exception('%s error in fini', mod_id)
    return mod


def _start_runtime_lifecycle(mod, logger, lobby_state_logger):
    mod._active = True
    _configure_scaleform_runtime_callbacks(
        mod._on_scaleform_view_populated,
        mod._on_scaleform_view_disposed,
        mod._on_lobby_route_log,
    )
    _install_t11_ui_name_hooks(mod._schedule_update)
    mod._lobby_route_log_handler = _attach_lobby_route_log_handler(
        mod._lobby_route_log_handler,
        _LobbyStateRouteLogHandler,
        lobby_state_logger,
        logger,
    )
    mod._start_scaleform_view()
    _refresh_vehicle_change_hooks(
        mod._on_vehicle_changed,
        mod._on_preview_vehicle_changed,
        'start',
        logger,
    )


def _stop_runtime_lifecycle(mod, logger, lobby_state_logger):
    mod._active = False
    mod._cancel_pending_update()
    mod._cancel_visibility_probe()
    mod._lobby_route_log_handler = _detach_lobby_route_log_handler(
        mod._lobby_route_log_handler,
        lobby_state_logger,
        logger,
    )
    mod._current_lobby_route_path = None
    _uninstall_t11_ui_name_hooks()
    mod._stop_scaleform_view()
    _detach_vehicle_change_hooks(mod._on_vehicle_changed, mod._on_preview_vehicle_changed)
    _configure_scaleform_runtime_callbacks(None, None, None)


def _handle_runtime_config_change(mod, reason, logger):
    if not mod._active:
        return

    mod._cancel_pending_update()
    mod._cancel_visibility_probe()
    mod._scaleform_payload = None

    if not _config.get('enabled', True):
        if mod._scaleform_view is not None:
            mod._scaleform_view_visible = _hide_scaleform_view(
                mod._scaleform_view,
                mod._scaleform_view_visible,
                reason,
                logger,
            )
        return

    mod._schedule_update(reason)
