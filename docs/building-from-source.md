# Building From Source

This page is for users who want to build the mods in this repository without adopting the full development workflow.

## Minimal Prerequisites

- Python 3 for the repository scripts.
- Python 2.7 for WoT-compatible `.pyc` output.
- A `.env` file with `WOT_GAME_DIR` and `WOT_PYTHON2_EXE` configured.
- Java and Apache Flex SDK only if you build a mod with ActionScript UI assets.

Install the repo commands into your active Python 3 environment once:

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
```

The `wot_mods_*` commands below resolve while that Python 3 environment is active.

If a newly added repo command is missing after you update the workspace, rerun `python -m pip install -e .` to regenerate the console-script stubs. The module form also stays available, for example `python -m tools.fetch_companion_artifacts`.

For a full workstation setup, see [Developing Mods](developing-mods.md).

## Build Commands

Build everything:

```powershell
wot_mods_build
```

Build one mod:

```powershell
wot_mods_build crew-post-progression
```

For `research-progress-bar`, the default build now includes the standalone configurator companion chain when the manifest defines it. Fetch the pinned companion artifacts first:

```powershell
wot_mods_fetch_companion_artifacts
wot_mods_build research-progress-bar
```

If you intentionally want only the main mod package without the companion `.wotmod` files, opt out explicitly:

```powershell
wot_mods_build --no-companion-bundle research-progress-bar
```

The tracked companion manifest lives at `tools/companion_artifacts_manifest.json`. Downloaded companion `.wotmod` files are stored in the ignored local cache under `.cache/companion-wotmods/` and are not committed.

When you intentionally want to refresh the pinned companion versions, run the separate manifest-update command first. It queries upstream release APIs, verifies the candidate artifacts, and rewrites the tracked manifest. Then run the normal fetch command again to repopulate the local cache from the new pins.

```powershell
wot_mods_update_companion_manifest
wot_mods_fetch_companion_artifacts
```

## Output

Successful builds are written to `dist/`.
Each built mod gets:

- a `.wotmod` package
- a release-bundle directory with install-ready files

## Deploy To A Local WoT Install

Deploy all mods:

```powershell
wot_mods_deploy
```

Deploy one mod:

```powershell
wot_mods_deploy crew-post-progression
```

For `research-progress-bar`, deployment also includes the configured companion chain by default after those artifacts have been fetched into the local cache.

Deploy only the main mod package when you explicitly want to skip the companion `.wotmod` files:

```powershell
wot_mods_deploy --no-companion-bundle research-progress-bar
```

Full cleanup and redeploy loop:

```powershell
wot_mods_cycle research-progress-bar
```

## Important Runtime Note

WoT does not hot-reload Python, SWF, or packaged mod changes from disk.
After deployment, restart the game before treating the new package as active.

## Next Steps

- For packaging/runtime conventions, see [Architecture](architecture.md).
- For a full edit-test-debug loop, see [Developing Mods](developing-mods.md).
