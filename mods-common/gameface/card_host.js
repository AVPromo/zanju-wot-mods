// The document side of a hover card in a window that a mod owns: the half that `card_window.py`
// in mods-common talks to. The build copies this file beside the scripts of each mod that takes
// it, and the card script of the mod starts it with the parts that are its own.
//
// The handshake, which campaign-tracker measured first:
//
// - The model is the root model of the document, `window.model`, and updates arrive through
//   `engine.on('viewEnv.onDataChanged')` with `viewEnv.addDataChangedCallback`. The model API of
//   the upstream guide, `viewEnv.getViewModel`, does not exist.
// - Python sends one JSON payload with a token for each card. A payload with the token of the
//   card on screen is Python changing one field, not a different card, and rebuilding the card
//   then would throw away a measurement that is already correct.
// - The card paints nothing until Python has placed the window, and Python cannot place it
//   before it knows the size. A hidden Wulf window runs no frames, so `requestAnimationFrame`
//   never fires there and the card could never measure itself. Python therefore shows the window
//   first, at the last place it had, and the card stays transparent until Python reveals it.
// - The card measures itself after layout, never in the frame that changed the DOM.
//   `getBoundingClientRect` right after a build reports the layout from before it, so a card
//   measured then came out short and lost its last rows. It is measured two frames later, and
//   once more a frame after that, to catch a late settle such as a font that loads.
//
// The size goes to the native surface with `viewEnv.resizeViewPx`, and to Python with the
// `onSized` command, together with the token, so that Python can ignore a size of a card that
// the pointer has already left.

import { parseJson, unwrap } from './helpers.js';

// A standalone view owns its whole document, so its model is the root one.
const ROOT_RES_ID = 0;

function nextFrame() {
    return new Promise(function (resolve) { requestAnimationFrame(resolve); });
}

function waitForDomBuilt() {
    return new Promise(function (resolve) {
        if (window.isDomBuilt) {
            resolve();
            return;
        }
        engine.on('self.onDomBuilt', resolve);
    });
}

function readModel() {
    return (typeof window !== 'undefined' && window.model) || null;
}

// Calls a command of the root model. A command can sit on the proxy or on its value.
function callCommand(model, name, arg, log) {
    const target = model && model[name];
    try {
        if (typeof target === 'function') {
            target.call(model, arg || {});
        } else if (target && typeof target.value === 'function') {
            target.value.call(target, arg || {});
        } else if (log) {
            log('the ' + name + ' command is missing on the model');
        }
    } catch (error) {
        if (log) {
            log('the ' + name + ' command failed: ' + error);
        }
    }
}

// The client's own documents set `lang` on the root element when they start, and a card style
// sheet reads it to select the font. A document of a mod does not run that code, so Python sends
// the code. With no `lang`, the card stays on PFDINMax, which draws nothing for Chinese,
// Japanese, Korean, Thai or Vietnamese text.
function applyLanguage(lang) {
    const root = document.documentElement;
    if (lang && root.getAttribute('lang') !== lang) {
        root.setAttribute('lang', lang);
    }
}

// Adds or removes one class and keeps every other class of the node.
function setClass(node, name, on) {
    const classes = String(node.className || '').split(' ').filter(function (item) {
        return item && item !== name;
    });
    if (on) {
        classes.push(name);
    }
    node.className = classes.join(' ');
}

// Starts the card. `options`:
//
// - `nodeId`: the ID of the card element, and `shownClass`: the class that reveals it.
// - `hasContent(payload)`: false before the first hover, when Python has sent no card yet.
// - `render(card, payload, sameToken)`: draws the card. Returns true when it built the card
//   again, and the card then takes a new measurement, or false when it only changed it in place.
// - `fit(card)`, optional: sizes parts of the card to their content once the layout has settled.
//   The card then takes one more frame before it is measured.
// - `onScale(card)`, optional: runs before the card measures again for a new interface scale.
// - `everySecond(card, payload)`, optional: runs once a second while the window lives.
// - `log`.
//
// Returns the functions that the tests drive.
function startCardHost(options) {
    const log = options.log || function () {};
    let lastPublished = '';
    // Bumped for each measurement, so a measurement for a card the pointer has already left
    // cannot publish over the current one.
    let measureGeneration = 0;
    let renderedToken = '';
    let currentPayload = null;

    function cardNode() {
        return document.getElementById(options.nodeId);
    }

    function render(model) {
        const card = cardNode();
        if (!card || !model) {
            return;
        }
        const payload = parseJson(unwrap(model.payload), 'card payload', log);
        if (!payload || !options.hasContent(payload)) {
            // Python hides the window rather than sending an empty card, so this is only reached
            // before the first hover. Still publish a size, because the engine gives the view a
            // limited time to report one and falls back to a default size if nothing arrives.
            publishSize('');
            return;
        }
        currentPayload = payload;
        const token = String(payload.token || '');
        const sameToken = token === renderedToken;
        // Before the build, so that the first layout and the size measured from it use the font.
        applyLanguage(payload.lang);
        if (!options.render(card, payload, sameToken)) {
            setClass(card, options.shownClass, Boolean(payload.reveal));
            return;
        }
        // A new card is never painted where the last one stood. Python reveals it once it has
        // moved the window, which it can only do once this render has been measured. A new build
        // of the card on screen keeps it revealed: the window has not moved.
        setClass(card, options.shownClass, sameToken && Boolean(payload.reveal));
        renderedToken = token;
        scheduleMeasure(token);
    }

    function scheduleMeasure(token) {
        measureGeneration += 1;
        const generation = measureGeneration;
        let steps = nextFrame().then(nextFrame);
        if (options.fit) {
            steps = steps.then(function () {
                const card = cardNode();
                if (generation === measureGeneration && card) {
                    options.fit(card);
                }
                return nextFrame();
            });
        }
        return steps
            .then(function () {
                if (generation !== measureGeneration) {
                    return null;
                }
                publishSize(token);
                return nextFrame();
            })
            .then(function () {
                if (generation === measureGeneration) {
                    publishSize(token);
                }
            })
            .catch(function (error) { log('card measurement failed: ' + error); });
    }

    function publishSize(token) {
        const card = cardNode();
        if (!card) {
            return;
        }
        const rect = card.getBoundingClientRect();
        const width = Math.ceil(rect.width);
        const height = Math.ceil(rect.height);
        if (!(width > 0 && height > 0)) {
            return;
        }
        try {
            viewEnv.resizeViewPx(width, height);
        } catch (error) {
            log('resizeViewPx failed: ' + error);
        }
        const key = token + ':' + width + 'x' + height;
        if (key === lastPublished) {
            return;
        }
        lastPublished = key;
        log('card measured ' + width + 'x' + height + ' (token ' + token + ')');
        callCommand(readModel(), 'onSized', { token: String(token || ''), width: width, height: height }, log);
    }

    function onScale() {
        const card = cardNode();
        if (card && options.onScale) {
            options.onScale(card);
        }
        scheduleMeasure(renderedToken);
    }

    if (typeof engine !== 'undefined') {
        engine.whenReady
            .then(waitForDomBuilt)
            // Two frames, so that the first render meets a settled layout.
            .then(nextFrame)
            .then(nextFrame)
            .then(function () {
                render(readModel());
                engine.on('viewEnv.onDataChanged', function () { render(readModel()); });
                // Every size of a card is in `rem`, so a new interface scale lays the card out
                // again, and the published size has to follow.
                engine.on('self.onScaleUpdated', onScale);
                viewEnv.addDataChangedCallback('model', ROOT_RES_ID, true);
                if (options.everySecond) {
                    // The window lives only while its card is on screen, so this ends with it.
                    setInterval(function () {
                        const card = cardNode();
                        if (card && currentPayload) {
                            options.everySecond(card, currentPayload);
                        }
                    }, 1000);
                }
                log('card window ready');
            })
            .catch(function (error) { log('card startup failed: ' + error); });
    }

    return { publishSize: publishSize, render: render, scheduleMeasure: scheduleMeasure };
}

export { applyLanguage, callCommand, nextFrame, readModel, setClass, startCardHost, waitForDomBuilt };
