// The bridge between a mod script in a garage document and its data model on the Python side.
// The build copies this file beside the scripts of each mod that takes it.
//
// - `find` gives the data model. It scans the sub-views of the document, because the model rides
//   on a sub-view whose ID the script cannot know. The last ID is tried first: once pushes are
//   wired up, `find` runs on every model write anywhere in the document, so it must stay one
//   lookup and not a scan.
// - `follow` subscribes to `viewEnv.onDataChanged`, the engine's own signal that a model in this
//   document was written. OpenWG's own ModelObserver subscribes to it as well. Python writes a
//   property the moment something changes, but a write is no event on this side: without this,
//   the script would see the change only on its next poll. The subscription names one sub-view,
//   and the garage can replace that sub-view, so it is renewed whenever the ID moves. Getting this
//   wrong makes the script late, not silent, because the poll still runs.
// - `setPollRate` runs the poll, which stays as a backstop. A mod polls fast until `pushSeen`
//   says that a push arrived, and slow after.
// - `invokeCommand` calls a command of the data model.
//
// Each mod keeps its flags on `document` under a prefix of its own, so a handler is registered
// once per document even when the module is evaluated again for another sub-view.

import { unwrap } from './helpers.js';

function createBridge(options) {
    const dataProperty = options.dataProperty;
    const onChange = options.onChange;
    const log = options.log || function () {};
    const flags = {
        bound: options.flagPrefix + 'PushBound',
        resId: options.flagPrefix + 'PushResId',
        seen: options.flagPrefix + 'PushSeen',
    };
    let dataResId = null;
    let pollTimer = null;
    let pollMs = null;

    function modelOn(id) {
        const view = window.subViews.get(id);
        const model = view && view.model;
        return model && model[dataProperty] ? model[dataProperty] : null;
    }

    function find() {
        if (typeof window === 'undefined' || !window.subViews) {
            return null;
        }
        if (dataResId !== null) {
            const known = modelOn(dataResId);
            if (known) {
                return known;
            }
        }
        const ids = window.subViews.ids();
        for (let i = 0; i < ids.length; i += 1) {
            const model = modelOn(ids[i]);
            if (model) {
                dataResId = ids[i];
                return model;
            }
        }
        dataResId = null;
        return null;
    }

    function onPush() {
        document[flags.seen] = true;
        onChange();
    }

    // Subscribes to pushes for the sub-view that `find` found last. True when it subscribed now.
    function follow() {
        if (dataResId === null || document[flags.resId] === dataResId) {
            return false;
        }
        if (typeof engine === 'undefined' || typeof viewEnv === 'undefined') {
            return false;
        }
        try {
            if (!document[flags.bound]) {
                // The handler belongs to the document, not to a view, so it is registered once.
                // A second registration would run the change handler twice for each push.
                engine.on('viewEnv.onDataChanged', onPush);
                document[flags.bound] = true;
            }
            // The third argument asks for descendants too: the data lives on a child model of the
            // sub-view, not on the sub-view's own model.
            viewEnv.addDataChangedCallback('model', dataResId, true);
            document[flags.resId] = dataResId;
            log('subscribed to model updates on sub-view ' + dataResId);
            return true;
        } catch (e) {
            // Never fatal: the poll still gets there, only later.
            log('could not subscribe to model updates, falling back to polling (' + e + ')');
            return false;
        }
    }

    function pushSeen() {
        return Boolean(document[flags.seen]);
    }

    function setPollRate(intervalMs) {
        if (intervalMs === pollMs) {
            return;
        }
        pollMs = intervalMs;
        if (pollTimer !== null) {
            clearInterval(pollTimer);
        }
        pollTimer = setInterval(onChange, intervalMs);
    }

    return {
        find: find,
        follow: follow,
        pushSeen: pushSeen,
        setPollRate: setPollRate,
        resId: function () { return dataResId; },
    };
}

// Calls the command `name` of a data model with one map argument. Wulf exposes a command as a
// callable on the model, and which of the wrapped proxy or its unwrapped value carries it differs
// across builds, so this tries both. Gameface rejects a bare scalar as "not a map".
function invokeCommand(data, name, arg, log) {
    const write = log || function () {};
    try {
        let host = null;
        if (data && typeof data[name] === 'function') {
            host = data;
        } else {
            const inner = unwrap(data);
            if (inner && typeof inner[name] === 'function') {
                host = inner;
            }
        }
        if (!host) {
            write('command missing: ' + name);
            return;
        }
        host[name](arg || {});
    } catch (e) {
        write('command failed: ' + name + ' (' + e + ')');
    }
}

export { createBridge, invokeCommand };
