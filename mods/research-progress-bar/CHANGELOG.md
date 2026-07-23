Changelog
=========

## Unreleased

- New **"Click to research or purchase"** setting (on by default, at the top of the settings). It turns all of the bar's interactivity below on or off. Every action goes through the game's own confirmation windows, so there is no risk from a misclick.
- The bar is interactive in the Research and Field Mods modes: clicking a marker starts the game's own research flow for that item, opening the same confirmation window as the tech tree or field modification screens — nothing is spent without confirming there.
  - A marker is clickable exactly when one of its displayed tooltip rows reads "ready for research", so with the "Show Total XP" setting off only Vehicle XP progress arms the click, and items still blocked by prerequisites are never clickable.
  - Clickable markers show a hand cursor on hover, and their tooltip gains a blue "Click to research." line at the bottom.
  - When several ready-to-research items have close enough XP costs that their markers overlap and stack in one tooltip, a single click would be ambiguous, so it is disabled and each item is numbered instead — hover the stack and press the matching number key (its tooltip shows a blue "Press N to research." line) to research that specific item.
  - Researching a **module** (by click or number key) now follows the research with the game's own "purchase and mount" popup once the research lands, so you can buy and fit it right away. Nothing is bought unless you confirm in that popup, and it is skipped if you cancel the research. Vehicles are exempt — they are only researched, and buying the vehicle is left to you.
  - On field modification levels with a choice between two modifications, the click researches the level itself. Once a level is researched but its variant is still unpicked, hover the marker and press **1** or **2** to choose — each option's tooltip shows its "Press X to purchase." hint above its stats, so you can compare before choosing. On a level whose variant is already picked, a click swaps to the other modification ("Click to change modification.").
  - On the second-slot-category level, a click opens the game's Field Modification screen to select or reassign the category (the choice is made inside that screen). Once a category is picked, the hangar's bottom loadout panel refreshes on its own, the same way it does after a loadout switch is toggled, instead of showing the previous category until a vehicle change.
- The Tier 11 upgrades mode is interactive too: a click on a currently reachable minor, major or final upgrade node opens the game's own upgrades menu, with a blue "Click to open the upgrades menu." tooltip line. The flat bar cannot show the branching upgrade tree, so the pick and purchase are made on that screen — nothing is spent from the bar.
  - The final upgrade node's tooltip, locked behind all the other nodes, now shows the combined "Cost with prerequisites" for the whole remaining tree and measures its progress against that total, the same way research items with prerequisites are shown.
  - A minor or major upgrade node whose remaining upgrades are all locked behind other, not-yet-researched nodes in the tree is now grayed out (like a prerequisite-blocked research item) and its tooltip reads "Requires other upgrades" instead of showing a reachable cost or progress. Reachability comes from the game's own per-node tree state, so it respects the branching upgrade paths.
  - The minor and major upgrade markers each stand in for every remaining node of their tier, so their tooltip now shows an "Upgrades remaining: N" line under the title with the respective (bold) count.
- The unlocked essentials / auxiliary loadout-switch levels are clickable too: a click toggles the loadout switch on or off directly, with a blue "Click to enable." / "Click to disable." tooltip line. No confirmation window appears for these — the toggle is free, exactly like the switch in the game's Field Modification screen. Once the game confirms the toggle, the hangar's bottom loadout panel refreshes on its own, so its loadout switches and status dots no longer need a vehicle change to update.
- Fixed the first vehicle research of a session failing with an "unlocks/vehicle/required_locked" error when the Research screen had not been opened yet. The game validates a vehicle unlock against its tech tree data, which it only loads once that screen is first opened; the bar now makes sure it is loaded before researching a vehicle.
- The bar now follows research and purchases confirmed by the game without needing a vehicle switch: it refreshes as soon as the change lands, instead of continuing to show a just-researched item as still available until another vehicle was selected and re-selected.
- The loadout-switch tooltips now name what each switch controls — e.g. "Essentials Loadout (shells and consumables)" — and show the switch state as "Enabled" in green or "Disabled" in red, instead of a plain "Active" / "Not active".

## 1.2.0 (4 July 2026)

- New "Show Total XP" setting (enabled by default). Turning it off hides the Total XP calculation everywhere: the Free XP (yellow) segment of the bar, the yellow highlight of markers reachable with Free XP, the Total XP counter next to the bar, and the Total XP row in tooltips — leaving only Vehicle XP progress.
- Research tooltips for items that have prerequisites now show the combined cost of the item plus its prerequisites, and the Vehicle XP / Total XP progress is measured against that combined total — so a module that looks cheaper on its own no longer understates what it actually takes to unlock. [[#6](https://github.com/przemyslaw-zan/zanju-wot-mods/issues/6)]
- New Russian translation. Thank you [@AVPromo](https://github.com/AVPromo)!
- Fixed untranslated text in the tooltips: the field modifications and upgrades progress now shows "Vehicle XP" / "Total XP", along with the "Prerequisites" heading and completed-item text, in the client language instead of always in English. [[#8](https://github.com/przemyslaw-zan/zanju-wot-mods/issues/8)]
- The Vehicle XP / Total XP rows in tooltips are now laid out as a real table with right-aligned columns. They were previously aligned by padding with spaces, which only lined up in the mod's monospace font — translations rendered in the fallback font (e.g. Russian) drifted apart as label lengths diverged.
- Russian and other Cyrillic text now renders in the mod's own font, matching English and Polish, instead of the system fallback font.
- Elite tooltips now show the reward name on its own line below the title, so the icon lines up with the title instead of floating between two lines.
- Translations now ship inside the mod package itself, so installing leaves no loose language files in the modpack's `mods/configs` folder. The `language` override in the config file is gone as part of this — the mod now always follows the game client's language.

## 1.1.0 (26 June 2026)

- Settings now survive a modpack reinstall instead of being reset to defaults.
- In-game settings now use Aslain's ModsSettings menu, with search, collapsible mods, and a reset-to-defaults button.

## 1.0.1 (17 June 2026)

- The progress bar now lays out correctly at non-default interface scaling (e.g. x2) instead of stretching off both edges of the screen. [[#2](https://github.com/przemyslaw-zan/zanju-wot-mods/issues/2)]
- Korean and other non-Latin characters now display correctly in the mod's tooltips — module names, upgrade names and descriptions, and field-modification stats — instead of appearing as empty boxes. [[#3](https://github.com/przemyslaw-zan/zanju-wot-mods/issues/3)]

## 1.0.0 (3 June 2026)

- Initial release of the mod.
