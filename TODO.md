# TODO

Follow-up backlog after the initial Python style-tooling rollout.

## Style-Gate Follow-Up

- Refactor `mods/research-progress-bar/src/zanju_rpb/main.py::_probe_t11_category_hints` and remove its temporary `# noqa: C901` suppression.
- Refactor `mods/research-progress-bar/src/zanju_rpb/main.py::_collect_post_progression` and remove its temporary `# noqa: C901` suppression.
- After both refactors land, rerun `wot_mods_lint check` and reassess whether `max-complexity = 25` should stay as-is or be tightened further.

## General Refactor Backlog

- Review `research-progress-bar` debug-heavy paths and remove debug-only code that is no longer useful.
- Split oversized runtime modules into smaller units as part of a broader codebase refactor, starting with `mods/research-progress-bar/src/zanju_rpb/main.py` and `mods/research-progress-bar/src/zanju_rpb/scaleform_modes.py`.