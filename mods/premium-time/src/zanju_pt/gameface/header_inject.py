"""Live remaining-time counters on the lobby header's subscription buttons.

The lobby top bar is a Gameface (HTML/JS) view: the WoT Plus and Premium Account button
labels are rendered client-side by the header's JS bundle from localization strings and
`expiryTime` on `UserAccountModel.subscriptions`, so neither the Python presenter nor the
view model exposes the text itself. To change those labels we inject JS into the header
document via `net.openwg.gameface`: its bootstrap runs in every Gameface view and loads
the modules listed in a `ModInjectModel` attached to any sub-view's view model.

We attach that marker by wrapping `UserAccountModel._initialize` (the model behind the
header's account panel, which contains both subscription buttons), together with a small
data model (`zanjuPtHeader`) carrying what the JS side cannot know by itself: localized
unit labels and the client-to-server clock offset. The injected JS (header_patch.js)
computes and renders the countdowns from the game's own `expiryTime`. If the OpenWG
library is not installed the mod keeps working without the header counters.
"""
from __future__ import print_function, unicode_literals

from frameworks.wulf import ViewModel

from ..formatting import server_time_offset
from ..localization import get_text as _loc

_MODULE_URL = 'coui://gui/gameface/mods/zanju_premiumtime/header_patch.js'
_INJECT_NAME = 'zanju_pt_header'
_DATA_PROPERTY = 'zanjuPtHeader'

_original_initialize = None


class _HeaderDataModel(ViewModel):
    """Formatting data consumed by header_patch.js."""

    def __init__(self, time_offset, units):
        self._initial = (time_offset, units)
        super(_HeaderDataModel, self).__init__(properties=4, commands=0)

    def _initialize(self):
        super(_HeaderDataModel, self)._initialize()
        time_offset, units = self._initial
        day_unit, hour_unit, minute_unit = units
        self._addNumberProperty('timeOffset', time_offset)
        self._addStringProperty('dayUnit', day_unit)
        self._addStringProperty('hourUnit', hour_unit)
        self._addStringProperty('minuteUnit', minute_unit)


def _build_data_model():
    # wulf number properties only accept ints; sub-second offset precision is irrelevant.
    return _HeaderDataModel(
        int(round(server_time_offset())),
        (
            _loc('UNIT_DAY_SHORT'),
            _loc('UNIT_HOUR_SHORT'),
            _loc('UNIT_MINUTE_SHORT'),
        ),
    )


def install(logger):
    """Patch UserAccountModel to carry our inject marker and data. Returns True when active."""
    global _original_initialize

    if _original_initialize is not None:
        return True

    try:
        from openwg_gameface import gf_mod_inject
    except ImportError:
        logger.info(
            'net.openwg.gameface not found; lobby header integration disabled '
            '(install the OpenWG Gameface library to enable it)'
        )
        return False

    try:
        from gui.impl.gen.view_models.views.lobby.page.header.user_account_model import (
            UserAccountModel,
        )
    except ImportError:
        logger.exception('Lobby header model not found; header integration disabled')
        return False

    original = UserAccountModel._initialize

    def _initialize_with_inject(self):
        original(self)
        try:
            gf_mod_inject(self, str(_INJECT_NAME), modules=[str(_MODULE_URL)])
            self._addViewModelProperty(str(_DATA_PROPERTY), _build_data_model())
        except Exception:
            logger.exception('Failed to attach header inject model')

    UserAccountModel._initialize = _initialize_with_inject
    _original_initialize = original
    logger.info('Lobby header integration installed (%s)', _MODULE_URL)
    return True


def uninstall(logger):
    global _original_initialize

    if _original_initialize is None:
        return
    try:
        from gui.impl.gen.view_models.views.lobby.page.header.user_account_model import (
            UserAccountModel,
        )
        UserAccountModel._initialize = _original_initialize
    except Exception:
        logger.exception('Failed to restore UserAccountModel._initialize')
    _original_initialize = None
