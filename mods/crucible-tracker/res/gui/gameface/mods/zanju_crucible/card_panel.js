// The Crucible hover card, as its own Gameface document, in a window the mod owns.
//
// card_host.js runs the window side, which is shared with campaign-tracker: the model, the size
// handshake with Python, and the reveal once Python has placed the window. This module gives it
// what is the Crucible's own: how to draw the card, how to fit the series list, and the
// countdowns that are rewritten once a second. See card_window.py in mods-common.

import { fitColumns, refreshTimes, renderCard, resetColumns } from './card.js';
import { startCardHost } from './card_host.js';
import { log } from './common.js';

// The snapshot of the card on screen, as JSON. Python pushes a new one while the card is up when
// the Crucible changes under the pointer.
let renderedSnapshot = '';

// Builds the card again for a new banner or a new snapshot. A payload that changes only the
// reveal flag leaves the card as it is.
function render(card, payload, sameToken) {
    const snapshotJson = JSON.stringify(payload.snapshot);
    if (sameToken && snapshotJson === renderedSnapshot) {
        return false;
    }
    renderCard(card, payload.snapshot);
    renderedSnapshot = snapshotJson;
    return true;
}

startCardHost({
    nodeId: 'zanju-crt-card',
    shownClass: 'zanju-crt-card-shown',
    hasContent: function (payload) { return Boolean(payload.snapshot); },
    render: render,
    // Once the content has settled, the series list is sized to its content, and the card takes a
    // frame to lay out at the new width before it is measured.
    fit: fitColumns,
    // The fitted widths are in pixels of the old scale, so the list measures again from its
    // natural widths.
    onScale: resetColumns,
    everySecond: function (card, payload) { refreshTimes(card, payload.snapshot); },
    log: log,
});
