Changelog
=========

## 1.1.2 (10 September 2026)

- Banner icons now carry the colour of the state they flag, matching the note the hover card shows for the same state. A pause or a locked vehicle reads yellow, and a mission past its primary objective reads green.
- Banners now count the vehicles spent on a mission that asks to be completed in several different ones. A vehicle locks itself out of such a mission by completing it. The count is therefore the one number saying how much of the mission is behind you.
- A banner now opens the campaign screen with the game's own back button. It walks back the way the game's own path does. For campaign 3 that is the campaign first, then the campaign map. The game's own garage banner has no such button. Escape follows the same path, so the garage is one or two presses further away.
- Fixed the mod being able to interrupt the game's own keys. Escape, Tab and the radial menu commands could stop working. The mod now watches Shift and Ctrl only while its banners are on screen.
- Fixed the mod doing more work on each refresh the longer the client ran. It kept every set of garage widgets it ever built, and wrote to all of them.
- New Russian and Ukrainian translations. Thank you [@ICELUV0x](https://github.com/ICELUV0x)!

## 1.1.1 (2 September 2026)

- Fixed the banner not working for the Fossa operation.
- The banners now show for the random battles only.

## 1.1.0 (2 September 2026)

- Moved banner tooltips into a Gameface window of their own, on a higher window layer. They now draw over the game's native windows, such as the platoon window.
- Fixed the banners not appearing in non-default garages.
- Updated for World of Tanks 2.4.

## 1.0.0 (28 August 2026)

- Initial release of the mod.
