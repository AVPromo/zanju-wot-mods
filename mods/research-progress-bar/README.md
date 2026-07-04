# Zanju's Research Progress Bar

![Mod showcase image](./images/mod.png)

### This mod adds a fully customisable progress bar which shows your progress in:

- **Module and vehicle research**
  - See how close you are to researching modules and vehicles _without entering any menu_.
  - On tier X vehicles you can _optionally_ show progress towards hypothetical future Tier 11 vehicles _that might be added in the future_.
- **Field modifications**
  - See how close you are to unlocking each field modification level _without entering any menu_.
  - Each level shows what options are available, or will be available once unlocked.
  - _Optionally_ the bar can stay displayed even after field modification research to quickly check what upgrade is selected _without entering any menu_.
- **Tier 11 upgrades system**
  - See how close you are to unlocking next upgrade _without entering any menu_.
  - Still helpful to see overall progress, even though a flat progress bar cannot display the complex upgrade tree.
- **Elite level progress**
  - See how close you are to reaching next elite level.
  - Shows progress towards cosmetic elements tied to elite level available for Tier 11 vehicles.
  - _Optionally_ the bar can display progress towards elite level badges.

### Other features of the mod:

- Different XP types are taken into account:
  - Separate calculation for research using vehicle XP only. (_Displayed in green_)
  - Separate calculation for research using vehicle XP + free XP. (_Displayed in yellow_)
  - Elite level progress is calculated based on base XP.
- _Optional_ warning messages:
  - **Research now!** message when you have enough vehicle XP to research all available items.
  - **Accelerate crew training!** message when you have already researched all available items.

![Mod configuration image](./images/config.png)

## Translations

Reference language `en` defines 75 strings. Translations are community-maintained and may lag behind; see [Translating](../../docs/translating.md) to add or update one, then regenerate this table with `zwm lint i18n`.

| Language | Coverage | Missing |
| --- | --- | --- |
| `pl` | 100% (75/75) | 0 |

## Install And Use

If you already have the prepared mod zip file, follow the general install path in [Installing Mods](../../docs/installing-mods.md).

## Build From Source

For the general build/toolchain workflow, see [Building From Source](../../docs/building-from-source.md).

## Develop

For the wider repository workflow, see:

- [Developing Mods](../../docs/developing-mods.md)
- [Architecture](../../docs/architecture.md)
- [Technical Reference](../../docs/reference/README.md)
