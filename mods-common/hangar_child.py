# -*- coding: utf-8 -*-
"""A child sub-view of a mod's own in a Gameface document of the garage.

`net.openwg.gameface` loads a mod into a Gameface document from a `ModInjectModel` on one of the
document's sub-views, and `gf_mod_inject` always writes to that one fixed field. A sub-view thus
holds one mod at most, and the last writer wins. `view_claim` makes a mod take one free candidate
of the client's own sub-views, but it protects only against mods that check too. A mod that writes
to a fixed sub-view with no check removes ours, and a mod that needs one exact sub-view finds it
taken by ours.

A child of the mod's own avoids both. A root view gets one more child, at a position ID that no
client resource and no other mod uses. The document lists it in `window.subViews`, OpenWG finds
the inject model on it, and nobody else writes to it.

Two routes, both measured in `main` on 2.4.1.0:

1. `gui.shared.system_factory.registerDynamicRandomHangarPresenters(posId, factory)`. The random
   garage view reads that list in `_getChildComponents` and builds the child with its own
   children. No patch is necessary. No client code calls this function on 2.4.1.0, so it is an
   extension point with no other user. `install` uses it.
2. A patch of the root view's `_onLoading` that calls `_registerChild` after the original. This
   reaches any root view: the random garage when route 1 is gone, the garage of each mode, and
   the lobby bars. `attach` uses it.

Each mode builds a root view and a document of its own, so a child of `RandomHangar` reaches the
random garage only. `MODE_GARAGES` names the root view of each mode on 2.4.1.0.

**A factory must never raise.** `ViewComponent._constructChild` logs and raises again, and that
breaks the build of the whole garage. Every step inside the child therefore catches its own
errors, and a factory that cannot build its child returns None, which the client logs and skips.

Every client import stays inside a function, so this module is importable outside the game.
"""
from __future__ import absolute_import, print_function, unicode_literals

ROUTE_DYNAMIC_PRESENTER = 'dynamicPresenter'
ROUTE_REGISTER_CHILD = 'registerChild'

# Root views, as (module, class). A mod that shows in more places than the random garage passes
# the ones it needs to `attach`.
RANDOM_GARAGE = ('gui.impl.lobby.hangar.random.random_hangar', 'RandomHangar')
# The garage of each mode, from the mode extensions of 2.4.1.0. Each builds the same main menu
# and vehicle menu presenters as the random garage, in a document of its own.
MODE_GARAGES = (
    ('comp7.gui.impl.lobby.hangar.comp7_hangar', 'Comp7Hangar'),
    ('comp7_light.gui.impl.lobby.hangar.comp7_light_hangar', 'Comp7LightHangar'),
    ('frontline.gui.impl.lobby.hangar_view', 'FrontlineHangar'),
    ('fun_random.gui.impl.lobby.hangar.fun_random_hangar', 'FunRandomHangar'),
    ('last_stand.gui.impl.lobby.hangar_view', 'HangarView'),
)
# The lobby bars, `mono/hangar/header` and `mono/hangar/footer`.
LOBBY_HEADER = ('gui.impl.lobby.page.lobby_header', 'LobbyHeader')
LOBBY_FOOTER = ('gui.impl.lobby.page.lobby_footer', 'LobbyFooter')

# The route of `install`, the patches to undo, and how deep the code is inside a patched
# `_onLoading` now.
_state = {
    'route': None,
    'patches': [],
    'depth': 0,
}


def make_factory(logger, inject_name, styles, modules, data_property, make_data_model):
    """A factory for a child that carries this mod's inject model and data model, or None.

    `make_data_model()` is called once for each child and returns the data model, or None.
    """
    try:
        from openwg_gameface import gf_mod_inject
    except ImportError:
        logger.info('net.openwg.gameface not found; the Gameface parts of the mod are disabled '
                    '(install the OpenWG Gameface library to enable them)')
        return None
    try:
        view_class = _host_view_class(_host_model_class(
            gf_mod_inject, inject_name, styles, modules, data_property, make_data_model, logger))
    except Exception:
        logger.exception('Failed to define the child view; the Gameface parts of the mod are disabled')
        return None
    return _safe_factory(view_class, logger)


def install(logger, pos_id, inject_name, styles, modules, data_property, make_data_model):
    """Give the random garage a child that carries this mod's inject model and data model.

    Returns the name of the route in use, or None when no route works.
    """
    if _state['route']:
        return _state['route']
    factory = make_factory(logger, inject_name, styles, modules, data_property, make_data_model)
    if factory is None:
        return None

    route = _register_dynamic_presenter(pos_id, factory, logger)
    if route is None and attach(logger, [RANDOM_GARAGE], pos_id, factory, 'Garage child view'):
        route = ROUTE_REGISTER_CHILD
    _state['route'] = route
    if route is None:
        logger.warning('No route to a garage child view works; the garage widgets are disabled')
    else:
        logger.info('Garage child view at %s (route %s)', hex(pos_id), route)
    return route


def attach(logger, parents, pos_id, factory, label):
    """Add a child from `factory` to every root view of `parents`, on each of its loads.

    `parents` holds (module, class) pairs. A parent that the client does not have is skipped.
    `label` names the child in the log. Returns the names of the classes patched.
    """
    patched = []
    for module_path, class_name in parents:
        parent_class = _import_class(module_path, class_name)
        if parent_class is None:
            logger.info('%s: the client has no %s; skipping it', label, class_name)
            continue
        _patch_on_loading(parent_class, pos_id, factory, label, logger)
        patched.append(class_name)
    if patched:
        logger.info('%s at %s in %s', label, hex(pos_id), ', '.join(patched))
    return patched


def inside_patched_root():
    """True while a root view patched by `attach` builds its own children.

    A root view builds every child, and every child model, inside its `_onLoading`. A mod that
    also claims a client sub-view as a fallback asks this, and claims only in a root view that
    it has no child in.
    """
    return _state['depth'] > 0


def uninstall(logger):
    _state['route'] = None
    _state['depth'] = 0
    while _state['patches']:
        parent_class, original, defined_here = _state['patches'].pop()
        try:
            if defined_here:
                parent_class._onLoading = original
            else:
                # The class inherited _onLoading, so removing the patch restores the inherited one.
                del parent_class._onLoading
        except Exception:
            logger.exception('Failed to restore %s._onLoading', parent_class.__name__)


def _import_class(module_path, class_name):
    try:
        module = __import__(str(module_path), globals(), locals(), [str(class_name)])
        return getattr(module, class_name)
    except Exception:
        return None


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
                logger.exception('Failed to attach the inject model to the child view')
                return
            try:
                data_model = make_data_model()
                if data_model is not None:
                    self._addViewModelProperty(str(data_property), data_model)
            except Exception:
                logger.exception('Failed to attach the data model to the child view')

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
            logger.exception('Failed to build the child view')
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


def _patch_on_loading(parent_class, pos_id, factory, label, logger):
    defined_here = '_onLoading' in parent_class.__dict__
    original = parent_class._onLoading

    def _on_loading_with_child(self, *args, **kwargs):
        _state['depth'] += 1
        try:
            original(self, *args, **kwargs)
        finally:
            _state['depth'] -= 1
        # After the original, the root's own children are in place, and _registerChild attaches
        # a new child at once. A failure here costs the child, not the root view.
        try:
            _attach(self, pos_id, factory, label, logger)
        except Exception:
            logger.exception('%s: failed to add the child to %s', label, type(self).__name__)

    parent_class._onLoading = _on_loading_with_child
    _state['patches'].append((parent_class, original, defined_here))


def _attach(parent, pos_id, factory, label, logger):
    if parent.getChildView(pos_id) is not None:
        return
    child = factory()
    if child is None:
        return
    parent._registerChild(pos_id, child)
    if parent.getChildView(pos_id) is not None:
        logger.info('%s added to %s', label, type(parent).__name__)
        return
    logger.warning('%s: %s did not take the child at %s', label, type(parent).__name__, hex(pos_id))
    try:
        parent._unregisterChild(child.uniqueID, True)
    except Exception:
        logger.exception('%s: failed to remove the child again', label)
