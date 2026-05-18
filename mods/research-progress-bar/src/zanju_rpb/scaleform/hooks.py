from __future__ import print_function, unicode_literals

import logging

from CurrentVehicle import g_currentPreviewVehicle, g_currentVehicle
from frameworks.wulf import WindowLayer
from gui.Scaleform.framework import ScopeTemplates, ViewSettings, g_entitiesFactories
from gui.Scaleform.framework.entities.View import View

_on_scaleform_view_populated = None
_on_scaleform_view_disposed = None
_on_lobby_route_log = None


def _configure_scaleform_runtime_callbacks(on_view_populated, on_view_disposed, on_lobby_route_log):
    global _on_lobby_route_log, _on_scaleform_view_disposed, _on_scaleform_view_populated

    _on_scaleform_view_populated = on_view_populated
    _on_scaleform_view_disposed = on_view_disposed
    _on_lobby_route_log = on_lobby_route_log


class _ScaleformGarageView(View):
    def as_setContextS(self, data):
        if self._isDAAPIInited():
            return self.flashObject.as_setContext(data)
        return None

    def as_setVisibleS(self, is_visible):
        if self._isDAAPIInited():
            return self.flashObject.as_setVisible(is_visible)
        return None

    def as_pingS(self):
        if self._isDAAPIInited():
            return self.flashObject.as_ping()
        return None

    def as_refreshLayoutS(self):
        if self._isDAAPIInited():
            return self.flashObject.as_refreshLayout()
        return None

    def _populate(self):
        super(_ScaleformGarageView, self)._populate()
        if callable(_on_scaleform_view_populated):
            _on_scaleform_view_populated(self)

    def _dispose(self):
        if callable(_on_scaleform_view_disposed):
            _on_scaleform_view_disposed(self)
        super(_ScaleformGarageView, self)._dispose()


class _LobbyStateRouteLogHandler(logging.Handler):
    def emit(self, record):
        if not callable(_on_lobby_route_log):
            return
        try:
            message = record.getMessage()
        except Exception:
            return
        _on_lobby_route_log(message)


def _refresh_vehicle_change_hooks(on_vehicle_changed, on_preview_vehicle_changed, reason, logger):
    try:
        try:
            g_currentVehicle.onChanged -= on_vehicle_changed
        except Exception:
            pass
        g_currentVehicle.onChanged += on_vehicle_changed
    except Exception:
        logger.exception('Failed to refresh current vehicle hook (%s)', reason)

    try:
        try:
            g_currentPreviewVehicle.onChanged -= on_preview_vehicle_changed
        except Exception:
            pass
        g_currentPreviewVehicle.onChanged += on_preview_vehicle_changed
    except Exception:
        logger.exception('Failed to refresh preview vehicle hook (%s)', reason)


def _detach_vehicle_change_hooks(on_vehicle_changed, on_preview_vehicle_changed):
    try:
        g_currentPreviewVehicle.onChanged -= on_preview_vehicle_changed
    except Exception:
        pass

    try:
        g_currentVehicle.onChanged -= on_vehicle_changed
    except Exception:
        pass


def _get_lobby_app(app_loader):
    app = None
    if hasattr(app_loader, 'getDefLobbyApp'):
        app = app_loader.getDefLobbyApp()
    if app is None and hasattr(app_loader, 'getApp'):
        app = app_loader.getApp()
    return app


def _attach_lobby_route_log_handler(current_handler, handler_class, lobby_state_logger, logger):
    if current_handler is not None:
        return current_handler

    try:
        handler = handler_class()
        handler.setLevel(logging.INFO)
        lobby_state_logger.addHandler(handler)
        return handler
    except Exception:
        logger.exception('Failed to attach lobby route log handler')
        return None


def _detach_lobby_route_log_handler(current_handler, lobby_state_logger, logger):
    if current_handler is None:
        return None

    try:
        lobby_state_logger.removeHandler(current_handler)
    except Exception:
        logger.exception('Failed to detach lobby route log handler')
    return None


def _attach_scaleform_container_hooks(current_container_manager, app_loader, on_view_added_to_container, logger):
    app = _get_lobby_app(app_loader)
    container_manager = getattr(app, 'containerManager', None) if app is not None else None
    if container_manager is current_container_manager:
        return current_container_manager

    current_container_manager = _detach_scaleform_container_hooks(
        current_container_manager,
        on_view_added_to_container,
        logger,
    )
    if container_manager is None:
        return None

    try:
        container_manager.onViewAddedToContainer += on_view_added_to_container
        return container_manager
    except Exception:
        logger.exception('Failed to attach scaleform container hooks')
        return None


def _detach_scaleform_container_hooks(current_container_manager, on_view_added_to_container, logger):
    if current_container_manager is None:
        return None

    try:
        current_container_manager.onViewAddedToContainer -= on_view_added_to_container
    except Exception:
        logger.exception('Failed to detach scaleform container hooks')
    return None


def _start_scaleform_view_runtime(
    current_settings_registered,
    current_hooks_registered,
    current_container_manager,
    app_loader,
    view_alias,
    view_class,
    swf_name,
    on_gui_space_entered,
    on_gui_space_left,
    on_view_added_to_container,
    sync_scaleform_view,
    logger,
):
    try:
        current_settings_registered = _register_scaleform_view_settings(
            current_settings_registered,
            view_alias,
            view_class,
            swf_name,
        )
        current_hooks_registered = _attach_scaleform_space_hooks(
            current_hooks_registered,
            app_loader,
            on_gui_space_entered,
            on_gui_space_left,
        )
        current_container_manager = _attach_scaleform_container_hooks(
            current_container_manager,
            app_loader,
            on_view_added_to_container,
            logger,
        )
        sync_scaleform_view('start')
    except Exception:
        logger.exception('Failed to start scaleform garage view')

    return current_settings_registered, current_hooks_registered, current_container_manager


def _stop_scaleform_view_runtime(
    current_container_manager,
    current_scaleform_view,
    current_scaleform_view_visible,
    current_hooks_registered,
    current_settings_registered,
    app_loader,
    on_view_added_to_container,
    on_gui_space_entered,
    on_gui_space_left,
    view_alias,
    logger,
):
    current_container_manager = _detach_scaleform_container_hooks(
        current_container_manager,
        on_view_added_to_container,
        logger,
    )

    if current_scaleform_view is not None:
        try:
            current_scaleform_view.destroy()
        except Exception:
            logger.exception('Failed to destroy scaleform garage view')
        finally:
            current_scaleform_view = None
            current_scaleform_view_visible = None

    current_hooks_registered = _detach_scaleform_space_hooks(
        current_hooks_registered,
        app_loader,
        on_gui_space_entered,
        on_gui_space_left,
        logger,
    )
    current_settings_registered = _unregister_scaleform_view_settings(
        current_settings_registered,
        view_alias,
        logger,
    )

    return (
        current_container_manager,
        current_scaleform_view,
        current_scaleform_view_visible,
        current_hooks_registered,
        current_settings_registered,
    )


def _register_scaleform_view_settings(current_registered, view_alias, view_class, swf_name):
    if current_registered:
        return current_registered

    g_entitiesFactories.addSettings(
        ViewSettings(
            view_alias,
            view_class,
            swf_name,
            WindowLayer.WINDOW,
            None,
            ScopeTemplates.GLOBAL_SCOPE,
        )
    )
    return True


def _attach_scaleform_space_hooks(current_registered, app_loader, on_gui_space_entered, on_gui_space_left):
    if current_registered:
        return current_registered

    app_loader.onGUISpaceEntered += on_gui_space_entered
    app_loader.onGUISpaceLeft += on_gui_space_left
    return True


def _detach_scaleform_space_hooks(current_registered, app_loader, on_gui_space_entered, on_gui_space_left, logger):
    if not current_registered:
        return False

    try:
        app_loader.onGUISpaceEntered -= on_gui_space_entered
        app_loader.onGUISpaceLeft -= on_gui_space_left
    except Exception:
        logger.exception('Failed to detach scaleform garage view hooks')
    return False


def _unregister_scaleform_view_settings(current_registered, view_alias, logger):
    if not current_registered:
        return False

    try:
        g_entitiesFactories.removeSettings(view_alias)
    except Exception:
        logger.exception('Failed to unregister scaleform garage view settings')
    return False
