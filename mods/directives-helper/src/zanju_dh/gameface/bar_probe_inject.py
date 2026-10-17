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
a child of its own to each bar, at a position ID that no client or mod resource uses (see
hangar_child). OpenWG's bootstrap loads mods from every sub-view, this one included, so the
probe gets into the bar documents and takes nothing from anyone.

See "The Lobby Bars Take Input Where They Draw Nothing" in docs/reference/gameface-mod-widgets.md.
"""
from __future__ import print_function, unicode_literals

import logging

from frameworks.wulf import ViewModel

from .. import hangar_child
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

# The bars: which edge of the screen each holds, its view class, and the class prefix of the
# element that view sizes itself from. The header's is its App root, `useSyncSizeTexture(0,
# 250)`. The footer's App root fills the whole view, and its `App_footer` element is the one with
# `useSyncSizeTexture(250, 0)`.
_BARS = (
    ('top', hangar_child.LOBBY_HEADER, 'App_'),
    ('bottom', hangar_child.LOBBY_FOOTER, 'App_footer_'),
)

_module_logger = logging.getLogger('zanju.directiveshelper')


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


def install(logger):
    """Add the probe to each lobby bar as a child of its own. Returns True when any is hooked.

    The children share hangar_child with the window, so window_inject.uninstall removes them too.
    """
    hooked = []
    for edge, parent, root_class in _BARS:
        factory = hangar_child.make_factory(
            logger, _INJECT_NAME, [], [_MODULE_URL], _DATA_PROPERTY,
            lambda edge=edge, root_class=root_class: _BarDataModel(edge, root_class, logger))
        if factory is None:
            # window_inject already logged why, and the window cannot appear without the library.
            return False
        if hangar_child.attach(logger, [parent], _POS_ID, factory, 'Bar probe'):
            hooked.append(edge)
        else:
            logger.warning('Could not set up the %s bar probe. The window uses the screen edge on that side.', edge)
    return bool(hooked)


def uninstall(logger):
    hangar_child.uninstall(logger)
