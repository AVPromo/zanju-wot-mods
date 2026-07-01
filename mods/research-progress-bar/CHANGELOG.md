Changelog
=========

## Unreleased

- Research tooltips for items that have prerequisites now show the combined cost of the item plus its prerequisites, and the Vehicle XP / Total XP progress is measured against that combined total — so a module that looks cheaper on its own no longer understates what it actually takes to unlock. [[#6](https://github.com/przemyslaw-zan/zanju-wot-mods/issues/6)]
- Fixed untranslated text in the tooltips: the field modifications and upgrades progress now shows "Vehicle XP" / "Total XP", along with the "Prerequisites" heading and completed-item text, in the client language instead of always in English. [[#8](https://github.com/przemyslaw-zan/zanju-wot-mods/issues/8)]
- Elite tooltips now show the reward name on its own line below the title, so the icon lines up with the title instead of floating between two lines.
- Translations now ship inside the mod package itself, so installing leaves no loose language files in the modpack's `mods/configs` folder.

## 1.1.0 (26 June 2026)

- Settings now survive a modpack reinstall instead of being reset to defaults.
- In-game settings now use Aslain's ModsSettings menu, with search, collapsible mods, and a reset-to-defaults button.

## 1.0.1 (17 June 2026)

- The progress bar now lays out correctly at non-default interface scaling (e.g. x2) instead of stretching off both edges of the screen. [[#2](https://github.com/przemyslaw-zan/zanju-wot-mods/issues/2)]
- Korean and other non-Latin characters now display correctly in the mod's tooltips — module names, upgrade names and descriptions, and field-modification stats — instead of appearing as empty boxes. [[#3](https://github.com/przemyslaw-zan/zanju-wot-mods/issues/3)]

## 1.0.0 (3 June 2026)

- Initial release of the mod.
