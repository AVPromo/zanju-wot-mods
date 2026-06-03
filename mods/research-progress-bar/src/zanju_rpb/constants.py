"""Stable constants for the research progress bar mod."""
from __future__ import print_function, unicode_literals

from gui.Scaleform.daapi.settings.views import VIEW_ALIAS


MOD_ID = 'zanju.researchprogressbar'
MOD_CONFIG_DIR_NAME = 'research-progress-bar'
MOD_VERSION = '0.1.0'
SCALEFORM_VIEW_ALIAS = 'ResearchProgressBarLobby'
SCALEFORM_FILE_NAME = 'research-progress-bar-lobby.swf'
_VISIBILITY_PROBE_DELAY = 0.25
_VISIBLE_ROUTE_PREFIX = 'Visible route changed to: '
_NAVIGATING_ROUTE_PREFIX = 'Navigating to '

_HANGAR_VIEW_ALIASES = frozenset((VIEW_ALIAS.LOBBY_HANGAR, VIEW_ALIAS.LEGACY_LOBBY_HANGAR))

_TIER_FIELD_MOD_RULES = {
    6: {'max_level': 5, 'xp_per_level': 3500},
    7: {'max_level': 5, 'xp_per_level': 7000},
    8: {'max_level': 6, 'xp_per_level': 11500},
    9: {'max_level': 7, 'xp_per_level': 20000},
    10: {'max_level': 8, 'xp_per_level': 28000},
}

_UNLOCK_MARKER_TYPE_BY_GUI_NAME = {
    'vehicleGun': 'gun',
    'vehicleTurret': 'turret',
    'vehicleEngine': 'engine',
    'vehicleChassis': 'suspension',
    'vehicleRadio': 'radio',
    'vehicle': 'vehicle',
}
