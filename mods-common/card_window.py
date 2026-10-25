# -*- coding: utf-8 -*-
"""A hover card in a Wulf window that the mod owns. campaign-tracker measured each rule here first.

A banner stays injected in the garage document, because only a widget inside that document can
measure the element it anchors to. The card does not need an anchor -- it needs to draw over
native windows, which nothing inside the garage document can do: an injected widget inherits the
host document's window band (`SUB_VIEW`, 5), and every native window is above that.

So the card gets a window of its own:

    _CardModel  ->  _CardView(ViewImpl)  ->  _CardWindow(WindowImpl, layer=...)  ->  main window

Positioning crosses Python. The banner script reports which banner the pointer is on and where
that banner sits, this module places the window under it, and the card's own script (card_host.js)
reports back how big it turned out so the placement can use the real size. That round trip was
measured at about 2 ms, which is why the seam is affordable.

The window is shown before it is placed, and the card inside it stays transparent until it is.
That ordering is forced: `requestAnimationFrame` does not run in a hidden Wulf window, and the
card cannot measure itself without a frame. Waiting for a size before showing the window
deadlocks -- eleven hovers produced no measurement at all until an unrelated route change
happened to render the view. So the window is shown first, at whatever size and position it
last had, with nothing painted in it, and the card is revealed once Python has moved it.

Band choice, from measurements on 2.3.1.3:

* `WINDOW` (7) is shared with the platoon window and ordered by activation, so a card there is
  covered the moment the player clicks the platoon window. That is the bug this module exists to
  fix, so 7 is not an option.
* `TOP_WINDOW` (10) draws over the platoon window at all times. It is also where `lobbyMenu`,
  `settingsWindow` and the client's dialogs live, so the card ties with those on activation --
  acceptable for a card that is only up while the pointer rests on a banner.
* `OVERLAY` (11) is above the lobby menu. The upstream guide reports that a panel there stops
  the second Escape press from closing that menu, so it is deliberately not used.

The window exists only while a card is on screen. It is built when the pointer enters a banner
and destroyed when it leaves, rather than built once and hidden between hovers.

That is not a tidiness choice, it is the whole reason this lifetime is written down. The client
refuses to open any queued notification window while another window on `FULLSCREEN_WINDOW`,
`TOP_WINDOW` or `OVERLAY` is loaded -- see `__overlappingWindowsPredicate` in
`gui/impl/pub/notification_window_controller.py`. Hiding does not help: `Window.hide` changes the
showing status and leaves `windowStatus` at `LOADED`, which is what that predicate reads. A card
window kept for the garage session therefore held every reward and event window back, and the
player got a "you missed events" notice whose button did nothing. Reported on campaign-tracker
1.1.1 and fixed by destroying the window instead. Nothing here may go back to keeping it.

Building it is therefore on the hover path, and everything on that path is synchronous. A build
that finished later would put a window on screen after the pointer had gone, which is the fault
above with extra steps.

The Python object survives the native window: it keeps answering attribute access and raises only
when a call reaches through to `proxy`. So a stored reference is not evidence that a window
exists, and `is_alive` is asked rather than `is not None`. Without that the card worked until the
first lobby rebuild and then failed for the rest of the session, once per hover, with
`AttributeError: 'NoneType' object has no attribute 'show'`.

The module also holds the lookups that every window of a mod needs: the layout ID in `R`, the
main window as the parent, and the language code for the fonts.

Every client import stays inside a function, so this module is importable outside the game.
See docs/reference/ui-and-scaleform.md#window-layers.
"""
from __future__ import absolute_import, print_function, unicode_literals

import json

# How far below the banner the card hangs, in client pixels at scale 1. The banner's own tail
# occupies the space above this.
_GAP_PX = 6


def layout_id(path):
    """The layout ID at `path` in the client's resource tree `R`, or None when there is no such
    entry. A mod declares its layouts in res/gui/gen_resources/<mod id>.json, and the client reads
    every such file at start, the files in mod packages too."""
    from gui.impl.gen import R
    try:
        node = R
        for name in path:
            node = getattr(node, name)
        value = int(node())
    except Exception:
        return None
    return value if value >= 0 else None


def main_window():
    """The lobby's or the battle's main window, or None while it is not loaded.

    Asked again for every build: a window reference kept across a teardown names an object that
    the client already destroyed.
    """
    from frameworks.wulf import WindowStatus
    from helpers import dependency
    from skeletons.gui.impl import IGuiLoader

    parent = dependency.instance(IGuiLoader).windowsManager.getMainWindow()
    if parent is None or parent.proxy is None or parent.windowStatus != WindowStatus.LOADED:
        return None
    return parent


def client_language():
    """The language code that the client's own documents put on `<html lang>`, or ''.

    A card needs it to select its font. PFDINMax has no glyphs for Chinese, Japanese, Korean,
    Thai or Vietnamese, and the card style sheets switch to Warhelios for those languages with
    `html[lang=...]`. Each client document sets that attribute from
    `R.strings.settings.LANGUAGE_CODE()` when it starts, in code that a mod's own document does not
    run. `getClientLanguage` reads the same string. Without it, the card on the Chinese client
    showed only digits and Latin letters.
    """
    try:
        from helpers import getClientLanguage
        return getClientLanguage() or ''
    except Exception:
        return ''


def read_arg(arg, key):
    """Read one key from the single map argument a Wulf command carries."""
    if isinstance(arg, dict):
        return arg.get(key)
    getter = getattr(arg, 'get', None)
    if callable(getter):
        try:
            return getter(key)
        except Exception:
            return None
    return None


def _model_class():
    """Define the model against the live client.

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


def _view_class():
    from frameworks.wulf import ViewFlags, ViewSettings
    from gui.impl.pub import ViewImpl

    class _CardView(ViewImpl):

        def __init__(self, layout, model):
            self._model = model
            super(_CardView, self).__init__(ViewSettings(layoutID=layout, flags=ViewFlags.VIEW, model=model))

        @property
        def viewModel(self):
            return self._model

    return _CardView


def _window_class(name):
    from frameworks.wulf import WindowFlags, WindowLayer
    from gui.impl.pub import WindowImpl

    class _CardWindow(WindowImpl):

        def __init__(self, content, parent):
            super(_CardWindow, self).__init__(
                WindowFlags.WINDOW, content=content, layer=WindowLayer.TOP_WINDOW, name=str(name), parent=parent)

        def _onReady(self):
            # `show(False)` on the window, not on the view: the argument means "do not take
            # focus". The card is never interactive, so it must never take focus from the garage.
            #
            # Shown and not hidden again. This window is built on the hover that wants it, so
            # ready always means wanted. It paints nothing until `_place` reveals the card.
            self.show(False)

    return _CardWindow


class CardWindow(object):
    """The hover card of one mod.

    `layout_path` is the path of the card's layout in `R`, `window_name` names the window, and
    `resource_file` names the gen_resources file of the mod for the log line that a missing
    layout writes.
    """

    def __init__(self, layout_path, window_name, resource_file):
        self.layout_path = tuple(layout_path)
        self.window_name = window_name
        self.resource_file = resource_file
        # Bumped on every hover, so a stale measurement can be told from a current one.
        self._token = 0
        # The reasons a build can fail that were already reported. Each is reported once: both
        # stay true for the rest of the session, and a hover is cheap to repeat.
        self._reported = set()
        self._discard()

    def _discard(self):
        """Forget the window, without reaching into a native side that may already be gone."""
        self._window = None
        self._model = None
        self._view = None
        # Which banner the card points at, and the rectangle of that banner.
        self.key = ''
        self._rect = None
        self._size = None
        # Whether `_show_window` already had work to do for this window. `_onReady` shows a window
        # built for a hover, so this stays False through the life of most of them.
        self._shown = False
        # The payload as a dictionary, so a re-push for one changed field does not rebuild it.
        self._payload = None

    def is_alive(self):
        """Whether the native side of the card window still exists.

        The Python wrapper outlives it. A destroyed window answers `windowStatus` and everything
        else quite happily, and only raises when a call reaches `proxy`, which is None by then.
        """
        window = self._window
        if window is None:
            return False
        try:
            if window.proxy is None:
                return False
            from frameworks.wulf import WindowStatus
            return window.windowStatus not in (WindowStatus.DESTROYING, WindowStatus.DESTROYED)
        except Exception:
            return False

    def show(self, key, rect, content, logger):
        """Point the card at one banner. `rect` is (x, y, w, h) in the garage document's pixels,
        and `content` holds the fields of the payload that the card of the mod draws."""
        self._token += 1
        payload = dict(content)
        payload.update({
            'token': str(self._token),
            # Painted only once the window has been moved. Until then the window is on screen and
            # empty, which is what lets the card's own frames run at all.
            'reveal': False,
            'lang': client_language(),
        })

        existed = self.is_alive()
        if not self._ensure_window(logger, payload):
            return

        # Set after the build, never before it: building forgets the window that was there, and
        # forgetting a window clears the banner and the rectangle that belong with it.
        self.key = key
        self._rect = rect
        # The size belongs to the card about to be drawn, not to the one that just left. Cleared so
        # a stale measurement cannot place the new card.
        self._size = None

        if existed:
            # A window carried over from the banner the pointer just left. A window built above
            # already holds this payload, so pushing it again would be a wasted round trip.
            self._push(payload, logger)
        self._show_window(logger)

    def update(self, changes, logger):
        """Re-push the card on screen with some fields changed, so it follows a change while the
        pointer stays on the banner."""
        payload = self._payload
        if not self.key or not payload or not self.is_alive():
            return
        payload = dict(payload)
        payload.update(changes)
        self._push(payload, logger)

    def hide(self, logger):
        """Take the card off screen by destroying its window. Cheap to call with nothing showing.

        Destroyed rather than hidden. A hidden window is still a loaded one, and a loaded window on
        this band stops the client opening its own queued notification windows -- see the module
        docstring for what that cost a player. The next hover builds a fresh one.
        """
        window = self._window if self.is_alive() else None
        self._discard()
        if window is None:
            return
        try:
            window.destroy()
        except Exception:
            logger.exception('Failed to destroy the hover card window')

    def uninstall(self, logger):
        """Destroy the window on teardown. The same work a hover-out does, under another name."""
        self.hide(logger)

    def _ensure_window(self, logger, payload):
        """Build the card window if it is not standing. False when it cannot be built right now.

        Synchronous throughout, and deliberately so. The resource tree and the lobby's main window
        are both ready long before a player can reach a banner, so waiting for either would buy
        nothing -- and a build that completed after the pointer left would leave a window standing
        with no card in it, which is the fault this lifetime exists to avoid.

        The payload is handed to the model at construction rather than pushed afterwards, because
        the view has not bound its properties yet at this point.
        """
        if self.is_alive():
            return True
        self._discard()
        parent = main_window()
        if parent is None:
            return False
        layout = layout_id(self.layout_path)
        if layout is None:
            self._report_once(
                logger, 'resources',
                'The client has no resource R.{0}; the hover card is disabled. The client reads it '
                'from gui/gen_resources/{1} in this mod at start.'.format(
                    '.'.join(self.layout_path), self.resource_file))
            return False
        model = _model_class()(json.dumps(payload), lambda *args: self._on_sized(logger, *args))
        view = _view_class()(layout, model)
        window = _window_class(self.window_name)(view, parent)
        self._model = model
        self._view = view
        self._window = window
        self._payload = payload
        window.load()
        return self.is_alive()

    def _report_once(self, logger, key, message):
        if key in self._reported:
            return
        self._reported.add(key)
        logger.warning(message)

    def _push(self, payload, logger):
        """Send the payload the card renders from. Kept in one place: several callers change one
        field each, and each needs the rest of it left alone."""
        self._payload = payload
        model = self._model
        if model is None:
            return
        try:
            with model.transaction() as live:
                live.setPayload(json.dumps(payload))
        except Exception:
            logger.exception('Failed to push the hover card payload')

    def _show_window(self, logger):
        """Put the window on screen so the card inside it starts receiving frames.

        A window still loading is left alone: `_onReady` shows it the moment it can, and reaching
        through to a native side that is not there yet would report a fault on every hover. So this
        only has work to do for a window carried over from the banner the pointer just left.

        Nothing is painted either way. The card stays transparent until `_place` reveals it.
        """
        if self._shown or not self.is_alive():
            return
        from frameworks.wulf import WindowStatus
        try:
            window = self._window
            if window.windowStatus != WindowStatus.LOADED:
                return
            window.show(False)
            self._shown = True
        except Exception:
            logger.exception('Failed to show the hover card')

    def _on_sized(self, logger, *args):
        """The card measured itself. Place the window and only then show it."""
        # A command handler runs inside the client's own dispatch, so nothing may leave it.
        try:
            arg = args[0] if args else None
            if read_arg(arg, 'token') != str(self._token):
                # A measurement for a card the pointer has already left.
                return
            width = read_arg(arg, 'width')
            height = read_arg(arg, 'height')
            if not width or not height:
                return
            self._size = (int(width), int(height))
            self._place(logger)
        except Exception:
            logger.exception('Failed to take the size of the hover card')

    def _place(self, logger):
        rect = self._rect
        size = self._size
        if rect is None or size is None or not self.is_alive():
            return
        window = self._window
        try:
            parent = window.parent
            screen_w, screen_h = parent.size if parent is not None else (0, 0)
            if screen_w <= 0:
                return
            left, top = place_under(rect, size, (screen_w, screen_h))
            window.move(left, top)
        except Exception:
            logger.exception('Failed to place the hover card')
            return

        # Placed, so it is safe to paint. One more push rather than a flag the card could have
        # guessed: the card cannot know when the window moved, and revealing itself a frame early
        # shows it at the position the previous card had.
        payload = self._payload
        if payload and not payload.get('reveal'):
            payload = dict(payload)
            payload['reveal'] = True
            self._push(payload, logger)


def place_under(rect, size, screen):
    """The top left corner of a card of `size`, centred under the banner at `rect` and clamped so
    a card near an edge stays wholly on screen rather than being cut."""
    banner_x, banner_y, banner_w, banner_h = rect
    width, height = size
    screen_w, screen_h = screen
    left = banner_x + (banner_w // 2) - (width // 2)
    top = banner_y + banner_h + _GAP_PX
    left = max(0, min(screen_w - width, left))
    top = max(0, min(screen_h - height, top))
    return int(left), int(top)
