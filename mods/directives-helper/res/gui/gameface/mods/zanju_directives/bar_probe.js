// Zanju Directives Helper — measures one of the garage's lobby bars from inside the bar's own
// document.
//
// Loaded into `mono/hangar/header` and `mono/hangar/footer` by net.openwg.gameface (see
// src/zanju_dh/gameface/bar_probe_inject.py). Each bar takes every press across its strip, also
// where it draws nothing, so the directives window must keep its title bar between them. The
// window lives in `mono/hangar/main` and cannot read these documents. Thus this module measures
// the strip of the document it runs in and reports it to Python with the `reportBar` command.
// Python knows which bar sent the report, and passes it on to the window.
//
// Each bar sizes its own view from one element and takes everything else out of the hit area:
// the App root in the header, the `App_footer` element in the footer. Python names the class
// prefix of that element in `rootClass`. See "The Lobby Bars Take Input Where They Draw Nothing" in
// docs/reference/gameface-mod-widgets.md.

import { createLog, unwrap } from './helpers.js';
import { createBridge, invokeCommand } from './model_bridge.js';

const DATA_PROPERTY = 'zanjuDhBarProbe';
// The strip changes size only with the screen width or the interface scale, so a slow poll is
// enough. A report goes out only when a number changes.
const POLL_INTERVAL_MS = 500;
// CSS modules name a component's classes `<Component>_<name>_<hash>`. The hash changes with each
// client build, the prefix does not. The header's App root is the outermost `App_` element.
const DEFAULT_ROOT_CLASS = 'App_';
// Flag on the document so a second evaluation of this module does not start a second poll.
const STARTED_FLAG = '__zanjuDhBarProbeStarted';

let lastReportJson = null;
// The poll runs for the whole garage session, so a fault in it is logged once, not twice a
// second for the rest of the session.
let tickFailed = false;

const log = createLog('zanju.directiveshelper.bars');

// Only the lookup of the bridge: the strip changes too rarely for pushes to pay, so the probe
// polls. See model_bridge.js.
const bridge = createBridge({
    dataProperty: DATA_PROPERTY,
    flagPrefix: '__zanjuDhBarProbe',
    onChange: function () { tick(); },
    log: log,
});

function hasClassPrefix(node, prefix) {
    // `className` is not a string on an SVG element.
    if (!node || typeof node.className !== 'string') {
        return false;
    }
    return node.className.split(' ').some((name) => name.indexOf(prefix) === 0);
}

function findBarRoot(start, prefix) {
    // Breadth first, so the outermost matching element is found before the ones inside it.
    // Walks `children` by hand rather than with an attribute selector, which this renderer is
    // not known to support.
    const queue = start ? [start] : [];
    while (queue.length) {
        const node = queue.shift();
        if (hasClassPrefix(node, prefix)) {
            return node;
        }
        const children = node.children || [];
        for (let index = 0; index < children.length; index += 1) {
            queue.push(children[index]);
        }
    }
    return null;
}

function rootClass(data) {
    const prefix = unwrap(data && data.rootClass);
    return typeof prefix === 'string' && prefix ? prefix : DEFAULT_ROOT_CLASS;
}

function pxPerRem() {
    if (typeof viewEnv !== 'undefined' && typeof viewEnv.remToPx === 'function') {
        const scale = Number(viewEnv.remToPx(1));
        if (scale > 0) {
            return scale;
        }
    }
    return 1;
}

function viewOrigin(scale) {
    // Where this view sits on the screen, in pixels. The element rectangles below are relative
    // to the view, and the window needs them in screen terms.
    try {
        if (typeof viewEnv !== 'undefined' && typeof viewEnv.getViewGlobalPositionRem === 'function') {
            const origin = viewEnv.getViewGlobalPositionRem();
            const x = Number(origin && origin.x);
            const y = Number(origin && origin.y);
            if (isFinite(x) && isFinite(y)) {
                return { x: x * scale, y: y * scale };
            }
        }
    } catch (e) {
        log('could not read the view position (' + e + ')');
    }
    return { x: 0, y: 0 };
}

function measure(prefix) {
    // The strip in screen pixels, or null when its element is not built yet. Rounded outwards:
    // a pixel too many leaves a gap, a pixel too few leaves the title bar under the strip.
    if (typeof document === 'undefined') {
        return null;
    }
    const element = findBarRoot(document.body, prefix || DEFAULT_ROOT_CLASS);
    if (!element || typeof element.getBoundingClientRect !== 'function') {
        return null;
    }
    const rect = element.getBoundingClientRect();
    if (!(rect.bottom > rect.top)) {
        return null;
    }
    const scale = pxPerRem();
    const origin = viewOrigin(scale);
    return {
        left: Math.floor(origin.x + rect.left),
        top: Math.floor(origin.y + rect.top),
        right: Math.ceil(origin.x + rect.right),
        bottom: Math.ceil(origin.y + rect.bottom),
        scale: scale,
    };
}

function tick() {
    // Runs inside the client's own document, so nothing may leave it.
    try {
        const data = bridge.find();
        if (!data) {
            return;
        }
        const prefix = rootClass(data);
        const report = measure(prefix);
        if (!report) {
            return;
        }
        const json = JSON.stringify(report);
        if (json === lastReportJson) {
            return;
        }
        lastReportJson = json;
        log('measured the bar (' + prefix + '): ' + json);
        invokeCommand(data, 'reportBar', report, log);
    } catch (e) {
        if (!tickFailed) {
            tickFailed = true;
            log('could not measure the bar (' + e + ')');
        }
    }
}

function start() {
    if (document[STARTED_FLAG]) {
        return;
    }
    document[STARTED_FLAG] = true;
    log('bar_probe.js loaded');
    setInterval(tick, POLL_INTERVAL_MS);
    tick();
}

// Auto-start only inside a game document. Under the test runner there is no Gameface view
// registry, so importing this module stays free of side effects.
if (typeof window !== 'undefined' && window.subViews) {
    start();
}

// Exported for the test suite only.
export { findBarRoot, measure, tick };
