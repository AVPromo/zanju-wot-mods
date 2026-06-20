# Developing Mods

This page is for contributors working on the code in this repository.

## Toolchain

The entire toolchain ships inside one Docker image
(`ghcr.io/przemyslaw-zan/zanju-wot-mods/toolchain`, public), so **Docker Desktop is
the only thing you install**. The image carries:

- Python 3 with the repo commands (`wot_mods_*`) and Black / Ruff / autopep8.
- Python 2.7 with Flake8 3.9.x, to compile and lint WoT-compatible `.pyc` files.
- Java + Apache Flex SDK (`mxmlc`) for ActionScript UI.

A local World of Tanks install is still needed for runtime validation (deploy/cycle).

## Local Setup (Dev Container)

1. Install **Docker Desktop** and the VS Code **Dev Containers** extension.
2. Copy `.env.example` to `.env` and set `WOT_GAME_DIR` to your WoT install path
   (e.g. `c:\Games\World_of_Tanks_EU`). Docker Compose reads it to bind-mount your
   install at `/game`; inside the container the tools see `WOT_GAME_DIR=/game`.
3. Open the repo in VS Code → **Reopen in Container**.

You stay in VS Code — same editor, terminal, and Source Control. Only the backend
(interpreter, terminal, tooling) runs inside the image. The first open pulls the
image; later opens reuse the container. `postCreateCommand` runs `pip install -e .`
so the `wot_mods_*` console scripts resolve in the container terminal:

```bash
wot_mods_build research-progress-bar
wot_mods_build --all
wot_mods_deploy research-progress-bar
wot_mods_cycle research-progress-bar
wot_mods_help          # environment check + command summary
```

The module form is equivalent and needs no install:

```bash
python3 -m tools.build research-progress-bar
python3 -m tools.lint check
```

Without VS Code, run any command via plain `docker run` — see the standalone
reference in [Building From Source](building-from-source.md#standalone-docker-run-no-vs-code).

For mod-targeting commands, pass one or more mod names explicitly; use `--all` only
when you really want every mod. `wot_mods_deploy` expects current build output in
`dist/`. **Close WoT before `wot_mods_cleanup`, `wot_mods_deploy`, and `wot_mods_cycle`** —
there is no automatic running-process check (the container can't see the Windows host);
in-use files are simply skipped.

Mods intended for the repository's rolling `Stable build` GitHub release should include
`mods/<name>/CHANGELOG.md`, because the generated release notes link each published mod to that file.

## Python Format and Lint Workflow

The repo-level entry point is:

```powershell
wot_mods_lint
wot_mods_lint check
```

That command is the current default gate locally and in CI for:

- Python 3 format check with Black.
- Python 3 lint with Ruff.
- Python 2.7 lint with Flake8 3.9.x.
- Python 2.7 conservative format check with autopep8 diff mode.

The Python 2.7 Flake8 gate also enforces a McCabe complexity limit so new changes do not keep pushing large runtime functions upward unchecked.

CI runs the same `wot_mods_lint` steps inside the toolchain image, so the Python 3 (Black/Ruff/autopep8) and Python 2.7 (Flake8 3.9.x against `mods/*/src`) surfaces use the exact interpreters you get locally — no environment drift. Every push to a non-`master` branch and every PR runs lint; on `master` the Stable Release workflow runs lint as a gate before building and publishing.

Useful variants:

```powershell
wot_mods_lint fix
wot_mods_lint py3-check
wot_mods_lint py3-format
wot_mods_lint py3-format-check
wot_mods_lint py27-lint
wot_mods_lint py27-format-check
wot_mods_lint py27-format
```

The Python 2.7 autopep8 path is intentionally conservative. It only applies low-risk whitespace, indentation, and blank-line fixes. CI checks that surface in diff mode, while local rewriting stays an explicit reviewed step via `wot_mods_lint py27-format`.

## Recommended Daily Loop

1. Edit source files.
2. Run `wot_mods_lint` or `wot_mods_lint check`.
3. If you want to normalize existing Python 2.7 formatting, review `wot_mods_lint py27-format-check` before applying `wot_mods_lint py27-format`.
4. Close WoT, then run `wot_mods_cycle <mod-name>`.
5. Restart or relaunch WoT.
6. Reproduce the scenario.
7. Inspect `python.log`.

## Useful Commands

Full format and lint gate:

```powershell
wot_mods_lint
wot_mods_lint check
```

Python 3 auto-fixes plus Python 2.7 lint:

```powershell
wot_mods_lint fix
```

Build one mod:

```powershell
wot_mods_build research-progress-bar
```

Cleanup one deployed mod:

```powershell
wot_mods_cleanup research-progress-bar
```

Cleanup, rebuild, and redeploy one mod:

```powershell
wot_mods_cycle research-progress-bar
```

Fresh log plus redeploy:

```powershell
wot_mods_cycle --fresh-log research-progress-bar
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
