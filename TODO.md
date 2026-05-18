# TODO

Follow-up backlog after the initial Python format-and-lint tooling rollout.

## Format-And-Lint Follow-Up

- Rerun `wot_mods_lint check` after the `research-progress-bar` cleanup and reassess whether `max-complexity = 25` should stay as-is or be tightened further.

## General Refactor Backlog

- Broad runtime splitting for `research-progress-bar` is mostly complete; only reopen it if `mods/research-progress-bar/src/zanju_rpb/main.py` or `mods/research-progress-bar/src/zanju_rpb/scaleform/modes.py` grow enough to justify another targeted slice.

## Research Progress Bar Guardrails

- Out of scope unless explicitly requested: changing mode semantics.
- Out of scope unless explicitly requested: redesigning the Scaleform layout.
- Out of scope unless explicitly requested: removing the production garage visibility-probe behavior.
- Future AS3 naming/package cleanup: build a second fake test mod and use it to collision-test default-package class names, helper names, and source/output path overlap before renaming `ResearchProgressBar*.as` files or introducing an AS3 package tree; the earlier unique-path finding justifies this test method, but file-path collisions and class-name collisions need to be validated separately.
- Future refactor guardrail: treat reflective prestige/elite adapter helpers in `zanju_rpb.main` as load-bearing runtime-contract code, not obvious dead code; before deleting or simplifying them, validate in-game across elite non-tier XI vehicles, tier XI vehicles, `eliteMode=customization_only`, and repeated vehicle switches.