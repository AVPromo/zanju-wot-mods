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

## 8. Research Progress Bar Crash Boundary (WoT 2.2.1.1)

Confirmed during live testing:

- `fieldModsProbeMode=full` is unstable and can hard-crash the client.
- `extractNextStepXPLightweight=true` can also reintroduce crashes, even with `fieldModsProbeMode=next-step-only`.
- Crash signature: `python.log` stops shortly after `Running scheduled research update` with no Python traceback.
- In scheduled hangar updates, `PostProgressionStepItem.getType()` remained stable and useful for Tier XI bucket classification.
- In scheduled hangar updates, `PostProgressionStepItem.getPrice()` remained crash-prone and should still be treated as unsafe.

Known-safe baseline:

- `fieldModsProbeMode=next-step-only`
- `extractNextStepXPLightweight=false`
- Immediate deferred scheduling (`BigWorld.callback(0.0, ...)`) is validated as stable.
- The custom Scaleform garage bar is the active UI path; structured `python.log` output remains available for debugging.

Validated UI bridge finding:

- Opening the Tier XI Vehicle Hub upgrades UI (`mono/vehicle_hub/main`) triggers the presenter path that fills node view-models with real prices.
- Hooking the presenter-side fill step and reading the already-populated node view-model price was stable in live testing; the mod logged `Tier-11 UI cache captured` for all 26 nodes and then switched to `source=veh_skill_tree_vm`.
- This is not a default garage data source. If the relevant upgrades UI has not been opened in the current client session, there is no presenter-populated price data to reuse from the garage.
- Treat this presenter path as a safe validation or session-cache source, not as a full replacement for an always-available garage-side API.

Future safety rule:

- Do not add deep post-progression object traversal in the scheduled update path unless tested in staged probe modes first (`completion-only` -> `steps-only` -> `state-only` -> `next-step-only`), with stability checks at each step.
- If real data already exists in a UI model, prefer observing that model population over calling deeper runtime methods from the scheduled update path.

## 9. Research Progress Bar UI Visibility (WoT 2.2.1.2)

Confirmed during live tuning:

- `ContactsPopover`, `SessionStatsPopover`, `messenger/lobbyChannelWindow`, and `lobbyMenu` should not force the bar to hide once z-order is correct.
- Destroying and reloading the bar window during those popups causes flashing and can close or disturb the popup itself.
- The stable approach is a persistent `SFWindow` plus an SWF-side visibility callback.
- Crew and personal-case style flows can arrive as `TOP_SUB_VIEW` overlays and should still hide the bar.
- Equipment, shells, consumables, and directives can remain inside the hangar subview and only announce themselves through lobby-state-machine route changes such as `subScope/subLayer/hangar/loadout/...`.
- Treat only `subScope/subLayer/hangar` and `subScope/subLayer/hangar/{root}` as default visible hangar routes.

Useful diagnostics:

- `Garage view gate[...]` lines show visibility decision transitions, including the effective route, subview, and block reason.
- `Scaleform garage view visibility -> ...` lines show actual SWF visibility changes.
- View lifecycle lines such as load, populated, disposed, and any exception traceback remain the primary signals for crash diagnosis.
