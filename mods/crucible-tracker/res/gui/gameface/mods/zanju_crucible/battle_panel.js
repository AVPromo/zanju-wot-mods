// The Crucible battle panel, as its own Gameface document, in a window the mod owns.
//
// Three jobs: draw the payload, publish the real size so Python can place and clamp the window,
// and report the press and the release of a drag. Python moves the window between the two by the
// cursor position, because mouse events stop when the pointer leaves this small window. See
// gameface/battle_panel.py.

import { refreshClocks, renderPanel } from './battle.js';
import { applyLanguage, callCommand, nextFrame, readModel, waitForDomBuilt } from './card_host.js';
import { log, parseJson, unwrap } from './common.js';

// A standalone view owns its whole document, so its model is the root one.
const ROOT_RES_ID = 0;
const CLOCK_INTERVAL_MS = 1000;
let lastSize = '';
let lastPayload = '';
let currentPayload = null;
let dragging = false;
// True when a ResizeObserver publishes each new size. See followSize.
let observed = false;

function panelNode() {
    return document.getElementById('zanju-crt-panel');
}

function command(name, arg) {
    callCommand(readModel(), name, arg, log);
}

function render() {
    const model = readModel();
    const node = panelNode();
    if (!model || !node) {
        return;
    }
    const raw = String(unwrap(model.payload) || '');
    if (raw === lastPayload) {
        return;
    }
    lastPayload = raw;
    const payload = parseJson(raw, 'panel payload');
    currentPayload = payload;
    // battle.css reads `lang` to select the font, as the card does. See card_host.js.
    applyLanguage(payload && payload.lang);
    renderPanel(node, payload);
    if (!observed) {
        scheduleMeasure();
    }
}

// The client's own views that follow their content do it this way: a ResizeObserver on the root,
// which calls back after each layout that changes its size, and the view resized from there. It
// also catches the first layout of a new window, which can settle after the frames that a
// measurement waits. On 25 October 2026 the panel first measured 300x22, its padding without its
// one row, and kept that height until the next payload.
function followSize() {
    const node = panelNode();
    if (typeof ResizeObserver !== 'function' || !node) {
        log('no ResizeObserver; the panel measures after each change and once a second');
        return false;
    }
    new ResizeObserver(function () { publishSize(); }).observe(node);
    return true;
}

// Without a ResizeObserver: measured after layout, never in the frame that changed the DOM, and
// once more a frame later for a late settle. card_host.js explains why.
function scheduleMeasure() {
    nextFrame()
        .then(nextFrame)
        .then(function () {
            publishSize();
            return nextFrame();
        })
        .then(publishSize)
        .catch(function (error) { log('panel measurement failed: ' + error); });
}

function readSize() {
    const node = panelNode();
    if (!node) {
        return null;
    }
    const rect = node.getBoundingClientRect();
    const width = Math.ceil(rect.width);
    const height = Math.ceil(rect.height);
    return width > 0 && height > 0 ? { width: width, height: height } : null;
}

function publishSize() {
    const size = readSize();
    if (!size) {
        return;
    }
    const width = size.width;
    const height = size.height;
    try {
        viewEnv.resizeViewPx(width, height);
    } catch (error) {
        log('resizeViewPx failed: ' + error);
    }
    const key = width + 'x' + height;
    if (key !== lastSize) {
        lastSize = key;
        command('onSized', { width: width, height: height });
    }
}

// Without a ResizeObserver, a size that differs from the published one is published each second,
// for a layout that settles late.
function publishChangedSize() {
    const size = readSize();
    if (size && size.width + 'x' + size.height !== lastSize) {
        publishSize();
    }
}

// The panel gets mouse events only while the player holds Ctrl, because the battle shows the
// cursor only then. A press of the left button starts a drag, and its release ends it.
function bindDrag() {
    document.addEventListener('mousedown', function (event) {
        if (event.button === 0) {
            dragging = true;
            command('onDrag', { phase: 'start' });
        }
    }, true);
    document.addEventListener('mouseup', function () {
        if (dragging) {
            dragging = false;
            command('onDrag', { phase: 'end' });
        }
    }, true);
}

engine.whenReady
    .then(waitForDomBuilt)
    .then(nextFrame)
    .then(nextFrame)
    .then(function () {
        bindDrag();
        observed = followSize();
        render();
        engine.on('viewEnv.onDataChanged', render);
        if (!observed) {
            // Every size here is in `rem`, so a change of the interface scale changes the size.
            engine.on('self.onScaleUpdated', scheduleMeasure);
        }
        viewEnv.addDataChangedCallback('model', ROOT_RES_ID, true);
        setInterval(function () {
            const node = panelNode();
            if (node && currentPayload) {
                refreshClocks(node, currentPayload);
            }
            if (!observed && !dragging) {
                publishChangedSize();
            }
        }, CLOCK_INTERVAL_MS);
    })
    .catch(function (error) { log('panel startup failed: ' + error); });
