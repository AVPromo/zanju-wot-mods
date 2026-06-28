"""Visibility gate and show/hide/load orchestration for the premium-time widget.

The widget is account-wide, so visibility is simpler than a per-vehicle overlay: show it
while the hangar is the active lobby view, and hide it whenever a fullscreen sub-view
(tech tree, store, settings, ...) or a vehicle preview is on top.
"""
from __future__ import print_function, unicode_literals

from CurrentVehicle import g_currentPreviewVehicle
from frameworks.wulf import WindowLayer
from gui.shared.personality import ServicesLocator
from skeletons.gui.app_loader import GuiGlobalSpaceID as SPACE_ID

from .. import config as _config_api
from . import view as _view_api
from . import views as _views_api
from ..constants import SCALEFORM_VIEW_ALIAS, _HANGAR_VIEW_ALIASES

_config = _config_api._config


def start_view(mod, logger):
    # Always register the view settings and hooks even when disabled, so the master
    # "enabled" toggle can switch the widget on later without a client restart. The
    # visibility gate ("disabled" block reason) keeps it hidden until enabled.
    try:
        mod._settings_registered = _view_api.register_view_settings(mod._settings_registered)
        mod._space_hooks_registered = _view_api.attach_space_hooks(
            mod._space_hooks_registered,
            ServicesLocator.appLoader,
            mod._on_space_entered,
            mod._on_space_left,
        )
        mod._container_manager = _view_api.attach_container_hooks(
            mod._container_manager,
            ServicesLocator.appLoader,
            mod._on_view_added_to_container,
            logger,
        )
        sync_view(mod, 'start', logger)
    except Exception:
        logger.exception('Failed to start premium-time view')


def stop_view(mod, logger):
    mod._view_requested = False
    mod._payload = None
    mod._last_seen_sub_view_alias = None

    mod._container_manager = _view_api.detach_container_hooks(
        mod._container_manager,
        mod._on_view_added_to_container,
        logger,
    )

    if mod._view is not None:
        _view_api.dispose_view(mod._view, 'stop', logger)
        mod._view = None
        mod._view_visible = None

    mod._space_hooks_registered = _view_api.detach_space_hooks(
        mod._space_hooks_registered,
        ServicesLocator.appLoader,
        mod._on_space_entered,
        mod._on_space_left,
        logger,
    )
    mod._settings_registered = _view_api.unregister_view_settings(mod._settings_registered, logger)


def _resolve_container_manager(mod):
    if mod._container_manager is not None:
        return mod._container_manager
    app = _view_api.get_lobby_app(ServicesLocator.appLoader)
    return getattr(app, 'containerManager', None) if app is not None else None


def _compute_block_reason(mod, container_manager, incoming_view, logger):
    if not mod._active:
        return 'inactive'
    if not _config.get('enabled', True):
        return 'disabled'
    if not mod._in_lobby:
        return 'not_in_lobby'
    if g_currentPreviewVehicle.isPresent():
        return 'preview_present'

    incoming_alias = _views_api.get_view_alias(incoming_view)
    incoming_layer = getattr(incoming_view, 'layer', None) if incoming_view is not None else None
    if incoming_layer == WindowLayer.SUB_VIEW and incoming_alias is not None:
        if incoming_alias not in _HANGAR_VIEW_ALIASES and incoming_alias != SCALEFORM_VIEW_ALIAS:
            return 'incoming_sub_view={0}'.format(incoming_alias)

    sub_alias = _views_api.get_active_view_alias(container_manager, WindowLayer.SUB_VIEW, logger)
    if sub_alias is None:
        sub_alias = mod._last_seen_sub_view_alias
    top_sub_alias = _views_api.get_active_view_alias(container_manager, WindowLayer.TOP_SUB_VIEW, logger)

    allow_missing_sub_view = sub_alias is None and mod._view is not None
    if sub_alias not in _HANGAR_VIEW_ALIASES and not allow_missing_sub_view:
        return 'sub_view={0}'.format(sub_alias)
    if top_sub_alias not in (None, SCALEFORM_VIEW_ALIAS):
        return 'top_sub_view={0}'.format(top_sub_alias)
    return None


def should_show(mod, logger, incoming_view=None):
    container_manager = _resolve_container_manager(mod)
    return _compute_block_reason(mod, container_manager, incoming_view, logger) is None


def sync_view(mod, reason, logger, incoming_view=None):
    container_manager = _resolve_container_manager(mod)
    block_reason = _compute_block_reason(mod, container_manager, incoming_view, logger)
    _log_gate(mod, reason, block_reason, logger)

    if block_reason is not None:
        if mod._view is not None:
            mod._view_visible = _view_api.hide_view(mod._view, mod._view_visible, reason, logger)
        return False

    if mod._view is None and not mod._view_requested:
        mod._view_requested = _view_api.request_view_load(
            mod._active,
            mod._view,
            mod._view_requested,
            _view_api.get_lobby_app(ServicesLocator.appLoader),
            reason,
            logger,
        )
    elif mod._view is not None and mod._payload is not None:
        mod._view_visible = _view_api.show_view(
            mod._view,
            mod._view_visible,
            mod._payload,
            reason,
            logger,
        )
    return True


def _log_gate(mod, reason, block_reason, logger):
    log_key = (block_reason,)
    if log_key == mod._last_gate_log_key:
        return
    mod._last_gate_log_key = log_key
    logger.info(
        'Premium-time gate[%s]: visible=%s reason=%s',
        reason,
        block_reason is None,
        block_reason or 'none',
    )


def render(mod, payload, logger):
    if not _config.get('enabled', True):
        return
    mod._payload = payload
    if payload is None:
        if mod._view is not None:
            mod._view_visible = _view_api.hide_view(mod._view, mod._view_visible, 'no_data', logger)
        return
    if sync_view(mod, 'data_update', logger):
        _view_api.push_payload(mod._view, mod._payload, logger)


# -- event handlers ----------------------------------------------------------

def on_space_entered(mod, space_id, logger):
    if not mod._active or space_id != SPACE_ID.LOBBY:
        return
    mod._in_lobby = True
    mod._container_manager = _view_api.attach_container_hooks(
        mod._container_manager,
        ServicesLocator.appLoader,
        mod._on_view_added_to_container,
        logger,
    )
    mod.schedule_update('lobby_entered')


def on_space_left(mod, space_id, logger):
    if space_id != SPACE_ID.LOBBY:
        return
    mod._in_lobby = False
    mod._container_manager = _view_api.detach_container_hooks(
        mod._container_manager,
        mod._on_view_added_to_container,
        logger,
    )
    mod._view_requested = False
    view = mod._view
    mod._view = None
    mod._view_visible = None
    _view_api.dispose_view(view, 'lobby_exit', logger)


def on_view_populated(mod, view, logger):
    mod._view_requested = False
    mod._view = view
    mod._view_visible = None
    if not should_show(mod, logger, view):
        sync_view(mod, 'populated_outside_hangar', logger, view)
        return
    mod._view_visible = _view_api.handle_populated_view(
        mod._view,
        mod._view_visible,
        mod._payload,
        logger,
    )


def on_view_disposed(mod, view, logger):
    if mod._view is view:
        mod._view = None
        mod._view_visible = None
    mod._view_requested = False
    logger.info('Premium-time view disposed')


def on_view_added_to_container(mod, view, logger):
    if not mod._active:
        return
    if getattr(view, 'layer', None) == WindowLayer.SUB_VIEW:
        mod._last_seen_sub_view_alias = _views_api.get_view_alias(view)
    if getattr(view, 'alias', None) == SCALEFORM_VIEW_ALIAS:
        return
    sync_view(mod, 'view_added_to_container', logger, view)
