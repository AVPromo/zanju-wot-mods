// The few things both documents need: the banner in the garage document, and the card in the
// mod's own window.

function log(message) {
    // console.error reaches game.log, tagged [UI] [Gameface]. console.log is untested here.
    console.error('[zanju.crucibletracker] ' + message);
}

function unwrap(value) {
    return value && typeof value === 'object' && 'value' in value ? value.value : value;
}

function parseJson(raw, what) {
    if (!raw) {
        return null;
    }
    try {
        return JSON.parse(raw);
    } catch (e) {
        log('could not parse the ' + what + ': ' + e);
        return null;
    }
}

function el(tag, className, text) {
    const node = document.createElement(tag);
    if (className) {
        node.className = className;
    }
    if (text !== undefined && text !== null) {
        node.textContent = text;
    }
    return node;
}

// Fills a template with values. The client's own strings use three placeholder forms, and our
// own strings use the first: `{name}`, `{{name}}` and `%(name)s`.
function fill(template, values) {
    let text = String(template || '');
    const names = Object.keys(values || {});
    for (let i = 0; i < names.length; i += 1) {
        const value = String(values[names[i]]);
        text = text.split('{{' + names[i] + '}}').join(value);
        text = text.split('{' + names[i] + '}').join(value);
        text = text.split('%(' + names[i] + ')s').join(value);
    }
    return text;
}

// An image from the client's own packages, as the client's own stylesheets name one. The path
// below `R.images` follows the folders, and a folder whose name starts with a digit takes a
// `c_` prefix: `missionIcons/32/` is `missionIcons.c_32`. directives-helper draws its directive
// icons the same way, so this notation is known to work in a mod's script.
function clientImage(resource) {
    return "url('R.images." + resource + "')";
}

const SHIELD_IMAGE = 'gui.maps.icons.userMissions.challenges.icons.shields.shield_32';
// The pair that the client's own Crucible screen draws one per shield: a shield left, and a shield
// spent, greyed.
const SHIELD_LEFT_IMAGE = 'gui.maps.icons.userMissions.challenges.icons.shields.shield_s';
const SHIELD_SPENT_IMAGE = 'gui.maps.icons.userMissions.challenges.icons.shields.loseShield_s';

function conditionImage(iconKey) {
    return 'gui.maps.icons.userMissions.challenges.missionIcons.c_32.' + iconKey;
}

// The client ships an icon for each currency it prices in: credits, gold, crystal (bonds) and a
// few more. Empty for a currency it has no icon for, and the price then stands alone.
const CURRENCIES_WITH_ICONS = ['credits', 'gold', 'crystal', 'equipCoin', 'freeXP'];

function currencyImage(currency) {
    return CURRENCIES_WITH_ICONS.indexOf(currency) >= 0
        ? 'gui.maps.icons.library.currency.' + currency + '_24x24'
        : '';
}

function two(n) {
    return n < 10 ? '0' + n : '' + n;
}

// The time left, by the rules of premium-time: the two largest units that carry a value, the
// first unpadded and the second with two digits. "3d 05h", "2h 11m", "5m 12s", "45s".
function formatRemaining(seconds, labels) {
    const total = Math.max(0, Math.floor(seconds));
    const units = [
        [Math.floor(total / 86400), labels.dayUnit || 'd'],
        [Math.floor((total % 86400) / 3600), labels.hourUnit || 'h'],
        [Math.floor((total % 3600) / 60), labels.minuteUnit || 'm'],
        [total % 60, labels.secondUnit || 's'],
    ];
    let first = -1;
    for (let i = 0; i < units.length; i += 1) {
        if (units[i][0] !== 0) {
            first = i;
            break;
        }
    }
    if (first === -1) {
        return '0' + (labels.secondUnit || 's');
    }
    return units.slice(first, first + 2)
        .map(function (unit, index) { return (index === 0 ? String(unit[0]) : two(unit[0])) + unit[1]; })
        .join(' ');
}

// True when the row at this index opens another set of conditions of a choice, so an "OR" goes
// above it. A row with no set index, from a transport of an older version, is a set of its own.
function startsSet(mission, index) {
    if (!index || !mission || mission.group !== 'or') {
        return false;
    }
    const rows = mission.rows || [];
    const setOf = function (i) { return rows[i] && rows[i].set !== undefined ? rows[i].set : i; };
    return setOf(index) !== setOf(index - 1);
}

// The server time now, in seconds. The snapshot carries the offset of the client clock.
function serverNow(snapshot) {
    return Date.now() / 1000 + (Number(snapshot && snapshot.timeOffset) || 0);
}

// The time left until a server time, written as above, or '' when there is no end.
function timeLeft(endTime, snapshot) {
    if (!endTime) {
        return '';
    }
    return formatRemaining(endTime - serverNow(snapshot), (snapshot && snapshot.labels) || {});
}

export {
    SHIELD_IMAGE,
    SHIELD_LEFT_IMAGE,
    SHIELD_SPENT_IMAGE,
    clientImage,
    conditionImage,
    currencyImage,
    el,
    fill,
    formatRemaining,
    log,
    parseJson,
    serverNow,
    startsSet,
    timeLeft,
    unwrap,
};
