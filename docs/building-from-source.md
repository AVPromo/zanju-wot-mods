# Building From Source

This page is for users who want to build the mods in this repository without adopting the full development workflow.

## Minimal Prerequisites

- Python 3 for the repository scripts.
- Python 2.7 for WoT-compatible `.pyc` output.
- A `.env` file copied from `.env.example`, with `WOT_PYTHON2_EXE` configured.
- The pinned WoT client version in `tools/wot_version_manifest.json`.
- `WOT_GAME_DIR` is optional for build-only CI, but required for deploy/cleanup/cycle and for local version.xml validation.
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
wot_mods_build --all
```

Build one mod:

```powershell
wot_mods_build crew-post-progression
```

If you omit both mod names and `--all`, the command will stop and list the available mods.

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

The pinned WoT target version lives at `tools/wot_version_manifest.json`.
If your local game updates, refresh that manifest before build/deploy:

```powershell
wot_mods_update_wot_version_manifest
```

When you intentionally want to refresh the pinned companion versions, run the separate manifest-update command first. It queries upstream release APIs, verifies the candidate artifacts, and rewrites the tracked manifest. Then run the normal fetch command again to repopulate the local cache from the new pins.

```powershell
wot_mods_update_companion_manifest
wot_mods_fetch_companion_artifacts
```

## CI Stable Build

Pushes to `master` publish the current repository bundles to the rolling GitHub release titled `Stable build`, backed by the fixed tag `stable`.

That release is generated from a clean CI build of the current `mods/` tree, not from whatever stale directories may already exist under `dist/`.

The release notes include one changelog link per published mod, so mods intended for that rolling release should include `mods/<name>/CHANGELOG.md`.

## Output

Successful builds are written to `dist/` as bundle directories. For end users, the main installation artifact is the generated zip file inside each bundle directory.

Each built mod bundle includes:

- `<mod-id>_<version>.zip` containing the same install-ready `mods/` tree as the bundle folder
- `mods/<wot_client_version>/<mod-id>_<version>.wotmod`
- `mods/configs/<mod-name>/...` for config and optional i18n files

## Deploy To A Local WoT Install

`wot_mods_deploy` copies pre-built artifacts from `dist/`, so run `wot_mods_build` first if you have not just built.
Close WoT before running `wot_mods_cleanup`, `wot_mods_deploy`, or `wot_mods_cycle`; those commands now fail fast while the client is running.

Deploy all mods:

```powershell
wot_mods_deploy --all
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

Full cleanup, rebuild, and redeploy loop:

```powershell
wot_mods_cycle research-progress-bar
```

## Important Runtime Note

WoT does not hot-reload Python, SWF, or packaged mod changes from disk.
After deployment, restart the game before treating the new package as active.

## Next Steps

- For packaging/runtime conventions, see [Architecture](architecture.md).
- For a full edit-test-debug loop, see [Developing Mods](developing-mods.md).
