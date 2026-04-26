# Debugging and Compatibility Playbook

## 1. Triage Order

When a mod breaks after a patch:

1. Confirm game version folder (`mods/<version>` mismatch is common).
2. Disable all but one suspected mod.
3. Reproduce once and capture `python.log`.
4. Search for first traceback, not last error line.
5. Re-enable dependencies incrementally.

## 2. Log Reading Rules

- `INFO` spam is usually not actionable.
- `WARNING` can be harmless or pre-failure signal.
- `ERROR` with traceback is primary target.
- Web/API response errors (e.g. HTTP 409) may be state-related, not code defects.

## 3. Common Root Causes

- Missing optional dependency
- Changed event/battle type in new patch
- Hooking wrong method name after client update
- Config schema mismatch or corrupted config
- UI resources moved or removed

## 4. Hardening Techniques

- Wrap hook logic in fail-safe guards.
- Use explicit fallback behavior when data missing.
- Keep ignore lists for unsupported battle modes.
- Avoid assumptions about vehicle descriptors in early battle states.

## 5. Patch Day Routine

1. Update folder paths to current version.
2. Run smoke tests: login, hangar, queue, battle start, battle end, replay.
3. Check for renamed imports/modules.
4. Release hotfix with minimal scope.
5. Update changelog with exact failure and fix.

## 6. Inter-Mod Conflict Isolation

- Temporarily remove XVM macros and heavy UI modifiers first.
- Test with and without settings/menu APIs.
- If issue appears only in modpack, verify load order and duplicate assets.

## 7. Quality Baseline Before Release

- No uncaught traceback in standard flow
- No broken UI panel lifecycle (create/destroy loops)
- Config auto-repair or migration works
- Clear uninstall path and rollback note
