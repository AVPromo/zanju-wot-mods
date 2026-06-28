"""
zanju_pt.main

Persistent hangar widget showing remaining premium time:
  - Premium Account                (classic WoT premium time)
  - WoT Plus / WoT Plus Pro         (renewable subscription)

BigWorld scripting uses Python 2.7. Avoid Python-3-only syntax.
"""
from __future__ import print_function, unicode_literals

import logging

import BigWorld
from gui.shared.personality import ServicesLocator
from helpers import dependency
from skeletons.gui.app_loader import GuiGlobalSpaceID as SPACE_ID
from skeletons.gui.shared import IItemsCache

from .collector import collect_premium_status
from .config import _build_display_preferences, _config, _load_config, _register_mod_settings
from .constants import MOD_ID, WIDGET_REFRESH_INTERVAL
from .scaleform import sync as _sync
from .scaleform import view as _view_api
from .scaleform.payload import build_premium_payload, summarize_payload

_logger = logging.getLogger('zanju.premiumtime')

_UPDATE_DELAY = 0.2
_UNSET = object()


def _cancel_callback(callback_id):
    if callback_id is None:
        return None
    try:
        BigWorld.cancelCallback(callback_id)
    except Exception:
        pass
    return None


def _reschedule_callback(is_active, callback_id, delay, callback_fn):
    if not is_active:
        return callback_id
    callback_id = _cancel_callback(callback_id)
    return BigWorld.callback(delay, callback_fn)


class PremiumTime(object):
    itemsCache = dependency.descriptor(IItemsCache)

    def __init__(self):
        self._active = False
        self._in_lobby = False
        self._view = None
        self._view_visible = None
        self._view_requested = False
        self._payload = None
        self._settings_registered = False
        self._space_hooks_registered = False
        self._container_manager = None
        self._last_seen_sub_view_alias = None
        self._last_gate_log_key = None
        self._last_payload_summary = _UNSET
        self._update_callback = None
        self._refresh_callback = None
        self._update_in_progress = False
        self._stats_hooks_registered = False
        self._discovery_state = {}

    # -- lifecycle -----------------------------------------------------------

    def start(self):
        self._active = True
        _view_api.configure_runtime_callbacks(self._on_view_populated, self._on_view_disposed)
        self._attach_stats_hooks()
        self._detect_initial_space()
        _sync.start_view(self, _logger)
        self._start_refresh_timer()
        self.schedule_update('start')

    def stop(self):
        self._active = False
        self._update_callback = _cancel_callback(self._update_callback)
        self._refresh_callback = _cancel_callback(self._refresh_callback)
        self._detach_stats_hooks()
        _sync.stop_view(self, _logger)
        _view_api.configure_runtime_callbacks(None, None)

    def on_external_config_changed(self, reason):
        if not self._active:
            return
        self._cancel_update()
        if not _config.get('enabled', True):
            _sync.hide_widget(self, reason, _logger)
            return
        self.schedule_update(reason)

    def _detect_initial_space(self):
        # init() can run while the lobby is already loaded (e.g. mod hot-reload); the
        # onGUISpaceEntered hook would not fire again, so seed the flag from the loader.
        try:
            space_id = ServicesLocator.appLoader.getSpaceID()
        except Exception:
            space_id = None
        if space_id == SPACE_ID.LOBBY:
            self._in_lobby = True

    # -- stats hooks ---------------------------------------------------------

    def _attach_stats_hooks(self):
        if self._stats_hooks_registered:
            return
        try:
            self.itemsCache.onSyncCompleted += self._on_items_synced
            self._stats_hooks_registered = True
        except Exception:
            _logger.exception('Failed to attach items cache sync hook')

    def _detach_stats_hooks(self):
        if not self._stats_hooks_registered:
            return
        try:
            self.itemsCache.onSyncCompleted -= self._on_items_synced
        except Exception:
            _logger.exception('Failed to detach items cache sync hook')
        self._stats_hooks_registered = False

    def _on_items_synced(self, *args):
        self.schedule_update('items_synced')

    # -- scaleform callbacks -------------------------------------------------

    def _on_view_populated(self, view):
        _sync.on_view_populated(self, view, _logger)

    def _on_view_disposed(self, view):
        _sync.on_view_disposed(self, view, _logger)

    def _on_space_entered(self, space_id):
        _sync.on_space_entered(self, space_id, _logger)

    def _on_space_left(self, space_id):
        _sync.on_space_left(self, space_id, _logger)

    def _on_view_added_to_container(self, _container, view):
        _sync.on_view_added_to_container(self, view, _logger)

    # -- update scheduling ---------------------------------------------------

    def schedule_update(self, reason):
        self._update_callback = _reschedule_callback(
            self._active,
            self._update_callback,
            _UPDATE_DELAY,
            self._deferred_update,
        )

    def _deferred_update(self):
        self._update_callback = None
        if not self._active:
            return
        try:
            self._update()
        except Exception:
            _logger.exception('Premium-time update failed')

    def _start_refresh_timer(self):
        self._refresh_callback = _reschedule_callback(
            self._active,
            self._refresh_callback,
            WIDGET_REFRESH_INTERVAL,
            self._on_refresh_tick,
        )

    def _on_refresh_tick(self):
        self._refresh_callback = None
        if not self._active:
            return
        if self._in_lobby:
            self.schedule_update('refresh_tick')
        self._start_refresh_timer()

    # -- update --------------------------------------------------------------

    def _update(self):
        if not self._active or not _config.get('enabled', True):
            return
        if self._update_in_progress:
            return

        self._update_in_progress = True
        try:
            status = collect_premium_status(self.itemsCache.items, _logger, self._discovery_state)
            payload = build_premium_payload(status, _build_display_preferences())
            self._log_payload(payload)
            _sync.render(self, payload, _logger)
        finally:
            self._update_in_progress = False

    def _cancel_update(self):
        self._update_callback = _cancel_callback(self._update_callback)

    def _log_payload(self, payload):
        summary = summarize_payload(payload)
        if summary == self._last_payload_summary:
            return
        self._last_payload_summary = summary
        _logger.info('Premium-time payload: %s', summary)


# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------

_mod = None


def _on_settings_changed(reason):
    if _mod is not None:
        _mod.on_external_config_changed(reason)


def init():
    global _mod
    _logger.info('%s initializing', MOD_ID)
    try:
        _load_config()
        _mod = PremiumTime()
        _register_mod_settings(MOD_ID, _on_settings_changed)
        _mod.start()
        _logger.info('%s initialized', MOD_ID)
    except Exception:
        _logger.exception('%s failed to initialize', MOD_ID)


def fini():
    global _mod
    try:
        if _mod is not None:
            _mod.stop()
            _mod = None
    except Exception:
        _logger.exception('%s error in fini', MOD_ID)
