# Building From Source

This page is for users who want to build the mods in this repository. The whole
toolchain (Python 3 tooling, Python 2.7 for `.pyc` output, Java + Apache Flex
SDK for UI, and the lint tools) ships inside one Docker image, so **the only
thing you need to install is Docker**.

## Prerequisites

- **Docker Desktop** (the engine — it just runs in the background).
- Optional, recommended: **VS Code** + the **Dev Containers** extension for the in-editor workflow.

No local Python 2.7/3, Java, or Flex SDK is required.

The published image is `ghcr.io/przemyslaw-zan/zanju-wot-mods/toolchain` (public). It
carries Python 3 (ruff/black/autopep8 + the `wot_mods_*` commands), Python 2.7
(flake8 3.9.x), and the Apache Flex SDK (`mxmlc`). CI builds and publishes it;
locally you just pull it.

## Dev Container (recommended)

Open the repo in VS Code → **Reopen in Container**. You stay in VS Code; the
integrated terminal, interpreter, and `wot_mods_*` commands all run inside the
image. See [Developing Mods](developing-mods.md) for the full loop.

## Standalone `docker run` (no VS Code)

Run any repo command in the image with the repo bind-mounted. PowerShell:

```powershell
# Build one mod (output lands in dist/ on your checkout)
docker run --rm -v "${PWD}:/workspace" -w /workspace `
  ghcr.io/przemyslaw-zan/zanju-wot-mods/toolchain python3 -m tools.build research-progress-bar

# Build everything
docker run --rm -v "${PWD}:/workspace" -w /workspace `
  ghcr.io/przemyslaw-zan/zanju-wot-mods/toolchain python3 -m tools.build --all

# Lint (Python 3 + Python 2.7)
docker run --rm -v "${PWD}:/workspace" -w /workspace `
  ghcr.io/przemyslaw-zan/zanju-wot-mods/toolchain python3 -m tools.lint
```

The `wot_mods_*` console scripts are equivalent to `python3 -m tools.<command>`;
the module form needs no install and is what these examples use.

For `research-progress-bar`, the default build includes the standalone configurator
companion chain when the manifest defines it. Fetch the pinned companion artifacts first:

```powershell
docker run --rm -v "${PWD}:/workspace" -w /workspace `
  ghcr.io/przemyslaw-zan/zanju-wot-mods/toolchain `
  bash -c 'python3 -m tools.fetch_companion_artifacts && python3 -m tools.build research-progress-bar'
```

To build only the main package without the companion `.wotmod` files, add `--no-companion-bundle`.

The tracked companion manifest lives at `tools/companion_artifacts_manifest.json`. Downloaded
companion `.wotmod` files are cached under the ignored `.cache/companion-wotmods/`.

The pinned WoT target version lives at `tools/wot_version_manifest.json`. If your local game
updates, refresh it before build/deploy (run inside the image as above):
`python3 -m tools.update_wot_version_manifest`.

## CI Stable Build

Pushes to `master` publish the current bundles to the rolling GitHub release titled
`Stable build` (tag `stable-build`). CI runs the same image: it lints, builds all mods
inside the image, and publishes. The toolchain image itself is rebuilt and pushed to GHCR
only when `tools/Dockerfile` or the `requirements-*.txt` files change.

The release notes include one changelog link per published mod, so mods intended for that
rolling release should include `mods/<name>/CHANGELOG.md`.

## Output

Successful builds are written to `dist/` as bundle directories. For end users, the main
installation artifact is the generated zip inside each bundle directory.

Each built mod bundle includes:

- `<mod-id>_<version>.zip` containing the install-ready `mods/` tree
- `mods/<wot_client_version>/<mod-id>_<version>.wotmod`
- `mods/configs/<mod-name>/...` for config and optional i18n files

## Deploy To A Local WoT Install

`wot_mods_deploy` copies pre-built artifacts from `dist/`, so build first. Deploy needs your
WoT install mounted at `/game`; the Dev Container does this from `WOT_GAME_DIR` in `.env`
(see [Developing Mods](developing-mods.md)). Standalone:

```powershell
docker run --rm -v "${PWD}:/workspace" -v "C:\Games\World_of_Tanks_EU:/game" `
  -e WOT_GAME_DIR=/game -w /workspace `
  ghcr.io/przemyslaw-zan/zanju-wot-mods/toolchain python3 -m tools.deploy research-progress-bar
```

**Close WoT before deploy/cleanup/cycle.** There is no automatic running-process check
(it can't see the Windows host from the container); in-use files are simply skipped.

## Important Runtime Note

WoT does not hot-reload Python, SWF, or packaged mod changes from disk. After deployment,
restart the game before treating the new package as active.

## Next Steps

- For packaging/runtime conventions, see [Architecture](architecture.md).
- For the full edit-test-debug loop, see [Developing Mods](developing-mods.md).
