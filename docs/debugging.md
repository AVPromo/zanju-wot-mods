# Debugging

This page covers general debugging and compatibility work for mods in this repository.

## Triage Order

1. Confirm the active WoT version folder.
2. Reproduce with as few mods enabled as possible.
3. Capture `python.log`.
4. Find the first relevant traceback or state transition.
5. Re-enable dependencies one by one if the issue only appears in a modpack.

## Reading `python.log`

- `INFO` lines are often state markers.
- `WARNING` lines may be harmless or may be early failure signals.
- `ERROR` lines with tracebacks are the primary target.
- Service or HTTP failures are not automatically mod failures.

## Common Failure Classes

- wrong hook target after a patch
- missing optional dependency
- stale package deployed to the wrong `mods/<version>/` folder
- config schema mismatch
- UI assets moved or removed by the client
- hidden lifecycle bugs in custom windows or panels

## Hardening Rules

- keep hooks fail-safe
- handle missing data explicitly
- treat patch-day fixes as minimal-scope work
- prefer stable UI/model paths over deep runtime probing when both exist

## Daily Validation Loop

1. deploy the target mod
2. restart the game
3. reproduce the scenario once
4. inspect `python.log`
5. narrow the failing surface before editing again

## Version-Specific Notes

Version-bound stability findings should be recorded close to the mod or subsystem they belong to.
General debugging guidance should stay in this page.

## Related Reading

- [Developing Mods](developing-mods.md)
- [Resources And External Links](resources.md)
- [Technical Reference](reference/README.md)
