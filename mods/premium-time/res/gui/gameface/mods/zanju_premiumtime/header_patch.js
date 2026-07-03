// Zanju Premium Time — live remaining-time counters on the lobby header buttons.
//
// Injected into the lobby header's Gameface document by net.openwg.gameface (see
// src/zanju_pt/gameface/header_inject.py). The Premium Account button normally shows
// "N d" / "Upgrade" and the WoT Plus button "Activate" / "Manage"; while a subscription
// is running we replace that label with a live "NNd NNh NNm" countdown computed from
// the game's own view model. Inactive subscriptions keep the game's default label.
//
// React owns these nodes and rewrites them on its own re-renders, so we re-apply on a
// short interval and re-capture the original label whenever React has repainted it.

const APPLY_INTERVAL_MS = 500;

const overrides = {
    premium: { original: null, last: null },
    wotPlus: { original: null, last: null },
};

function unwrap(value) {
    return value && typeof value === 'object' && 'value' in value ? value.value : value;
}

function findAccountModel() {
    const ids = window.subViews.ids();
    for (const id of ids) {
        const view = window.subViews.get(id);
        const model = view && view.model;
        if (model && model.zanjuPtHeader && model.subscriptions) {
            return model;
        }
    }
    return null;
}

function labelOf(testId) {
    const button = document.querySelector('[data-test-id="' + testId + '"]');
    return button ? button.querySelector('div[class*="Premiums_text"]') : null;
}

function two(n) {
    return n < 10 ? '0' + n : '' + n;
}

function formatRemaining(seconds, cfg) {
    const total = Math.max(0, Math.floor(seconds));
    const days = Math.floor(total / 86400);
    const hours = Math.floor((total % 86400) / 3600);
    const minutes = Math.floor((total % 3600) / 60);
    return days + unwrap(cfg.dayUnit)
        + ' ' + two(hours) + unwrap(cfg.hourUnit)
        + ' ' + two(minutes) + unwrap(cfg.minuteUnit);
}

function setLabel(key, text) {
    const el = labelOf(key);
    const st = overrides[key];
    if (!el) {
        st.original = null;
        st.last = null;
        return;
    }
    if (text === null) {
        // Restore the game's label if ours is still on screen; otherwise React already did.
        if (st.last !== null && el.textContent === st.last && st.original !== null) {
            el.textContent = st.original;
        }
        st.original = null;
        st.last = null;
        return;
    }
    if (el.textContent !== st.last) {
        // React repainted since our last write: remember its label as the restore target.
        st.original = el.textContent;
    }
    if (el.textContent !== text) {
        el.textContent = text;
    }
    st.last = text;
}

function tick() {
    const model = findAccountModel();
    if (!model) {
        return;
    }
    const cfg = model.zanjuPtHeader;
    const subs = model.subscriptions;
    if (!cfg || !subs || !subs.premiumAccount || !subs.wotPlus) {
        return;
    }
    const now = Date.now() / 1000 + (Number(unwrap(cfg.timeOffset)) || 0);

    const premiumState = unwrap(subs.premiumAccount.state);
    const premiumExpiry = Number(unwrap(subs.premiumAccount.expiryTime)) || 0;
    if (premiumState === 'Active' && premiumExpiry > now) {
        setLabel('premium', formatRemaining(premiumExpiry - now, cfg));
    } else {
        setLabel('premium', null);
    }

    const wotPlusState = unwrap(subs.wotPlus.state);
    const wotPlusExpiry = Number(unwrap(subs.wotPlus.expiryTime)) || 0;
    if ((wotPlusState === 'Active' || wotPlusState === 'Cancelled') && wotPlusExpiry > now) {
        setLabel('wotPlus', formatRemaining(wotPlusExpiry - now, cfg));
    } else {
        setLabel('wotPlus', null);
    }
}

console.log('[zanju.premiumtime] header_patch.js loaded');
tick();
setInterval(tick, APPLY_INTERVAL_MS);
