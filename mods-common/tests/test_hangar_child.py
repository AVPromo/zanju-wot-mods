# -*- coding: utf-8 -*-
"""Tests for the child sub-view that a mod adds to the random garage.

The client classes are stood in for. The stand-ins keep only the behavior the module depends on:
a ViewComponent builds its model from the class it is given, and the client's child
construction raises again when a factory raises.
"""
from __future__ import absolute_import, print_function, unicode_literals

import sys
import types
import unittest

from mods_common import hangar_child


class _Logger(object):
    def __init__(self):
        self.exceptions = []
        self.warnings = []

    def info(self, message, *args):
        pass

    def warning(self, message, *args):
        self.warnings.append(message)

    def exception(self, message, *args):
        self.exceptions.append(message)


class _ViewModel(object):
    def __init__(self, properties=0, commands=0):
        self.properties = {}
        self._initialize()

    def _initialize(self):
        pass

    def _addViewModelProperty(self, name, model):
        self.properties[name] = model


class _ViewComponent(object):
    def __init__(self, model=None):
        self.model = model()


class _RandomHangar(object):
    def __init__(self):
        self.children = {}

    def _onLoading(self, *args, **kwargs):
        self.loaded = True

    def getChildView(self, pos_id):
        return self.children.get(pos_id)

    def _registerChild(self, pos_id, child):
        self.children[pos_id] = child


def _put_module(name, module):
    """Register a stand-in module, and every parent package it needs, as attributes too."""
    parts = name.split('.')
    for index in range(1, len(parts)):
        parent_name = '.'.join(parts[:index])
        if sys.modules.get(parent_name) is None:
            sys.modules[str(parent_name)] = types.ModuleType(str(parent_name))
        if index > 1:
            setattr(sys.modules['.'.join(parts[:index - 1])], str(parts[index - 1]), sys.modules[parent_name])
    sys.modules[str(name)] = module
    if len(parts) > 1 and module is not None:
        setattr(sys.modules['.'.join(parts[:-1])], str(parts[-1]), module)


def _install_modules(with_dynamic=True, with_openwg=True):
    registered = {}
    injected = []

    def register(pos_id, factory):
        registered[pos_id] = factory

    def gf_mod_inject(model, name, modules=None, styles=None):
        injected.append((name, modules, styles))

    modules = {
        'frameworks.wulf': types.ModuleType(str('frameworks.wulf')),
        'gui.impl.pub.view_component': types.ModuleType(str('gui.impl.pub.view_component')),
        'gui.impl.lobby.hangar.random.random_hangar': types.ModuleType(
            str('gui.impl.lobby.hangar.random.random_hangar')),
        'gui.shared.system_factory': types.ModuleType(str('gui.shared.system_factory')),
        'openwg_gameface': types.ModuleType(str('openwg_gameface')),
    }
    modules['frameworks.wulf'].ViewModel = _ViewModel
    modules['gui.impl.pub.view_component'].ViewComponent = _ViewComponent
    modules['gui.impl.lobby.hangar.random.random_hangar'].RandomHangar = _RandomHangar
    if with_dynamic:
        modules['gui.shared.system_factory'].registerDynamicRandomHangarPresenters = register
    if with_openwg:
        modules['openwg_gameface'].gf_mod_inject = gf_mod_inject
    else:
        modules['openwg_gameface'] = None
    for name, module in sorted(modules.items()):
        _put_module(name, module)
    return registered, injected


class _BaseRoot(object):
    """A root view whose _onLoading is inherited, as FunRandomHangar's is."""

    def __init__(self):
        self.children = {}
        self.seen_inside = None

    def _onLoading(self, *args, **kwargs):
        # A root view builds its children here, so a fallback asks the marker at this point.
        self.seen_inside = hangar_child.inside_patched_root()

    def getChildView(self, pos_id):
        return self.children.get(pos_id)

    def _registerChild(self, pos_id, child):
        self.children[pos_id] = child


class _ModeHangar(_BaseRoot):
    pass


def _put_mode_module():
    module = types.ModuleType(str('zanju_test_modes.hangar'))
    module.ModeHangar = _ModeHangar
    _put_module('zanju_test_modes.hangar', module)


class HangarChildTest(unittest.TestCase):

    def setUp(self):
        self.saved = dict(sys.modules)
        self.original_on_loading = _RandomHangar._onLoading
        hangar_child._state.update(route=None, patches=[], depth=0)
        self.logger = _Logger()

    def tearDown(self):
        hangar_child.uninstall(self.logger)
        _RandomHangar._onLoading = self.original_on_loading
        _ModeHangar.__dict__.get('_onLoading') and delattr(_ModeHangar, '_onLoading')
        sys.modules.clear()
        sys.modules.update(self.saved)

    def _install(self, make_data_model):
        return hangar_child.install(self.logger, 0x5A4E4354, 'zanju_test', ['a.css'], ['a.js'],
                                    'zanjuTest', make_data_model)

    def test_the_dynamic_presenter_is_the_first_route(self):
        registered, injected = _install_modules()
        route = self._install(lambda: 'data')
        self.assertEqual(route, hangar_child.ROUTE_DYNAMIC_PRESENTER)
        child = registered[0x5A4E4354]()
        self.assertEqual(child.model.properties, {'zanjuTest': 'data'})
        self.assertEqual(injected, [('zanju_test', ['a.js'], ['a.css'])])

    def test_a_client_without_the_dynamic_list_gets_the_patch(self):
        _install_modules(with_dynamic=False)
        route = self._install(lambda: 'data')
        self.assertEqual(route, hangar_child.ROUTE_REGISTER_CHILD)
        hangar = _RandomHangar()
        hangar._onLoading()
        self.assertTrue(hangar.loaded)
        self.assertEqual(hangar.getChildView(0x5A4E4354).model.properties, {'zanjuTest': 'data'})

    def test_the_patch_is_undone_on_uninstall(self):
        _install_modules(with_dynamic=False)
        self._install(lambda: 'data')
        hangar_child.uninstall(self.logger)
        hangar = _RandomHangar()
        hangar._onLoading()
        self.assertIsNone(hangar.getChildView(0x5A4E4354))

    def test_no_openwg_means_no_route(self):
        registered, _ = _install_modules(with_openwg=False)
        self.assertIsNone(self._install(lambda: 'data'))
        self.assertEqual(registered, {})

    def test_a_data_model_that_raises_costs_the_data_not_the_garage(self):
        registered, injected = _install_modules()
        self._install(lambda: 1 / 0)
        child = registered[0x5A4E4354]()
        self.assertIsNotNone(child)
        self.assertEqual(child.model.properties, {})
        self.assertEqual(len(injected), 1)
        self.assertEqual(len(self.logger.exceptions), 1)

    def test_a_factory_that_cannot_build_returns_none_rather_than_raise(self):
        registered, _ = _install_modules()
        self._install(lambda: 'data')
        _ViewComponent_init = _ViewComponent.__init__

        def failing_init(self, model=None):
            raise RuntimeError('construction failed')

        _ViewComponent.__init__ = failing_init
        try:
            self.assertIsNone(registered[0x5A4E4354]())
        finally:
            _ViewComponent.__init__ = _ViewComponent_init
        self.assertEqual(len(self.logger.exceptions), 1)

    def test_a_second_install_keeps_the_first_route(self):
        registered, _ = _install_modules()
        self._install(lambda: 'data')
        self.assertEqual(self._install(lambda: 'other'), hangar_child.ROUTE_DYNAMIC_PRESENTER)
        self.assertEqual(len(registered), 1)

    def test_attach_adds_the_child_to_every_root_the_client_has(self):
        _install_modules()
        _put_mode_module()
        factory = hangar_child.make_factory(self.logger, 'zanju_test', [], ['a.js'], 'zanjuTest', lambda: 'data')
        parents = [hangar_child.RANDOM_GARAGE, ('zanju_test_modes.hangar', 'ModeHangar'),
                   ('zanju_test_modes.gone', 'Gone')]
        patched = hangar_child.attach(self.logger, parents, 0x5A4E4448, factory, 'Test child')
        self.assertEqual(patched, ['RandomHangar', 'ModeHangar'])
        mode = _ModeHangar()
        mode._onLoading()
        self.assertEqual(mode.getChildView(0x5A4E4448).model.properties, {'zanjuTest': 'data'})
        # A second load of the same root view adds no second child.
        child = mode.getChildView(0x5A4E4448)
        mode._onLoading()
        self.assertIs(mode.getChildView(0x5A4E4448), child)

    def test_the_marker_is_up_only_while_a_patched_root_builds_its_children(self):
        _install_modules()
        _put_mode_module()
        factory = hangar_child.make_factory(self.logger, 'zanju_test', [], ['a.js'], 'zanjuTest', lambda: 'data')
        mode = _ModeHangar()
        mode._onLoading()
        self.assertFalse(mode.seen_inside)
        hangar_child.attach(self.logger, [('zanju_test_modes.hangar', 'ModeHangar')], 0x5A4E4448, factory, 'Test child')
        mode = _ModeHangar()
        mode._onLoading()
        self.assertTrue(mode.seen_inside)
        self.assertFalse(hangar_child.inside_patched_root())

    def test_an_inherited_on_loading_is_inherited_again_after_uninstall(self):
        _install_modules()
        _put_mode_module()
        factory = hangar_child.make_factory(self.logger, 'zanju_test', [], ['a.js'], 'zanjuTest', lambda: 'data')
        hangar_child.attach(self.logger, [('zanju_test_modes.hangar', 'ModeHangar')], 0x5A4E4448, factory, 'Test child')
        self.assertIn('_onLoading', _ModeHangar.__dict__)
        hangar_child.uninstall(self.logger)
        self.assertNotIn('_onLoading', _ModeHangar.__dict__)
        mode = _ModeHangar()
        mode._onLoading()
        self.assertIsNone(mode.getChildView(0x5A4E4448))

    def test_no_openwg_means_no_factory(self):
        _install_modules(with_openwg=False)
        self.assertIsNone(hangar_child.make_factory(self.logger, 'zanju_test', [], ['a.js'], 'zanjuTest',
                                                    lambda: 'data'))


if __name__ == '__main__':
    unittest.main()
