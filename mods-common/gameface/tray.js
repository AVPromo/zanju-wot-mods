// Shared banner tray: the garage banners of several mods stand in rows beside the vehicle name.
//
// Each mod keeps its own root, its own z-index and its own pointer handling. The mods share only
// the arithmetic, through a small hidden list in the garage document:
//
//     <div id="zanju-banner-tray" style="display: none">
//       <i data-owner="zanju.campaigntracker" data-rank="10" data-side="right" data-width="212"
//          data-seq="4"></i>
//       <i data-owner="zanju.crucibletracker" data-rank="20" data-side="right" data-width="64"
//          data-seq="2"></i>
//     </div>
//
// A row stands on the left or on the right side of the vehicle name block. On each side, the
// row with the lowest rank stands nearest the name, and two equal ranks sort by owner. A mod
// writes its own entry while its row is on screen and removes it while the row is hidden, so the
// other rows close the gap. A mod that is alone is the only entry, so its row starts at the
// vehicle name block.
//
// The list is a contract between mods, and players mix releases. A new version may add an
// attribute. Every version must ignore an attribute that it does not know, and must read a
// missing side as the right side, which is where the first version stood.
//
// The build copies this one file into the Gameface folder of each mod that imports it. Each mod
// thus has its own copy and its own module state. See
// docs/reference/runtime-layout-and-packaging.md and docs/reference/gameface-mod-widgets.md.

const TRAY_ID = 'zanju-banner-tray';
// The garage's own vehicle name and experience block. Matched on the component name, because the
// game builds its class names with a content hash (`VehicleInfoWidget_b24b193a`) that changes
// whenever Wargaming edits that stylesheet.
const ANCHOR_SELECTOR = '[class*="VehicleInfoWidget_"]';
// Where a row starts, measured from the top corner of the block on its side. The horizontal
// value clears the role icon that the game hangs off the right corner.
const ANCHOR_OFFSET_X_PX = 25;
const ANCHOR_OFFSET_Y_PX = 10;
// The space between two banners, and between two rows. Every banner fills its slot exactly, so
// this is the gap as it is seen, border to border.
const ROW_GAP_PX = 12;
// The smallest width and height that this module accepts as the size of the screen. On 2.4.1.0
// `innerWidth` and `innerHeight` can be 1 when a module starts, so a smaller value means that
// the page has no layout yet.
const MIN_SCREEN_PX = 100;

const SIDE_LEFT = 'left';
const SIDE_RIGHT = 'right';

// The block the rows hang off, kept between calls. A detached node still answers
// getBoundingClientRect, with zeroes, so the cache is kept only while the node is attached.
let anchorEl = null;

// Walks up checking identity first, rather than using `ancestor.contains(node)`: this renderer
// does not report a node as containing itself.
function isWithin(ancestor, node, maxDepth) {
    let current = node;
    const limit = maxDepth || 8;
    for (let depth = 0; ancestor && current && depth < limit; depth += 1) {
        if (current === ancestor) {
            return true;
        }
        current = current.parentNode;
    }
    return false;
}

// Whether a node is still part of the document. The garage nests the anchor deep, so the walk
// goes further than `isWithin` does by default.
function isAttached(node) {
    return isWithin(document.body, node, 64);
}

function findAnchor() {
    if (anchorEl && isAttached(anchorEl)) {
        return anchorEl;
    }
    anchorEl = null;
    if (typeof document === 'undefined' || !document.querySelectorAll) {
        return null;
    }
    // The class prefix matches the root of the component and every descendant, so take the
    // outermost match rather than the first one in document order.
    const matches = document.querySelectorAll(ANCHOR_SELECTOR);
    for (let i = 0; i < matches.length; i += 1) {
        let outermost = true;
        for (let j = 0; j < matches.length; j += 1) {
            if (i !== j && isWithin(matches[j], matches[i])) {
                outermost = false;
                break;
            }
        }
        if (outermost) {
            anchorEl = matches[i];
            return anchorEl;
        }
    }
    return null;
}

// The rectangle of the vehicle name block, or null while the garage does not show it. Null is
// the cue for every row to stay hidden rather than to stand somewhere else.
function anchorRect() {
    const element = findAnchor();
    if (!element || !element.getBoundingClientRect) {
        return null;
    }
    const rect = element.getBoundingClientRect();
    if (!rect || (!rect.width && !rect.height)) {
        return null;
    }
    return { left: rect.left, top: rect.top, right: rect.right, bottom: rect.bottom };
}

// Keeps a banner on the screen. A screen smaller than any real screen means that the page has no
// layout yet, and then the position stays as it is.
function clampToViewport(x, y) {
    const w = Number(window.innerWidth) || 0;
    const h = Number(window.innerHeight) || 0;
    let left = x;
    let top = y;
    if (w >= MIN_SCREEN_PX && h >= MIN_SCREEN_PX) {
        left = Math.max(0, Math.min(w - 40, left));
        top = Math.max(0, Math.min(h - 20, top));
    }
    return { x: Math.round(left), y: Math.round(top) };
}

function normalizeSide(side) {
    return side === SIDE_LEFT ? SIDE_LEFT : SIDE_RIGHT;
}

function getTray(create) {
    let tray = document.getElementById(TRAY_ID);
    if (!tray && create) {
        tray = document.createElement('div');
        tray.id = TRAY_ID;
        tray.style.display = 'none';
        document.body.appendChild(tray);
    }
    return tray;
}

function entryNode(tray, owner) {
    return tray ? tray.querySelector('[data-owner="' + owner + '"]') : null;
}

function readEntry(node) {
    return {
        owner: String(node.getAttribute('data-owner') || ''),
        rank: Number(node.getAttribute('data-rank')) || 0,
        side: normalizeSide(node.getAttribute('data-side')),
        width: Math.max(0, Number(node.getAttribute('data-width')) || 0),
    };
}

// Every entry in the list, whatever mod wrote it.
function readEntries() {
    const tray = getTray(false);
    if (!tray) {
        return [];
    }
    const nodes = tray.querySelectorAll('[data-owner]');
    const entries = [];
    for (let i = 0; i < nodes.length; i += 1) {
        entries.push(readEntry(nodes[i]));
    }
    return entries;
}

// Writes this mod's entry. Returns true when something changed. An unchanged entry writes
// nothing, so a mod that publishes on every tick does not wake the observers of the others.
function publishEntry(entry) {
    const tray = getTray(true);
    let node = entryNode(tray, entry.owner);
    if (!node) {
        node = document.createElement('i');
        node.setAttribute('data-owner', entry.owner);
        tray.appendChild(node);
    }
    const values = {
        'data-rank': String(entry.rank),
        'data-side': normalizeSide(entry.side),
        'data-width': String(Math.max(0, Math.round(entry.width || 0))),
    };
    let changed = false;
    const names = Object.keys(values);
    for (let i = 0; i < names.length; i += 1) {
        if (node.getAttribute(names[i]) !== values[names[i]]) {
            node.setAttribute(names[i], values[names[i]]);
            changed = true;
        }
    }
    if (changed) {
        // Written last, so an observer that keys on it reads the other values already in place.
        node.setAttribute('data-seq', String((Number(node.getAttribute('data-seq')) || 0) + 1));
    }
    return changed;
}

// Removes this mod's entry, so the other rows close the gap. Returns true when there was one.
function withdrawEntry(owner) {
    const tray = getTray(false);
    const node = entryNode(tray, owner);
    if (!node) {
        return false;
    }
    tray.removeChild(node);
    return true;
}

function compareEntries(a, b) {
    if (a.rank !== b.rank) {
        return a.rank - b.rank;
    }
    if (a.owner === b.owner) {
        return 0;
    }
    return a.owner < b.owner ? -1 : 1;
}

// Where the row of `self` starts, given every entry and the rectangle of the vehicle name.
//
// The rows on a side stack outward from the name, the lowest rank nearest. On the right side a
// row starts after every nearer row. On the left side a row ends before every nearer row, so it
// starts its own width further left. The banners inside a row always run left to right.
//
// `self` is passed apart from `entries` so the answer does not depend on whether this mod's own
// entry already reached the list.
function rowOrigin(entries, self, rect) {
    const side = normalizeSide(self.side);
    let offset = 0;
    for (let i = 0; i < entries.length; i += 1) {
        const other = entries[i];
        if (other.owner === self.owner || normalizeSide(other.side) !== side) {
            continue;
        }
        if (compareEntries(other, self) < 0 && other.width > 0) {
            offset += other.width + ROW_GAP_PX;
        }
    }
    const y = Math.round(rect.top + ANCHOR_OFFSET_Y_PX);
    if (side === SIDE_LEFT) {
        return { x: Math.round(rect.left - ANCHOR_OFFSET_X_PX - offset - (self.width || 0)), y: y };
    }
    return { x: Math.round(rect.right + ANCHOR_OFFSET_X_PX + offset), y: y };
}

function ownerOfNode(node) {
    return node && node.getAttribute ? node.getAttribute('data-owner') : null;
}

// Whether a batch of mutation records concerns a row other than the one of `owner`.
function concernsOthers(records, owner) {
    for (let i = 0; i < records.length; i += 1) {
        const record = records[i];
        const target = ownerOfNode(record.target);
        if (target && target !== owner) {
            return true;
        }
        const lists = [record.addedNodes, record.removedNodes];
        for (let j = 0; j < lists.length; j += 1) {
            const nodes = lists[j] || [];
            for (let k = 0; k < nodes.length; k += 1) {
                const added = ownerOfNode(nodes[k]);
                if (added && added !== owner) {
                    return true;
                }
            }
        }
    }
    return false;
}

// Calls `callback` when the row of another mod changes. Measured on 2.4.1.0: a change reached an
// observer in another script in 0 to 1 ms, where a poll every 100 ms took up to 87 ms. Returns
// what happened, so the caller can log it: a mod must keep a poll as the backstop either way.
function observeTray(owner, callback) {
    const flag = '__zanjuTrayObserved_' + owner;
    if (document[flag]) {
        return 'observing';
    }
    if (typeof MutationObserver !== 'function') {
        return 'unavailable';
    }
    try {
        const observer = new MutationObserver(function (records) {
            if (concernsOthers(records, owner)) {
                callback();
            }
        });
        observer.observe(getTray(true), { attributes: true, childList: true, subtree: true });
        document[flag] = true;
        return 'observing';
    } catch (e) {
        return 'failed: ' + e;
    }
}

export {
    ANCHOR_OFFSET_X_PX,
    ANCHOR_OFFSET_Y_PX,
    ANCHOR_SELECTOR,
    MIN_SCREEN_PX,
    ROW_GAP_PX,
    SIDE_LEFT,
    SIDE_RIGHT,
    TRAY_ID,
    anchorRect,
    clampToViewport,
    concernsOthers,
    findAnchor,
    isAttached,
    isWithin,
    normalizeSide,
    observeTray,
    publishEntry,
    readEntries,
    rowOrigin,
    withdrawEntry,
};
