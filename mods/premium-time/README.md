# Zanju's Premium Time

### A small, always-on hangar widget that shows how much premium time you have left.

The widget reads your account state and displays the remaining time for the two
independent premium subscriptions:

- **Premium Account** — the classic WoT premium time.
- **WoT Plus / WoT Plus Pro** — the renewable subscription (the active tier is detected
  and labelled automatically).

Each line shows the time remaining as a compact `Xd Yh` value, colour-coded by urgency
(green → amber under 3 days → red under 1 day). A subscription you do not currently hold
is shown as **Inactive**, or hidden entirely via the settings.

### Settings

Configured in-game through Aslain's ModsSettings menu:

- **Show Premium Account** — toggle the Premium Account line.
- **Show WoT Plus** — toggle the WoT Plus / WoT Plus Pro line.
- **Hide when inactive** — hide the widget completely when nothing is active.
- **Screen corner** — anchor the widget to any of the four hangar corners.

Settings live in `%APPDATA%/zanju_wot_mods_cache/premium-time/config.json` and survive
modpack reinstalls.

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

### Data sources

- **Premium Account** — `itemsCache.items.stats.activePremiumExpiryTime` (falling back to
  `totalPremiumExpiryTime`, then legacy fields on older clients).
- **WoT Plus** — `IWotPlusController.getExpiryTime()` (falling back to `getState()`, then
  account-stats / player probes). When the controller exposes a known accessor it is
  treated as authoritative, so a zero expiry means "no active subscription" rather than a
  read failure.

If none of the known WoT Plus shapes match on a future client, the collector logs the
candidate attribute names once to `python.log` (search for `WoT Plus expiry not resolved`)
so the field can be re-pinned without guesswork.

Not yet verified in-game: **WoT Plus Pro** tier detection (whether the line should read
"WoT Plus" vs "WoT Plus Pro"). It currently defaults to "WoT Plus"; confirming the Pro flag
needs an account with an active WoT Plus Pro subscription.
