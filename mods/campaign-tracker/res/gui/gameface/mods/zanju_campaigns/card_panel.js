// The campaign hover card, as its own Gameface document.
//
// The card used to be a child of the banner, inside the garage document. That pinned it to the
// garage's window band, so a native window such as the platoon window drew over it whatever
// z-index it carried. It now renders here, in a window the mod owns on a band of its own. See
// card_window.py in mods-common for the Python half and docs/reference/choosing-a-ui-approach.md
// for why this route was taken.
//
// card_host.js runs the window side, which is shared with crucible-tracker: the model, the size
// handshake with Python, and the reveal once Python has placed the window. This module gives it
// what is the campaigns' own: how to draw the card, and how to light the hint lines when only the
// held keys change.

import { applyHints, renderCard } from './card.js';
import { startCardHost } from './card_host.js';
import { log, parseHeldKeys } from './common.js';

// Builds the card for a new banner. A payload for the card on screen changes one field, the
// reveal flag or the held keys, and only the hint lines follow it.
function render(card, payload, sameToken) {
    const keys = parseHeldKeys(payload.heldKeys);
    if (sameToken) {
        applyHints(card, keys, payload.entry);
        return false;
    }
    renderCard(card, payload.entry, payload.labels || {});
    applyHints(card, keys, payload.entry);
    return true;
}

startCardHost({
    nodeId: 'zanju-ct-card',
    shownClass: 'zanju-ct-card-shown',
    hasContent: function (payload) { return Boolean(payload.entry); },
    render: render,
    log: log,
});
