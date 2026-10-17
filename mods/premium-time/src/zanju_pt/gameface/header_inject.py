"""Live remaining-time counters on the lobby header's subscription buttons.

The lobby top bar is a Gameface (HTML/JS) view: the Premium Account button
labels are rendered client-side by the header's JS bundle from localization strings and
`expiryTime` on `UserAccountModel.subscriptions`, so neither the Python presenter nor the
view model exposes the text itself. To change those labels we inject JS into the header
document via `net.openwg.gameface`: its bootstrap runs in every Gameface view and loads
the modules listed in a `ModInjectModel` attached to any sub-view's view model.

The inject model rides on a child view of the mod's own in `LobbyHeader`, at a position ID
that no client resource and no other mod uses (see hangar_child). An earlier version wrote it
onto the client's own `UserAccountModel`, with no check, so a mod that did the same removed
ours, or found the view taken by ours. Beside the inject model sits a small data model
(`zanjuPtHeader`) carrying what the JS side cannot know by itself: localized unit labels and
the client-to-server clock offset. The injected JS (header_patch.js) reads the game's own
`expiryTime` from `UserAccountModel` and renders the countdown. If the OpenWG library is not
installed the mod keeps working without the header counters.
"""
from __future__ import print_function, unicode_literals

from frameworks.wulf import ViewModel

from .. import hangar_child
from ..formatting import build_header_payload

_MODULE_URL = 'coui://gui/gameface/mods/zanju_premiumtime/header_patch.js'
_INJECT_NAME = 'zanju_pt_header'
_DATA_PROPERTY = 'zanjuPtHeader'
# The position of the child in LobbyHeader: `ZNPT`. directives-helper has a child of its own in
# the same bar at `ZNDH`, and two children of one parent need two IDs.
_POS_ID = 0x5A4E5054


class _HeaderDataModel(ViewModel):
    """Formatting data consumed by header_patch.js (payload built in formatting.py)."""

    def __init__(self, payload):
        self._payload = payload
        # `properties` must match the number added below, or wulf drops the extras.
        super(_HeaderDataModel, self).__init__(properties=5, commands=0)

    def _initialize(self):
        super(_HeaderDataModel, self)._initialize()
        self._addNumberProperty('timeOffset', self._payload['timeOffset'])
        self._addStringProperty('dayUnit', self._payload['dayUnit'])
        self._addStringProperty('hourUnit', self._payload['hourUnit'])
        self._addStringProperty('minuteUnit', self._payload['minuteUnit'])
        self._addStringProperty('secondUnit', self._payload['secondUnit'])


def install(logger):
    """Give the lobby header a child that carries our inject marker and data. Returns True when
    active."""
    factory = hangar_child.make_factory(
        logger, _INJECT_NAME, [], [_MODULE_URL], _DATA_PROPERTY,
        lambda: _HeaderDataModel(build_header_payload()))
    if factory is None:
        return False
    if not hangar_child.attach(logger, [hangar_child.LOBBY_HEADER], _POS_ID, factory, 'Premium time counter'):
        logger.warning('The client has no lobby header to patch; the header counter is disabled')
        return False
    logger.info('Lobby header integration installed (%s)', _MODULE_URL)
    return True


def uninstall(logger):
    hangar_child.uninstall(logger)
