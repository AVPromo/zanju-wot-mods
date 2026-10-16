// The Crucible hover card, in one of two modes.
//
// - With an active series, the card is about that series only: its name and the time left, one
//   shield for each shield of the series, and every mission of the series with its conditions.
//   The current mission stands out, and a mission before it is marked completed.
// - With no active series: every series the player can see, grouped by difficulty.
//
// Both modes start with the header and the warnings, and end with the vehicles in battle and the
// click hint.
//
// Every label comes from the snapshot, so translation stays on the Python side. Most labels are
// the client's own strings, which also gives the card the client's own words in every language.
//
// Each time on the card is a countdown, written by the rules of the premium-time counter. A time
// element keeps its end and its template, so `refreshTimes` can rewrite it every second without
// a new render.

import {
    SHIELD_IMAGE,
    SHIELD_LEFT_IMAGE,
    SHIELD_SPENT_IMAGE,
    clientImage,
    conditionImage,
    currencyImage,
    el,
    fill,
    startsSet,
    timeLeft,
} from './common.js';

const DIFFICULTY_ORDER = ['hard', 'medium', 'easy'];

// The column that takes the spare width when the card is wider than the list, so the time stays at
// the right edge. Only after `fitColumns`: before, it would stretch and spoil its own measure.
const GROWING_COLUMN = 'zanju-crt-series-avail';
const GROWING_CLASS = 'zanju-crt-series-grow';

// The columns of a series row, in order. `fitColumns` gives each one the width of its widest cell.
const COLUMNS = [
    'zanju-crt-series-name',
    'zanju-crt-series-shields',
    'zanju-crt-series-completions',
    'zanju-crt-series-avail',
    'zanju-crt-series-time',
];

// What the player can do with a series now. Python works the answer out (`availability` in
// crucible.py), and this only draws it. A start or a free restart reads green, but grey while
// another series is active, because the client refuses both until that series ends.
function buildAvailability(entry, labels) {
    const node = el('div', 'zanju-crt-series-avail');
    const muted = entry.blocked ? ' zanju-crt-avail-blocked' : '';
    if (entry.availability === 'active') {
        node.className += ' zanju-crt-avail-active';
        node.textContent = labels.active || '';
    } else if (entry.availability === 'start') {
        node.className += ' zanju-crt-avail-good' + muted;
        node.textContent = labels.available || '';
    } else if (entry.availability === 'freeRestart') {
        node.className += ' zanju-crt-avail-good' + muted;
        node.textContent = labels.freeRestart || '';
    } else if (entry.availability === 'paidRestart') {
        node.appendChild(el('div', 'zanju-crt-avail-label', labels.restartFor || ''));
        const price = el('div', 'zanju-crt-price zanju-crt-currency-' + (entry.restartCurrency || 'none'));
        price.appendChild(icon('zanju-crt-series-icon', currencyImage(entry.restartCurrency)));
        price.appendChild(el('div', 'zanju-crt-series-number', entry.restartCostText || ''));
        node.appendChild(price);
    }
    return node;
}

function icon(className, resource) {
    const node = el('div', className);
    if (resource) {
        node.style.backgroundImage = clientImage(resource);
    }
    return node;
}

// A countdown. `template` is the client's "Will end in %(timer)s", or empty for the time alone.
function countdown(className, endTime, template, soonest) {
    const node = el('div', className + ' zanju-crt-countdown' + (soonest ? ' zanju-crt-soonest' : ''));
    node._zanjuEnd = endTime || 0;
    node._zanjuTemplate = template || '';
    return node;
}

function writeCountdown(node, snapshot) {
    const left = timeLeft(node._zanjuEnd, snapshot);
    const text = left && node._zanjuTemplate ? fill(node._zanjuTemplate, { timer: left }) : left;
    if (node.textContent !== text) {
        node.textContent = text;
    }
}

// Rewrites every countdown on the card. card_panel.js calls it once a second.
function refreshTimes(card, snapshot) {
    const nodes = card.querySelectorAll('.zanju-crt-countdown');
    for (let i = 0; i < nodes.length; i += 1) {
        writeCountdown(nodes[i], snapshot);
    }
}

// One shield for each shield of the series, the spent ones greyed, then the count. The client's
// own Crucible screen draws them the same way.
function buildShieldRow(active) {
    const left = Math.max(0, active.shields || 0);
    const limit = Math.max(left, active.shieldsLimit || 0);
    const line = el('div', 'zanju-crt-focus-shields' + (left <= 1 ? ' zanju-crt-focus-shields-last' : ''));
    for (let i = 0; i < limit; i += 1) {
        line.appendChild(icon(i < left ? 'zanju-crt-focus-shield' : 'zanju-crt-focus-shield zanju-crt-focus-shield-spent',
            i < left ? SHIELD_LEFT_IMAGE : SHIELD_SPENT_IMAGE));
    }
    line.appendChild(el('div', 'zanju-crt-focus-shield-count', String(left) + '/' + String(limit)));
    return line;
}

function buildCondition(row) {
    const node = el('div', 'zanju-crt-cond');
    const line = el('div', 'zanju-crt-cond-line');
    line.appendChild(icon('zanju-crt-cond-icon', row.icon ? conditionImage(row.icon) : ''));
    line.appendChild(el('div', 'zanju-crt-cond-text', row.text || row.title || ''));
    node.appendChild(line);
    return node;
}

// The missions of the active series. A snapshot from before the list carries only the current
// mission, and then the card shows that one.
function seriesMissions(active) {
    if ((active.missions || []).length) {
        return active.missions;
    }
    const current = active.mission;
    if (!current || !(current.rows || []).length) {
        return [];
    }
    return [{ stage: active.stage, state: 'current', group: current.group, rows: current.rows }];
}

function buildMission(mission, labels) {
    const node = el('div', 'zanju-crt-mission zanju-crt-mission-' + (mission.state || 'next'));
    const head = el('div', 'zanju-crt-mission-head');
    head.appendChild(el('div', 'zanju-crt-mission-title', fill(labels.missionNumber, { stage: mission.stage })));
    if (mission.state === 'done') {
        head.appendChild(el('div', 'zanju-crt-mission-completed', labels.completed || ''));
    }
    node.appendChild(head);
    const rows = mission.rows || [];
    for (let i = 0; i < rows.length; i += 1) {
        if (startsSet(mission, i)) {
            node.appendChild(el('div', 'zanju-crt-or', labels.or || ''));
        }
        node.appendChild(buildCondition(rows[i]));
    }
    return node;
}

// The active series alone: the name with the time left on the right, the shields, and the
// missions.
function appendFocus(card, active, labels) {
    const top = el('div', 'zanju-crt-focus-top');
    top.appendChild(el('div', 'zanju-crt-focus-name', active.name || ''));
    if (active.endTime) {
        top.appendChild(countdown('zanju-crt-focus-time', active.endTime, '', false));
    }
    card.appendChild(top);
    card.appendChild(buildShieldRow(active));
    const missions = seriesMissions(active);
    if (!missions.length) {
        return;
    }
    const block = el('div', 'zanju-crt-missions');
    for (let i = 0; i < missions.length; i += 1) {
        if (i) {
            // A rule between two missions, as between the shields and the first mission.
            block.appendChild(el('div', 'zanju-crt-mission-rule'));
        }
        block.appendChild(buildMission(missions[i], labels));
    }
    card.appendChild(block);
}

// One series: its name, its shields, its completions, what the player can do with it now, and
// the time left.
// The warnings, in the yellow of the campaign-tracker card, at the top where the player reads
// first: the vehicle in the garage cannot play, and a battle in progress decides the current
// mission, or a series that starts now.
function appendWarnings(card, snapshot, labels) {
    if (snapshot.vehicleFits === false) {
        card.appendChild(el('div', 'zanju-crt-note-warning', labels.vehicleRestriction || ''));
    }
    if ((snapshot.inBattle || []).length) {
        const text = snapshot.active ? labels.inBattleActive : labels.inBattleWarning;
        card.appendChild(el('div', 'zanju-crt-note-warning', text || ''));
    }
}

// The vehicles in a battle that has not ended, one per row, the way the campaign-tracker card
// lists locked vehicles. Each row carries the crossed swords that the banner counts.
function appendInBattle(card, names, labels) {
    if (!names.length) {
        return;
    }
    const block = el('div', 'zanju-crt-battles');
    block.appendChild(el('div', 'zanju-crt-battles-label', labels.inBattle || ''));
    for (let i = 0; i < names.length; i += 1) {
        const row = el('div', 'zanju-crt-battles-row');
        row.appendChild(el('div', 'zanju-crt-battles-icon'));
        row.appendChild(el('div', 'zanju-crt-battles-name', names[i]));
        block.appendChild(row);
    }
    card.appendChild(block);
}

function buildSeriesRow(entry, labels) {
    const row = el('div', 'zanju-crt-series' + (entry.state === 'active' ? ' zanju-crt-series-active' : ''));
    row.appendChild(el('div', 'zanju-crt-series-name', entry.name || ''));

    const shields = el('div', 'zanju-crt-series-shields' + (entry.state === 'active' && entry.shields <= 1
        ? ' zanju-crt-series-shields-last' : ''));
    shields.appendChild(icon('zanju-crt-series-icon', SHIELD_IMAGE));
    shields.appendChild(el('div', 'zanju-crt-series-number', String(entry.shields)));
    row.appendChild(shields);

    row.appendChild(el('div', 'zanju-crt-series-completions',
        fill(labels.completions, { done: entry.wins, allowed: entry.allowedCompletions })));
    row.appendChild(buildAvailability(entry, labels));
    row.appendChild(countdown('zanju-crt-series-time', entry.endTime, '', entry.soonest));
    return row;
}

function appendSeries(card, series, labels) {
    const block = el('div', 'zanju-crt-list');
    for (let d = 0; d < DIFFICULTY_ORDER.length; d += 1) {
        const group = series.filter(function (entry) { return entry.difficulty === DIFFICULTY_ORDER[d]; });
        if (!group.length) {
            continue;
        }
        block.appendChild(el('div', 'zanju-crt-group', labels[DIFFICULTY_ORDER[d]] || ''));
        for (let i = 0; i < group.length; i += 1) {
            block.appendChild(buildSeriesRow(group[i], labels));
        }
    }
    card.appendChild(block);
}

function widthOf(node) {
    const rect = node.getBoundingClientRect();
    return rect && rect.width > 0 ? rect.width : 0;
}

// Sizes the series list to its content. Every cell of a column takes the width of the widest cell
// in it, so the columns stand in line from row to row with one gap between every two. The card
// then takes the width of the list. The availability column is the one that changes the most: a
// paid restart with its price is about three times as wide as "Available".
//
// Call it only after a frame has laid out the new content. This renderer does not lay out on
// `getBoundingClientRect`, so a measure in the same frame reads the layout from before.
function fitColumns(card) {
    const rows = card.querySelectorAll('.zanju-crt-series');
    if (!rows.length) {
        return null;
    }
    const widths = COLUMNS.map(function (name) {
        const cells = card.querySelectorAll('.' + name);
        let widest = 0;
        for (let i = 0; i < cells.length; i += 1) {
            widest = Math.max(widest, widthOf(cells[i]));
        }
        return Math.ceil(widest);
    });
    // The gap and the frame of the card are read off the layout as it stands, so the arithmetic
    // follows the interface scale without knowing it.
    const first = rows[0].children;
    const gap = Math.max(0, first[1].getBoundingClientRect().left - first[0].getBoundingClientRect().right);
    const frame = Math.max(0, widthOf(card) - widthOf(rows[0]));
    COLUMNS.forEach(function (name, index) {
        const cells = card.querySelectorAll('.' + name);
        for (let i = 0; i < cells.length; i += 1) {
            if (name === GROWING_COLUMN) {
                // A floor, not a width: when the card is wider than the list, this column takes the
                // rest, and the time stays at the right edge.
                cells[i].style.minWidth = widths[index] + 'px';
                cells[i].className += ' ' + GROWING_CLASS;
            } else {
                cells[i].style.width = widths[index] + 'px';
            }
        }
    });
    const total = widths.reduce(function (sum, width) { return sum + width; }, 0)
        + gap * (COLUMNS.length - 1) + frame;
    card.style.width = Math.ceil(total) + 'px';
    return { widths: widths, gap: gap, width: Math.ceil(total) };
}

// Undoes `fitColumns`, so the next measure reads the natural widths again: on a change of the
// interface scale, the widths in pixels are stale.
function resetColumns(card) {
    card.style.width = '';
    COLUMNS.forEach(function (name) {
        const cells = card.querySelectorAll('.' + name);
        for (let i = 0; i < cells.length; i += 1) {
            cells[i].style.width = '';
            cells[i].style.minWidth = '';
            cells[i].className = cells[i].className.split(' ' + GROWING_CLASS).join('');
        }
    });
}

// The class of the card for its mode. card_panel.js adds and removes only its own reveal class.
const CARD_CLASS = 'zanju-crt-card';
const FOCUS_CLASS = 'zanju-crt-card-focus';

function setMode(card, focus) {
    const classes = String(card.className || '').split(' ').filter(function (name) {
        return name && name !== CARD_CLASS && name !== FOCUS_CLASS;
    });
    card.className = [CARD_CLASS].concat(focus ? [FOCUS_CLASS] : [], classes).join(' ');
}

function renderCard(card, snapshot) {
    card.textContent = '';
    // A new list measures from its natural widths. The cells are new, but the card is not.
    card.style.width = '';
    const labels = (snapshot && snapshot.labels) || {};
    const active = snapshot && snapshot.active;
    setMode(card, Boolean(active));
    card.appendChild(el('div', 'zanju-crt-card-header', labels.header || ''));
    if (snapshot) {
        appendWarnings(card, snapshot, labels);
    }
    if (active) {
        appendFocus(card, active, labels);
    } else {
        card.appendChild(el('div', 'zanju-crt-note', labels.noActive || ''));
    }
    appendInBattle(card, (snapshot && snapshot.inBattle) || [], labels);
    const series = (snapshot && snapshot.series) || [];
    if (!active && series.length) {
        appendSeries(card, series, labels);
    }
    card.appendChild(el('div', 'zanju-crt-hint', labels.hintOpen || ''));
    refreshTimes(card, snapshot);
}

export { buildAvailability, buildCondition, fitColumns, refreshTimes, renderCard, resetColumns };
