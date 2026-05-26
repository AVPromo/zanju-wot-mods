# Developing Mods

This page is for contributors working on the code in this repository.

## Toolchain

Core runtime and build requirements:

- Python 3 for repo tools such as `wot_mods_build`, `wot_mods_cycle`, and `wot_mods_deploy`.
- Python 2.7 to compile WoT-compatible `.pyc` files.
- A local World of Tanks install for runtime validation.

Contributor format and lint tools:

- Black and Ruff in the Python 3 environment.
- Flake8 3.9.x in the Python 2.7 environment.
- autopep8 in the Python 3 environment for conservative Python 2.7 formatting.

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

Install the format and lint tooling with the interpreters you already use for the repo:

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
python -m pip install -e .
C:\Python27\python.exe -m pip install -r requirements-lint-py27.txt
```

Use the same Python 2.7 executable in the second command that you point `WOT_PYTHON2_EXE` at in `.env`.

If you do not want to activate the environment in that shell, use `.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt` and `.\.venv\Scripts\python.exe -m pip install -e .` instead.

The editable install adds `wot_mods_build`, `wot_mods_cleanup`, `wot_mods_cycle`, `wot_mods_deploy`, `wot_mods_fetch_companion_artifacts`, `wot_mods_help`, `wot_mods_update_companion_manifest`, and `wot_mods_lint` to the active Python 3 environment. Activate that environment before expecting the commands to resolve on `PATH`.

If `pyproject.toml` changes add a new repo command, rerun `python -m pip install -e .` in that environment so the console-script stubs are regenerated.

For a quick environment check plus the available repo-command summary, run `wot_mods_help`.

The module form stays available when you want it:

```powershell
python -m tools.help
python -m tools.build research-progress-bar
python -m tools.lint check
```

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

CI is split by host interpreter, not only by target source tree. `wot_mods_lint py27-format-check` runs from the Python 3 tooling environment because autopep8 and the installed repo commands live there, but it checks the Python 2.7 runtime source under `mods/*/src`. The Python 2.7 lint job is separate because Flake8 3.9.x is intentionally executed inside a Python 2.7 environment against that same runtime code.

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
4. Run `wot_mods_cycle <mod-name>`.
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

Cleanup and redeploy one mod:

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
