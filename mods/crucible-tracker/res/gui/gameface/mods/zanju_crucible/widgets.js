// Zanju Crucible Tracker — one small garage banner for the Crucible.
//
// Loaded into the persistent `mono/hangar/main` document by net.openwg.gameface (see
// src/zanju_crt/gameface/widgets_inject.py), which also attaches the `zanjuCrtWidgets` data
// model this reads: a JSON snapshot of the Crucible.
//
// The banner has the shape and the width of the campaign-tracker banners, so the two read as
// one row. The client's Crucible shield heads it, in the place of the campaign numeral.
//
// - With an active series: the emblem alone in the head, a shield with the shields left out of
//   all shields below it, the current mission out of all missions, and the time until the
//   series ends.
// - With no active series: the emblem, the number of series still open, and the time until the
//   first of them ends. That is the rule of the client's own Crucible banner.
// - In both: crossed swords and a count, in the warning yellow, while vehicles that can play the
//   Crucible are in a battle that has not ended. The card says why that matters.
//
// The banner goes grey when the vehicle in the garage cannot play: below the Crucible tiers, or
// outside the tiers of the current mission.
//
// The series name is too long for a banner this narrow, so only the card gives it. The time
// counts down on every tick, by the rules of the premium-time counter.
//
// A click opens the client's own Crucible screen. A hover shows the card, which a window of the
// mod's own draws. This file reports where the banner is, and Python owns the card window.
//
// The banner is our own DOM subtree appended to the document body, and it never changes an
// element that the game renders. The root stays `pointer-events: none`, so it never takes the
// garage's drag-to-rotate, and the banner is one direct child that takes input again.
//
// The banner stands in the shared banner tray beside the vehicle name, through tray.js. The
// build copies tray.js in beside this file from mods-common/gameface/.
//
// See docs/reference/gameface-mod-widgets.md.

import { SHIELD_IMAGE, clientImage, el, log, parseJson, timeLeft, unwrap } from './common.js';
import {
    SIDE_RIGHT,
    anchorRect,
    clampToViewport,
    isAttached,
    isWithin,
    normalizeSide,
    observeTray,
    publishEntry,
    readEntries,
    rowOrigin,
    withdrawEntry,
} from './tray.js';

const ROOT_ID = 'zanju-crt-root';
const DATA_PROPERTY = 'zanjuCrtWidgets';
// The snapshot normally arrives by push. These are the backstop poll rates, before and after a
// push has arrived.
const POLL_INTERVAL_MS = 1000;
const UNPUSHED_POLL_INTERVAL_MS = 100;
// Flags on the document, so a handler is registered once even if this module is evaluated again
// for another sub-view.
const PUSH_BOUND_FLAG = '__zanjuCrtPushBound';
const PUSH_RES_ID_FLAG = '__zanjuCrtPushResId';
const PUSH_SEEN_FLAG = '__zanjuCrtPushSeen';
const CLICK_BOUND_FLAG = '__zanjuCrtClickBound';
// This mod's entry in the shared banner tray. campaign-tracker takes 10, so its row stands
// nearest the vehicle name on either side.
const TRAY_OWNER = 'zanju.crucibletracker';
const TRAY_RANK = 20;
// The key of the one banner. The card window keys its state on it.
const BANNER_KEY = 'crucible';
// Slot width used when the banner cannot be measured yet. The campaign-tracker slot.
const NOMINAL_WIDGET_WIDTH_PX = 60;

let lastSnapshotJson = null;
let dataResId = null;
let pollTimer = null;
let currentPollMs = null;
let traySide = SIDE_RIGHT;
// The banner model on screen, or null when there is no banner to draw.
let bannerShown = null;
// The snapshot behind it, for the clock offset and the unit labels of the countdown.
let shownSnapshot = null;
let lastOriginKey = '';
let bannerPlaced = false;
let hovered = false;

function modelOn(id) {
    const view = window.subViews.get(id);
    const model = view && view.model;
    return model && model[DATA_PROPERTY] ? model[DATA_PROPERTY] : null;
}

function findDataModel() {
    if (typeof window === 'undefined' || !window.subViews) {
        return null;
    }
    if (dataResId !== null) {
        const known = modelOn(dataResId);
        if (known) {
            return known;
        }
    }
    const ids = window.subViews.ids();
    for (const id of ids) {
        const model = modelOn(id);
        if (model) {
            dataResId = id;
            return model;
        }
    }
    dataResId = null;
    return null;
}

// Python writing a property raises no event here. `viewEnv.onDataChanged` is the engine's own
// signal, and the subscription names one sub-view, so it is renewed whenever that view moves.
function bindModelPush() {
    if (dataResId === null || document[PUSH_RES_ID_FLAG] === dataResId) {
        return;
    }
    if (typeof engine === 'undefined' || typeof viewEnv === 'undefined') {
        return;
    }
    try {
        if (!document[PUSH_BOUND_FLAG]) {
            engine.on('viewEnv.onDataChanged', onPush);
            document[PUSH_BOUND_FLAG] = true;
        }
        viewEnv.addDataChangedCallback('model', dataResId, true);
        document[PUSH_RES_ID_FLAG] = dataResId;
    } catch (e) {
        log('could not subscribe to model updates, falling back to polling (' + e + ')');
    }
}

function onPush() {
    document[PUSH_SEEN_FLAG] = true;
    tick();
}

function invokeCommand(data, name, arg) {
    try {
        let host = null;
        if (data && typeof data[name] === 'function') {
            host = data;
        } else {
            const inner = unwrap(data);
            if (inner && typeof inner[name] === 'function') {
                host = inner;
            }
        }
        if (!host) {
            log('command missing: ' + name);
            return;
        }
        host[name](arg || {});
    } catch (e) {
        log('command failed: ' + name + ' (' + e + ')');
    }
}

function getRoot() {
    return document.getElementById(ROOT_ID);
}

function buildRoot() {
    const root = el('div', 'zanju-crt-root');
    root.id = ROOT_ID;
    document.body.appendChild(root);
    return root;
}

// What the banner shows, worked out from the snapshot. Null means no banner at all: the Crucible
// is off on this server, or no series is open to the player.
function bannerModel(snapshot) {
    if (!snapshot || !snapshot.enabled || !(snapshot.series || []).length) {
        return null;
    }
    const active = snapshot.active;
    const common = {
        idle: snapshot.vehicleFits === false,
        endTime: snapshot.nearestEnd || 0,
        inBattle: (snapshot.inBattle || []).length,
    };
    if (active) {
        return Object.assign(common, {
            shields: active.shields || 0,
            shieldsLimit: active.shieldsLimit || 0,
            value: String(active.stage || 0) + '/' + String(active.total || 0),
        });
    }
    return Object.assign(common, {
        shields: null,
        value: String(snapshot.openCount || 0),
    });
}

function buildBanner() {
    const widget = el('div', 'zanju-crt-widget');
    const face = el('div', 'zanju-crt-face');
    const head = el('div', 'zanju-crt-head');
    const emblem = el('div', 'zanju-crt-emblem');
    emblem.style.backgroundImage = clientImage(SHIELD_IMAGE);
    head.appendChild(emblem);
    face.appendChild(head);
    // The shields of the active series: the client's shield, then the shields left out of all.
    const shields = el('div', 'zanju-crt-shields');
    const shield = el('div', 'zanju-crt-shields-icon');
    shield.style.backgroundImage = clientImage(SHIELD_IMAGE);
    shields.appendChild(shield);
    shields.appendChild(el('div', 'zanju-crt-shields-count'));
    face.appendChild(shields);
    face.appendChild(el('div', 'zanju-crt-value'));
    face.appendChild(el('div', 'zanju-crt-time'));
    // The client's own in-battle mark from the vehicle carousel, tinted the way the campaign
    // banners tint their flags. The card lists the vehicles.
    const battle = el('div', 'zanju-crt-battle');
    battle.appendChild(el('div', 'zanju-crt-battle-icon'));
    battle.appendChild(el('div', 'zanju-crt-battle-count'));
    face.appendChild(battle);
    widget.appendChild(face);
    // The point the banner hangs to, the same two layers as on the campaign-tracker banners.
    const tail = el('div', 'zanju-crt-tail');
    tail.appendChild(el('div', 'zanju-crt-tail-fill'));
    widget.appendChild(tail);
    widget.addEventListener('mouseenter', function () {
        hovered = true;
        reportHover(widget);
    });
    widget.addEventListener('mouseleave', function () {
        hovered = false;
        reportHover(null);
    });
    return widget;
}

function renderBanner(widget, model, snapshot) {
    widget.className = 'zanju-crt-widget' + (model.idle ? ' zanju-crt-widget-idle' : '');
    const shields = widget.querySelector('.zanju-crt-shields');
    if (model.shields === null) {
        shields.className = 'zanju-crt-shields zanju-crt-shields-empty';
        widget.querySelector('.zanju-crt-shields-count').textContent = '';
    } else {
        shields.className = 'zanju-crt-shields' + (model.shields <= 1 ? ' zanju-crt-shields-last' : '');
        widget.querySelector('.zanju-crt-shields-count').textContent =
            String(model.shields) + '/' + String(model.shieldsLimit);
    }
    widget.querySelector('.zanju-crt-value').textContent = model.value;
    const battle = widget.querySelector('.zanju-crt-battle');
    battle.className = 'zanju-crt-battle' + (model.inBattle ? '' : ' zanju-crt-battle-empty');
    widget.querySelector('.zanju-crt-battle-count').textContent = model.inBattle ? String(model.inBattle) : '';
    renderTime(widget, model, snapshot);
}

// The countdown row. Called on every tick, so it writes only when the text changed.
function renderTime(widget, model, snapshot) {
    const node = widget.querySelector('.zanju-crt-time');
    const text = timeLeft(model.endTime, snapshot);
    if (node.textContent !== text) {
        node.textContent = text;
    }
    const className = 'zanju-crt-time' + (text ? '' : ' zanju-crt-time-empty');
    if (node.className !== className) {
        node.className = className;
    }
}

// Builds, updates or removes the one banner. Returns the model on screen, or null.
function renderWidgets(root, snapshot) {
    const model = bannerModel(snapshot);
    let widget = root.querySelector('.zanju-crt-widget');
    if (!model) {
        if (widget) {
            root.removeChild(widget);
        }
        return null;
    }
    if (!widget) {
        widget = buildBanner();
        root.appendChild(widget);
    }
    renderBanner(widget, model, snapshot);
    return model;
}

function reportHover(widget) {
    const data = findDataModel();
    if (!data) {
        return;
    }
    if (!widget || !isAttached(widget)) {
        invokeCommand(data, 'cardHover', { key: '' });
        return;
    }
    const rect = widget.getBoundingClientRect();
    invokeCommand(data, 'cardHover', {
        key: BANNER_KEY,
        x: Math.round(rect.left),
        y: Math.round(rect.top),
        w: Math.round(rect.width),
        h: Math.round(rect.height),
    });
}

function bindClicks(data) {
    if (document[CLICK_BOUND_FLAG]) {
        return;
    }
    document[CLICK_BOUND_FLAG] = true;
    // Document level, capture phase: a plain `click` listener on our own element does not fire
    // in this renderer. Only a press inside our own banner is ours to take.
    document.addEventListener('mouseup', function (event) {
        const root = getRoot();
        const widget = root && root.querySelector('.zanju-crt-widget');
        if (!widget || !isWithin(widget, event.target)) {
            return;
        }
        event.stopPropagation();
        invokeCommand(findDataModel() || data, 'openCrucible', {});
    }, true);
}

function bannerWidth(widget) {
    try {
        const rect = widget.getBoundingClientRect();
        if (rect && rect.width > 0) {
            return { width: Math.round(rect.width), measured: true };
        }
    } catch (e) {
        // Not measurable yet: the nominal slot stands in.
    }
    return { width: NOMINAL_WIDGET_WIDTH_PX, measured: false };
}

// Places the banner in the shared tray. The tray says where this row starts, after the rows with
// a lower rank on the same side.
function updateLayout(root, side) {
    const widget = root.querySelector('.zanju-crt-widget');
    const rect = anchorRect();
    if (!widget || !rect) {
        bannerPlaced = false;
        lastOriginKey = '';
        withdrawEntry(TRAY_OWNER);
        return;
    }
    const size = bannerWidth(widget);
    const self = { owner: TRAY_OWNER, rank: TRAY_RANK, side: normalizeSide(side), width: size.width };
    publishEntry(self);
    const origin = rowOrigin(readEntries(), self, rect);
    const key = origin.x + ':' + origin.y;
    if (key !== lastOriginKey) {
        const point = clampToViewport(origin.x, origin.y);
        widget.style.left = point.x + 'px';
        widget.style.top = point.y + 'px';
        if (!bannerPlaced) {
            log('banner placed on the ' + self.side + ' side');
        }
        // Remembered only on a real width, so a banner measured late is laid out again.
        lastOriginKey = size.measured ? key : '';
        if (hovered) {
            reportHover(widget);
        }
    }
    bannerPlaced = true;
}

function tick() {
    const data = findDataModel();
    if (!data) {
        return;
    }
    let root = getRoot();
    if (!root) {
        root = buildRoot();
        bindClicks(data);
        lastSnapshotJson = null;
        bannerShown = null;
        lastOriginKey = '';
        bannerPlaced = false;
    }
    bindModelPush();

    const visible = unwrap(data.visible);
    const raw = unwrap(data.snapshot);
    if (raw !== lastSnapshotJson) {
        lastSnapshotJson = raw;
        const snapshot = parseJson(raw, 'snapshot');
        if (snapshot) {
            traySide = normalizeSide(snapshot.layout && snapshot.layout.side);
            bannerShown = renderWidgets(root, snapshot);
            shownSnapshot = snapshot;
            lastOriginKey = '';
        }
    } else if (bannerShown) {
        const widget = root.querySelector('.zanju-crt-widget');
        if (widget) {
            renderTime(widget, bannerShown, shownSnapshot);
        }
    }

    // A banner that is not on screen leaves the tray, so the other rows close the gap.
    if (visible !== false && bannerShown) {
        updateLayout(root, traySide);
    } else {
        withdrawEntry(TRAY_OWNER);
        lastOriginKey = '';
        bannerPlaced = false;
    }
    root.style.display = visible !== false && bannerShown && bannerPlaced ? 'block' : 'none';
    setPollRate(document[PUSH_SEEN_FLAG] && bannerPlaced ? POLL_INTERVAL_MS : UNPUSHED_POLL_INTERVAL_MS);
}

function setPollRate(intervalMs) {
    if (intervalMs === currentPollMs) {
        return;
    }
    currentPollMs = intervalMs;
    if (pollTimer !== null) {
        clearInterval(pollTimer);
    }
    pollTimer = setInterval(tick, intervalMs);
}

// Another mod's row moved, so this one may have to.
function onTrayChanged() {
    lastOriginKey = '';
    tick();
}

function start() {
    log('widgets.js loaded');
    log('banner tray: ' + observeTray(TRAY_OWNER, onTrayChanged));
    setPollRate(UNPUSHED_POLL_INTERVAL_MS);
    tick();
}

// Auto-start only inside the game document. Under the test runner there is no Gameface view
// registry, so importing this module has no side effects.
if (typeof window !== 'undefined' && window.subViews) {
    start();
}

export {
    NOMINAL_WIDGET_WIDTH_PX,
    TRAY_OWNER,
    TRAY_RANK,
    bannerModel,
    buildBanner,
    renderBanner,
    renderTime,
    renderWidgets,
    updateLayout,
};
