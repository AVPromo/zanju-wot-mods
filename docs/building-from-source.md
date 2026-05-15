# Building From Source

This page is for users who want to build the mods in this repository without adopting the full development workflow.

## Minimal Prerequisites

- Python 3 for the repository scripts.
- Python 2.7 for WoT-compatible `.pyc` output.
- A `.env` file with `WOT_GAME_DIR` and `WOT_PYTHON2_EXE` configured.
- Java and Apache Flex SDK only if you build a mod with ActionScript UI assets.

For a full workstation setup, see [Developing Mods](developing-mods.md).

## Build Commands

Build everything:

```powershell
python build.py
```

Build one mod:

```powershell
python build.py research-progress-bar
```

## Output

Successful builds are written to `dist/`.
Each built mod gets:

- a `.wotmod` package
- a release-bundle directory with install-ready files

## Deploy To A Local WoT Install

Deploy all mods:

```powershell
python dev_test_deploy.py
```

Deploy one mod:

```powershell
python dev_test_deploy.py research-progress-bar
```

Full cleanup and redeploy loop:

```powershell
python dev_test_cycle.py research-progress-bar
```

## Important Runtime Note

WoT does not hot-reload Python, SWF, or packaged mod changes from disk.
After deployment, restart the game before treating the new package as active.

## Next Steps

- For packaging/runtime conventions, see [Architecture](architecture.md).
- For a full edit-test-debug loop, see [Developing Mods](developing-mods.md).
