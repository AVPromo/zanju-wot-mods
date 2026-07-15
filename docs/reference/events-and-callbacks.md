# Events And Callbacks

## Current Vehicle Events

Typical hooks:

```python
from CurrentVehicle import g_currentVehicle, g_currentPreviewVehicle

g_currentVehicle.onChanged += handler
g_currentVehicle.onChangeStarted += handler

g_currentPreviewVehicle.onChanged += handler
g_currentPreviewVehicle.onChangeStarted += handler
g_currentPreviewVehicle.onComponentInstalled += handler
g_currentPreviewVehicle.onPostProgressionChanged += handler
g_currentPreviewVehicle.onVehicleUnlocked += handler
g_currentPreviewVehicle.onVehicleInventoryChanged += handler
g_currentPreviewVehicle.onSelected += handler
```

## Player Events

```python
from PlayerEvents import g_playerEvents

g_playerEvents.onInventoryResync += handler
g_playerEvents.onDossiersResync += handler
g_playerEvents.onStatsResync += handler
```

## Items Cache Sync Events

```python
itemsCache.onSyncStarted += handler
itemsCache.onSyncCompleted += handler
itemsCache.onSyncFailed += handler
itemsCache.onPMSyncCompleted += handler
```

Typical post-progression diff check:

```python
def _onSyncCompleted(self, _, diff):
    if self.intCD in diff.get(GUI_ITEM_TYPE.VEH_POST_PROGRESSION, {}):
        self._onPostProgressionUpdate()
```

## Client Update Manager

Key-based callback pattern:

```python
from gui.ClientUpdateManager import g_clientUpdateManager

g_clientUpdateManager.addCallbacks({
    'inventory': self._onInventoryUpdate,
    'stats.unlocks': self._onUpdateUnlocks,
    'cache.vehsLock': self._onLocksUpdate,
    'groupLocks': self._onRotationUpdate,
})

g_clientUpdateManager.removeObjectCallbacks(self)
```

## Lifecycle Pattern

Typical mod lifecycle shape:

```python
class MyMod(object):
    def init(self):
        g_playerEvents.onInventoryResync += self.__onInventoryResync
        g_playerEvents.onStatsResync += self.__onStatsResync
        self.itemsCache.onSyncCompleted += self.__onSyncCompleted

    def fini(self):
        self.itemsCache.onSyncCompleted -= self.__onSyncCompleted
        g_playerEvents.onStatsResync -= self.__onStatsResync
        g_playerEvents.onInventoryResync -= self.__onInventoryResync
```

## Notes

- Prefer explicit unsubscribe paths in reverse order during shutdown.
- Treat sync callbacks as noisy and diff-driven; filter them down to the specific GUI item types or cache keys you actually need.
- Early transition events often arrive before every dependent object is ready, so keep guards around vehicle and preview state.
- `g_currentVehicle.onChanged` only fires on a vehicle *switch*. It is not enough to
  follow server-confirmed changes to the selected vehicle (a research, purchase or
  unlock): those arrive as an items-cache sync, so the UI silently keeps showing the
  pre-change state until the player switches vehicles. Subscribe to
  `itemsCache.onSyncCompleted(updateReason, invalidItems)` as well
  (`ItemsCache.__invalidateData`/`__invalidateFullData` fire it with those two args).
  Filtering it is optional if the resulting update is coalesced to the next tick and
  exits early while the UI is hidden — correctness is easier to keep than a diff filter.

## Refreshing The Hangar Bottom Bar (Loadout Panel) After A Server-Side Change

Verified live on EU 2.3 while wiring the loadout-switch toggle; implementation
in `mods/research-progress-bar/src/zanju_rpb/actions.py`.

The 2.x hangar bottom bar (crew / modules / directives / ammunition /
consumables, with the loadout switches and their status dots) is
`gui.impl.lobby.hangar.presenters.loadout_presenter.LoadoutPresenter` plus its
child presenters — NOT the classic `ammunition_panel` view, whose refresh
hooks (`AmmunitionInjectEvent.INVALIDATE_INJECT_VIEW`, its
`g_currentVehicle.onChanged` full update) fire into nothing in this hangar.

Why it never refreshes in place: all these presenters render from an
`InteractingItem` (`gui.impl.lobby.tank_setup.interactors.base`) holding a
vehicle COPY made when the panel loaded. `LoadoutPresenter.__onVehicleChanged`
only rebuilds that copy when the vehicle actually changes
(`needToRecreate = intCD differs or item dead`); a same-vehicle
`g_currentVehicle.onChanged` keeps the stale copy — raising the event
repeatedly just re-reads stale data (and re-renders the whole hangar).

Working refresh recipe, scoped to the bar:

1. Wait until the changed state is actually READABLE. An item-action's success
   code returns fast (~0.3s), but the inventory diff carrying the new state
   arrives with a later batched server sync (observed ~0.1s up to many
   seconds). Poll the readable state, re-resolving `g_currentVehicle.item`
   each tick — itemsCache can REPLACE the gui item instance when the diff
   lands, so a captured reference can stay stale forever.
2. Swap a fresh copy into the live `InteractingItem` (mirror WG's
   `__createVehicleCopy`: `items.getVehicleCopy(current)` + battle-abilities
   sync), found via `gc.get_objects()` isinstance scan (fine at click
   frequency).
3. Fire `wrapper.onItemUpdated(None)`: `LoadoutPresenter.__onItemUpdated`
   pushes the fresh copy into its ammunition groups controller
   (`updateVehicle` + `updateGroupsModels` → `_setupStates`), rewriting the
   switch models without touching the rest of the hangar.

Note: swapping the copy discards un-applied draft edits in the bar (same as a
vehicle re-selection).

The same refresh is needed after any server-side change the bar renders, not just
the loadout switches — e.g. picking the second slot category
(`SET_EQUIPMENT_SLOT_TYPE`) leaves the panel showing the old category otherwise.
Each such change needs its own readable, server-confirmed value to wait on, since
the action's success code returns before the diff lands:

- loadout switch: the disabled-switch state (see
  `_resolve_post_progression_setup_switch_active`).
- second slot category: `items.inventory.getDynSlotTypeID(vehIntCD)` (0 when
  unset). This is the value `RoleSlotModItem.__applyDynamicSlotCategory` derives
  its displayed category from, so it is exactly what the panel re-reads.

Performance: the gc scan and WG's group-model rebuild each cause a small
main-thread hitch. Cache the found wrappers between uses (they survive vehicle
changes — LoadoutPresenter reuses them via `setItem`; liveness =
`getItem() is not None and len(wrapper.onItemUpdated) > 0`, since WG's `Event`
subclasses `list` and a finalized presenter tree leaves it empty) and pre-warm
the cache at click time so the scan merges into the game's own click freeze
instead of stacking a second one. The rebuild cost itself is WG's — their own
UI freezes the same way on this update.
