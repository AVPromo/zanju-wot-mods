# Installing Mods

This page is for players who want to install a prepared mod package without building the source tree.

## What You Need

- A World of Tanks installation.
- A prepared release bundle for the mod you want to install.

A release bundle usually contains:

- one `.wotmod` package
- one config folder or `config.json`
- optional localisation files

If you only have the repository source tree, use [Building From Source](building-from-source.md) instead.

## Install A Release Bundle

1. Find your current WoT version folder under `World_of_Tanks*/mods/`.
2. Copy the mod's `.wotmod` file into `mods/<current-version>/`.
3. Copy the mod's config files into `mods/configs/<mod-name>/`.
4. Restart the game.

## Update A Mod

1. Close the game.
2. Replace the old `.wotmod` in `mods/<current-version>/`.
3. Replace config files only if the release notes tell you to do so.
4. Start the game and verify the mod loads.

## Remove A Mod

1. Close the game.
2. Delete the mod's `.wotmod` from `mods/<current-version>/`.
3. Delete the matching config directory from `mods/configs/` if you want a full cleanup.

## Included Public Mods

See [Included Mods](../README.md#included-mods) in the repository root for the current public mod list.

## When Installation Is Not Enough

- If you need to produce the package yourself, go to [Building From Source](building-from-source.md).
- If you want to change code or debug behavior, go to [Developing Mods](developing-mods.md).
