// The battle panel of the Crucible: the conditions of the current mission and their progress.
//
// Python sends the whole panel as one payload (see battle_session.py): the series, the client
// text of each condition, and for each condition that the panel can count, the figures, the
// state and the time limit. This module only draws it. battle_panel.js runs the window.

import { SHIELD_IMAGE, clientImage, conditionImage, el, fill, serverNow, startsSet } from './common.js';

const STATE_CLASSES = {
    met: ' zanju-crt-prow-met',
    closed: ' zanju-crt-prow-closed',
};

function two(n) {
    return n < 10 ? '0' + n : '' + n;
}

// The time left of a time limit, as M:SS. Rounded down, as the battle clock of the client is, so
// both clocks change on the same second.
function formatClock(seconds) {
    const total = Math.max(0, Math.floor(seconds));
    return Math.floor(total / 60) + ':' + two(total % 60);
}

function icon(className, resource) {
    const node = el('div', className);
    if (resource) {
        node.style.backgroundImage = clientImage(resource);
    }
    return node;
}

function buildHead(payload) {
    const series = payload.series || {};
    const labels = payload.labels || {};
    const head = el('div', 'zanju-crt-panel-head' + (payload.done ? ' zanju-crt-panel-done' : ''));
    // A payload with no shield count shows no shield, rather than an empty or a wrong count.
    if (typeof series.shields === 'number') {
        head.appendChild(icon('zanju-crt-panel-shield', SHIELD_IMAGE));
        head.appendChild(el('div', 'zanju-crt-panel-shields', String(series.shields)));
    }
    head.appendChild(el('div', 'zanju-crt-panel-name', series.name || ''));
    if (series.stage && series.total) {
        head.appendChild(el('div', 'zanju-crt-panel-stage',
            fill(labels.mission, { stage: series.stage, total: series.total })));
    }
    return head;
}

// The bar and the figures of a condition that the panel counts, and the clock of a time limit.
// After a reconnect, a row has no figures, but its time limit still counts down.
function buildMeter(row) {
    const meter = el('div', 'zanju-crt-prow-meter');
    if (row.live) {
        const bar = el('div', 'zanju-crt-prow-bar');
        const level = el('div', 'zanju-crt-prow-fill');
        level.style.width = (Math.max(0, Math.min(1, Number(row.ratio) || 0)) * 100).toFixed(1) + '%';
        bar.appendChild(level);
        meter.appendChild(bar);
        meter.appendChild(el('div', 'zanju-crt-prow-figures', (row.valueText || '0') + ' / ' + (row.targetText || '')));
    }
    if (row.timeLimit) {
        const clock = el('div', 'zanju-crt-prow-clock');
        clock._zanjuDeadline = row.deadline || null;
        clock._zanjuLimit = row.timeLimit;
        // Only a counted condition can close: with no figures, nobody knows if it was met.
        clock._zanjuCloses = Boolean(row.live) && row.state !== 'met';
        meter.appendChild(clock);
    }
    return meter;
}

// A rule of the condition that the figures cannot show, such as "no direct shot on an ally" of
// High Caliber, above the figures. Red once the rule is broken.
function buildRule(rule, labels) {
    return el('div', 'zanju-crt-prow-rule' + (rule.broken ? ' zanju-crt-prow-rule-broken' : ''),
        labels[rule.key] || '');
}

function buildRow(row, labels) {
    const node = el('div', 'zanju-crt-prow' + (row.live ? (STATE_CLASSES[row.state] || '') : ''));
    const line = el('div', 'zanju-crt-prow-line');
    line.appendChild(icon('zanju-crt-prow-icon', row.icon ? conditionImage(row.icon) : ''));
    line.appendChild(el('div', 'zanju-crt-prow-text', row.text || ''));
    node.appendChild(line);
    const rules = row.rules || [];
    for (let i = 0; i < rules.length; i += 1) {
        node.appendChild(buildRule(rules[i], labels || {}));
    }
    if (row.live || row.timeLimit) {
        node.appendChild(buildMeter(row));
    }
    return node;
}

function renderPanel(node, payload) {
    while (node.firstChild) {
        node.removeChild(node.firstChild);
    }
    if (!payload) {
        return;
    }
    node.appendChild(buildHead(payload));
    const rows = payload.rows || [];
    const list = el('div', 'zanju-crt-panel-rows');
    // The separators follow the sets, as on the hover card.
    const mission = { group: payload.group, rows: rows };
    for (let i = 0; i < rows.length; i += 1) {
        if (startsSet(mission, i)) {
            list.appendChild(el('div', 'zanju-crt-panel-or', (payload.labels || {}).or || ''));
        }
        list.appendChild(buildRow(rows[i], payload.labels));
    }
    node.appendChild(list);
    refreshClocks(node, payload);
}

// Rewrite each time limit from the clock. Before the battle starts, the limit has no deadline yet
// and shows its whole length. A limit that runs out before its condition is met closes the row,
// a second before Python has a reason to say so.
function refreshClocks(node, payload) {
    const clocks = node.querySelectorAll('.zanju-crt-prow-clock');
    const now = serverNow(payload);
    for (let i = 0; i < clocks.length; i += 1) {
        const clock = clocks[i];
        const left = clock._zanjuDeadline ? clock._zanjuDeadline - now : clock._zanjuLimit;
        clock.textContent = formatClock(left);
        if (clock._zanjuDeadline && left <= 0 && clock._zanjuCloses) {
            const row = clock.parentNode && clock.parentNode.parentNode;
            if (row && row.className.indexOf('zanju-crt-prow-closed') < 0) {
                row.className += STATE_CLASSES.closed;
            }
        }
    }
}

export { formatClock, refreshClocks, renderPanel };
