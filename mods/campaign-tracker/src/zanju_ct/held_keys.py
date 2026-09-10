# -*- coding: utf-8 -*-
"""Which modifier keys the player is holding, tracked on the Python side.

The hover card lights the line for the keys held right now, so it has to hear about a key going
down while the pointer sits still over a banner. Asking the widget document for that does not
work: an injected Gameface sub-view is not given keyboard events until the player has clicked
into the document, so the highlight stayed dead until the garage had been dragged, and reading
the flags off mouse events instead only answered once the pointer moved.

`gui.InputHandler.g_instance` is the client's own answer, and it works in the garage. The
game's tooltip manager subscribes to exactly these two events to do exactly this job -- it is
how "hold Alt for more detail" knows the key went down. Following it means the mod hears about a
key the moment the game does, with no polling and no focus to win first.

Two properties of that bus set the rules for this module. `onKeyDown` and `onKeyUp` are class
attributes of `_InputHandler`, built once at import and never cleared, so a subscription lasts
the whole session and fires in battle as well as in the garage. And `game.handleKeyEvent` calls
the dispatch with no guard, ahead of `GUI.handleKeyEvent`, the messenger and the avatar's own
input handler. `Event` raises the fault of a delegate again after it logs it, so an exception
that escapes this module takes Escape, Tab, the radial menu and every battle command with it for
that key. Nothing here may raise, and the consumer decides what is worth doing -- see
`widgets_inject._apply_held_keys`, which does nothing while the widgets are off screen.

A click is still read from the click event itself, which was always reliable. This is only for
what the card says before the click.

Every client import stays inside a function, so this module is importable outside the game.
"""
from __future__ import absolute_import, print_function, unicode_literals

# Sent to the widgets as one string, because a wulf model property is cheaper than two and the
# widget only ever asks which of these four states it is in.
SHIFT = 'shift'
CTRL = 'ctrl'

_callback = None
_installed = False
_shift = False
_ctrl = False
# Kept from `install`, because `_on_key` is handed an event and nothing else.
_logger = None
# Whether the callback already failed once. Its fault is reported one time and no more.
_reported_failure = False


def text():
    """The held modifiers, as the widgets read them: '', 'shift', 'ctrl' or 'shift ctrl'."""
    held = []
    if _shift:
        held.append(SHIFT)
    if _ctrl:
        held.append(CTRL)
    return ' '.join(held)


def install(logger, on_change):
    """Subscribe to the client's key events, replacing any earlier subscription.

    Safe to call repeatedly. `Event` refuses a handler it already holds, so re-subscribing
    costs nothing -- but unlike the lobby's own events, this one belongs to a module-level
    singleton that outlives every lobby teardown, so the subscription is made once and kept.
    """
    global _callback, _installed, _logger, _reported_failure
    _callback = on_change
    _logger = logger
    _reported_failure = False
    if _installed:
        return True

    try:
        from gui import InputHandler
        InputHandler.g_instance.onKeyDown += _on_key
        InputHandler.g_instance.onKeyUp += _on_key
        _installed = True
        logger.info('Subscribed to modifier keys')
        return True
    except Exception:
        # The banners still work: the click reads its own event. Only the highlight is lost.
        logger.exception('Failed to subscribe to key events; the card cannot light a line')
        return False


def uninstall(logger):
    global _callback, _installed, _shift, _ctrl
    _callback = None
    _shift = False
    _ctrl = False
    if not _installed:
        return
    _installed = False
    try:
        from gui import InputHandler
        InputHandler.g_instance.onKeyDown -= _on_key
        InputHandler.g_instance.onKeyUp -= _on_key
    except Exception:
        logger.exception('Failed to unsubscribe from key events')


def _on_key(event):
    """One key went down or up. Only the four modifier keys change anything here."""
    try:
        held = _read_key(event)
    except Exception:
        # No logging: this runs on every key the player presses anywhere in the client, in
        # battle as well as in the garage, so a broken read would fill the log.
        return
    if held is None:
        return

    global _shift, _ctrl
    name, down = held
    if name == SHIFT:
        if _shift == down:
            return
        _shift = down
    else:
        if _ctrl == down:
            return
        _ctrl = down

    if _callback is None:
        return
    try:
        _callback()
    except Exception:
        _report_failure()


def _report_failure():
    """Report the first fault the callback raises, then stay quiet.

    The guard around the call is the point, not this line. See the module docstring for what an
    exception leaving `_on_key` costs the player. Only the first fault reaches the log, because
    a fault that repeats writes on every modifier key for the rest of the session.
    """
    global _reported_failure
    if _reported_failure or _logger is None:
        return
    _reported_failure = True
    try:
        _logger.exception('The modifier key callback failed; the card cannot light a line')
    except Exception:
        # Even the report has to be unable to raise into the client's key dispatch.
        pass


def _read_key(event):
    """`(SHIFT or CTRL, is it down)` for a modifier key, or None for any other key.

    Both sides of the keyboard map to the same modifier, the way every other consumer of these
    events treats them.
    """
    from Keys import KEY_LCONTROL, KEY_LSHIFT, KEY_RCONTROL, KEY_RSHIFT
    key = event.key
    if key in (KEY_LSHIFT, KEY_RSHIFT):
        return (SHIFT, bool(event.isKeyDown()))
    if key in (KEY_LCONTROL, KEY_RCONTROL):
        return (CTRL, bool(event.isKeyDown()))
    return None
