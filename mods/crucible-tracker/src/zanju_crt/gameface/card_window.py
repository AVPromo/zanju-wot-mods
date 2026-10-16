# -*- coding: utf-8 -*-
"""The hover card of the Crucible banner, in a Wulf window the mod owns.

A near copy of the card window of campaign-tracker, which holds the full reasoning in its
docstring. In short:

* The banner stays injected in the garage document, because only a widget inside that document
  can measure the vehicle name block it hangs beside. The card needs to draw over native windows,
  which nothing inside the garage document can do, so it gets a window of its own on
  `TOP_WINDOW` (10).
* The window exists only while a card is on screen. A loaded window on that band stops the client
  from opening its own queued notification windows, also while it is hidden.
* The window is shown before it is placed, and the card stays transparent until it is. A hidden
  Wulf window runs no frames, so the card cannot measure itself there.
* The Python wrapper outlives the native window, so `is_alive` is asked rather than `is not None`.

See docs/reference/ui-and-scaleform.md#window-layers.
"""
from __future__ import print_function, unicode_literals

import json

# Rebuilt on every hover so a stale measurement can be told from a current one.
_token = 0

_state = {
    'window': None,
    'model': None,
    'view': None,
    'key': '',
    'rect': None,
    'size': None,
    # Whether `_show_window` already had work to do for this window. `_onReady` shows a window
    # built for a hover, so this stays False through the life of most of them.
    'shown': False,
    # The payload as a dictionary, so a re-push for one changed field does not rebuild it.
    'payload': None,
}

# How far below the banner the card hangs, in client pixels at scale 1. The banner's own tail
# occupies the space above this.
_GAP_PX = 6

# Whether the two reasons a build can fail were already reported. Each is reported once: both
# stay true for the rest of the session, and a hover is cheap to repeat.
_reported = set()

# Where the card's layout sits in the client's resource tree, `R`. The entry is in
# res/gui/gen_resources/zanju.crucibletracker.json. The client reads every
# `gui/gen_resources/*.json` at start, the files in mod packages too, so no restart is necessary.
LAYOUT_PATH = ('mods', 'zanju', 'crucibletracker', 'views', 'CrucibleCard')


def _layer():
    """The band to build on. Imported late so this module stays importable under the tests."""
    from frameworks.wulf import WindowLayer
    return WindowLayer.TOP_WINDOW


def build_model_class():
    """Define the model against the live client, so this file imports outside the game.

    A hand-written view model gets no generated setters. `_addStringProperty` registers the
    storage; the setter has to be written by hand against the same property index.
    """
    from frameworks.wulf import ViewModel

    class _CardModel(ViewModel):
        """One JSON payload out to the card, one size report back from it."""

        def __init__(self, payload, on_sized):
            self._payload = payload
            self._on_sized = on_sized
            super(_CardModel, self).__init__(properties=1, commands=1)

        def _initialize(self):
            super(_CardModel, self)._initialize()
            self._addStringProperty('payload', self._payload)
            self.onSized = self._addCommand('onSized')
            self.onSized += self._on_sized

        def setPayload(self, payload):
            self._payload = payload
            self._setString(0, payload)

    return _CardModel


def build_view_class():
    from frameworks.wulf import ViewFlags, ViewSettings
    from gui.impl.pub import ViewImpl

    class _CardView(ViewImpl):

        def __init__(self, layout_id, model):
            self._model = model
            super(_CardView, self).__init__(
                ViewSettings(layoutID=layout_id, flags=ViewFlags.VIEW, model=model))

        @property
        def viewModel(self):
            return self._model

    return _CardView


def build_window_class(layer):
    from frameworks.wulf import WindowFlags
    from gui.impl.pub import WindowImpl

    class _CardWindow(WindowImpl):

        def __init__(self, content, parent):
            super(_CardWindow, self).__init__(
                WindowFlags.WINDOW,
                content=content,
                layer=layer,
                name=str('ZanjuCrucibleCard'),
                parent=parent,
            )

        def _onReady(self):
            # `show(False)` on the window, not on the view: the argument means "do not take
            # focus". The card is never interactive, so it must never take focus from the
            # garage.
            #
            # Shown and not hidden again. This window is built on the hover that wants it, so
            # ready always means wanted. It paints nothing until `_place` reveals the card.
            self.show(False)

    return _CardWindow


def is_alive():
    """Whether the native side of the card window still exists.

    The Python wrapper outlives it. A destroyed window answers `windowStatus` and everything
    else quite happily, and only raises when a call reaches `proxy`, which is None by then.
    """
    window = _state['window']
    if window is None:
        return False
    try:
        if window.proxy is None:
            return False
        from frameworks.wulf import WindowStatus
        return window.windowStatus not in (WindowStatus.DESTROYING, WindowStatus.DESTROYED)
    except Exception:
        return False


def _discard():
    """Forget the window, without reaching into a native side that may already be gone."""
    _state['window'] = None
    _state['view'] = None
    _state['model'] = None
    _state['key'] = ''
    _state['rect'] = None
    _state['size'] = None
    _state['shown'] = False
    _state['payload'] = None


def _ensure_window(logger, payload):
    """Build the card window if it is not standing. False when it cannot be built right now.

    Synchronous throughout, and deliberately so. The resource tree and the lobby's main window
    are both ready long before a player can reach a banner, so waiting for either would buy
    nothing -- and a build that completed after the pointer left would leave a window standing
    with no card in it, which is the fault this module's lifetime exists to avoid.

    The payload is handed to the model at construction rather than pushed afterwards, because
    the view has not bound its properties yet at this point.
    """
    if is_alive():
        return True
    _discard()

    parent = _main_window()
    if parent is None:
        return False
    return _build(logger, parent, payload)


def _main_window():
    """The lobby's main window, or None while it is not loaded.

    Re-resolved on every build: a window reference kept across a lobby teardown names an object
    the client already destroyed.
    """
    from frameworks.wulf import WindowStatus
    from helpers import dependency
    from skeletons.gui.impl import IGuiLoader

    parent = dependency.instance(IGuiLoader).windowsManager.getMainWindow()
    if parent is None or parent.proxy is None or parent.windowStatus != WindowStatus.LOADED:
        return None
    return parent


def _report_once(logger, key, message):
    if key in _reported:
        return
    _reported.add(key)
    logger.warning(message)


def _layout_id():
    """The card's layout ID, or None when the client's resource tree has no such entry."""
    from gui.impl.gen import R

    try:
        node = R
        for name in LAYOUT_PATH:
            node = getattr(node, name)
        layout_id = int(node())
    except Exception:
        return None
    return layout_id if layout_id >= 0 else None


def _build(logger, parent, payload):
    layout_id = _layout_id()
    if layout_id is None:
        _report_once(
            logger, 'resources',
            'The client has no resource R.{0}; the hover card is disabled. The client reads it '
            'from gui/gen_resources/zanju.crucibletracker.json in this mod at '
            'start.'.format('.'.join(LAYOUT_PATH)))
        return False

    model = build_model_class()(json.dumps(payload), lambda *args: _on_sized(logger, *args))
    view = build_view_class()(layout_id, model)
    window = build_window_class(_layer())(view, parent)
    _state['model'] = model
    _state['view'] = view
    _state['window'] = window
    _state['payload'] = payload
    window.load()
    logger.debug('Hover card window built on layer %s', _layer())
    return is_alive()


def _push(payload, logger):
    """Send the payload the card renders from. Kept in one place: three callers change one
    field each, and each needs the rest of it left alone."""
    _state['payload'] = payload
    model = _state['model']
    if model is None:
        return
    try:
        with model.transaction() as live:
            live.setPayload(json.dumps(payload))
    except Exception:
        logger.exception('Failed to push the hover card payload')


def show(key, rect, snapshot, logger):
    """Point the card at the banner. `rect` is (x, y, w, h) in the garage document's pixels."""
    global _token
    _token += 1
    payload = {
        'snapshot': snapshot,
        'token': str(_token),
        # Painted only once the window has been moved. Until then the window is on screen and
        # empty, which is what lets the card's own frames run at all.
        'reveal': False,
        'lang': _client_language(),
    }

    existed = is_alive()
    if not _ensure_window(logger, payload):
        return

    # Set after the build, never before it: building forgets the window that was there, and
    # forgetting a window clears the banner and rectangle that belong with it.
    _state['key'] = key
    _state['rect'] = rect
    # The size belongs to the card about to be drawn, not to the one that just left. Cleared so
    # a stale measurement cannot place the new card.
    _state['size'] = None

    if existed:
        # A window carried over from the banner the pointer just left. A window built above
        # already holds this payload, so pushing it again would be a wasted round trip.
        _push(payload, logger)
    _show_window(logger)


def _client_language():
    """The language code that the client's own documents put on `<html lang>`, or ''.

    The card needs it to select its font. PFDINMax has no glyphs for Chinese, Japanese, Korean,
    Thai or Vietnamese. card.css switches to Warhelios for those languages with `html[lang=...]`.
    Each client document sets that attribute from `R.strings.settings.LANGUAGE_CODE()` when it
    starts, in code that a mod's own document does not run. `getClientLanguage` reads the same
    string. Without it, the card on the Chinese client showed only digits and Latin letters.
    """
    try:
        from helpers import getClientLanguage
        return getClientLanguage() or ''
    except Exception:
        return ''


def _show_window(logger):
    """Put the window on screen so the card inside it starts receiving frames.

    A window still loading is left alone: `_onReady` shows it the moment it can, and reaching
    through to a native side that is not there yet would report a fault on every hover. So this
    only has work to do for a window carried over from the banner the pointer just left.

    Nothing is painted either way. The card stays transparent until `_place` reveals it.
    """
    if _state['shown'] or not is_alive():
        return
    from frameworks.wulf import WindowStatus
    try:
        window = _state['window']
        if window.windowStatus != WindowStatus.LOADED:
            return
        window.show(False)
        _state['shown'] = True
    except Exception:
        logger.exception('Failed to show the hover card')


def hide(logger):
    """Take the card off screen by destroying its window. Cheap to call with nothing showing.

    Destroyed rather than hidden. A hidden window is still a loaded one, and a loaded window on
    this band stops the client opening its own queued notification windows -- see the module
    docstring for what that cost a player. The next hover builds a fresh one.
    """
    window = _state['window'] if is_alive() else None
    _discard()
    if window is None:
        return
    try:
        window.destroy()
    except Exception:
        logger.exception('Failed to destroy the hover card window')


def update(snapshot, logger):
    """Re-push the card on screen with a new snapshot, so it follows a change under the pointer."""
    payload = _state['payload']
    if not _state['key'] or not payload or not is_alive():
        return
    payload = dict(payload)
    payload['snapshot'] = snapshot
    _push(payload, logger)


def _on_sized(logger, *args):
    """The card measured itself. Place the window and only then show it."""
    arg = args[0] if args else None
    token = _read(arg, 'token')
    if token != str(_token):
        # A measurement for a card the pointer has already left.
        return
    width = _read(arg, 'width')
    height = _read(arg, 'height')
    if not width or not height:
        return
    _state['size'] = (int(width), int(height))
    _place(logger)


def _place(logger):
    rect = _state['rect']
    size = _state['size']
    if rect is None or size is None or not is_alive():
        return
    window = _state['window']
    try:
        parent = window.parent
        screen_w, screen_h = parent.size if parent is not None else (0, 0)
        if screen_w <= 0:
            return
        width, height = size
        banner_x, banner_y, banner_w, banner_h = rect
        # Centred on the banner, hanging below it, and clamped so a card near an edge stays
        # wholly on screen rather than being cut.
        left = banner_x + (banner_w // 2) - (width // 2)
        top = banner_y + banner_h + _GAP_PX
        left = max(0, min(screen_w - width, left))
        top = max(0, min(screen_h - height, top))
        window.move(int(left), int(top))
    except Exception:
        logger.exception('Failed to place the hover card')
        return

    # Placed, so it is safe to paint. One more push rather than a flag the card could have
    # guessed: the card cannot know when the window moved, and revealing itself a frame early
    # shows it at the position the previous card had.
    payload = _state['payload']
    if payload and not payload.get('reveal'):
        payload = dict(payload)
        payload['reveal'] = True
        _push(payload, logger)


def _read(arg, key):
    """Read one key from the single map argument a wulf command carries."""
    if isinstance(arg, dict):
        return arg.get(key)
    getter = getattr(arg, 'get', None)
    if callable(getter):
        try:
            return arg.get(key)
        except Exception:
            return None
    return None


def uninstall(logger):
    """Destroy the window on teardown. The same work a hover-out does, under another name."""
    hide(logger)
