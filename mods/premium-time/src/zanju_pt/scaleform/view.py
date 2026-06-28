"""Scaleform view registration, hooks, and low-level as_* wrappers."""
from __future__ import print_function, unicode_literals

from frameworks.wulf import WindowLayer
from gui.Scaleform.framework import ScopeTemplates, ViewSettings, g_entitiesFactories
from gui.Scaleform.framework.entities.View import View
from gui.Scaleform.framework.managers.loaders import SFViewLoadParams

from ..constants import SCALEFORM_FILE_NAME, SCALEFORM_VIEW_ALIAS

_on_view_populated = None
_on_view_disposed = None


def configure_runtime_callbacks(on_populated, on_disposed):
    global _on_view_disposed, _on_view_populated

    _on_view_populated = on_populated
    _on_view_disposed = on_disposed


class _PremiumTimeView(View):
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
        super(_PremiumTimeView, self)._populate()
        if callable(_on_view_populated):
            _on_view_populated(self)

    def _dispose(self):
        if callable(_on_view_disposed):
            _on_view_disposed(self)
        super(_PremiumTimeView, self)._dispose()


# -- low-level as_* wrappers -------------------------------------------------

def push_payload(view, payload, logger):
    if view is None or payload is None:
        return False
    try:
        view.as_setContextS(payload)
        return True
    except Exception:
        logger.exception('Failed to push data to premium-time view')
        return False


def set_view_visible(view, current_visible, is_visible, reason, logger):
    if view is None:
        return current_visible
    if current_visible is is_visible:
        return current_visible

    try:
        view.as_setVisibleS(is_visible)
        logger.info('Premium-time view visibility -> %s (%s)', is_visible, reason)
        if is_visible:
            _refresh_layout(view, 'visible:{0}'.format(reason), logger)
        return is_visible
    except Exception:
        logger.exception('Failed to set premium-time view visibility=%s (%s)', is_visible, reason)
        return current_visible


def hide_view(view, current_visible, reason, logger):
    return set_view_visible(view, current_visible, False, reason, logger)


def show_view(view, current_visible, payload, reason, logger):
    if view is None or payload is None:
        return current_visible
    push_payload(view, payload, logger)
    return set_view_visible(view, current_visible, True, reason, logger)


def handle_populated_view(view, current_visible, payload, logger):
    if payload is None:
        return hide_view(view, current_visible, 'populated_no_data', logger)

    try:
        logger.info('Premium-time view populated (%s)', view.as_pingS())
    except Exception:
        logger.exception('Premium-time view ping failed')

    return show_view(view, current_visible, payload, 'populated', logger)


def dispose_view(view, reason, logger):
    if view is None:
        return False
    try:
        view.destroy()
        logger.info('Disposed premium-time view (%s)', reason)
        return True
    except Exception:
        logger.exception('Failed to dispose premium-time view (%s)', reason)
        return False


def _refresh_layout(view, reason, logger):
    if view is None:
        return
    try:
        view.as_refreshLayoutS()
    except Exception:
        logger.exception('Failed to refresh premium-time view layout (%s)', reason)


def request_view_load(is_active, view, view_requested, app, reason, logger):
    if not is_active or view is not None or view_requested or app is None:
        return view_requested
    try:
        app.loadView(SFViewLoadParams(SCALEFORM_VIEW_ALIAS))
        logger.info('Requested premium-time view load (%s)', reason)
        return True
    except Exception:
        logger.exception('Failed to request premium-time view load (%s)', reason)
        return False


# -- view settings registration ---------------------------------------------

def register_view_settings(current_registered):
    if current_registered:
        return current_registered

    g_entitiesFactories.addSettings(
        ViewSettings(
            SCALEFORM_VIEW_ALIAS,
            _PremiumTimeView,
            SCALEFORM_FILE_NAME,
            WindowLayer.WINDOW,
            None,
            ScopeTemplates.GLOBAL_SCOPE,
        )
    )
    return True


def unregister_view_settings(current_registered, logger):
    if not current_registered:
        return False
    try:
        g_entitiesFactories.removeSettings(SCALEFORM_VIEW_ALIAS)
    except Exception:
        logger.exception('Failed to unregister premium-time view settings')
    return False


# -- app / container hook helpers -------------------------------------------

def get_lobby_app(app_loader):
    app = None
    if hasattr(app_loader, 'getDefLobbyApp'):
        app = app_loader.getDefLobbyApp()
    if app is None and hasattr(app_loader, 'getApp'):
        app = app_loader.getApp()
    return app


def attach_space_hooks(current_registered, app_loader, on_space_entered, on_space_left):
    if current_registered:
        return current_registered
    app_loader.onGUISpaceEntered += on_space_entered
    app_loader.onGUISpaceLeft += on_space_left
    return True


def detach_space_hooks(current_registered, app_loader, on_space_entered, on_space_left, logger):
    if not current_registered:
        return False
    try:
        app_loader.onGUISpaceEntered -= on_space_entered
        app_loader.onGUISpaceLeft -= on_space_left
    except Exception:
        logger.exception('Failed to detach premium-time space hooks')
    return False


def attach_container_hooks(current_manager, app_loader, on_view_added, logger):
    app = get_lobby_app(app_loader)
    container_manager = getattr(app, 'containerManager', None) if app is not None else None
    if container_manager is current_manager:
        return current_manager

    current_manager = detach_container_hooks(current_manager, on_view_added, logger)
    if container_manager is None:
        return None

    try:
        container_manager.onViewAddedToContainer += on_view_added
        return container_manager
    except Exception:
        logger.exception('Failed to attach premium-time container hooks')
        return None


def detach_container_hooks(current_manager, on_view_added, logger):
    if current_manager is None:
        return None
    try:
        current_manager.onViewAddedToContainer -= on_view_added
    except Exception:
        logger.exception('Failed to detach premium-time container hooks')
    return None
