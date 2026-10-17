# Zanju's Crucible Tracker

### This mod shows your Crucible missions beside the vehicle name in the garage.

- **Active series at a glance** — while a series is active, the banner shows your shields left out of all shields, the current mission and the time left in the series. With no active series, it counts the series that end first and that you have not completed yet, and shows when they end. The count reads free / silver / gold: how many of them you can start or restart for nothing, and how many restart for credits or for gold. Once you complete all of them, the banner moves on to the series that end next. With every series completed, it shows a green check.
- **Details on hover** — while a series is active, the card is about that series only: its name and time left, one icon for each shield with the spent ones greyed, and every mission of the series with its conditions. With no active series, the card lists every series you can play. Each row has the shields, the completions, the start or restart price and the time left.
- **Warnings** — the banner goes grey when the vehicle in the garage is below the Crucible tiers. Crossed swords and a count show your vehicles of those tiers that are still in a random battle. The result of that battle completes or fails the current mission, or a series that you start now, and the card lists those vehicles.
- **One click to the Crucible** — click the banner to open the game's Crucible screen.
- **Shares the row with Campaign Tracker** — both banners stand in one row, on the side of the name you choose.
- **Progress in battle** — a panel shows each condition of the current mission. Under a condition that the panel can count, a bar fills, with the figures beside it. A condition with a time limit, such as "within the first 5 minutes of battle", also counts down as M:SS. When a mission offers a choice of condition sets, an "OR" stands between the sets. The panel shows only in a battle of the mission's battle types and vehicle tiers.
- **Awards too** — the panel counts some awards by their rule: High Caliber as damage of 20% of the enemy team's HP, and Top Gun as 6 kills.
- **Move the panel** — hold Ctrl and drag the panel. The mod keeps the position, and the panel cannot leave the screen. The panel hides while you hold Tab.

The panel follows what the game reports during the battle. The battle results decide the mission, so the figures are an estimate. The panel cannot count some conditions, such as "be among the top 5 players", and it shows their text only. After a reconnect, the panel cannot know what happened before it, so it shows the conditions without figures. A time limit still counts down.

## Settings

With Aslain's Mod Menu installed, the settings are in the game's settings window, under the name of the mod:

- **Garage banner** — show the banner in the garage.
- **Battle panel** — show the progress of the current mission in battle.
- **Banner position** — the left or the right side of the vehicle name.

Without Mod Menu, edit `%APPDATA%\zanju_wot_mods_cache\crucible-tracker\config.json`. The mod creates that file on its first start.

## Translations

Reference language `en` defines 23 strings. Translations are community-maintained and may lag behind; see [Translating](../../docs/translating.md) to add or update one, then regenerate this table with `zwm lint i18n`.

| Language | Coverage | Missing |
| --- | --- | --- |
| _none yet_ | — | — |

## Install And Use

If you already have the prepared mod zip file, follow the general install path in [Installing Mods](../../docs/installing-mods.md).

## Build From Source

For the general build/toolchain workflow, see [Building From Source](../../docs/building-from-source.md).

## Develop

For the wider repository workflow, see:

- [Developing Mods](../../docs/developing-mods.md)
- [Architecture](../../docs/architecture.md)
- [Technical Reference](../../docs/reference/README.md)
