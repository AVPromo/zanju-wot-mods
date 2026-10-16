// The Crucible hover card, as its own Gameface document, in a window the mod owns.
//
// A near copy of card_panel.js of campaign-tracker, which explains each step. In short: the
// model is the document's root model, updates arrive through `viewEnv.onDataChanged`, the card
// measures itself after layout and publishes the size, and it stays transparent until Python has
// moved the window under the banner. See gameface/card_window.py.

import { fitColumns, refreshTimes, renderCard, resetColumns } from './card.js';
import { log, parseJson } from './common.js';

// A standalone view owns its whole document, so its model is the root one.
const ROOT_RES_ID = 0;

// The card is only ever as big as its content, and Python needs the real number to place the
// window under the banner. Measured after layout has settled, then published once per change.
let lastPublished = '';
// Bumped on every render so a measurement scheduled for a card the pointer has already left
// cannot publish over the current one.
let measureGeneration = 0;
// The token whose card is currently built. A payload arriving with the same token is Python
// changing one field -- the reveal flag or the held keys -- not a different card.
let renderedToken = '';
// The snapshot the card on screen was built from. Python pushes a new one while the card is up
// when the Crucible changes under the pointer.
let renderedSnapshot = '';
// The same snapshot, parsed, for the countdowns. Each time on the card is rewritten once a second.
let currentSnapshot = null;
const COUNTDOWN_INTERVAL_MS = 1000;
// The token of the card on screen. Python rejects a size carrying any other token, so a measure
// that was not triggered by a payload -- a scale change, say -- has to quote this one.
let currentToken = '';

function cardNode() {
    return document.getElementById('zanju-crt-card');
}

function readModel() {
    return window.model || null;
}

function render(model) {
    const card = cardNode();
    if (!card || !model) {
        return;
    }
    const payload = parseJson(model.payload, 'card payload');
    if (!payload || !payload.snapshot) {
        // Python hides the window rather than sending an empty card, so this is only reached
        // before the first hover. Leave the last card standing -- it is not on screen -- but
        // still publish a size, because the engine gives the view a limited window to report
        // one and falls back to a default size if nothing arrives.
        publishSize('');
        return;
    }
    const token = String(payload.token || '');
    const snapshotJson = JSON.stringify(payload.snapshot);
    currentSnapshot = payload.snapshot;

    if (token === renderedToken && snapshotJson === renderedSnapshot) {
        // Same card, only the reveal flag changed. Rebuilding it would throw away a measurement
        // that is already correct and start the whole handshake again.
        setRevealed(card, payload.reveal);
        return;
    }

    // Before the build, so that the first layout and the size measured from it use the right font.
    applyLanguage(payload.lang);
    renderCard(card, payload.snapshot);
    // A new card is never painted where the last one stood. Python reveals it once it has
    // moved the window, which it can only do once this render has been measured. A new snapshot
    // for the card on screen keeps it revealed: the window has not moved.
    setRevealed(card, token === renderedToken && payload.reveal);
    renderedToken = token;
    renderedSnapshot = snapshotJson;
    currentToken = token;
    scheduleMeasure(token);
}

// The client's own documents set `lang` on the root element when they start, and card.css reads
// it to select the font. This document does not run that code, so Python sends the code instead.
// With no `lang`, the card stays on PFDINMax, which draws nothing for Chinese, Japanese, Korean,
// Thai or Vietnamese text.
function applyLanguage(lang) {
    const root = document.documentElement;
    if (lang && root.getAttribute('lang') !== lang) {
        root.setAttribute('lang', lang);
    }
}

// Adds or removes the reveal class only. The card keeps the class of its mode (see card.js).
function setRevealed(card, revealed) {
    const classes = String(card.className || '').split(' ').filter(function (name) {
        return name && name !== 'zanju-crt-card-shown';
    });
    if (revealed) {
        classes.push('zanju-crt-card-shown');
    }
    card.className = classes.join(' ');
}

// Measure after layout, never in the frame that changed the DOM.
//
// This is what the bottom of the card was being cut off by. `getBoundingClientRect` right after
// building the card reports the layout as it stood before the new content, so the height came
// back short, `resizeViewPx` gave the native surface that short height, and the last rows -- the
// hint lines -- fell outside it. It read as random because whether the old layout was already
// close to the new one depends on which banner was hovered before.
//
// Measured twice: once two frames later, and once more after that. The second pass costs one
// comparison and catches a late settle, such as a font becoming available between the two.
// One step more than in campaign-tracker: once the content has settled, the series list is sized
// to its content, and the card takes a frame to lay out at the new width before it is measured.
function scheduleMeasure(token) {
    measureGeneration += 1;
    const generation = measureGeneration;
    nextFrame()
        .then(nextFrame)
        .then(function () {
            const card = cardNode();
            if (generation === measureGeneration && card) {
                fitColumns(card);
            }
            return nextFrame();
        })
        .then(function () {
            if (generation !== measureGeneration) {
                return null;
            }
            publishSize(token);
            return nextFrame();
        })
        .then(function () {
            if (generation === measureGeneration) {
                publishSize(token);
            }
        })
        .catch(function (error) { log('card measurement failed: ' + error); });
}

// Tell the native surface how big the card actually is, then tell Python, which cannot measure
// the DOM and must not place the window before it knows.
function publishSize(token) {
    const card = cardNode();
    if (!card) {
        return;
    }
    const rect = card.getBoundingClientRect();
    const width = Math.ceil(rect.width);
    const height = Math.ceil(rect.height);
    if (!(width > 0 && height > 0)) {
        return;
    }

    try {
        viewEnv.resizeViewPx(width, height);
    } catch (error) {
        log('resizeViewPx failed: ' + error);
    }

    // The token comes back with the size so Python can ignore a measurement for a card it has
    // already moved past -- the pointer can leave one banner and enter another between a push
    // and the frame that measures it.
    const key = token + ':' + width + 'x' + height;
    if (key === lastPublished) {
        return;
    }
    lastPublished = key;
    log('card measured ' + width + 'x' + height + ' (token ' + token + ')');
    const model = readModel();
    const sized = model && model.onSized;
    if (typeof sized === 'function') {
        sized.call(model, { token: String(token || ''), width: width, height: height });
    } else if (sized && typeof sized.value === 'function') {
        sized.value.call(sized, { token: String(token || ''), width: width, height: height });
    } else {
        log('the onSized command is missing on the card model');
    }
}

function waitForDomBuilt() {
    return new Promise(function (resolve) {
        if (window.isDomBuilt) {
            resolve();
            return;
        }
        engine.on('self.onDomBuilt', resolve);
    });
}

function nextFrame() {
    return new Promise(function (resolve) { requestAnimationFrame(resolve); });
}

engine.whenReady
    .then(waitForDomBuilt)
    // Two frames: the card is measured, and a measurement taken before layout settles reports
    // the wrapped width rather than the intended one.
    .then(nextFrame)
    .then(nextFrame)
    .then(function () {
        render(readModel());
        engine.on('viewEnv.onDataChanged', function () { render(readModel()); });
        // The surface follows the interface scale: every size here is in `rem`, so a scale
        // change re-lays the card out and the published size has to follow it.
        engine.on('self.onScaleUpdated', function () {
            // The fitted widths are in pixels of the old scale, so the list measures again from
            // its natural widths.
            const card = cardNode();
            if (card) {
                resetColumns(card);
            }
            scheduleMeasure(currentToken);
        });
        viewEnv.addDataChangedCallback('model', ROOT_RES_ID, true);
        // The window lives only while the pointer is on the banner, so this interval dies with it.
        setInterval(function () {
            const card = cardNode();
            if (card && currentSnapshot) {
                refreshTimes(card, currentSnapshot);
            }
        }, COUNTDOWN_INTERVAL_MS);
        log('card window ready');
    })
    .catch(function (error) { log('card startup failed: ' + error); });

export { publishSize, render, scheduleMeasure };
