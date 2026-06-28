# Installing Mods

This page is for players who want to install a ready-to-use mod without building anything from source.

## What You Need

- A World of Tanks installation.
- The mod zip file for the mod you want to install.

The zip file is the main installation file for users. When you open it, it already contains the correct folder structure, usually starting with a `mods/` folder.

Some mods also include companion `.wotmod` files inside that same `mods/` folder when they depend on a shared in-game UI or configuration stack. If that happens, keep the included files together instead of copying only one of them.

If you only have the repository source tree, use [Building From Source](building-from-source.md) instead.

## Simplest Installation Method

This is the easiest method if you already know where your World of Tanks game folder is.

1. Close World of Tanks.
2. Copy the mod zip file into your main World of Tanks game folder.
3. Right-click the zip file and choose `Extract here`.
4. If Windows asks whether you want to replace existing files, choose yes or agree to all replacements.
5. Start the game.

The needed files should land in the correct places automatically because the zip already contains the right folder layout.

## Manual Method: Extract Elsewhere First

Use this method if you want to look inside the zip before copying anything into the game.

1. Close World of Tanks.
2. Extract the zip file somewhere else first, for example on your desktop.
3. Open the extracted folder. You should see folders such as `mods`.
4. Open your World of Tanks game folder in another window.
5. Drag the extracted folders into the game folder.
6. If Windows asks whether you want to merge folders with the same name, allow it.
7. If Windows asks whether you want to replace files, allow that too.
8. Start the game.

## Updating A Mod

1. Close the game.
2. Install the newer zip file the same way you installed the old one.
3. If Windows asks about replacing files, agree to the replacements.
4. Replace config files only if the mod author or release notes tell you to do so.
5. Start the game and verify the mod loads.

## Removing A Mod

1. Close the game.
2. Delete the mod's `.wotmod` file from `mods/<current-version>/`. Translations live inside that package, so removing it also removes them.
3. The mod's settings are stored in your WoT AppData folder; delete that folder too for a full cleanup.

## Included Public Mods

See [Included Mods](../README.md#included-mods) in the repository root for the current public mod list.

## When Installation Is Not Enough

- If you need to produce the zip file yourself, go to [Building From Source](building-from-source.md).
- If you want to change code or debug behavior, go to [Developing Mods](developing-mods.md).
