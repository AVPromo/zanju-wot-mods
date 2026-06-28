"""Stable constants for the premium time mod."""
from __future__ import print_function, unicode_literals

from gui.Scaleform.daapi.settings.views import VIEW_ALIAS

# MOD_ID / MOD_NAME come from meta.xml via the build-generated _mod_meta module
# (see tools/commands/build.py). meta.xml is the single authored source of these values.
from ._mod_meta import MOD_ID, MOD_NAME  # noqa: F401

MOD_CONFIG_DIR_NAME = 'premium-time'
SCALEFORM_VIEW_ALIAS = 'PremiumTimeLobby'
SCALEFORM_FILE_NAME = 'premium-time-lobby.swf'

# Hangar containers in which the account-wide widget should stay visible. Any other
# top sub-view (tech tree, store, settings, etc.) hides it.
_HANGAR_VIEW_ALIASES = frozenset((VIEW_ALIAS.LOBBY_HANGAR, VIEW_ALIAS.LEGACY_LOBBY_HANGAR))

# Widget refresh cadence (seconds). Remaining time is shown in days/hours, so a slow
# tick is plenty to keep the countdown current without churn.
WIDGET_REFRESH_INTERVAL = 60.0
