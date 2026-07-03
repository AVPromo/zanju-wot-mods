"""Exact end time in the WoT Plus header-button tooltip.

Hovering the WoT Plus header button opens a "param tooltip": a `ParamTooltipView`
(Python) hosting the Gameface tooltips document, which renders the
`wot_plus_header_widget` template from JSON params. The template is fixed, so the extra
"Ends on" line is appended to the DOM by tooltip_patch.js. That view is the tooltip
document's ROOT (its model is `window.model`, not a subView), which the OpenWG
ModInjectModel injector never scans — so the script is loaded via our shadowed copy of
the document shell (res/gui/gameface/_dist/.../tooltips/tooltips.html) instead.

This module supplies the data: `ParamTooltipModel` backs every param tooltip and its
type is only set after creation, so a ready-made localized line
(`zanjuPtTooltip.wotPlusEndsOn`, computed fresh on every hover) is attached to all of
them; the JS side acts only when the tooltip actually is the WoT Plus header widget.
"""
from __future__ import print_function, unicode_literals

from frameworks.wulf import ViewModel

from ..formatting import end_datetime_text, ends_on_label, server_now

_DATA_PROPERTY = 'zanjuPtTooltip'

_original_initialize = None


class _TooltipDataModel(ViewModel):
    """Pre-formatted strings consumed by tooltip_patch.js."""

    def __init__(self, label, value):
        self._label = label
        self._value = value
        super(_TooltipDataModel, self).__init__(properties=2, commands=0)

    def _initialize(self):
        super(_TooltipDataModel, self)._initialize()
        self._addStringProperty('wotPlusEndsOnLabel', self._label)
        self._addStringProperty('wotPlusEndsOnValue', self._value)


def _wot_plus_ends_on(logger):
    """'<date> <time> UTC+X' end-time value for the current WoT Plus subscription, or ''."""
    try:
        from helpers import dependency
        from skeletons.gui.game_control import IWotPlusController
        expiry = dependency.instance(IWotPlusController).getExpiryTime()
    except Exception:
        logger.exception('Failed to read WoT Plus expiry time')
        return ''
    if not expiry:
        return ''
    expiry = int(expiry)
    if expiry <= server_now():
        return ''
    return end_datetime_text(expiry)


def install(logger):
    """Patch ParamTooltipModel to carry our tooltip data. Returns True when active."""
    global _original_initialize

    if _original_initialize is not None:
        return True

    try:
        from gui.impl.gen.view_models.views.param_tooltip_model import ParamTooltipModel
    except ImportError:
        logger.exception('Param tooltip model not found; WoT Plus tooltip integration disabled')
        return False

    original = ParamTooltipModel._initialize

    def _initialize_with_data(self):
        original(self)
        try:
            data_model = _TooltipDataModel(ends_on_label(), _wot_plus_ends_on(logger))
            self._addViewModelProperty(str(_DATA_PROPERTY), data_model)
        except Exception:
            logger.exception('Failed to attach tooltip data model')

    ParamTooltipModel._initialize = _initialize_with_data
    _original_initialize = original
    logger.info('WoT Plus tooltip integration installed')
    return True


def uninstall(logger):
    global _original_initialize

    if _original_initialize is None:
        return
    try:
        from gui.impl.gen.view_models.views.param_tooltip_model import ParamTooltipModel
        ParamTooltipModel._initialize = _original_initialize
    except Exception:
        logger.exception('Failed to restore ParamTooltipModel._initialize')
    _original_initialize = None
