// Tests for the garage directives window.
//
// Run via `zwm test directives-helper`. The module auto-starts only when a Gameface view
// registry is present, so importing it here neither builds a window nor starts a timer.

import { test, describe, beforeEach, afterEach } from 'node:test';
import assert from 'node:assert/strict';

import {
    applyFolded,
    applyHeaderWarning,
    applyPosition,
    buildRoot,
    findDataModel,
    parseSnapshot,
    renderBody,
    texts,
    tick,
    ROOT_ID,
} from '../res/gui/gameface/mods/zanju_directives/window.js';

class FakeNode {
    constructor(tag = 'div', className = '') {
        this.tag = tag;
        this.className = className;
        this.id = '';
        this.children = [];
        this._text = '';
        this.parentNode = null;
        this.style = new Proxy({}, {
            get: (target, key) => (key in target ? target[key] : ''),
            set: (target, key, value) => {
                target[key] = value;
                return true;
            },
        });
    }

    get textContent() {
        return this.children.length ? this.children.map((c) => c.textContent).join('') : this._text;
    }

    set textContent(value) {
        this.children = [];
        this._text = value;
    }

    appendChild(child) {
        this.children.push(child);
        child.parentNode = this;
        return child;
    }

    contains(node) {
        if (node === this) {
            return true;
        }
        return this.children.some((child) => child.contains(node));
    }

    querySelectorAll(selector) {
        const wanted = selector.replace(/^\./, '');
        const found = [];
        for (const child of this.children) {
            if (child.className.split(' ').includes(wanted)) {
                found.push(child);
            }
            found.push(...child.querySelectorAll(selector));
        }
        return found;
    }

    querySelector(selector) {
        return this.querySelectorAll(selector)[0] || null;
    }
}

function snapshotFixture(overrides = {}) {
    return Object.assign(
        {
            vehicleName: 'Object 260',
            hasVehicle: true,
            autoResupply: true,
            resupplyWarning: false,
            labels: {
                title: 'Directives',
                equipment: 'Equipment',
                crewImprove: 'Improve perk effect',
                crewGrant: 'Grant perk at 100%',
                noneAvailable: 'None available for this tank',
                autoResupply: 'Auto-resupply',
                resupplyWarning: 'Your last one. Auto-resupply will buy a replacement after the battle.',
                noVehicle: 'No vehicle selected',
                empty: 'No directives owned',
            },
            categories: [
                {
                    category: 'equipment',
                    total: 6,
                    directives: [
                        { intCD: 2, name: 'Improved Aiming', icon: 'improvedSights', count: 6, equipped: true },
                    ],
                },
                {
                    category: 'crewImprove',
                    total: 75,
                    directives: [
                        { intCD: 1, name: 'Repairs', icon: 'repairs', count: 75, equipped: false },
                    ],
                },
                {
                    category: 'crewGrant',
                    total: 9,
                    directives: [
                        { intCD: 3, name: 'Adrenaline', icon: 'adrenaline', count: 9, equipped: false },
                    ],
                },
            ],
        },
        overrides
    );
}

describe('parseSnapshot', () => {
    const realConsoleError = console.error;

    beforeEach(() => {
        console.error = () => {};
    });

    afterEach(() => {
        console.error = realConsoleError;
    });

    test('reads a JSON payload', () => {
        assert.deepEqual(parseSnapshot('{"hasVehicle":true}'), { hasVehicle: true });
    });

    test('returns null for an empty payload', () => {
        assert.equal(parseSnapshot(''), null);
    });

    test('survives malformed JSON', () => {
        assert.equal(parseSnapshot('{oops'), null);
    });
});

describe('texts', () => {
    test('uses the labels the Python side supplied', () => {
        const labels = texts(snapshotFixture());
        assert.equal(labels.categories.crewImprove, 'Improve perk effect');
        assert.equal(labels.categories.crewGrant, 'Grant perk at 100%');
        assert.equal(labels.autoResupply, 'Auto-resupply');
    });

    test('falls back to English when labels are missing', () => {
        // Translation lives on the Python side; if the payload arrives without labels the
        // window still has to render something readable.
        const labels = texts({});
        assert.equal(labels.title, 'Directives');
        assert.equal(labels.categories.equipment, 'Equipment');
    });
});

describe('renderBody', () => {
    beforeEach(() => {
        globalThis.document = { createElement: (tag) => new FakeNode(tag) };
    });

    afterEach(() => {
        delete globalThis.document;
    });

    function render(snapshot) {
        const body = new FakeNode();
        renderBody(body, snapshot, texts(snapshot));
        return body;
    }

    test('gives every directive a tile with its count and name', () => {
        const body = render(snapshotFixture());
        const names = body.querySelectorAll('.zanju-dh-tip').map((n) => n.textContent);
        const counts = body.querySelectorAll('.zanju-dh-badge').map((n) => n.textContent);
        assert.deepEqual(names, ['Improved Aiming', 'Repairs', 'Adrenaline']);
        assert.deepEqual(counts, ['6', '75', '9']);
    });

    test('points each tile at the game\'s own artefact icon', () => {
        const body = render(snapshotFixture());
        const icon = body.querySelector('.zanju-dh-icon');
        assert.match(icon.style.backgroundImage, /R\.images\.gui\.maps\.icons\.artefact\.improvedSights/);
    });

    test('falls back to an initial when a directive has no icon', () => {
        const snapshot = snapshotFixture();
        snapshot.categories[0].directives[0].icon = '';
        const body = render(snapshot);
        assert.equal(body.querySelector('.zanju-dh-icon').textContent, 'I');
    });

    test('shows every category heading', () => {
        const body = render(snapshotFixture());
        const headings = body.querySelectorAll('.zanju-dh-category-name').map((n) => n.textContent);
        assert.deepEqual(headings, ['Equipment', 'Improve perk effect', 'Grant perk at 100%']);
        assert.equal(body.querySelectorAll('.zanju-dh-category-total').length, 0,
            'the per-category sum was dropped');
    });

    test('ticks the checkbox when auto-resupply is on', () => {
        const body = render(snapshotFixture());
        const row = body.querySelector('.zanju-dh-auto');
        assert.match(row.textContent, /Auto-resupply/);
        assert.match(row.querySelector('.zanju-dh-check').className, /zanju-dh-check-on/);
    });

    test('leaves the checkbox empty when auto-resupply is off', () => {
        const body = render(snapshotFixture({ autoResupply: false }));
        const row = body.querySelector('.zanju-dh-auto');
        assert.doesNotMatch(row.querySelector('.zanju-dh-check').className, /zanju-dh-check-on/);
    });

    test('warns when resupply would buy a replacement', () => {
        const body = render(snapshotFixture({ resupplyWarning: true }));
        const warning = body.querySelector('.zanju-dh-warning');
        assert.ok(warning, 'the warning should be shown');
        assert.match(warning.querySelector('.zanju-dh-warn-tip').textContent, /buy a replacement/);
    });

    test('no warning when there is nothing to warn about', () => {
        const body = render(snapshotFixture());
        assert.equal(body.querySelector('.zanju-dh-warning'), null);
    });

    test('the warning shares the checkbox row so nothing below it moves', () => {
        // The row exists in both states; only its contents differ. If the warning ever became
        // a row of its own, every section under it would jump as it came and went.
        const quiet = render(snapshotFixture());
        const warned = render(snapshotFixture({ resupplyWarning: true }));
        const rowIndex = (body) => body.children.findIndex((c) => /zanju-dh-auto/.test(c.className));
        assert.equal(rowIndex(quiet), rowIndex(warned));
        assert.equal(quiet.children.length, warned.children.length);
        assert.ok(warned.querySelector('.zanju-dh-auto').contains(
            warned.querySelector('.zanju-dh-warning')), 'the warning belongs to the row');
    });

    test('clicking the warning toggles the setting too', () => {
        // It marks the row, so a click anywhere in it — marker included — reaches the toggle,
        // which is the fix the warning is pointing at.
        const row = render(snapshotFixture({ resupplyWarning: true })).querySelector('.zanju-dh-auto');
        assert.equal(row._zanjuDhAutoToggle, true);
    });

    test('the auto-resupply row can be clicked to toggle it', () => {
        const row = render(snapshotFixture()).querySelector('.zanju-dh-auto');
        assert.equal(row._zanjuDhAutoToggle, true);
        assert.match(row.className, /zanju-dh-clickable/);
    });

    test('offers no toggle when the setting could not be read', () => {
        // A failed read must not render as "disabled": the click would then act on a guess.
        const row = render(snapshotFixture({ autoResupply: null })).querySelector('.zanju-dh-auto');
        assert.equal(row._zanjuDhAutoToggle, undefined);
        assert.doesNotMatch(row.className, /zanju-dh-clickable/);
        assert.match(row.textContent, /No vehicle selected/);
    });

    test('keeps an empty section visible with a placeholder', () => {
        // The three sections stay in the same order and place whatever the tank can take.
        const snapshot = snapshotFixture();
        snapshot.categories[2].directives = [];
        snapshot.categories[2].total = 0;
        const body = render(snapshot);
        assert.equal(body.querySelectorAll('.zanju-dh-category-name').length, 3);
        assert.match(body.querySelector('.zanju-dh-empty').textContent, /None available/);
    });

    test('tiles carry the id needed to fit them', () => {
        const body = render(snapshotFixture());
        const tile = body.querySelectorAll('.zanju-dh-tile')[0];
        assert.equal(tile._zanjuDhIntCD, 2);
    });

    test('never dims a tile', () => {
        // Only directives that fit the tank are rendered at all now, so nothing is greyed.
        const body = render(snapshotFixture());
        const tiles = body.querySelectorAll('.zanju-dh-tile');
        assert.ok(tiles.length > 0);
        assert.ok(tiles.every((tile) => !/zanju-dh-tile-unusable/.test(tile.className)));
    });

    test('marks the fitted directive', () => {
        const body = render(snapshotFixture());
        const tile = body.querySelectorAll('.zanju-dh-tile').find((t) => t.textContent.includes('Improved Aiming'));
        assert.match(tile.className, /zanju-dh-tile-equipped/);
    });

    test('says so when no vehicle is selected', () => {
        const body = render(snapshotFixture({ hasVehicle: false, autoResupply: null }));
        assert.match(body.querySelector('.zanju-dh-auto').textContent, /No vehicle selected/);
    });

    test('says so when the depot is empty', () => {
        const body = render(snapshotFixture({ categories: [] }));
        assert.match(body.textContent, /No directives owned/);
    });

    test('re-rendering replaces the previous rows', () => {
        const body = new FakeNode();
        const snapshot = snapshotFixture();
        renderBody(body, snapshot, texts(snapshot));
        renderBody(body, snapshot, texts(snapshot));
        assert.equal(body.querySelectorAll('.zanju-dh-tile').length, 3, 'tiles must not accumulate');
    });
});

describe('window chrome', () => {
    let root;

    beforeEach(() => {
        const body = new FakeNode('body');
        globalThis.document = {
            body,
            createElement: (tag) => new FakeNode(tag),
            getElementById: (id) => body.children.find((child) => child.id === id) || null,
        };
        root = buildRoot();
    });

    afterEach(() => {
        delete globalThis.document;
    });

    test('shows and hides with the garage view', () => {
        // The window belongs to the default garage view only, the same rule the research
        // progress bar follows.
        const data = { snapshot: '{}', visible: false, x: -1, y: -1 };
        globalThis.window = {
            innerWidth: 1920,
            innerHeight: 1080,
            subViews: { ids: () => [1], get: () => ({ model: { zanjuDhWindow: data } }) },
        };
        tick();
        assert.equal(document.getElementById('zanju-dh-root').style.display, 'none');

        data.visible = true;
        tick();
        assert.equal(document.getElementById('zanju-dh-root').style.display, 'flex');
        delete globalThis.window;
    });

    test('does not re-apply a stored position once placed', () => {
        // The drag is reported to Python but the view model keeps its original coordinates,
        // so re-applying would yank the window back a moment after each drop.
        globalThis.window = { innerWidth: 1920, innerHeight: 1080 };
        applyPosition(root, { x: 300, y: 400, viewportWidth: 1920, viewportHeight: 1080 });
        root.style.left = '800px';
        applyPosition(root, { x: 300, y: 400, viewportWidth: 1920, viewportHeight: 1080 });
        assert.equal(root.style.left, '800px', 'the dragged position must survive');
        delete globalThis.window;
    });

    test('the root never takes pointer events, the header does', () => {
        // The garage listens for drag-to-rotate; a root that accepted input everywhere
        // would swallow it and the player could no longer turn the tank.
        assert.equal(root.className, 'zanju-dh-root');
        assert.match(root.querySelector('.zanju-dh-header').className, /zanju-dh-hot/);
    });

    test('marks the title bar so a folded window still warns', () => {
        // Folded, the title bar is all that is left; the stylesheet shows the mark only then,
        // so the flag is set here regardless and CSS decides when it is visible.
        applyHeaderWarning(root, true);
        assert.match(root.querySelector('.zanju-dh-header-warn').className,
            /zanju-dh-header-warn-on/);

        applyHeaderWarning(root, false);
        assert.doesNotMatch(root.querySelector('.zanju-dh-header-warn').className,
            /zanju-dh-header-warn-on/);
    });

    test('folding hides the body and flips the toggle', () => {
        applyFolded(root, true);
        assert.match(root.className, /zanju-dh-folded/);
        assert.equal(root.querySelector('.zanju-dh-fold').textContent, '+');

        applyFolded(root, false);
        assert.doesNotMatch(root.className, /zanju-dh-folded/);
        assert.equal(root.querySelector('.zanju-dh-fold').textContent, '−');
    });

    test('parks the window in a default corner when never positioned', () => {
        applyPosition(root, { x: -1, y: -1, viewportWidth: 0, viewportHeight: 0 });
        assert.equal(root.style.left, '24px');
        assert.ok(parseInt(root.style.top, 10) > 0);
    });

    test('restores a stored position', () => {
        globalThis.window = { innerWidth: 1920, innerHeight: 1080 };
        applyPosition(root, { x: 300, y: 400, viewportWidth: 1920, viewportHeight: 1080 });
        assert.equal(root.style.left, '300px');
        assert.equal(root.style.top, '400px');
        delete globalThis.window;
    });

    test('rescales a position captured at another resolution', () => {
        // WoT's UI scale is quantized per resolution bucket, so raw pixels from a 4K session
        // would strand the window off-screen at 1080p.
        globalThis.window = { innerWidth: 1920, innerHeight: 1080 };
        applyPosition(root, { x: 3000, y: 2000, viewportWidth: 3840, viewportHeight: 2160 });
        assert.equal(root.style.left, '1500px');
        assert.equal(root.style.top, '1000px');
        delete globalThis.window;
    });

    test('clamps a stored position inside the viewport', () => {
        globalThis.window = { innerWidth: 1920, innerHeight: 1080 };
        applyPosition(root, { x: 5000, y: 5000, viewportWidth: 1920, viewportHeight: 1080 });
        assert.ok(parseInt(root.style.left, 10) <= 1920);
        assert.ok(parseInt(root.style.top, 10) <= 1080);
        delete globalThis.window;
    });

    test('never moves the window mid-drag', () => {
        root._zanjuDhDragging = true;
        root.style.left = '111px';
        applyPosition(root, { x: 900, y: 900, viewportWidth: 0, viewportHeight: 0 });
        assert.equal(root.style.left, '111px');
    });
});

describe('model lookup', () => {
    afterEach(() => {
        delete globalThis.window;
    });

    test('finds our data on whichever sub-view was free', () => {
        // The inject lands on the first unclaimed hangar sub-view, so the window locates its
        // model by scanning rather than assuming a fixed one.
        const data = { snapshot: '{}' };
        globalThis.window = {
            subViews: {
                ids: () => [1, 2, 3],
                get: (id) => (id === 3 ? { model: { zanjuDhWindow: data } } : { model: {} }),
            },
        };
        assert.equal(findDataModel(), data);
    });

    test('returns null when no sub-view carries it', () => {
        globalThis.window = { subViews: { ids: () => [1], get: () => ({ model: {} }) } };
        assert.equal(findDataModel(), null);
    });

    test('tick does nothing without a model', () => {
        globalThis.window = { subViews: { ids: () => [], get: () => null } };
        assert.doesNotThrow(() => tick());
    });
});
