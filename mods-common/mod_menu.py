# -*- coding: utf-8 -*-
"""In-game settings through Aslain's Mod Menu, for a mod whose config file is the source of truth.

The mod keeps its settings in its own `config.json` in AppData. The menu is a mirror of it:

- `setModTemplate` gets a template built from the factory defaults, so the per-mod Reset of the
  menu restores the real defaults.
- `setModDefaults` declares the same defaults where the menu has it (Mod Menu 1.7.0 and later).
  From 1.7.0 the menu no longer derives the defaults again when only a default changes.
- `updateModSettings` then pushes the values in the config. The menu calls the change callback
  for that push too, so a guard drops that echo.

Never set `settingsVersion`. See docs/reference/in-game-settings.md for both points.

The menu is optional. Without it the mod works from its config file alone.

Every client import stays inside a function, so this module is importable outside the game.
"""
from __future__ import absolute_import, print_function, unicode_literals

try:
    _TEXT_TYPE = unicode  # noqa: F821
except NameError:
    _TEXT_TYPE = str

try:
    _STRING_TYPES = (basestring,)  # noqa: F821
except NameError:
    _STRING_TYPES = (str,)

# The linkages whose values this mod is pushing right now. A change callback for one of them is
# the echo of the push, not a change by the player.
_syncing = set()


def register(mod_id, template, defaults, values, on_change, logger):
    """Show the mod in the menu. Returns True when the menu took the template.

    `on_change(settings)` gets the menu's values as a plain dict whenever the player changes one.
    """
    api = _api()
    if api is None:
        logger.info('Mod Menu (gui.aslainMenu) not found; the settings are in config.json only')
        return False
    linkage = native_key(mod_id)

    def _on_settings_changed(changed_linkage, new_settings):
        if native_key(changed_linkage) != linkage or linkage in _syncing:
            return
        if not isinstance(new_settings, dict):
            return
        try:
            on_change(dict(new_settings))
        except Exception:
            logger.exception('Failed to apply a change from Mod Menu')

    try:
        api.setModTemplate(linkage, native(template), _on_settings_changed)
    except Exception:
        logger.exception('Failed to register with Mod Menu')
        return False
    declare = getattr(api, 'setModDefaults', None)
    if callable(declare):
        try:
            declare(linkage, native(defaults))
        except Exception:
            # The Reset target is a convenience. It must never stop the menu from working.
            logger.exception('Failed to declare the defaults to Mod Menu')
    push(mod_id, values, logger)
    logger.info('Registered with Mod Menu')
    return True


def push(mod_id, values, logger):
    """Show these values in the menu, without hearing them back as a change."""
    api = _api()
    if api is None:
        return
    linkage = native_key(mod_id)
    _syncing.add(linkage)
    try:
        api.updateModSettings(linkage, native(values))
    except Exception:
        logger.exception('Failed to push the settings to Mod Menu')
    finally:
        _syncing.discard(linkage)


def _api():
    try:
        from gui.aslainMenu import g_modsSettingsApi
        return g_modsSettingsApi
    except Exception:
        return None


def native(value):
    """The value with each text as UTF-8 bytes on Python 2, which is what the menu stores."""
    if isinstance(value, _TEXT_TYPE) and _TEXT_TYPE is not str:
        return value.encode('utf-8')
    if isinstance(value, list):
        return [native(item) for item in value]
    if isinstance(value, tuple):
        return tuple(native(item) for item in value)
    if isinstance(value, dict):
        return dict((native(key), native(item)) for key, item in value.items())
    return value


def native_key(value):
    converted = native(value)
    if isinstance(converted, _STRING_TYPES):
        return converted
    return '{0}'.format(converted)
