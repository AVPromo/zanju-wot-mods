# -*- coding: utf-8 -*-
"""Carries the bar probe into the garage's top bar and bottom bar documents.

The lobby bars are separate Gameface documents over the garage: `mono/hangar/header` at the
top, `mono/hangar/footer` at the bottom. Each takes every press across its strip, also where it
draws nothing, so the directives window must keep its title bar between them. The window lives
in `mono/hangar/main` and cannot read the bar documents. Thus bar_probe.js runs inside each bar
document, measures the strip, and reports it with the `reportBar` command. This module passes
each report to window_inject, which pushes it to the window.

The probe does not claim one of the bars' own sub-views. A sub-view holds one mod at most (see
view_claim), and a claimed view is a view that another mod cannot have. Instead the probe adds
a child of its own to each bar, at a position ID that no client or mod resource uses. OpenWG's
bootstrap loads mods from every sub-view, this one included, so the probe gets into the bar
documents and takes nothing from anyone.

See "The Lobby Bars Take Input Where They Draw Nothing" in docs/reference/gameface-mod-widgets.md.
"""
from __future__ import print_function, unicode_literals

import logging

from frameworks.wulf import ViewModel

from . import window_inject

_MODULE_URL = 'coui://gui/gameface/mods/zanju_directives/bar_probe.js'
_INJECT_NAME = 'zanju_dh_bar_probe'
_DATA_PROPERTY = 'zanjuDhBarProbe'

# Where the probe's child sits among a bar's children. Client resource IDs, and the IDs OpenWG
# gives mod resources, count up from zero and were near 136,000 on 2.4.0.2, so a number this far
# out collides with neither. Position IDs belong to one parent, so both bars can use the same
# one. Measured on 2.4.0.2: the header and the footer each attached a child here, and the probe
# loaded in both documents.
_POS_ID = 0x5A4E4448

# The bars: which edge of the screen each holds, where its view class lives, and the class prefix
# of the element that view sizes itself from. The header's is its App root, `useSyncSizeTexture(0,
# 250)`. The footer's App root fills the whole view, and its `App_footer` element is the one with
# `useSyncSizeTexture(250, 0)`.
_BARS = (
    ('top', 'gui.impl.lobby.page.lobby_header', 'LobbyHeader', 'App_'),
    ('bottom', 'gui.impl.lobby.page.lobby_footer', 'LobbyFooter', 'App_footer_'),
)

_module_logger = logging.getLogger('zanju.directiveshelper')
# ViewComponent builds its model with no arguments, so the model reads the inject function from
# here. Set by install().
_gf_mod_inject = None

# (class, original _onLoading, whether the class defined it itself)
_patched = []


class _BarDataModel(ViewModel):
    """What bar_probe.js needs: the element to measure, and the command to report it with."""

    def __init__(self, edge, root_class, logger):
        self._edge = edge
        self._root_class = root_class
        self._logger = logger
        super(_BarDataModel, self).__init__(properties=1, commands=1)

    def _initialize(self):
        super(_BarDataModel, self)._initialize()
        self._addStringProperty('rootClass', self._root_class)
        self.reportBar = self._addCommand('reportBar')
        self.reportBar += self.__onReportBar

    def __onReportBar(self, *args):
        # A command handler runs inside the client's own dispatch, so nothing may leave it. See
        # "A Listener That Raises Stops The Ones Behind It" in docs/reference/events-and-callbacks.md.
        try:
            window_inject.report_bar(self._edge, args[0] if args else None, self._logger)
        except Exception:
            self._logger.exception('Failed to pass on the %s bar report', self._edge)


class _ProbeHostModel(ViewModel):
    """The model of the probe's own child in a bar: OpenWG's inject model and the probe's data."""

    # Set on the subclass for each bar, because ViewComponent builds the model with no arguments.
    EDGE = None
    ROOT_CLASS = None

    def __init__(self):
        super(_ProbeHostModel, self).__init__(properties=2, commands=0)

    def _initialize(self):
        super(_ProbeHostModel, self)._initialize()
        _gf_mod_inject(self, str(_INJECT_NAME), modules=[str(_MODULE_URL)])
        self._addViewModelProperty(
            str(_DATA_PROPERTY), _BarDataModel(self.EDGE, self.ROOT_CLASS, _module_logger))


def _probe_view_class(edge, root_class):
    # Imported here rather than at the top, so a client that moved the class costs the probe
    # and not the whole mod.
    from gui.impl.pub.view_component import ViewComponent

    host_model = type(str('_ProbeHostModel_' + edge), (_ProbeHostModel,), {
        'EDGE': edge,
        'ROOT_CLASS': root_class,
    })

    class _ProbeView(ViewComponent):
        def __init__(self):
            # The same call the bars' own presenters make.
            super(_ProbeView, self).__init__(model=host_model)

    return _ProbeView


def install(logger):
    """Add the probe to each lobby bar as a child of its own. Returns True when any is hooked."""
    global _gf_mod_inject
    if _patched:
        return True

    try:
        from openwg_gameface import gf_mod_inject
    except ImportError:
        # window_inject already logs this, and the window cannot appear without the library.
        return False
    _gf_mod_inject = gf_mod_inject

    for edge, module_path, class_name, root_class in _BARS:
        try:
            module = __import__(module_path, globals(), locals(), [str(class_name)])
            bar_class = getattr(module, class_name)
            probe_view = _probe_view_class(edge, root_class)
        except Exception:
            logger.exception('Could not set up the %s bar probe. The window uses the screen edge on that side.', edge)
            continue
        _patch(bar_class, edge, probe_view, logger)

    if not _patched:
        return False
    logger.info('Bar probe installed (%d bars)', len(_patched))
    return True


def _patch(bar_class, edge, probe_view, logger):
    defined_here = '_onLoading' in bar_class.__dict__
    original = bar_class._onLoading

    def _on_loading_with_probe(self, *args, **kwargs):
        original(self, *args, **kwargs)
        # After the original, the bar's own children are in place, and _registerChild attaches a
        # new child at once. A failure here costs the probe, not the bar.
        child = None
        try:
            child = probe_view()
            self._registerChild(_POS_ID, child)
            if self.getChildView(_POS_ID) is not None:
                logger.info('Bar probe added to %s', type(self).__name__)
                return
            logger.warning(
                '%s did not take the bar probe. The window uses the screen edge on that side.', type(self).__name__)
        except Exception:
            logger.exception('Failed to add the bar probe to %s', type(self).__name__)
        if child is not None:
            try:
                self._unregisterChild(child.uniqueID, True)
            except Exception:
                logger.exception('Failed to remove the bar probe from %s', type(self).__name__)

    bar_class._onLoading = _on_loading_with_probe
    _patched.append((bar_class, original, defined_here))


def uninstall(logger):
    while _patched:
        bar_class, original, defined_here = _patched.pop()
        try:
            if defined_here:
                bar_class._onLoading = original
            else:
                # The class inherited _onLoading, so removing the patch restores the inherited one.
                del bar_class._onLoading
        except Exception:
            logger.exception('Failed to restore %s._onLoading', bar_class.__name__)
