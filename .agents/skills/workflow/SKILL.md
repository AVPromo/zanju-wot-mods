---
name: workflow
description: "Repository workflow guidance for zanju-wot-mods. Use when working on mods, build/deploy scripts, docs, validation, release bundles, or WoT UI assets. Keywords: build.py, dev_test_deploy.py, dev_test_cycle.py, python.log, docs sync, release bundle, research-progress-bar."
---

# Repository Workflow

Use this skill for normal work in this repository.
It captures repo-specific conventions, documentation expectations, and validation workflow.

## Use This Skill For

- Editing a mod under `mods/<name>/`.
- Changing packaging, deployment, release-bundle, or build behavior.
- Updating docs or checking whether docs became stale after a code change.
- Deciding whether to run `build.py`, `dev_test_deploy.py`, or `dev_test_cycle.py`.
- Working on WoT UI assets, Scaleform code, or Python/runtime integration.

## Core Principles

1. Keep docs current whenever behavior, install steps, build flow, or technical knowledge changes.
2. Prefer repo-established patterns over inventing a new structure.
3. Validate at the narrowest useful scope first, then use build/deploy/runtime checks when the change warrants it.
4. Treat WoT as non-hot-reloading: copying files to disk is not proof that the running client loaded them.

## Repo Conventions

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

- `build.py` automatically runs `mods/<mod>/ui/compile_ui.py` when present.
- Generated UI output belongs under `mods/<mod>/ui/build/res/`.
- For garage Scaleform views, reuse the repo's WoT-compatible view pattern rather than ad hoc raw display roots.

### Packaging And Deploy

- `python build.py <mod>` is the canonical package build for one mod.
- `python dev_test_deploy.py <mod>` builds and deploys the mod to every detected `mods/<version>/` folder and also copies config/i18n.
- `python dev_test_cycle.py <mod>` performs cleanup and then deploy.
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
- `build.py` release-bundle `README.txt` template when install or package layout changes

Apply these repo-specific rules:

- Do not list WIP or experimental mods as public entry points until they have stable user-facing documentation.
- Prefer linking to third-party APIs or upstream docs rather than restating their documentation locally.
- If a change establishes a new runtime constraint or debugging finding, capture it in docs or repo memory rather than leaving it only in code.

## Dev Cycle Rule

When work is centered on a specific mod and local runtime validation would materially help:

1. Ask once per session whether the user wants `python dev_test_cycle.py <mod>` to be the default deploy/validation path for that mod.
2. Remember the answer for the session, keyed by mod name.
3. Reuse that choice until the user changes it.
4. If the user opts out, prefer `python dev_test_deploy.py <mod>` or a narrower validation step.

Do not ask about the dev cycle when:

- the task is docs-only
- there is no current mod being worked on
- the validation is obviously static and local

Record the session preference in session memory only when it is likely to matter again later in the session.
Keep the note short, for example: `research-progress-bar: prefer dev_test_cycle by default`.

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
- Packaging, UI, or build-flow change: run `python build.py <mod>` or the relevant helper.
- Local runtime validation for one mod: ask once about the session dev-cycle preference, then use `dev_test_cycle.py <mod>` or `dev_test_deploy.py <mod>` as appropriate.
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
- If runtime validation matters, ask once about `dev_test_cycle.py <mod>` and remember the answer.
- Use `--fresh-log` only when clean-log validation is the point and WoT is closed.

### UI Change

- Update AS3 and any paired Python integration.
- Let `build.py` or the deploy helpers invoke `ui/compile_ui.py` automatically.
- Treat WoT restart as required before interpreting in-game results.