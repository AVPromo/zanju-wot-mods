# TODO

Follow-up backlog after the initial Python format-and-lint tooling rollout.

## Format-And-Lint Follow-Up

- Rerun `wot_mods_lint check` after the `research-progress-bar` cleanup and reassess whether `max-complexity = 25` should stay as-is or be tightened further.

## General Refactor Backlog

- Split oversized runtime modules into smaller units as part of a broader codebase refactor, starting with `mods/research-progress-bar/src/zanju_rpb/main.py` and `mods/research-progress-bar/src/zanju_rpb/scaleform_modes.py`.

## Research Progress Bar Guardrails

- Out of scope unless explicitly requested: changing mode semantics.
- Out of scope unless explicitly requested: redesigning the Scaleform layout.
- Out of scope unless explicitly requested: removing the production garage visibility-probe behavior.
- Future refactor guardrail: treat reflective prestige/elite adapter helpers in `zanju_rpb.main` as load-bearing runtime-contract code, not obvious dead code; before deleting or simplifying them, validate in-game across elite non-tier XI vehicles, tier XI vehicles, `eliteMode=customization_only`, and repeated vehicle switches.