# Zanju's Premium Time

### Shows exactly how much premium time you have left, right on the lobby header.

The game's own Premium Account header button only shows a coarse day count — "3 d" tells
you nothing about whether that means three days or three days and 23 hours. This mod
integrates into that existing UI instead of adding its own window:

- **Header counter** — while Premium Account is running, its header button shows a live
  countdown that gets more precise as time runs out: it keeps the two largest units still
  worth showing, so `3d 05h` with days to go and `5m 12s` in the final hour. When premium
  is not running, the button keeps the game's default label.
- **Tooltip end time** — the button's hover tooltip gains the exact end date and time, to
  the second, with the UTC offset.

There is nothing to configure: the mod has no settings and keeps no config file.

### Requirements

The header counter needs the
[OpenWG Gameface](https://gitlab.com/openwg/wot.gameface) library
(`net.openwg.gameface`, bundled with popular modpacks such as Aslain's). Without it the
mod still works, but only the tooltip end time is shown.

## Translations

Reference language `en` defines 5 strings. Translations are community-maintained and may lag behind; see [Translating](../../docs/translating.md) to add or update one, then regenerate this table with `zwm lint i18n`.

| Language | Coverage | Missing |
| --- | --- | --- |
| `pl` | 100% (5/5) | 0 |

## Install And Use

If you already have the prepared mod zip file, follow the general install path in
[Installing Mods](../../docs/installing-mods.md).

## Build From Source

For the general build/toolchain workflow, see
[Building From Source](../../docs/building-from-source.md).

## Develop

For the wider repository workflow, see:

- [Developing Mods](../../docs/developing-mods.md)
- [Architecture](../../docs/architecture.md)
- [Technical Reference](../../docs/reference/README.md)

### How it hooks the game UI

The lobby header is a Gameface (HTML/JS) view whose text is rendered by the game's JS
bundle, not by Python, while its tooltip is a classic Python-built one. The mod therefore
works on both sides:

- **Header counter** — `UserAccountModel._initialize` is wrapped to attach an OpenWG
  `ModInjectModel` (which makes the OpenWG bootstrap load `header_patch.js` into the
  header document) plus a small `zanjuPtHeader` data model with localized unit labels
  and the client↔server clock offset. The injected JS computes the countdown from the
  game's own `subscriptions.premiumAccount.expiryTime` and rewrites the button label.
- **Tooltip end time** — a classic Python blocks tooltip
  (`AmmunitionEmptyBlockTooltipData` with the `#tooltips:header/premium_buy` alias);
  `_packBlocks` is wrapped to append the end-time text block for that alias only.

Two things the JS side has to respect, both of which caused visible bugs before they were
understood:

- The label lives in a `<span>` inside `div[class*="Premiums_text"]`. Writing
  `textContent` on the div deletes that span, and React — still holding a reference to the
  detached node — writes every later update off-screen, freezing the label.
- The client only learns that premium ended when the server pushes a new premium mask, so
  the view model can still report `Active` after the expiry timestamp has passed. The
  counter holds at zero rather than handing the button back early, which would repaint the
  label captured while the subscription was still running.

### Data source

`itemsCache.items.stats` (`isPremium`, `activePremiumExpiryTime`) — the same fields the
game's own header presenter uses. The header counter reads `expiryTime` / `state` straight
from the game's header view model.

WoT Plus is deliberately not covered; see
[WoT Plus Subscriptions](../../docs/reference/wot-plus-subscriptions.md) for its data model
and what re-adding it would involve.
