"""
zanju_rpb.main

Displays research progress for the currently selected vehicle in the hangar:
  - Module / next vehicle unlock progress  (tech tree XP)
  - Elite status progress                  (modules unlocked / total needed)
    - Field modification tree progress       (post-progression / "field mods")

BigWorld scripting uses Python 2.7. Avoid Python-3-only syntax.
"""
from __future__ import print_function, unicode_literals

import logging

from CurrentVehicle import g_currentVehicle
from helpers import dependency
from . import collector as _collector_api
from . import runtime_lifecycle as _runtime_lifecycle_api
from .scaleform import sync as _scaleform_sync_api
from . import runtime_updates as _runtime_updates_api
from . import t11_action_metadata as _t11_action_metadata_api
from .constants import (
    MOD_ID,
    MOD_VERSION,
)
from . import config as _config_api
from skeletons.gui.shared import IItemsCache

_logger = logging.getLogger('zanju.researchprogressbar')
_lobby_state_logger = logging.getLogger('gui.lobby_state_machine.lobby_state_machine')

_config = _config_api._config
_collect_research_progress_data = _collector_api._collect_research_progress_data
_cancel_pending_update_runtime = _runtime_updates_api._cancel_pending_update
_cancel_visibility_probe_runtime = _runtime_updates_api._cancel_visibility_probe
_finalize_runtime = _runtime_lifecycle_api._finalize_runtime
_handle_registered_mod_settings_change = _runtime_lifecycle_api._handle_registered_mod_settings_change
_handle_runtime_config_change = _runtime_lifecycle_api._handle_runtime_config_change
_handle_lobby_route_log_runtime = _runtime_updates_api._handle_lobby_route_log
_handle_preview_vehicle_changed_runtime = _runtime_updates_api._handle_preview_vehicle_changed
_handle_vehicle_changed_runtime = _runtime_updates_api._handle_vehicle_changed
_initialize_runtime = _runtime_lifecycle_api._initialize_runtime
_run_deferred_update_runtime = _runtime_updates_api._run_deferred_update
_run_visibility_probe_runtime = _runtime_updates_api._run_visibility_probe
_schedule_update_runtime = _runtime_updates_api._schedule_update
_schedule_visibility_probe_runtime = _runtime_updates_api._schedule_visibility_probe
_start_runtime_lifecycle = _runtime_lifecycle_api._start_runtime_lifecycle
_stop_runtime_lifecycle = _runtime_lifecycle_api._stop_runtime_lifecycle
_evaluate_scaleform_view_visibility = _scaleform_sync_api._evaluate_scaleform_visibility
_handle_gui_space_entered = _scaleform_sync_api._handle_gui_space_entered
_handle_gui_space_left = _scaleform_sync_api._handle_gui_space_left
_handle_view_added_to_container_runtime = _scaleform_sync_api._handle_view_added_to_container
_handle_scaleform_view_disposed_runtime = _scaleform_sync_api._handle_scaleform_view_disposed
_handle_scaleform_view_populated_runtime = _scaleform_sync_api._handle_scaleform_view_populated
_render_scaleform_view_runtime = _scaleform_sync_api._render_scaleform_view
_start_scaleform_view_runtime = _scaleform_sync_api._start_scaleform_view
_stop_scaleform_view_runtime = _scaleform_sync_api._stop_scaleform_view
_should_show_scaleform_view_runtime = _scaleform_sync_api._should_show_scaleform_view
_sync_scaleform_view_runtime = _scaleform_sync_api._sync_scaleform_view
_extract_t11_action_marker_meta = _t11_action_metadata_api._extract_t11_action_marker_meta


def _on_registered_mod_settings_changed(reason):
    _handle_registered_mod_settings_change(_mod, reason)


# ---------------------------------------------------------------------------
# Core mod class
# ---------------------------------------------------------------------------

class ResearchProgressBar(object):
    itemsCache = dependency.descriptor(IItemsCache)

    def __init__(self):
        self._active = False
        self._pending_update_callback = None
        self._visibility_probe_callback = None
        self._update_in_progress = False
        self._scaleform_view = None
        self._scaleform_payload = None
        self._scaleform_view_requested = False
        self._scaleform_settings_registered = False
        self._scaleform_hooks_registered = False
        self._scaleform_container_manager = None
        self._scaleform_view_visible = None
        self._lobby_route_log_handler = None
        self._current_lobby_route_path = None
        self._last_context_log_key = None
        self._last_scaleform_payload_log_key = None
        self._last_seen_sub_view_alias = None

    # -- lifecycle -----------------------------------------------------------

    def start(self):
        _start_runtime_lifecycle(self, _logger, _lobby_state_logger)
        # Avoid running heavy collection during early login/loading phase.
        # First update is triggered by onChanged once hangar vehicle selection settles.

    def stop(self):
        _stop_runtime_lifecycle(self, _logger, _lobby_state_logger)

    def on_external_config_changed(self, reason):
        _handle_runtime_config_change(self, reason, _logger)

    def _start_scaleform_view(self):
        _start_scaleform_view_runtime(self, _logger)

    def _stop_scaleform_view(self):
        _stop_scaleform_view_runtime(self, _logger)

    def _on_lobby_route_log(self, message):
        _handle_lobby_route_log_runtime(self, message, _logger)

    def _evaluate_scaleform_visibility(self, reason=None, incoming_view=None):
        return _evaluate_scaleform_view_visibility(self, _logger, reason, incoming_view)

    def _should_show_scaleform_view(self, reason=None, incoming_view=None):
        return _should_show_scaleform_view_runtime(self, _logger, reason, incoming_view)

    def _sync_scaleform_view(self, reason, incoming_view=None):
        return _sync_scaleform_view_runtime(self, reason, _logger, incoming_view)

    def _on_gui_space_entered(self, space_id):
        _handle_gui_space_entered(self, space_id, _logger)

    def _on_gui_space_left(self, space_id):
        _handle_gui_space_left(self, space_id, _logger)

    def _on_scaleform_view_populated(self, view):
        _handle_scaleform_view_populated_runtime(self, view, _logger)

    def _on_scaleform_view_disposed(self, view):
        _handle_scaleform_view_disposed_runtime(self, view, _logger)

    def _render_scaleform_view(self, vehicle, data):
        _render_scaleform_view_runtime(self, vehicle, data, _logger)

    def _cancel_pending_update(self):
        _cancel_pending_update_runtime(self)

    def _cancel_visibility_probe(self):
        _cancel_visibility_probe_runtime(self)

    def _schedule_visibility_probe(self, reason):
        _schedule_visibility_probe_runtime(self, reason)

    def _run_visibility_probe(self):
        _run_visibility_probe_runtime(self, _logger)

    def _schedule_update(self, reason):
        _schedule_update_runtime(self, reason)

    # -- event handlers ------------------------------------------------------

    def _on_vehicle_changed(self):
        _handle_vehicle_changed_runtime(self)

    def _on_preview_vehicle_changed(self):
        _handle_preview_vehicle_changed_runtime(self)

    def _on_view_added_to_container(self, _container, view):
        _handle_view_added_to_container_runtime(self, view, _logger)

    def _deferred_update(self):
        _run_deferred_update_runtime(self, _logger)

    # -- data collection -----------------------------------------------------

    def _update(self):
        if not _config.get('enabled'):
            return
        if not self._sync_scaleform_view('update_precheck'):
            return
        if self._update_in_progress:
            return

        self._update_in_progress = True
        try:
            vehicle = g_currentVehicle.item
            if vehicle is None:
                return

            try:
                stats = self.itemsCache.items.stats
            except Exception:
                _logger.exception('itemsCache not ready')
                return

            data = self._collect(vehicle, stats)
            self._render(vehicle, data)
        finally:
            self._update_in_progress = False

    def _collect(self, vehicle, stats):
        return _collect_research_progress_data(
            vehicle,
            stats,
            self.itemsCache.items,
            _extract_t11_action_marker_meta,
        )

    # -- rendering -----------------------------------------------------------

    def _render(self, vehicle, data):
        self._render_scaleform_view(vehicle, data)


# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------

_mod = None


def init():
    global _mod
    _mod = _initialize_runtime(
        _mod,
        ResearchProgressBar,
        MOD_ID,
        MOD_VERSION,
        _on_registered_mod_settings_changed,
        _logger,
    )


def fini():
    global _mod
    _mod = _finalize_runtime(_mod, MOD_ID, _logger)
