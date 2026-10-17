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
    scheduleMeasure();
}

// Measured after layout, never in the frame that changed the DOM, and once more a frame later
// for a late settle. card_host.js explains why.
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

function publishSize() {
    const node = panelNode();
    if (!node) {
        return;
    }
    const rect = node.getBoundingClientRect();
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
    const key = width + 'x' + height;
    if (key !== lastSize) {
        lastSize = key;
        command('onSized', { width: width, height: height });
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
        render();
        engine.on('viewEnv.onDataChanged', render);
        // Every size here is in `rem`, so a change of the interface scale changes the size.
        engine.on('self.onScaleUpdated', scheduleMeasure);
        viewEnv.addDataChangedCallback('model', ROOT_RES_ID, true);
        setInterval(function () {
            const node = panelNode();
            if (node && currentPayload) {
                refreshClocks(node, currentPayload);
            }
        }, CLOCK_INTERVAL_MS);
    })
    .catch(function (error) { log('panel startup failed: ' + error); });
