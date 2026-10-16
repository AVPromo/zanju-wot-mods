# Zanju's Campaign Tracker

![Mod showcase image](./images/campaign_legacy.png)
![Mod showcase image, campaign 3](./images/campaign_modern.png)

### This mod brings back the personal mission campaign banners the UI rework removed.

- **Support for all campaigns** — works with the old style of campaigns 1 and 2, and the new style of campaign 3.
- **Details on hover** — hover over a banner for the conditions and your progress.
- **Interactive** — click a banner to open its mission. Shift-click and Ctrl-click pause or reset the missions that allow it.
- **Locked vehicles** — for missions that require several different vehicles, shows the progress and warns when your tank is locked out.

## Settings

With Aslain's Mod Menu installed, the settings are in the game's settings window, under the name of the mod:

- **Banner position** — the left or the right side of the vehicle name. The banner of Crucible Tracker shares the row on the same side.

Without Mod Menu, edit `%APPDATA%\zanju_wot_mods_cache\campaign-tracker\config.json`. The mod creates that file on its first start.

## Translations

Reference language `en` defines 14 strings. Translations are community-maintained and may lag behind; see [Translating](../../docs/translating.md) to add or update one, then regenerate this table with `zwm lint i18n`.

| Language | Coverage | Missing |
| --- | --- | --- |
| `pl` | 71% (10/14) | 4 |
| `ru` | 71% (10/14) | 4 |
| `uk` | 71% (10/14) | 4 |
| `zh_cn` | 71% (10/14) | 4 |

## Install And Use

If you already have the prepared mod zip file, follow the general install path in [Installing Mods](../../docs/installing-mods.md).

## Build From Source

For the general build/toolchain workflow, see [Building From Source](../../docs/building-from-source.md).

## Develop

For the wider repository workflow, see:

- [Developing Mods](../../docs/developing-mods.md)
- [Architecture](../../docs/architecture.md)
- [Technical Reference](../../docs/reference/README.md)
