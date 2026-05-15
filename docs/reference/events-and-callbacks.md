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