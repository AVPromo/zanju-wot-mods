# Developing Mods

This page is for contributors working on the code in this repository.

## Toolchain

Core requirements:

- Python 3 for repo scripts such as `build.py` and deploy helpers.
- Python 2.7 to compile WoT-compatible `.pyc` files.
- A local World of Tanks install for runtime validation.

UI work adds:

- Java
- Apache Flex SDK (`mxmlc`)
- FFDec for SWF inspection

## Local Setup

Create `.env` in the repository root and set:

```text
WOT_GAME_DIR=C:\Games\World_of_Tanks_EU
WOT_PYTHON2_EXE=C:\Python27\python.exe
```

## Recommended Daily Loop

1. Edit source files.
2. Run `python dev_test_cycle.py <mod-name>`.
3. Restart or relaunch WoT.
4. Reproduce the scenario.
5. Inspect `python.log`.

## Useful Commands

Build one mod:

```powershell
python build.py research-progress-bar
```

Cleanup one deployed mod:

```powershell
python dev_test_cleanup.py research-progress-bar
```

Cleanup and redeploy one mod:

```powershell
python dev_test_cycle.py research-progress-bar
```

Fresh log plus redeploy:

```powershell
python dev_test_cycle.py --fresh-log research-progress-bar
```

## Repository Conventions

- Keep a thin top-level `mod_*.py` bootstrap in `src/`.
- Put implementation into a uniquely named internal package.
- Use explicit relative imports inside the package.
- Keep user config under `mods/configs/<mod-name>/`.
- Treat generated SWF output and release bundles as build artifacts, not source.

## Where To Go Next

- [Architecture](architecture.md) for packaging, runtime layout, and UI patterns.
- [Debugging](debugging.md) for triage and stability rules.
- [Technical Reference](reference/README.md) for game-facing APIs and runtime knowledge.
