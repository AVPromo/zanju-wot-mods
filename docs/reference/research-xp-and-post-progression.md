# Research, XP, And Post-Progression

## Vehicle XP And Free XP

Typical access pattern:

```python
stats = self.itemsCache.items.stats
veh_xp = stats.vehiclesXPs.get(veh_intCD, 0)
free_xp = stats.freeXP
actual_free_xp = stats.actualFreeXP
pp_xp = stats.postProgressionXP
ext_money = stats.getMoneyExt(veh_intCD)
```

Useful related data:

- `stats.unlocks`
- `stats.initialUnlocks`
- `stats.eliteVehicles`
- `stats.multipliedVehicles`
- `stats.prestigeMilestonesAchieved`

Vehicle-facing XP and unlock properties:

```python
vehicle.xp
vehicle.dailyXPFactor
vehicle.isElite
vehicle.isFullyElite
vehicle.getUnlocksDescrs()
vehicle.getUnlockDescrByIntCD(intCD)
vehicle.getAutoUnlockedItems()
vehicle.getEliteStatusProgress()
```

## Vehicle Research Surface

Useful `Vehicle` properties and methods include:

- `vehicle.xp`
- `vehicle.dailyXPFactor`
- `vehicle.isElite`
- `vehicle.isFullyElite`
- `vehicle.getUnlocksDescrs()`
- `vehicle.getUnlockDescrByIntCD(intCD)`
- `vehicle.getAutoUnlockedItems()`
- `vehicle.getEliteStatusProgress()`

Module and equipment surfaces commonly used during research/mod-state work:

```python
vehicle.modules
vehicle.optDevices
vehicle.consumables
vehicle.battleBoosters
vehicle.battleAbilities
vehicle.shells
vehicle.setupLayouts
```

Checking whether a module is unlocked:

```python
unlocks = self.itemsCache.items.stats.unlocks
is_module_unlocked = module_intCD in unlocks
```

## Post-Progression Imports

Common post-progression imports:

```python
from post_progression_common import ACTION_TYPES, VEH_SKILL_TREE_ID_OFFSET
from skeletons.gui.game_control import IVehiclePostProgressionController
from gui.veh_post_progression.models.progression import PostProgressionItem
from gui.veh_post_progression.models.modifications import PostProgressionActionItem
```

Additional useful post-progression constants and helpers:

```python
from post_progression_common import (
	ACTION_TYPES,
	PAIR_TYPES,
	TankSetupLayouts,
	TankSetups,
	TankSetupGroupsId,
	TANK_SETUP_GROUPS,
	FEATURE_BY_GROUP_ID,
	GROUP_ID_BY_FEATURE,
	GROUP_ID_BY_LAYOUT,
	ROLESLOT_FEATURE,
	SETUPS_FEATURES,
	FEATURES_NAMES,
	VehicleState,
	makeActionCompDescr,
	parseActionCompDescr,
	VEH_SKILL_TREE_ID_OFFSET,
)
```

## Post-Progression Objects

Common live object surface:

```python
pp = vehicle.postProgression

pp.isActive(vehicle)
pp.isExists()
pp.isAvailable(vehicle)
pp.isVehSkillTree()
pp.getCompletion()
pp.iterOrderedSteps()
pp.iterUnorderedSteps()
pp.getStep(stepID)
pp.getFirstPurchasableStep(balance)
pp.getState()
pp.getRawTree()
```

Vehicle-level helpers:

```python
vehicle.postProgression
vehicle.isPostProgressionActive
vehicle.isPostProgressionExists
vehicle.isRoleSlotActive
vehicle.postProgressionAvailability(unlockOnly=False)
```

Controller access pattern:

```python
from skeletons.gui.game_control import IVehiclePostProgressionController

class MyMod(object):
	postProgressionCtrl = dependency.descriptor(IVehiclePostProgressionController)
```

## Safety Notes For This Repo

Live testing in this repository established a practical safety boundary:

- shallow post-progression reads can be stable
- deep scheduled-update traversal can hard-crash the client with no Python traceback
- presenter/view-model materialization is often safer than deeper runtime probing when the same value is already exposed through UI state

Validated local safety boundary:

- `PostProgressionStepItem.getType()` was stable in scheduled hangar updates used by this repo
- `PostProgressionStepItem.getPrice()` should still be treated as unsafe in scheduled hangar updates
- `pp.getFirstPurchasableStep(balance)` is useful as a safer hint source than deeper price traversal

## Tier XI / Vehicle Hub Notes

Tier XI data often surfaces through the vehicle hub and skill-tree presenters rather than through a single clean always-available garage-side API.
Treat those UI-derived values as session-scoped data sources, not as proof that deeper object traversal is safe in all contexts.

The most important practical consequence is that presenter-populated data can be reused once the relevant UI has been opened in the session, but it should not be treated as a guaranteed always-available garage-side API.
