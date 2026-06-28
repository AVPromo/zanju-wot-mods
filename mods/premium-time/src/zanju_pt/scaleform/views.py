"""Helpers for resolving the topmost active view alias on a lobby container layer."""
from __future__ import print_function, unicode_literals

from numbers import Integral


def get_view_alias(view):
    if view is None:
        return None

    alias = getattr(view, 'alias', None)
    if alias is None or isinstance(alias, Integral):
        config = getattr(view, 'as_config', None)
        if config is not None:
            config_alias = getattr(config, 'alias', None)
            if config_alias is not None:
                alias = config_alias
    return alias


def get_active_view_alias(container_manager, layer, logger):
    view = _get_topmost_view_for_layer(container_manager, layer, logger)
    if view is None:
        return None
    return get_view_alias(view)


def _get_topmost_view_for_layer(container_manager, layer, logger):
    if container_manager is None:
        return None

    try:
        container = container_manager.getContainer(layer)
        if container is None:
            return None
        get_topmost_view = getattr(container, 'getTopmostView', None)
        if callable(get_topmost_view):
            return get_topmost_view()

        view = None
        num_children = getattr(container, 'numChildren', 0)
        if callable(num_children):
            num_children = num_children()
        get_child_at = getattr(container, 'getChildAt', None)
        if callable(get_child_at) and num_children:
            view = get_child_at(num_children - 1)
        return view
    except Exception:
        if logger is not None:
            logger.exception('Failed to resolve topmost lobby view for layer=%s', layer)
        return None
