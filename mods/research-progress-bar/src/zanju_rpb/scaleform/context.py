from __future__ import print_function, unicode_literals

from CurrentVehicle import g_currentPreviewVehicle, g_currentVehicle
from frameworks.wulf import WindowLayer

from . import views as _scaleform_views_api

_get_active_view_alias = _scaleform_views_api._get_active_view_alias
_get_view_alias = _scaleform_views_api._get_view_alias


def _build_scaleform_context(container_manager, last_seen_sub_view_alias, incoming_view, logger):
    active_sub_view_alias = _get_active_view_alias(container_manager, WindowLayer.SUB_VIEW, logger)
    if active_sub_view_alias is None:
        active_sub_view_alias = last_seen_sub_view_alias

    return {
        'active_sub_view_alias': active_sub_view_alias,
        'active_top_sub_view_alias': _get_active_view_alias(container_manager, WindowLayer.TOP_SUB_VIEW, logger),
        'active_window_alias': _get_active_view_alias(container_manager, WindowLayer.WINDOW, logger),
        'active_top_window_alias': _get_active_view_alias(container_manager, WindowLayer.TOP_WINDOW, logger),
        'preview_present': g_currentPreviewVehicle.isPresent(),
        'vehicle_present': g_currentVehicle.item is not None,
        'incoming_alias': _get_view_alias(incoming_view),
        'incoming_layer': getattr(incoming_view, 'layer', None) if incoming_view is not None else None,
    }


def _log_scaleform_context(
    reason,
    context,
    block_reason,
    current_lobby_route_path,
    last_context_log_key,
    logger,
):
    log_key = (
        block_reason is None,
        block_reason,
        current_lobby_route_path,
        context['active_sub_view_alias'],
        context['active_top_sub_view_alias'],
        context['preview_present'],
        context['vehicle_present'],
    )
    if log_key == last_context_log_key:
        return last_context_log_key

    logger.info(
        'Garage view gate[%s]: visible=%s reason=%s route=%s sub=%s topSub=%s preview=%s vehicle=%s',
        reason,
        block_reason is None,
        block_reason or 'none',
        current_lobby_route_path,
        context['active_sub_view_alias'],
        context['active_top_sub_view_alias'],
        context['preview_present'],
        context['vehicle_present'],
    )
    return log_key
