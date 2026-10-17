// The small helpers that every script of our mods needs. The build copies this file beside the
// scripts of each mod that imports it.

// A log function for one mod. Each line carries the tag of the mod, such as
// `zanju.crucibletracker`, so the lines of two mods in one document stay apart.
function createLog(tag) {
    return function log(message) {
        // console.error reaches game.log, tagged [UI] [Gameface]. console.log is untested there.
        console.error('[' + tag + '] ' + message);
    };
}

// The value of a Wulf property, which can arrive wrapped as `{ value: x }`.
function unwrap(value) {
    return value && typeof value === 'object' && 'value' in value ? value.value : value;
}

// A JSON string from Python, or null when it is empty or broken. `what` names it in the log line
// that a broken one writes.
function parseJson(raw, what, log) {
    if (!raw) {
        return null;
    }
    try {
        return JSON.parse(raw);
    } catch (e) {
        if (log) {
            log('could not parse the ' + what + ': ' + e);
        }
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

export { createLog, el, parseJson, unwrap };
