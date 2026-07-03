// Zanju Premium Time — exact end time in the WoT Plus header-button tooltip.
//
// Loaded into the mono/hangar tooltips document via our shadowed tooltips.html (see
// res/gui/gameface/_dist/.../tooltips/tooltips.html). The tooltip's content view is the
// document ROOT, so its ParamTooltipModel — carrying our `zanjuPtTooltip` data attached
// in src/zanju_pt/gameface/tooltip_inject.py — is `window.model`. Once the WoT Plus
// header widget tooltip has rendered, a pre-formatted, localized "Ends on: <date time>"
// section is appended to its content. Other tooltip types are left untouched.

const RETRY_MS = 100;
const MAX_ATTEMPTS = 50;
const SECTION_CLASS = 'zanju-pt-ends-on';

let attempts = 0;

function unwrap(value) {
    return value && typeof value === 'object' && 'value' in value ? value.value : value;
}

function findTooltipModel() {
    const root = window.model;
    if (root && root.zanjuPtTooltip) {
        return root;
    }
    if (window.subViews) {
        const ids = window.subViews.ids();
        for (const id of ids) {
            const view = window.subViews.get(id);
            const model = view && view.model;
            if (model && model.zanjuPtTooltip) {
                return model;
            }
        }
    }
    return null;
}

function retry() {
    attempts += 1;
    if (attempts < MAX_ATTEMPTS) {
        setTimeout(tryAppend, RETRY_MS);
    }
}

function tryAppend() {
    let model = null;
    try {
        model = findTooltipModel();
    } catch (e) {
        return retry(); // Engine bindings may not be ready yet.
    }
    if (!model) {
        return retry();
    }
    const type = unwrap(model.type);
    if (!type) {
        return retry(); // The type is set shortly after the tooltip view is created.
    }
    if (type !== 'wot_plus_header_widget') {
        return;
    }
    const label = unwrap(model.zanjuPtTooltip.wotPlusEndsOnLabel);
    const value = unwrap(model.zanjuPtTooltip.wotPlusEndsOnValue);
    if (!value) {
        return;
    }
    const wrapper = document.querySelector('div[class*="Index_wrapper"]');
    if (!wrapper) {
        return retry(); // The template renders a few frames after the document loads.
    }
    if (wrapper.querySelector('.' + SECTION_CLASS)) {
        return;
    }
    const section = document.createElement('div');
    section.className = SECTION_CLASS;
    section.style.marginTop = '0.5em';
    section.style.textAlign = 'center';

    const labelSpan = document.createElement('span');
    labelSpan.textContent = label + ' ';
    labelSpan.style.opacity = '0.8';
    section.appendChild(labelSpan);

    const valueSpan = document.createElement('span');
    valueSpan.textContent = value;
    // Same gold the game's own UI uses (defined in the document's lib.css).
    valueSpan.style.color = 'var(--color-currency-gold, #fecc88)';
    section.appendChild(valueSpan);

    wrapper.appendChild(section);
}

console.log('[zanju.premiumtime] tooltip_patch.js loaded');
tryAppend();
