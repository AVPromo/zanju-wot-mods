// Tests for the shared plumbing scripts: helpers.js, countdown.js and model_bridge.js, run by
// `node --test`. The fakes stand in only for what the scripts call.

import assert from 'node:assert/strict';
import test from 'node:test';

const helpers = await import('../gameface/helpers.js');
const countdown = await import('../gameface/countdown.js');
const modelBridge = await import('../gameface/model_bridge.js');

const UNITS = { dayUnit: 'd', hourUnit: 'h', minuteUnit: 'm', secondUnit: 's' };

function withGlobals(values, body) {
    const saved = {};
    for (const name of Object.keys(values)) {
        saved[name] = globalThis[name];
        globalThis[name] = values[name];
    }
    try {
        return body();
    } finally {
        for (const name of Object.keys(values)) {
            if (saved[name] === undefined) {
                delete globalThis[name];
            } else {
                globalThis[name] = saved[name];
            }
        }
    }
}

test('a log line carries the tag of its mod', () => {
    const lines = [];
    const original = console.error;
    console.error = (line) => lines.push(line);
    try {
        helpers.createLog('zanju.test')('hello');
    } finally {
        console.error = original;
    }
    assert.deepEqual(lines, ['[zanju.test] hello']);
});

test('a wrapped Wulf value is unwrapped, and a plain one is left alone', () => {
    assert.equal(helpers.unwrap({ value: 3 }), 3);
    assert.equal(helpers.unwrap(3), 3);
    assert.equal(helpers.unwrap(null), null);
});

test('broken JSON is null, and the log names what it was', () => {
    const lines = [];
    assert.deepEqual(helpers.parseJson('{"a":1}', 'snapshot', (line) => lines.push(line)), { a: 1 });
    assert.equal(helpers.parseJson('', 'snapshot', (line) => lines.push(line)), null);
    assert.equal(helpers.parseJson('{oops', 'snapshot', (line) => lines.push(line)), null);
    assert.equal(lines.length, 1);
    assert.match(lines[0], /^could not parse the snapshot: /);
    // No log function, no line, and still no throw.
    assert.equal(helpers.parseJson('{oops', 'snapshot'), null);
});

test('the countdown shows the two largest units that carry a value', () => {
    assert.equal(countdown.formatRemaining(5 * 86400 + 3 * 3600 + 59, UNITS), '5d 03h');
    assert.equal(countdown.formatRemaining(2 * 3600 + 11 * 60 + 5, UNITS), '2h 11m');
    assert.equal(countdown.formatRemaining(5 * 60 + 2, UNITS), '5m 02s');
    assert.equal(countdown.formatRemaining(45, UNITS), '45s');
    assert.equal(countdown.formatRemaining(86400 + 59, UNITS), '1d 00h');
    assert.equal(countdown.formatRemaining(-3, UNITS), '0s');
});

test('the countdown takes Wulf values and falls back to English letters', () => {
    const wrapped = { dayUnit: { value: 'д' }, hourUnit: { value: 'ч' } };
    assert.equal(countdown.formatRemaining(86400 + 3600, wrapped), '1д 01ч');
    assert.equal(countdown.formatRemaining(61, {}), '1m 01s');
    assert.equal(countdown.formatRemaining(61, null), '1m 01s');
    assert.equal(countdown.formatRemaining(3 * 86400 + 3 * 3600 + 3 * 60, UNITS, 3), '3d 03h 03m');
});

function bridgeFor(views, onChange) {
    return modelBridge.createBridge({
        dataProperty: 'zanjuTest',
        flagPrefix: '__zanjuTest',
        onChange: onChange || (() => {}),
    });
}

test('the bridge finds the data model on whichever sub-view carries it', () => {
    const data = { snapshot: '{}' };
    const views = { 3: { model: {} }, 8: { model: { zanjuTest: data } } };
    withGlobals({ window: { subViews: { ids: () => [3, 8], get: (id) => views[id] } }, document: {} }, () => {
        const bridge = bridgeFor();
        assert.equal(bridge.find(), data);
        assert.equal(bridge.resId(), 8);
        // A moved model is still found, and the ID follows it.
        views[9] = views[8];
        delete views[8];
        window.subViews.ids = () => [3, 9];
        assert.equal(bridge.find(), data);
        assert.equal(bridge.resId(), 9);
        window.subViews.ids = () => [3];
        delete views[9];
        assert.equal(bridge.find(), null);
        assert.equal(bridge.resId(), null);
    });
});

test('the push subscription follows the sub-view when the garage replaces it', () => {
    // The regression from campaign-tracker: the garage rebuilt the sub-view that the model rode
    // on, and the subscription kept naming the destroyed one, so every push after the first went
    // nowhere and everything fell back to the slow poll.
    const subscribed = [];
    const handlers = [];
    const model = { zanjuTest: { snapshot: '{}' } };
    const globals = {
        engine: { on: (name, handler) => handlers.push(handler) },
        viewEnv: { addDataChangedCallback: (_kind, id) => subscribed.push(id) },
        window: { subViews: { ids: () => [7], get: (id) => (id === 7 ? { model } : null) } },
        document: {},
    };
    withGlobals(globals, () => {
        let changes = 0;
        const bridge = bridgeFor(null, () => { changes += 1; });
        bridge.find();
        assert.equal(bridge.follow(), true);
        assert.deepEqual(subscribed, [7]);
        // Nothing moved, so nothing is renewed: this runs on every tick.
        assert.equal(bridge.follow(), false);

        window.subViews = { ids: () => [9], get: (id) => (id === 9 ? { model } : null) };
        bridge.find();
        assert.equal(bridge.follow(), true);
        assert.deepEqual(subscribed, [7, 9]);
        // The engine-level handler belongs to the document and is registered once, or each push
        // would run the change handler once per registration.
        assert.equal(handlers.length, 1);

        assert.equal(bridge.pushSeen(), false);
        handlers[0]();
        assert.equal(bridge.pushSeen(), true);
        assert.equal(changes, 1);
    });
});

test('with no engine, the bridge stays on its poll', () => {
    const model = { zanjuTest: {} };
    withGlobals({ window: { subViews: { ids: () => [1], get: () => ({ model }) } }, document: {} }, () => {
        const bridge = bridgeFor();
        bridge.find();
        assert.equal(bridge.follow(), false);
    });
});

test('a command is called on the proxy or on its value, with one map argument', () => {
    const calls = [];
    const lines = [];
    const log = (line) => lines.push(line);
    modelBridge.invokeCommand({ act: (arg) => calls.push(['proxy', arg]) }, 'act', { a: 1 }, log);
    modelBridge.invokeCommand({ value: { act: (arg) => calls.push(['value', arg]) } }, 'act', null, log);
    modelBridge.invokeCommand({}, 'act', {}, log);
    modelBridge.invokeCommand({ act: () => { throw new Error('boom'); } }, 'act', {}, log);
    assert.deepEqual(calls, [['proxy', { a: 1 }], ['value', {}]]);
    assert.deepEqual(lines, ['command missing: act', 'command failed: act (Error: boom)']);
});
