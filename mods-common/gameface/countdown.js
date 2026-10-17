// The time left, as premium-time first wrote it: the two largest units that carry a value, the
// first unpadded and the second with two digits. "3d 05h", "2h 11m", "5m 12s", "45s".
//
// Two units keep a label short enough for a header button or a banner, and seconds appear exactly
// when less than an hour is left, where they are the only thing that still moves. The second unit
// keeps two digits ("2h 05m", never "2h 5m"), so the label does not get wider as it counts down.

import { unwrap } from './helpers.js';

const DEFAULT_MAX_UNITS = 2;
const FALLBACK_UNITS = { dayUnit: 'd', hourUnit: 'h', minuteUnit: 'm', secondUnit: 's' };

function two(n) {
    return n < 10 ? '0' + n : '' + n;
}

// The label of one unit from `units`, which has the keys dayUnit, hourUnit, minuteUnit and
// secondUnit. A value can be a Wulf property. A missing one takes the English letter.
function unitLabel(units, key) {
    const value = unwrap(units && units[key]);
    return value === undefined || value === null || value === '' ? FALLBACK_UNITS[key] : String(value);
}

function formatRemaining(seconds, units, maxUnits) {
    const total = Math.max(0, Math.floor(seconds));
    const parts = [
        [Math.floor(total / 86400), unitLabel(units, 'dayUnit')],
        [Math.floor((total % 86400) / 3600), unitLabel(units, 'hourUnit')],
        [Math.floor((total % 3600) / 60), unitLabel(units, 'minuteUnit')],
        [total % 60, unitLabel(units, 'secondUnit')],
    ];
    let first = -1;
    for (let i = 0; i < parts.length; i += 1) {
        if (parts[i][0] !== 0) {
            first = i;
            break;
        }
    }
    if (first === -1) {
        return '0' + unitLabel(units, 'secondUnit');
    }
    return parts.slice(first, first + (maxUnits || DEFAULT_MAX_UNITS))
        .map(function (part, index) { return (index === 0 ? String(part[0]) : two(part[0])) + part[1]; })
        .join(' ');
}

export { formatRemaining };
