"""
mod_modname.py

Minimal WoT mod skeleton.

Entry points called by the WoT client:
  init()  - called once on client startup (before hangar loads)
  fini()  - called on client shutdown

All top-level code runs at import time; keep it minimal and guard everything.
"""

import BigWorld
import logging

# Use a namespaced logger so your lines are identifiable in python.log
_logger = logging.getLogger('com.yourname.modname')


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
MOD_ID = 'com.yourname.modname'
MOD_VERSION = '0.1.0.0'

# Default config values. Override from config file in _load_config().
_config = {
    'enabled': True,
    'logLevel': 'INFO',
}


def _load_config():
    """Read config from mods/configs/<mod-name>/config.json.
    Falls back to defaults if file is missing or malformed.
    """
    import json
    import os

    config_path = os.path.join(
        BigWorld.wg_getPreferencesFilePath(),  # resolves to game user dir
        '..', '..', 'mods', 'configs', 'modname', 'config.json'
    )
    config_path = os.path.normpath(config_path)

    if not os.path.isfile(config_path):
        _logger.info('Config not found at %s, using defaults', config_path)
        return

    try:
        with open(config_path, 'r') as fh:
            data = json.load(fh)
        _config.update(data)
        _logger.info('Config loaded from %s', config_path)
    except Exception:
        _logger.exception('Failed to read config, using defaults')


# ---------------------------------------------------------------------------
# Hooks
# ---------------------------------------------------------------------------
# Add your BigWorld.callback / Event subscriptions below.
# Keep every hook wrapped in a try/except so a crash here
# does not take down other mods.

def _on_hangar_loaded():
    """Example: called after the hangar is ready."""
    try:
        if not _config.get('enabled'):
            return
        _logger.info('Hangar loaded hook fired')
        # TODO: your hangar logic here
    except Exception:
        _logger.exception('Error in _on_hangar_loaded')


# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------

def init():
    """Called by WoT client at startup. Register hooks here."""
    _logger.info('%s v%s initializing', MOD_ID, MOD_VERSION)
    try:
        _load_config()
        # Subscribe to events after config is loaded.
        # Example: g_appLoader events, Avatar.onEnterWorld, etc.
        # from gui.app_loader import g_appLoader
        # g_appLoader.onGUISpaceEntered += _on_space_entered
        _logger.info('%s initialized successfully', MOD_ID)
    except Exception:
        _logger.exception('%s failed to initialize', MOD_ID)


def fini():
    """Called by WoT client on shutdown. Clean up subscriptions here."""
    try:
        # Unsubscribe from any events registered in init().
        pass
    except Exception:
        _logger.exception('%s error during fini', MOD_ID)
