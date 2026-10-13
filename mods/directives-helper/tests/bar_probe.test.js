// Tests for the probe that measures the garage's lobby bars from inside their own documents.
//
// Run via `zwm test directives-helper`. The module auto-starts only when a Gameface view
// registry is present, so importing it here neither measures anything nor starts a timer.

import { test, describe, beforeEach, afterEach } from 'node:test';
import assert from 'node:assert/strict';

import { findBarRoot, measure, tick } from '../res/gui/gameface/mods/zanju_directives/bar_probe.js';

function node(className, children = [], rect = null) {
    const element = { className, children, parentNode: null };
    for (const child of children) {
        child.parentNode = element;
    }
    if (rect) {
        element.getBoundingClientRect = () => rect;
    }
    return element;
}

function rect(left, top, width, height) {
    return { left, top, width, height, right: left + width, bottom: top + height };
}

// The header's shape: a media wrapper, the App root, and App elements inside the root.
function headerTree(appRect) {
    const inner = node('App_leftSide_6c377b80', [node('App_userProfile_7aef8044')]);
    const app = node('App_fe4b7101 App_base__battleButtonVisible_0', [inner], appRect);
    return {
        app,
        body: node('', [node('', [node('media-wrapper mediaLarge mediaLargeWidth', [app])])]),
    };
}

describe('findBarRoot', () => {
    test('finds the outermost App element, not one inside it', () => {
        const { app, body } = headerTree(rect(0, 0, 1920, 82));
        assert.equal(findBarRoot(body, 'App_'), app);
    });

    test('does not take a component whose name only starts with App', () => {
        const body = node('', [node('AppHeader_title_1234')]);
        assert.equal(findBarRoot(body, 'App_'), null);
    });

    test('finds the footer element inside the footer\'s full-height App root', () => {
        // The footer's App root fills the whole view, 250rem above the bar included. The element
        // its view is sized from is `App_footer`, inside it.
        const footer = node('App_footer_8633140e App_footer__oldStyle_ed955e9f');
        const body = node('', [node('media-wrapper', [node('App_cabb9f2f', [footer])])]);
        assert.equal(findBarRoot(body, 'App_footer_'), footer);
    });

    test('survives an SVG element, whose className is not a string', () => {
        const svg = { className: { baseVal: 'App_icon' }, children: [] };
        assert.equal(findBarRoot(node('', [svg]), 'App_'), null);
    });
});

describe('measure and report', () => {
    const realConsoleError = console.error;
    let reports;
    let tree;

    beforeEach(() => {
        console.error = () => {};
        reports = [];
        tree = headerTree(rect(0, 0, 1920, 82));
        const data = { rootClass: 'App_', reportBar: (arg) => reports.push(arg) };
        globalThis.document = { body: tree.body };
        globalThis.window = {
            innerWidth: 1920,
            innerHeight: 1080,
            subViews: { ids: () => [7], get: () => ({ model: { zanjuDhBarProbe: data } }) },
        };
    });

    afterEach(() => {
        console.error = realConsoleError;
        delete globalThis.document;
        delete globalThis.window;
        delete globalThis.viewEnv;
    });

    test('reports the App root in screen pixels', () => {
        globalThis.viewEnv = { remToPx: (rem) => rem * 2, getViewGlobalPositionRem: () => ({ x: 0, y: 5 }) };
        assert.deepEqual(measure('App_'), { left: 0, top: 10, right: 1920, bottom: 92, scale: 2 });
    });

    test('rounds the bottom edge up, so the window never ends a pixel under the strip', () => {
        tree.app.getBoundingClientRect = () => rect(0, 0, 1920, 82.25);
        assert.equal(measure('App_').bottom, 83);
    });

    test('measures nothing before the App root has a size', () => {
        tree.app.getBoundingClientRect = () => rect(0, 0, 1920, 0);
        assert.equal(measure('App_'), null);
    });

    test('a fault while measuring stays inside the header document', () => {
        // The poll runs in the client's own document for the whole session.
        tree.app.getBoundingClientRect = () => {
            throw new Error('no layout');
        };
        assert.doesNotThrow(() => tick());
        assert.equal(reports.length, 0);
    });

    test('reports once per change, not on every poll', () => {
        tick();
        tick();
        assert.equal(reports.length, 1);
        assert.equal(reports[0].bottom, 82);

        tree.app.getBoundingClientRect = () => rect(0, 0, 2560, 88);
        tick();
        assert.equal(reports.length, 2);
        assert.equal(reports[1].bottom, 88);
    });
});
