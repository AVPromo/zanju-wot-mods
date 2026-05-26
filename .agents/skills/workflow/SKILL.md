---
name: workflow
description: "Repository workflow guidance for zanju-wot-mods. Use when working on mods, build/deploy scripts, docs, validation, release bundles, or WoT UI assets. Keywords: wot_mods_build, wot_mods_deploy, wot_mods_cycle, python.log, docs sync, release bundle, research-progress-bar, tools/."
---

# Repository Workflow

Use this skill for normal work in this repository.
It captures repo-specific conventions, documentation expectations, and validation workflow.

## Use This Skill For

- Editing a mod under `mods/<name>/`.
- Changing packaging, deployment, release-bundle, or build behavior.
- Updating docs or checking whether docs became stale after a code change.
- Deciding whether to run `wot_mods_build`, `wot_mods_deploy`, or `wot_mods_cycle`.
- Working on WoT UI assets, Scaleform code, or Python/runtime integration.

## Core Principles

1. Keep docs current whenever behavior, install steps, build flow, or technical knowledge changes.
2. Prefer repo-established patterns over inventing a new structure.
3. Validate at the narrowest useful scope first, then use build/deploy/runtime checks when the change warrants it.
4. Treat WoT as non-hot-reloading: copying files to disk is not proof that the running client loaded them.

## Repo Conventions

### Python Tooling Environment

- Prefer the project venv interpreter for repo commands when available: `./.venv/Scripts/python.exe -m tools.lint ...` on Windows.
- Do not assume the system `python` has repo lint dependencies such as Black, Ruff, autopep8, or Flake8 installed.
- When `wot_mods_*` commands are not on `PATH`, the module form remains valid and is often the least ambiguous option, for example `./.venv/Scripts/python.exe -m tools.lint check`.
- The Python 2.7 lint gate is still part of the normal repo workflow even when you invoke `tools.lint` from the Python 3 venv; it shells out to the configured Python 2.7 executable for the runtime source under `mods/*/src`.

### Mod Layout

- Real mods live under `mods/<mod-name>/`.
- Keep a thin top-level loader in `src/mod_*.py` and move implementation into a namespaced internal package under `src/<package>/`.
- Do not use a top-level bootstrap file and package directory with the same module name.
- Prefer explicit relative imports inside the internal package.

### Config And Localisation

- Use exactly one config source per mod: `config.json` or `config/`.
- Author localisation in `i18n/*.yml` when possible; the repo tooling stages those files both into the `.wotmod` text resources and into `mods/configs/<mod>/i18n/` during deploy.
- Keep human-readable names consistent across `meta.xml`, localisation, README text, and docs.

### UI Assets

- `wot_mods_build` automatically runs `mods/<mod>/ui/compile_ui.py` when present.
- Generated UI output belongs under `mods/<mod>/ui/build/res/`.
- For garage Scaleform views, reuse the repo's WoT-compatible view pattern rather than ad hoc raw display roots.

### Packaging And Deploy

- `wot_mods_build <mod>` is the canonical package build for one mod.
- `wot_mods_deploy <mod>` deploys pre-built `dist/` artifacts to the pinned WoT version folder and also copies config/i18n.
- `wot_mods_cleanup <mod>` removes deployed WoT package/config targets for the selected mod.
- `wot_mods_cycle <mod>` performs cleanup + build + deploy.
- `wot_mods_cleanup`, `wot_mods_deploy`, and `wot_mods_cycle` require WoT to be closed and fail fast if the client is running.
- Prefer one-mod commands when the task is scoped to one mod.
- `dist/<mod-id>_<version>/` is the canonical release-bundle layout.

## Docs Sync Checklist

After every non-trivial change, explicitly ask whether any documentation became stale or is now missing new information.
Do not assume code-only work means docs are unaffected.

Review the smallest relevant set of these:

- root `README.md` for public entry points and workflow routing
- the affected mod README
- `docs/installing-mods.md`, `docs/building-from-source.md`, and `docs/developing-mods.md`
- `docs/reference/` pages for new technical discoveries or changed behavior
- `docs/resources.md` when a new external reference matters
- `tools/build.py` release-bundle `README.txt` template when install or package layout changes

Apply these repo-specific rules:

- Do not list WIP or experimental mods as public entry points until they have stable user-facing documentation.
- Prefer linking to third-party APIs or upstream docs rather than restating their documentation locally.
- If a change establishes a new runtime constraint or debugging finding, capture it in docs or repo memory rather than leaving it only in code.

## Dev Cycle Rule

When work is centered on a specific mod and local runtime validation would materially help:

1. Ask once per session whether the user wants `wot_mods_cycle <mod>` to be the default deploy/validation path for that mod.
2. Remember the answer for the session, keyed by mod name.
3. Reuse that choice until the user changes it.
4. If the user opts out, prefer `wot_mods_deploy <mod>` or a narrower validation step.

Do not ask about the dev cycle when:

- the task is docs-only
- there is no current mod being worked on
- the validation is obviously static and local

Record the session preference in session memory only when it is likely to matter again later in the session.
Keep the note short, for example: `research-progress-bar: prefer wot_mods_cycle by default`.

### Choosing `--fresh-log`

Decide this yourself; do not make it a routine user prompt.

Use `--fresh-log` when all of these are true:

- you plan to validate through `python.log`
- stale log noise would make the result ambiguous
- WoT is closed, because `--fresh-log` requires that

Avoid `--fresh-log` when:

- the work is docs-only or static
- you are not planning log-based validation
- preserving older log context matters
- WoT is running

Always note that WoT must be restarted or re-entered before Python, UI, or packaged asset changes are actually loaded by the client.

## Validation Order

- Touched Python file: prefer `python -m py_compile` or the narrowest available syntax/import check.
- For repo lint/format gates, prefer `./.venv/Scripts/python.exe -m tools.lint ...` if the shell's default `python` is not known-good for this repo.
- Packaging, UI, or build-flow change: run `wot_mods_build <mod>` or the relevant helper.
- Local runtime validation for one mod: ask once about the session dev-cycle preference, then use `wot_mods_cycle <mod>` or `wot_mods_deploy <mod>` as appropriate.
- Docs-only changes: verify links and references; do not run deploy scripts by default.

## Examples

### Docs-Only Change

- Update the relevant docs.
- Check whether root or mod-level docs also became stale.
- Run a markdown link sanity check.
- Skip deploy scripts unless the user explicitly wants them.

### Python Change In One Mod

- Update the code.
- Check docs fallout.
- Run a narrow Python validation step.
- If you need the repo lint gate, use the project venv explicitly before assuming the active shell can resolve the lint dependencies.
- If runtime validation matters, ask once about `wot_mods_cycle <mod>` and remember the answer.
- Use `--fresh-log` only when clean-log validation is the point and WoT is closed.

### UI Change

- Update AS3 and any paired Python integration.
- Let `wot_mods_build` or the deploy helpers invoke `ui/compile_ui.py` automatically.
- Treat WoT restart as required before interpreting in-game results.