from __future__ import print_function, unicode_literals

import re

from frameworks.wulf import WindowLayer
from helpers import dependency
from skeletons.gui.impl import IGuiLoader

from ..constants import (
    SCALEFORM_VIEW_ALIAS,
    _HANGAR_VIEW_ALIASES,
    _NAVIGATING_ROUTE_PREFIX,
    _VISIBLE_ROUTE_PREFIX,
)

_ROUTE_PATH_RE = re.compile(r'\((subScope/[^)]*)\)')
_DEFAULT_HANGAR_ROUTES = frozenset((
    'subScope/subLayer/hangar',
    'subScope/subLayer/hangar/{root}',
))
# Layers WG's modal dialogs live on, above the bar's own WINDOW layer: the research
# confirm dialogs are TOP_WINDOW, fullscreen popups (e.g. the elite window) are
# FULLSCREEN_WINDOW.
_MODAL_WINDOW_LAYERS = frozenset((
    WindowLayer.TOP_WINDOW,
    WindowLayer.FULLSCREEN_WINDOW,
))


def _is_modal_window_open():
    """Whether one of WG's modal dialogs is currently up.

    Rebuilding the bar destroys and recreates its marker sprites. Doing that while a
    dialog owns the modal focus corrupts WG's focus stack, which blanks the hangar
    ammo bar until the next vehicle change -- the bar must therefore never rebuild
    under a dialog, only once it is gone.
    """
    try:
        windows_manager = dependency.instance(IGuiLoader).windowsManager
        return bool(windows_manager.findWindows(_is_modal_window))
    except Exception:
        return False


def _is_modal_window(window):
    try:
        return window.layer in _MODAL_WINDOW_LAYERS
    except Exception:
        return False


def _extract_route_path(message):
    if message.startswith(_NAVIGATING_ROUTE_PREFIX):
        return message[len(_NAVIGATING_ROUTE_PREFIX):].strip()

    if message.startswith(_VISIBLE_ROUTE_PREFIX):
        match = _ROUTE_PATH_RE.search(message)
        if match is not None:
            return match.group(1)

    return None


def _is_default_hangar_route(route_path):
    return route_path in _DEFAULT_HANGAR_ROUTES


def _get_scaleform_block_reason(
    context,
    is_active,
    scaleform_enabled,
    current_lobby_route_path,
    has_scaleform_view
):
    if not is_active:
        return 'inactive'
    if not scaleform_enabled:
        return 'scaleform_disabled'
    if context['preview_present']:
        return 'preview_vehicle_present'
    if not context['vehicle_present']:
        return 'no_current_vehicle'
    if current_lobby_route_path is not None and not _is_default_hangar_route(current_lobby_route_path):
        return 'lobby_route={0}'.format(current_lobby_route_path)

    incoming_alias = context['incoming_alias']
    incoming_layer = context['incoming_layer']
    effective_sub_view_alias = context['active_sub_view_alias']
    effective_top_sub_view_alias = context['active_top_sub_view_alias']
    if incoming_layer == WindowLayer.SUB_VIEW and incoming_alias is not None:
        effective_sub_view_alias = incoming_alias
    if incoming_layer == WindowLayer.TOP_SUB_VIEW and incoming_alias is not None:
        effective_top_sub_view_alias = incoming_alias

    if incoming_layer == WindowLayer.SUB_VIEW:
        if incoming_alias not in _HANGAR_VIEW_ALIASES and incoming_alias != SCALEFORM_VIEW_ALIAS:
            return 'incoming_sub_view={0}'.format(incoming_alias)
    if incoming_layer == WindowLayer.TOP_SUB_VIEW and incoming_alias != SCALEFORM_VIEW_ALIAS:
        return 'incoming_top_sub_view={0}'.format(incoming_alias)

    allow_missing_sub_view = effective_sub_view_alias is None and has_scaleform_view
    if effective_sub_view_alias not in _HANGAR_VIEW_ALIASES and not allow_missing_sub_view:
        return 'sub_view={0}'.format(effective_sub_view_alias)
    if effective_top_sub_view_alias not in (None, SCALEFORM_VIEW_ALIAS):
        return 'top_sub_view={0}'.format(effective_top_sub_view_alias)
    return None


def _needs_visibility_probe(context, block_reason):
    if block_reason is None:
        return False

    incoming_layer = context['incoming_layer']
    if incoming_layer == WindowLayer.TOP_SUB_VIEW:
        return True
    if context['active_top_sub_view_alias'] not in (None, SCALEFORM_VIEW_ALIAS):
        return True
    return False


def _should_dispose_scaleform_view_for_block(
    current_lobby_route_path,
    context,
    dispose_route_prefixes,
    dispose_sub_view_aliases
):
    route_path = current_lobby_route_path or ''
    if route_path.startswith(dispose_route_prefixes):
        return True

    incoming_alias = context.get('incoming_alias')
    active_sub_view_alias = context.get('active_sub_view_alias')
    return (
        incoming_alias in dispose_sub_view_aliases
        or active_sub_view_alias in dispose_sub_view_aliases
    )
