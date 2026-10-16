// Tests for the shared banner tray, run by `node --test`.
//
// A minimal DOM stands in for the renderer: only the calls the tray makes are implemented.

import assert from 'node:assert/strict';
import test from 'node:test';

class FakeNode {
    constructor(tag) {
        this.tagName = tag;
        this.className = '';
        this.children = [];
        this.parentNode = null;
        this.style = {};
        this.attributes = {};
        this.id = '';
    }

    appendChild(child) {
        child.parentNode = this;
        this.children.push(child);
        return child;
    }

    removeChild(child) {
        this.children = this.children.filter((node) => node !== child);
        child.parentNode = null;
    }

    setAttribute(name, value) {
        this.attributes[name] = String(value);
    }

    getAttribute(name) {
        return Object.prototype.hasOwnProperty.call(this.attributes, name) ? this.attributes[name] : null;
    }

    getBoundingClientRect() {
        return this._rect || { left: 0, top: 0, right: 0, bottom: 0, width: 0, height: 0 };
    }

    _walk(out) {
        for (const child of this.children) {
            out.push(child);
            child._walk(out);
        }
        return out;
    }

    _matches(selector) {
        const attribute = selector.match(/^\[([a-z-]+)(\*?)(?:="(.*)")?\]$/);
        if (!attribute) {
            return false;
        }
        const [, name, operator, value] = attribute;
        const actual = name === 'class' ? this.className : this.getAttribute(name);
        if (actual === null || actual === undefined || actual === '') {
            return false;
        }
        if (value === undefined) {
            return true;
        }
        return operator === '*' ? String(actual).includes(value) : actual === value;
    }

    querySelector(selector) {
        return this._walk([]).find((node) => node._matches(selector)) || null;
    }

    querySelectorAll(selector) {
        return this._walk([]).filter((node) => node._matches(selector));
    }
}

const body = new FakeNode('body');
global.document = {
    createElement: (tag) => new FakeNode(tag),
    body,
    querySelectorAll: (selector) => body.querySelectorAll(selector),
    getElementById: (id) => body._walk([]).find((node) => node.id === id) || null,
};
global.window = { innerWidth: 1920, innerHeight: 1080 };

const tray = await import('../gameface/tray.js');

function clearBody() {
    body.children.slice().forEach((child) => body.removeChild(child));
    for (const key of Object.keys(global.document)) {
        if (key.startsWith('__zanjuTrayObserved_')) {
            delete global.document[key];
        }
    }
}

function addAnchor(rect) {
    const anchor = new FakeNode('div');
    anchor.className = 'VehicleInfoWidget_b24b193a';
    anchor._rect = rect;
    body.appendChild(anchor);
    return anchor;
}

const RECT = { left: 800, top: 100, right: 1000, bottom: 160 };

function entry(owner, rank, side, width) {
    return { owner, rank, side, width };
}

test('a mod that is alone starts its row at the vehicle name, on either side', () => {
    const right = tray.rowOrigin([], entry('a', 10, 'right', 120), RECT);
    assert.deepEqual(right, { x: 1000 + tray.ANCHOR_OFFSET_X_PX, y: 100 + tray.ANCHOR_OFFSET_Y_PX });
    const left = tray.rowOrigin([], entry('a', 10, 'left', 120), RECT);
    assert.deepEqual(left, { x: 800 - tray.ANCHOR_OFFSET_X_PX - 120, y: 100 + tray.ANCHOR_OFFSET_Y_PX });
});

test('on the right, a row starts after every row with a lower rank', () => {
    const entries = [entry('ct', 10, 'right', 200), entry('crt', 20, 'right', 64)];
    assert.equal(tray.rowOrigin(entries, entries[0], RECT).x, 1000 + tray.ANCHOR_OFFSET_X_PX);
    assert.equal(tray.rowOrigin(entries, entries[1], RECT).x,
        1000 + tray.ANCHOR_OFFSET_X_PX + 200 + tray.ROW_GAP_PX);
});

test('on the left, the lowest rank stands nearest the name and the others stack outward', () => {
    const entries = [entry('ct', 10, 'left', 200), entry('crt', 20, 'left', 64)];
    const near = tray.rowOrigin(entries, entries[0], RECT);
    const far = tray.rowOrigin(entries, entries[1], RECT);
    assert.equal(near.x + 200, 800 - tray.ANCHOR_OFFSET_X_PX);
    assert.equal(far.x + 64 + tray.ROW_GAP_PX, near.x);
});

test('rows on different sides do not push each other', () => {
    const entries = [entry('ct', 10, 'right', 200), entry('crt', 20, 'left', 64)];
    assert.equal(tray.rowOrigin(entries, entries[1], RECT).x, 800 - tray.ANCHOR_OFFSET_X_PX - 64);
    assert.equal(tray.rowOrigin(entries, entries[0], RECT).x, 1000 + tray.ANCHOR_OFFSET_X_PX);
});

test('two equal ranks sort by owner, never by load order', () => {
    const entries = [entry('zeta', 10, 'right', 50), entry('alpha', 10, 'right', 70)];
    assert.equal(tray.rowOrigin(entries, entries[1], RECT).x, 1000 + tray.ANCHOR_OFFSET_X_PX);
    assert.equal(tray.rowOrigin(entries, entries[0], RECT).x,
        1000 + tray.ANCHOR_OFFSET_X_PX + 70 + tray.ROW_GAP_PX);
});

test('the own entry counts the same whether it is in the list or not', () => {
    const self = entry('crt', 20, 'right', 64);
    const other = entry('ct', 10, 'right', 200);
    assert.deepEqual(tray.rowOrigin([other], self, RECT), tray.rowOrigin([other, self], self, RECT));
});

test('a row of no width yet takes no room from the rows after it', () => {
    const entries = [entry('ct', 10, 'right', 0), entry('crt', 20, 'right', 64)];
    assert.equal(tray.rowOrigin(entries, entries[1], RECT).x, 1000 + tray.ANCHOR_OFFSET_X_PX);
});

test('an entry with no side, from an older release, stands on the right', () => {
    clearBody();
    const list = document.createElement('div');
    list.id = tray.TRAY_ID;
    const node = document.createElement('i');
    node.setAttribute('data-owner', 'old.mod');
    node.setAttribute('data-rank', '5');
    node.setAttribute('data-width', '90');
    node.setAttribute('data-unknown', 'ignored');
    list.appendChild(node);
    body.appendChild(list);
    assert.deepEqual(tray.readEntries(), [{ owner: 'old.mod', rank: 5, side: 'right', width: 90 }]);
    clearBody();
});

test('publishing creates the list and the entry, and an unchanged entry writes nothing', () => {
    clearBody();
    assert.equal(tray.publishEntry(entry('ct', 10, 'right', 120.4)), true);
    const node = document.getElementById(tray.TRAY_ID).querySelector('[data-owner="ct"]');
    assert.equal(node.getAttribute('data-width'), '120');
    assert.equal(node.getAttribute('data-seq'), '1');
    assert.equal(tray.publishEntry(entry('ct', 10, 'right', 120)), false);
    assert.equal(node.getAttribute('data-seq'), '1');
    assert.equal(tray.publishEntry(entry('ct', 10, 'left', 120)), true);
    assert.equal(node.getAttribute('data-seq'), '2');
    clearBody();
});

test('the list is hidden, so it never draws or takes input', () => {
    clearBody();
    tray.publishEntry(entry('ct', 10, 'right', 120));
    assert.equal(document.getElementById(tray.TRAY_ID).style.display, 'none');
    clearBody();
});

test('a withdrawn entry leaves the list, and the next row closes the gap', () => {
    clearBody();
    tray.publishEntry(entry('ct', 10, 'right', 200));
    tray.publishEntry(entry('crt', 20, 'right', 64));
    const self = entry('crt', 20, 'right', 64);
    assert.notEqual(tray.rowOrigin(tray.readEntries(), self, RECT).x, 1000 + tray.ANCHOR_OFFSET_X_PX);
    assert.equal(tray.withdrawEntry('ct'), true);
    assert.equal(tray.withdrawEntry('ct'), false);
    assert.equal(tray.rowOrigin(tray.readEntries(), self, RECT).x, 1000 + tray.ANCHOR_OFFSET_X_PX);
    clearBody();
});

test('a mutation reports only the rows of other mods', () => {
    const own = document.createElement('i');
    own.setAttribute('data-owner', 'ct');
    const other = document.createElement('i');
    other.setAttribute('data-owner', 'crt');
    assert.equal(tray.concernsOthers([{ target: own }], 'ct'), false);
    assert.equal(tray.concernsOthers([{ target: other }], 'ct'), true);
    assert.equal(tray.concernsOthers([{ target: {}, removedNodes: [other] }], 'ct'), true);
    assert.equal(tray.concernsOthers([{ target: {}, addedNodes: [own] }], 'ct'), false);
});

test('with no MutationObserver, the caller hears so and keeps its poll', () => {
    clearBody();
    assert.equal(tray.observeTray('ct', () => {}), 'unavailable');
    clearBody();
});

test('an observer is set up once per owner and document', () => {
    clearBody();
    let built = 0;
    global.MutationObserver = class {
        constructor(callback) {
            built += 1;
            this.callback = callback;
        }

        observe() {}
    };
    try {
        assert.equal(tray.observeTray('ct', () => {}), 'observing');
        assert.equal(tray.observeTray('ct', () => {}), 'observing');
        assert.equal(built, 1);
    } finally {
        delete global.MutationObserver;
        clearBody();
    }
});

test('the row starts down and right of the anchor top-right corner', () => {
    clearBody();
    addAnchor({ left: 900, top: 100, right: 1020, bottom: 160, width: 120, height: 60 });
    assert.deepEqual(tray.anchorRect(), { left: 900, top: 100, right: 1020, bottom: 160 });
    clearBody();
});

test('there is no anchor at all while the name block is off stage', () => {
    clearBody();
    assert.equal(tray.anchorRect(), null);
});

test('the outermost match is the anchor, not a node inside it', () => {
    clearBody();
    const outer = addAnchor({ left: 900, top: 100, right: 1020, bottom: 160, width: 120, height: 60 });
    const inner = new FakeNode('div');
    inner.className = 'VehicleInfoWidget_name_1234';
    inner._rect = { left: 910, top: 110, right: 950, bottom: 120, width: 40, height: 10 };
    outer.appendChild(inner);
    assert.equal(tray.findAnchor(), outer);
    clearBody();
});

test('a detached anchor is not mistaken for one still on stage', () => {
    clearBody();
    const anchor = addAnchor({ left: 0, top: 0, right: 10, bottom: 10, width: 10, height: 10 });
    assert.equal(tray.isAttached(anchor), true);
    body.removeChild(anchor);
    assert.equal(tray.isAttached(anchor), false);
});

test('a position is clamped so a banner can never sit off-screen', () => {
    assert.deepEqual(tray.clampToViewport(-50, -50), { x: 0, y: 0 });
    assert.deepEqual(tray.clampToViewport(99999, 99999), { x: 1880, y: 1060 });
});

test('a page that reads 1 by 1 does not pin the banners to the corner', () => {
    const realWindow = global.window;
    global.window = { innerWidth: 1, innerHeight: 1 };
    try {
        assert.deepEqual(tray.clampToViewport(1030, 100), { x: 1030, y: 100 });
    } finally {
        global.window = realWindow;
    }
});

test('the side is left only when it says left', () => {
    assert.equal(tray.normalizeSide('left'), 'left');
    assert.equal(tray.normalizeSide('right'), 'right');
    assert.equal(tray.normalizeSide(undefined), 'right');
    assert.equal(tray.normalizeSide('LEFT'), 'right');
});
