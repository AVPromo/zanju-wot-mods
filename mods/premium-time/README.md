# Zanju's Premium Time

### Shows exactly how much premium time you have left, right on the lobby header.

The game's own header buttons only show a coarse day count for Premium Account and an
"Activate" / "Manage" label for WoT Plus. This mod integrates into that existing UI
instead of adding its own window:

- **Header counters** — while a subscription is running, its header button shows a live
  `NNd NNh NNm` countdown. Inactive subscriptions keep the game's default label.
- **Tooltip end time** — the hover tooltips of both buttons gain the exact end date and
  time (to the second, with the UTC offset) of the subscription.

Covers the two independent premium subscriptions:

- **Premium Account** — the classic WoT premium time.
- **WoT Plus / WoT Plus Pro** — the renewable subscription.

There is nothing to configure: the mod has no settings and keeps no config file.

### Requirements

The header counters and the WoT Plus tooltip line need the
[OpenWG Gameface](https://gitlab.com/openwg/wot.gameface) library
(`net.openwg.gameface`, bundled with popular modpacks such as Aslain's). Without it the
mod still works, but only the Premium Account tooltip line is shown.

## Translations

Reference language `en` defines 4 strings. Translations are community-maintained and may lag behind; see [Translating](../../docs/translating.md) to add or update one, then regenerate this table with `zwm lint i18n`.

| Language | Coverage | Missing |
| --- | --- | --- |
| `pl` | 100% (4/4) | 0 |

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

The lobby header and its tooltips are Gameface (HTML/JS) views; their texts are rendered
by the game's JS bundles, not by Python. The mod therefore works on both sides:

- **Header counters** — `UserAccountModel._initialize` is wrapped to attach an OpenWG
  `ModInjectModel` (which makes the OpenWG bootstrap load `header_patch.js` into the
  header document) plus a small `zanjuPtHeader` data model with localized unit labels
  and the client↔server clock offset. The injected JS computes the countdowns from the
  game's own `subscriptions.*.expiryTime` and rewrites the button labels, restoring the
  originals when a subscription is inactive.
- **WoT Plus tooltip** — the hover tooltip is a param tooltip (`ParamTooltipModel`)
  rendering the `wot_plus_header_widget` template. Its content view is the tooltip
  document's root (`window.model`, not a subview), which the OpenWG injector never
  scans — so the mod ships a shadowed copy of the document shell
  (`res/gui/gameface/_dist/.../tooltips/tooltips.html`, refresh it from the game
  package on client updates) that loads `tooltip_patch.js` directly. The wrapped model
  carries a pre-formatted, localized "Ends on: …" line (computed fresh on every hover)
  that the script appends to the tooltip content.
- **Premium Account tooltip** — a classic Python blocks tooltip
  (`AmmunitionEmptyBlockTooltipData` with the `#tooltips:header/premium_buy` alias);
  `_packBlocks` is wrapped to append the end-time text block for that alias only.

### Data sources

- **Premium Account** — `itemsCache.items.stats` (`isPremium`,
  `activePremiumExpiryTime`), the same fields the game's header presenter uses.
- **WoT Plus** — `IWotPlusController.getExpiryTime()`; the header counter reads
  `expiryTime`/`state` straight from the game's own header view model.
