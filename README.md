# Zanju's WoT Mods

Source repository for World of Tanks mods, build tooling, and game-facing technical notes.

## Included Mods

- [Zanju's Research Progress Bar](mods/research-progress-bar/README.md)  
  Custom hangar progress bar covering research, field modifications, Tier XI upgrade-tree progress, and elite progress modes.

WIP or experimental mods are intentionally not listed here as public entry points.

## Install And Use

Use this path if you want to install a prepared mod package and keep it updated.

- [Installing Mods](docs/installing-mods.md)

## Build From Source

Use this path if you want to build `.wotmod` packages yourself without changing the code.

- Prerequisites: Python 3, Python 2.7, and `.env` configured with `WOT_GAME_DIR` and `WOT_PYTHON2_EXE`
- UI builds additionally need Java and Apache Flex SDK

- [Building From Source](docs/building-from-source.md)
- [Architecture](docs/architecture.md)

## Develop And Extend

Use this path if you want to change code, add features, or create new mods in this workspace.

- Prerequisites: Python 3, Python 2.7, a local WoT install, and `.env` configured with `WOT_GAME_DIR` and `WOT_PYTHON2_EXE`
- UI and reverse-engineering work additionally need Java, Apache Flex SDK, and FFDec
- Activate the repo `.venv` and install the repo commands with `python -m pip install -e .`
- Run `wot_mods_lint check` before build or deploy once the local style tooling is installed

- [Developing Mods](docs/developing-mods.md)
- [Architecture](docs/architecture.md)
- [Technical Reference](docs/reference/README.md)
- [Debugging](docs/debugging.md)

## Reference

- [Technical Reference](docs/reference/README.md)
- [Resources And External Links](docs/resources.md)
