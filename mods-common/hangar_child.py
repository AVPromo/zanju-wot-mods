# -*- coding: utf-8 -*-
"""A child sub-view of a mod's own in the random garage document, `mono/hangar/main`.

`net.openwg.gameface` loads a mod into a Gameface document from a `ModInjectModel` on one of the
document's sub-views, and `gf_mod_inject` always writes to that one fixed field. A sub-view thus
holds one mod at most, and the last writer wins. `view_claim` makes a mod take one free candidate
of the client's own sub-views, but it protects only against mods that check too. A mod that writes
to a fixed sub-view with no check removes ours, and a mod that needs one exact sub-view finds it
taken by ours.

A child of the mod's own avoids both. The random garage view gets one more child, at a position
ID that no client resource and no other mod uses. The document lists it in `window.subViews`,
OpenWG finds the inject model on it, and nobody else writes to it.

Two routes, both measured in `main` on 2.4.1.0:

1. `gui.shared.system_factory.registerDynamicRandomHangarPresenters(posId, factory)`. The random
   garage view reads that list in `_getChildComponents` and builds the child with its own
   children. No patch is necessary. No client code calls this function on 2.4.1.0, so it is an
   extension point with no other user.
2. When that function is gone, a patch of `RandomHangar._onLoading` that calls `_registerChild`
   after the original. directives-helper adds its bar probe to the lobby bars the same way.

Both reach the random garage only. Each mode builds a root view and a document of its own.

**A factory must never raise.** `ViewComponent._constructChild` logs and raises again, and that
breaks the build of the whole garage. Every step inside the child therefore catches its own
errors, and a factory that cannot build its child returns None, which the client logs and skips.

Every client import stays inside a function, so this module is importable outside the game.
"""
from __future__ import absolute_import, print_function, unicode_literals

ROUTE_DYNAMIC_PRESENTER = 'dynamicPresenter'
ROUTE_REGISTER_CHILD = 'registerChild'

# The route in use, and the patch to undo for route 2. The dynamic presenter list has no remove
# call, so route 1 stays registered until the client closes.
_state = {
    'route': None,
    'patch': None,
}


def install(logger, pos_id, inject_name, styles, modules, data_property, make_data_model):
    """Give the random garage a child that carries this mod's inject model and data model.

    `make_data_model()` is called once for each garage build and returns the data model for that
    build, or None. Returns the name of the route in use, or None when no route works.
    """
    if _state['route']:
        return _state['route']
    try:
        from openwg_gameface import gf_mod_inject
    except ImportError:
        logger.info('net.openwg.gameface not found; the garage widgets are disabled '
                    '(install the OpenWG Gameface library to enable them)')
        return None
    try:
        view_class = _host_view_class(_host_model_class(
            gf_mod_inject, inject_name, styles, modules, data_property, make_data_model, logger))
    except Exception:
        logger.exception('Failed to define the garage child view; the garage widgets are disabled')
        return None
    factory = _safe_factory(view_class, logger)

    route = _register_dynamic_presenter(pos_id, factory, logger)
    if route is None:
        route = _patch_random_hangar(pos_id, factory, logger)
    _state['route'] = route
    if route is None:
        logger.warning('No route to a garage child view works; the garage widgets are disabled')
    else:
        logger.info('Garage child view at %s (route %s)', hex(pos_id), route)
    return route


def uninstall(logger):
    patch = _state['patch']
    _state['patch'] = None
    _state['route'] = None
    if patch is None:
        return
    cls, original = patch
    try:
        cls._onLoading = original
    except Exception:
        logger.exception('Failed to restore RandomHangar._onLoading')


def _host_model_class(gf_mod_inject, inject_name, styles, modules, data_property, make_data_model, logger):
    from frameworks.wulf import ViewModel

    class _HostModel(ViewModel):
        """The model of the child: OpenWG's inject model, then the mod's data model."""

        def __init__(self):
            # Two properties: the one gf_mod_inject adds, and the data model.
            super(_HostModel, self).__init__(properties=2, commands=0)

        def _initialize(self):
            super(_HostModel, self)._initialize()
            kwargs = {'modules': [str(url) for url in modules]}
            if styles:
                kwargs['styles'] = [str(url) for url in styles]
            try:
                gf_mod_inject(self, str(inject_name), **kwargs)
            except Exception:
                logger.exception('Failed to attach the inject model to the garage child view')
                return
            try:
                data_model = make_data_model()
                if data_model is not None:
                    self._addViewModelProperty(str(data_property), data_model)
            except Exception:
                logger.exception('Failed to attach the data model to the garage child view')

    return _HostModel


def _host_view_class(host_model):
    from gui.impl.pub.view_component import ViewComponent

    class _HostView(ViewComponent):

        def __init__(self):
            # The same call the garage's own presenters make. ViewComponent builds the model.
            super(_HostView, self).__init__(model=host_model)

    return _HostView


def _safe_factory(view_class, logger):
    def factory():
        try:
            return view_class()
        except Exception:
            # None, not a raise: the client logs a None child and skips it, but a raise breaks
            # the build of the whole garage.
            logger.exception('Failed to build the garage child view')
            return None
    return factory


def _register_dynamic_presenter(pos_id, factory, logger):
    try:
        from gui.shared.system_factory import registerDynamicRandomHangarPresenters
    except Exception:
        logger.info('The client has no registerDynamicRandomHangarPresenters; trying a patch')
        return None
    try:
        registerDynamicRandomHangarPresenters(pos_id, factory)
    except Exception:
        logger.exception('Failed to register the garage child view; trying a patch')
        return None
    return ROUTE_DYNAMIC_PRESENTER


def _patch_random_hangar(pos_id, factory, logger):
    try:
        from gui.impl.lobby.hangar.random.random_hangar import RandomHangar
    except Exception:
        logger.exception('The client has no RandomHangar to patch')
        return None
    original = RandomHangar._onLoading

    def _on_loading_with_child(self, *args, **kwargs):
        original(self, *args, **kwargs)
        # After the original, the garage's own children are in place, and _registerChild attaches
        # a new child at once. A failure here costs the widgets, not the garage.
        try:
            _attach(self, pos_id, factory, logger)
        except Exception:
            logger.exception('Failed to add the child view to the garage')

    RandomHangar._onLoading = _on_loading_with_child
    _state['patch'] = (RandomHangar, original)
    return ROUTE_REGISTER_CHILD


def _attach(hangar, pos_id, factory, logger):
    if hangar.getChildView(pos_id) is not None:
        return
    child = factory()
    if child is None:
        return
    hangar._registerChild(pos_id, child)
    if hangar.getChildView(pos_id) is not None:
        return
    logger.warning('The garage did not take the child view at %s', hex(pos_id))
    try:
        hangar._unregisterChild(child.uniqueID, True)
    except Exception:
        logger.exception('Failed to remove the child view again')
