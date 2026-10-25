// Tests for the document side of a hover card window, card_host.js, run by `node --test`. The
// card is driven without an engine, so the startup chain stays off and the tests call render.

import assert from 'node:assert/strict';
import test from 'node:test';

const host = await import('../gameface/card_host.js');

class FakeNode {
    constructor() {
        this.className = '';
        this.attributes = {};
        this._rect = { width: 0, height: 0 };
    }

    setAttribute(name, value) {
        this.attributes[name] = String(value);
    }

    getAttribute(name) {
        return Object.prototype.hasOwnProperty.call(this.attributes, name) ? this.attributes[name] : null;
    }

    getBoundingClientRect() {
        return this._rect;
    }
}

function setUp(model) {
    const card = new FakeNode();
    const root = new FakeNode();
    globalThis.document = { documentElement: root, getElementById: () => card };
    globalThis.window = { model: model };
    return { card, root };
}

function tearDown() {
    delete globalThis.document;
    delete globalThis.window;
    delete globalThis.viewEnv;
    delete globalThis.requestAnimationFrame;
}

function payload(fields) {
    return { payload: JSON.stringify(Object.assign({ token: '1', reveal: false, lang: 'zh_cn' }, fields)) };
}

function startHost(renders) {
    return host.startCardHost({
        nodeId: 'card',
        shownClass: 'shown',
        hasContent: (data) => Boolean(data.content),
        render: (card, data, sameToken) => {
            renders.push([data.content, sameToken]);
            return !sameToken;
        },
    });
}

test('a new card is drawn hidden, with the language of the client', () => {
    const renders = [];
    const env = setUp(payload({ content: 'a' }));
    env.card.className = 'card mode';
    globalThis.requestAnimationFrame = () => {};
    try {
        startHost(renders).render(window.model);
        assert.deepEqual(renders, [['a', false]]);
        assert.equal(env.root.getAttribute('lang'), 'zh_cn');
        assert.equal(env.card.className, 'card mode');
    } finally {
        tearDown();
    }
});

test('the reveal flag of the card on screen shows it and keeps its other classes', () => {
    const renders = [];
    const env = setUp(payload({ content: 'a' }));
    env.card.className = 'card mode';
    globalThis.requestAnimationFrame = () => {};
    try {
        const card = startHost(renders);
        card.render(window.model);
        card.render(payload({ content: 'a', reveal: true }));
        assert.deepEqual(renders, [['a', false], ['a', true]]);
        assert.equal(env.card.className, 'card mode shown');
    } finally {
        tearDown();
    }
});

test('before the first hover, nothing is drawn but a size is still published', () => {
    const renders = [];
    const resized = [];
    const env = setUp({ payload: '' });
    env.card._rect = { width: 380.2, height: 100 };
    globalThis.viewEnv = { resizeViewPx: (width, height) => resized.push([width, height]) };
    try {
        startHost(renders).render(window.model);
        assert.deepEqual(renders, []);
        assert.deepEqual(resized, [[381, 100]]);
    } finally {
        tearDown();
    }
});

test('a size goes to Python once, with the token of its card', () => {
    const sized = [];
    const env = setUp({ payload: '', onSized: (arg) => sized.push(arg) });
    env.card._rect = { width: 400, height: 300 };
    globalThis.viewEnv = { resizeViewPx: () => {} };
    try {
        const card = startHost([]);
        card.publishSize('4');
        card.publishSize('4');
        assert.deepEqual(sized, [{ token: '4', width: 400, height: 300 }]);
    } finally {
        tearDown();
    }
});

test('setClass adds and removes one class only', () => {
    const node = new FakeNode();
    node.className = 'a b';
    host.setClass(node, 'c', true);
    assert.equal(node.className, 'a b c');
    host.setClass(node, 'a', false);
    assert.equal(node.className, 'b c');
});
