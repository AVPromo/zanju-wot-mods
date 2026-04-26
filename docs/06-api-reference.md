# WoT Mod API Reference — XP, Research, Modules, Field Modifications

> Source: decompiled from `Armagomen/wot_decompiled` (WoT client v2.1.1.0).  
> All paths are relative to `scripts/client/` unless marked `[common]` (shared with server, from `scripts/common/`).

---

## 1. Python Import Paths

### Core vehicle & cache

```python
from CurrentVehicle import g_currentVehicle, g_currentPreviewVehicle
from gui.ClientUpdateManager import g_clientUpdateManager
from gui.shared.gui_items.Vehicle import Vehicle
from gui.shared.gui_items import GUI_ITEM_TYPE, GUI_ITEM_TYPE_NAMES
from gui.shared.gui_items.vehicle_equipment import VehicleEquipment, SUPPORT_EXT_DATA_FEATURES
from gui.shared.utils.requesters import REQ_CRITERIA
from gui.shared.money import Money, Currency, DynamicMoney
from skeletons.gui.shared import IItemsCache
from skeletons.gui.shared.gui_items import IGuiItemsFactory
from helpers import dependency
from items.vehicles import VehicleDescr, getItemByCompactDescr, getVehicleType
from items import filterIntCDsByItemType, getTypeInfoByName, getTypeOfCompactDescr, vehicles
from dossiers2.custom.cache import getCache as getDossiersCache
```

### Events & player state

```python
from Event import Event, EventManager
from PlayerEvents import g_playerEvents
```

### Post-progression (field modifications / "experimental upgrades")

```python
# [common] — importable from both client and server
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
    unpackActionCDs,
    packPostProgression,
    makeDefaultSetupsIndexes,
    makeDefaultSetupsInVehicle,
    VEH_SKILL_TREE_ID_OFFSET,
    EXT_DATA_SLOT_KEY,         # = 'customRoleSlotTypeId'
    EXT_DATA_PROGRESSION_KEY,  # = 'vehPostProgression'
    SERVER_SETTINGS_KEY,       # = 'vehicle_post_progression_config'
)

# Client-side GUI models
from gui.veh_post_progression.models.progression import (
    PostProgressionItem,
    PostProgressionAvailability,
    PostProgressionCompletion,
    AvailabilityCheckResult,
)
from gui.veh_post_progression.models.modifications import (
    PostProgressionActionItem,
    PostProgressionActionState,
    PostProgressionActionTooltip,
)
from gui.veh_post_progression.models.ext_money import ExtendedMoney
from gui.veh_post_progression import helpers as vpp_helpers

# Controller skeleton (dependency injection)
from skeletons.gui.game_control import IVehiclePostProgressionController
```

### Stats / XP requester

```python
from gui.shared.utils.requesters.StatsRequester import StatsRequester
# Accessed via itemsCache (not instantiated directly):
from skeletons.gui.shared.utils.requesters import IStatsRequester
```

### Account settings

```python
from account_helpers.AccountSettings import (
    AccountSettings,
    CURRENT_VEHICLE,
    ROYALE_VEHICLE,
    VPP_ENTRY_POINT_LAST_SEEN_STEP,
)
```

### Nation change helpers

```python
from nation_change.nation_change_helpers import NationalGroupDataAccumulator
```

---

## 2. Vehicle XP & Research Progress

### Accessing XP and unlock data

All accessed via the `itemsCache` singleton (injected with `dependency.descriptor(IItemsCache)`):

```python
class MyMod(object):
    itemsCache = dependency.descriptor(IItemsCache)

    def _example(self):
        stats = self.itemsCache.items.stats

        # --- Vehicle XP ---
        veh_xp = stats.vehiclesXPs.get(veh_intCD, 0)
        # vehiclesXPs is a NationalGroupDataAccumulator wrapping getCacheValue('vehTypeXP', {})

        # --- Free XP ---
        free_xp = stats.freeXP          # max(actualFreeXP, 0)
        actual_free_xp = stats.actualFreeXP  # getCacheValue('freeXP', 0) — wallet-gated

        # --- Post-progression (field mod) XP ---
        pp_xp = stats.postProgressionXP  # getCacheValue('XPpp', 0)

        # --- ExtendedMoney (combines vehXP + freeXP for unlock windows) ---
        ext = stats.getMoneyExt(veh_intCD)
        # ext.xp = freeXP + vehicleXP
        # ext.vehXP = vehicleXP
        # ext.freeXP = freeXP

        # --- Unlocks (set of intCDs that are researched) ---
        unlocked_set = stats.unlocks          # getCacheValue('unlocks', set())
        initial_unlocks = stats.initialUnlocks  # getCacheValue(('initial', 'unlocks'), set())

        # --- Elite vehicles ---
        elite_set = stats.eliteVehicles       # getCacheValue('eliteVehicles', set())

        # --- Daily XP multiplier vehicles ---
        multiplied = stats.multipliedVehicles  # getCacheValue('multipliedXPVehs', list())

        # --- Prestige/Elite Levels milestones ---
        milestones = stats.prestigeMilestonesAchieved  # getCacheValue('prestigeMilestonesAchieved', dict())

        # --- Max researched tier by nation ---
        by_nation = stats.getMaxResearchedLevelByNations()  # dict nationID -> int
        max_tier = stats.getMaxResearchedLevel(nationID)    # int, default = MIN_VEHICLE_LEVEL
```

### `Vehicle` properties (GUI item, from `gui.shared.gui_items.Vehicle`)

```python
vehicle = self.itemsCache.items.getVehicle(invID)  # returns Vehicle | None
vehicle = self.itemsCache.items.getItemByCD(intCD)  # by compact descriptor

# XP
vehicle.xp             # tank XP (int)
vehicle.dailyXPFactor  # daily XP multiplier (int, -1 if not applicable)

# Elite/unlock status
vehicle.isElite        # True if all stock modules are unlocked
vehicle.isFullyElite   # True if all researches done (isElite + no pending unlocksDescrs)

# Unlock descriptors — tech tree research nodes
for unlockIdx, xpCost, intCD, prereqs in vehicle.getUnlocksDescrs():
    pass  # unlockIdx: int, xpCost: int, intCD: int, prereqs: set of intCDs

unlockIdx, xpCost, prereqs = vehicle.getUnlockDescrByIntCD(intCD)
# Returns (-1, 0, set()) if not found

auto_unlocked = vehicle.getAutoUnlockedItems()  # list of intCDs unlocked automatically

# Elite progress breakdown
progress = vehicle.getEliteStatusProgress()
# progress.unlocked  -> set of unlocked module intCDs
# progress.toUnlock  -> set of not yet unlocked intCDs
# progress.total     -> all modules required for elite

# Compact descriptor
vehicle.intCD          # int compact descriptor
vehicle.invID          # inventory ID
vehicle.descriptor     # VehicleDescr (items level)
vehicle.typeDescr      # vehicle type descriptor (= descriptor.type)
vehicle.isInInventory  # bool — owned
vehicle.isLocked       # bool — locked (in battle / queue)
vehicle.isRented       # bool
vehicle.rentalIsOver   # bool
vehicle.isBroken       # bool
vehicle.hasModulesToSelect  # bool — has module research choices
```

---

## 3. Module Unlocking & Tech Tree

### Module access

```python
vehicle.gun          # VehicleGun
vehicle.turret       # VehicleTurret (None if no turrets)
vehicle.engine       # VehicleEngine
vehicle.chassis      # VehicleChassis
vehicle.radio        # VehicleRadio
vehicle.fuelTank     # VehicleFuelTank
vehicle.modules      # tuple: (chassis, turret|None, gun, engine, radio)

vehicle.optDevices      # VehicleEquipment — optional devices
vehicle.consumables     # consumables
vehicle.battleBoosters  # battle boosters
vehicle.battleAbilities # battle abilities
vehicle.shells          # ammunition
vehicle.setupLayouts    # dual/alternate equipment setup layouts
```

### `GUI_ITEM_TYPE` constants relevant to modules/research

```python
from gui.shared.gui_items import GUI_ITEM_TYPE

GUI_ITEM_TYPE.VEHICLE
GUI_ITEM_TYPE.TURRET
GUI_ITEM_TYPE.GUN
GUI_ITEM_TYPE.CHASSIS
GUI_ITEM_TYPE.ENGINE
GUI_ITEM_TYPE.RADIO
GUI_ITEM_TYPE.FUEL_TANK
GUI_ITEM_TYPE.VEHICLE_MODULES   # group: all module types
GUI_ITEM_TYPE.OPT_DEVICE
GUI_ITEM_TYPE.SHELL
GUI_ITEM_TYPE.TANKMAN
GUI_ITEM_TYPE.VEH_POST_PROGRESSION  # used in sync diff for field mod updates
GUI_ITEM_TYPE.CUSTOMIZATION
GUI_ITEM_TYPE.CAMOUFLAGE
GUI_ITEM_TYPE.MODIFICATION
```

### Checking if a module is unlocked

```python
unlocks = self.itemsCache.items.stats.unlocks   # set of intCDs
is_module_unlocked = module_intCD in unlocks

# Or on the vehicle descriptor level:
for unlockIdx, data in enumerate(vehicle.descriptor.type.unlocksDescrs):
    # data[0] = xpCost, data[1] = intCD, data[2:] = prereq intCDs
    if data[1] == target_intCD:
        is_prereq_met = all(p in unlocks for p in data[2:])
```

### `REQ_CRITERIA` for vehicle queries

```python
from gui.shared.utils.requesters import REQ_CRITERIA

vehicles = self.itemsCache.items.getVehicles(
    criteria=REQ_CRITERIA.INVENTORY
            | ~REQ_CRITERIA.VEHICLE.MODE_HIDDEN
            | ~REQ_CRITERIA.VEHICLE.EVENT_BATTLE
            | REQ_CRITERIA.VEHICLE.ACTIVE_IN_NATION_GROUP
)
```

---

## 4. Field Modifications / Post-Progression ("Experimental / Tier-11 Upgrades")

### Constants (`post_progression_common` — `[common]`)

```python
# Feature names (strings used as keys)
ROLESLOT_FEATURE = 'roleSlot'
SETUPS_FEATURES = ('shells_consumables_switch', 'opt_dev_boosters_switch')
FEATURES_NAMES = SETUPS_FEATURES + (ROLESLOT_FEATURE,)

# Inventory ext data keys
EXT_DATA_SLOT_KEY = 'customRoleSlotTypeId'
EXT_DATA_PROGRESSION_KEY = 'vehPostProgression'

# Server settings key
SERVER_SETTINGS_KEY = 'vehicle_post_progression_config'

# Prices keys
POST_PROGRESSION_UNLOCK_MODIFICATIONS_PRICES = (
    'unlockBaseModificationCost', 'unlockPairModificationCost',
    'Modification10000xp', 'Modification20000xp', 'Modification25000xp',
    'Modification30000xp', 'Modification40000xp'
)
POST_PROGRESSION_BUY_MODIFICATIONS_PRICES = ('buyPairModificationCost',)

# Currencies allowed
ALLOWED_CURRENCIES_FOR_TREE_STEP = {'xp'}
ALLOWED_CURRENCIES_FOR_BUY_MODIFICATION_STEP = {'credits'}

# Skill tree ID offset (veh-specific skill trees have id >= 10000)
VEH_SKILL_TREE_ID_OFFSET = 10000
```

### `ACTION_TYPES` class

```python
class ACTION_TYPES:
    MODIFICATION = 1       # single modification (permanent)
    PAIR_MODIFICATION = 2  # choose one of two modifications
    FEATURE = 3            # enable a feature (e.g. dual setup switch, role slot)
    BIT_PACK = 4           # internal packed format
```

### `PAIR_TYPES` class

```python
class PAIR_TYPES:
    NOT_SET = 0
    FIRST = 1
    SECOND = 2
```

### `TankSetupLayouts` / `TankSetups` / `TankSetupGroupsId`

```python
class TankSetupLayouts(object):
    OPTIONAL_DEVICES = 'devicesLayout'
    EQUIPMENT        = 'eqsLayout'
    SHELLS           = 'shellsLayout'
    BATTLE_BOOSTERS  = 'boostersLayout'

class TankSetups(object):
    OPTIONAL_DEVICES = 'devicesSetups'
    EQUIPMENT        = 'eqsSetups'
    SHELLS           = 'shellsSetups'
    BATTLE_BOOSTERS  = 'boostersSetups'

class TankSetupGroupsId(object):
    EQUIPMENT_AND_SHELLS             = 1  # consumables + shells dual-setup
    OPTIONAL_DEVICES_AND_BOOSTERS    = 2  # opt devices + boosters dual-setup

# Full mapping: group -> (layout1, layout2)
TANK_SETUP_GROUPS = {
    TankSetupGroupsId.OPTIONAL_DEVICES_AND_BOOSTERS: (
        TankSetupLayouts.OPTIONAL_DEVICES,
        TankSetupLayouts.BATTLE_BOOSTERS,
    ),
    TankSetupGroupsId.EQUIPMENT_AND_SHELLS: (
        TankSetupLayouts.EQUIPMENT,
        TankSetupLayouts.SHELLS,
    ),
}

# Feature name -> group id
FEATURE_BY_GROUP_ID = {
    TankSetupGroupsId.EQUIPMENT_AND_SHELLS:          'shells_consumables_switch',
    TankSetupGroupsId.OPTIONAL_DEVICES_AND_BOOSTERS: 'opt_dev_boosters_switch',
}
```

### `VehicleState` class (tracks per-vehicle post-progression state)

```python
from post_progression_common import VehicleState

state = VehicleState()               # empty state
state = VehicleState(data)           # from raw data (list of 4 items)
state = vehicle.postProgression.getState()  # copy from live vehicle

# Unlock steps
state.unlocks                        # set of unlocked stepIDs
state.isUnlocked(stepID)             # bool
state.addUnlock(stepID)
state.removeUnlock(stepID)

# Pair choices (for PAIR_MODIFICATION actions)
state.pairs                          # dict stepID -> PAIR_TYPES value
state.setPair(stepID, PAIR_TYPES.FIRST)
state.getPair(stepID)                # returns PAIR_TYPES value or None
state.removePair(stepID)

# Features (dual-setup / role slot)
state.features                       # set of featureIDs
state.hasFeature(featureID)
state.addFeature(featureID)
state.removeFeature(featureID)

# Disabled switches (alternate setups temporarily disabled pre-battle)
state.disabledSwitches               # set of groupIDs
state.isSwitchDisabled(groupID)
state.addDisabledSwitch(groupID)
state.removeDisabledSwitch(groupID)
state.toggleSwitchLayout(groupID)

# Serialization
state.toRawData()                    # list[unlocks, pairs, features, disabledSwitches]
state.toActionCDs(tree)              # list of compact descriptors for server
state.toBattleActionCDsPack(tree)    # packed int for battle

# Utility
state.clean(removeUnlocks, removePairs, removeFeatures, removeDisabledSwitches)
state.isEmpty()                      # bool
state.isResearchedTree(tree)         # bool — all steps done
```

### `PostProgressionItem` — the GUI model for a vehicle's field mods

```python
pp = vehicle.postProgression   # PostProgressionItem | None (lazy, from Vehicle property)

# Availability checks
pp.isActive(veh)               # exists + not disabled
pp.isExists(settings=None)     # server feature flag enabled for this vehType
pp.isDisabled(veh, settings=None, skipRentalIsOver=False)
pp.isAvailable(veh, unlockOnly=False)  # AvailabilityCheckResult (truthy if available)
pp.isRoleSlotActive(veh)       # role slot specifically active
pp.isRoleSlotExists(externalState=None)
pp.isSetupSwitchActive(veh, groupID)   # dual setup switch active for given group
pp.isPrebattleSwitchDisabled(groupID)
pp.isFeatureEnabled(featureName)       # server config check
pp.isDefined()                 # has a ProgressionTree in cache
pp.isVehSkillTree()            # tree.id >= VEH_SKILL_TREE_ID_OFFSET

# Completion
pp.getCompletion()             # PostProgressionCompletion.EMPTY / PARTIAL / FULL

# Steps
pp.iterOrderedSteps()          # OrderedStepsIterator — steps in unlock order
pp.iterUnorderedSteps()        # UnorederdStepsIterator — all steps
pp.getStep(stepID)             # PostProgressionStepItem
pp.getFirstPurchasableStep(balance)  # step purchasable with given ExtendedMoney | None

# Active modifications
pp.getActiveModifications(vehicle, ignoreDisabled=False)
    # returns [actionID, ...] for received steps with a non-None activeID

# Pairs
pp.getInstalledMultiIds()      # (stepIDs_list, purchasedTypeID_list)

# Raw data
pp.getRawTree()                # ProgressionTree from vehicles.g_cache
pp.getState(implicitCopy=True) # VehicleState
pp.getVehType()                # VehicleType
pp.setState(state)
pp.clone()                     # deep copy
```

### `PostProgressionAvailability` enum values

```python
PostProgressionAvailability.AVAILABLE
PostProgressionAvailability.NOT_EXISTS
PostProgressionAvailability.VEH_NOT_ELITE
PostProgressionAvailability.VEH_NOT_IN_INVENTORY
PostProgressionAvailability.VEH_IS_RENTED
PostProgressionAvailability.VEH_IS_RENT_OVER
PostProgressionAvailability.VEH_IN_BATTLE
PostProgressionAvailability.VEH_IN_FORMATION
PostProgressionAvailability.VEH_IN_QUEUE
PostProgressionAvailability.VEH_IN_BREAKER
PostProgressionAvailability.VEH_IS_BROKEN
```

### Action compact descriptor helpers

```python
from post_progression_common import makeActionCompDescr, parseActionCompDescr

# Pack
cd = makeActionCompDescr(ACTION_TYPES.MODIFICATION, itemId, subId=0)
cd = makeActionCompDescr(ACTION_TYPES.PAIR_MODIFICATION, itemId, PAIR_TYPES.FIRST)
cd = makeActionCompDescr(ACTION_TYPES.FEATURE, featureId, 0)

# Unpack
actionType, itemID, subId = parseActionCompDescr(cd)
```

### Helper functions (`gui.veh_post_progression.helpers`)

```python
from gui.veh_post_progression.helpers import (
    getVehicleState,       # list[actionCD] -> VehicleState (features only)
    setFeatures,           # (state, actionCDs) -> None
    setDisabledSwitches,   # (state, groupIDs) -> None
    getInstalledShells,    # (shellsCDs, shellsLayout) -> installed list
    updateInvInstalled,    # (invData, setupsIndexes) -> None
    storeLastSeenStep,     # (vehicleIntCD, stepID) -> None
    needToShowCounter,     # (vehicle) -> bool — show "new step available" badge
)
```

### Getting field mod data on Vehicle

```python
vehicle.postProgression              # PostProgressionItem
vehicle.isPostProgressionActive      # bool
vehicle.isPostProgressionExists      # bool
vehicle.isRoleSlotActive             # bool
vehicle.postProgressionAvailability(unlockOnly=False)  # AvailabilityCheckResult

# Methods
vehicle.installPostProgression(customState, ignoreDisabled=False, rebuildAttrs=True)
vehicle.installPostProgressionItem(postProgressionItem)
vehicle.clearPostProgression()
vehicle.isSetupSwitchActive(groupID)  # True if dual-setup for this group is active
```

### Controller (dependency injection)

```python
from skeletons.gui.game_control import IVehiclePostProgressionController

class MyMod(object):
    __postProgressionCtrl = dependency.descriptor(IVehiclePostProgressionController)

    def check(self, vehicle):
        ctrl = self.__postProgressionCtrl
        ctrl.isDisabledFor(vehicle)               # bool
        ctrl.isExistsFor(vehType, settings=None)  # bool
        ctrl.getSettings()                         # VehiclePostProgressionConfig
        ctrl.processVehExtData(vehType, extData)
```

---

## 5. Events & Callbacks

### `g_currentVehicle` events

```python
from CurrentVehicle import g_currentVehicle, g_currentPreviewVehicle

g_currentVehicle.onChanged        += handler  # after selection changes
g_currentVehicle.onChangeStarted  += handler  # before change begins
g_currentVehicle.onChanged        -= handler  # unsubscribe
```

### `g_currentPreviewVehicle` events (tech tree / preview screen)

```python
g_currentPreviewVehicle.onChanged              += handler
g_currentPreviewVehicle.onChangeStarted        += handler
g_currentPreviewVehicle.onComponentInstalled   += handler  # module preview installed
g_currentPreviewVehicle.onPostProgressionChanged += handler  # field mod updated
g_currentPreviewVehicle.onVehicleUnlocked      += handler  # vehicle researched
g_currentPreviewVehicle.onVehicleInventoryChanged += handler
g_currentPreviewVehicle.onSelected             += handler
g_currentPreviewVehicle.onHeroStateUpdated     += handler
```

### `g_playerEvents` events

```python
from PlayerEvents import g_playerEvents

g_playerEvents.onInventoryResync   += handler  # inventory data resynced
g_playerEvents.onDossiersResync    += handler  # dossier data resynced
g_playerEvents.onStatsResync       += handler  # stats (XP, credits, etc.) resynced
g_playerEvents.onCenterIsLongDisconnected += handler
```

### `itemsCache` sync events

```python
itemsCache.onSyncStarted    += handler              # before sync
itemsCache.onSyncCompleted  += lambda reason, diff: ...  # after sync
itemsCache.onSyncFailed     += lambda reason: ...   # sync failed
itemsCache.onPMSyncCompleted += handler

# CACHE_SYNC_REASON values:
from gui.shared.items_cache import CACHE_SYNC_REASON
# SHOW_GUI=1, CLIENT_UPDATE=2, SHOP_RESYNC=3,
# INVENTORY_RESYNC=4, DOSSIER_RESYNC=5, STATS_RESYNC=6
```

### `g_clientUpdateManager` key-based callbacks

```python
from gui.ClientUpdateManager import g_clientUpdateManager

g_clientUpdateManager.addCallbacks({
    'inventory':        self._onInventoryUpdate,    # invDiff dict
    'stats.unlocks':    self._onUpdateUnlocks,      # new unlock set
    'cache.vehsLock':   self._onLocksUpdate,        # vehicle lock changes
    'groupLocks':       self._onRotationUpdate,     # rotation group changes
})

# Cleanup — removes ALL callbacks registered by this object:
g_clientUpdateManager.removeObjectCallbacks(self)
```

### `_onSyncCompleted` — detecting field mod updates in diff

```python
def _onSyncCompleted(self, _, diff):
    if self.intCD in diff.get(GUI_ITEM_TYPE.VEH_POST_PROGRESSION, {}):
        self._onPostProgressionUpdate()
```

### `_onInventoryUpdate` — detecting module changes

```python
def _onInventoryUpdate(self, invDiff):
    isComponentsChanged = (
        GUI_ITEM_TYPE.TURRET in invDiff or
        GUI_ITEM_TYPE.GUN in invDiff
    )
    vehsDiff = invDiff.get(GUI_ITEM_TYPE.VEHICLE, {})
    isVehicleChanged = any(
        self.__vehInvID in hive or (self.__vehInvID, '_r') in hive
        for hive in vehsDiff.itervalues()
    )
```

---

## 6. `init()` / `fini()` Pattern

Standard WoT mod lifecycle pattern (from `ItemsCache`, `_CachedVehicle`):

```python
from gui.ClientUpdateManager import g_clientUpdateManager
from PlayerEvents import g_playerEvents
from skeletons.gui.shared import IItemsCache
from helpers import dependency


class MyMod(object):
    itemsCache = dependency.descriptor(IItemsCache)

    def init(self):
        # Subscribe to events
        g_playerEvents.onInventoryResync += self.__onInventoryResync
        g_playerEvents.onStatsResync     += self.__onStatsResync
        self.itemsCache.onSyncCompleted  += self.__onSyncCompleted
        g_clientUpdateManager.addCallbacks({
            'stats.unlocks': self.__onUnlocks,
        })

    def fini(self):
        # Unsubscribe in reverse order
        g_clientUpdateManager.removeObjectCallbacks(self)
        self.itemsCache.onSyncCompleted  -= self.__onSyncCompleted
        g_playerEvents.onStatsResync     -= self.__onStatsResync
        g_playerEvents.onInventoryResync -= self.__onInventoryResync

    def __onInventoryResync(self):
        pass

    def __onStatsResync(self):
        pass

    def __onSyncCompleted(self, reason, diff):
        pass

    def __onUnlocks(self, unlocks):
        # unlocks = set of newly unlocked intCDs in this update
        pass
```

---

## 7. `g_currentVehicle` Singleton — Quick Reference

```python
from CurrentVehicle import g_currentVehicle

# Item access
vehicle = g_currentVehicle.item    # gui Vehicle object | None
intCD   = g_currentVehicle.intCD   # int | None
invID   = g_currentVehicle.invID   # int

# State checks
g_currentVehicle.isPresent()
g_currentVehicle.isInBattle()
g_currentVehicle.isInHangar()
g_currentVehicle.isAlive()
g_currentVehicle.isLocked()
g_currentVehicle.isElite()         # via vehicle.isElite
g_currentVehicle.isCrewFull()
g_currentVehicle.isReadyToFight()
g_currentVehicle.isEquipmentLocked()
g_currentVehicle.isOptionalDevicesLocked()
g_currentVehicle.isPostProgressionActive()

# Vehicle selection
g_currentVehicle.selectVehicle(vehInvID, callback=None)
g_currentVehicle.selectNoVehicle()
g_currentVehicle.getDossier()      # VehicleDossier
```

---

## 8. Battle context (field mods in battle)

### From `client/Vehicle.py` (the battle entity, not the GUI item)

```python
# Called by engine when server-side post-progression data changes:
def set_vehPostProgression(self, _=None): ...
def set_disabledSwitches(self, _=None): ...
def set_setups(self, _=None): ...
def set_setupsIndexes(self, _=None): ...
def set_enhancements(self, _=None): ...
def set_crewCompactDescrs(self, _=None): ...
def set_customRoleSlotTypeId(self, _=None): ...
```

### From `gui/battle_control/controllers/prebattle_setups_ctrl.py`

```python
from post_progression_common import (
    EXT_DATA_PROGRESSION_KEY,  # 'vehPostProgression'
    EXT_DATA_SLOT_KEY,         # 'customRoleSlotTypeId'
    TANK_SETUP_GROUPS,
    TankSetupLayouts,
    TankSetups,
    VehicleState,
    unpackActionCDs,
)
```

The pre-battle setup controller builds the active equipment config using `unpackActionCDs(actionCDs, vppCache, treeID)` and maps each `TankSetups.*` layout to a slot.

---

## 9. Useful `Vehicle` State Flags (VEHICLE_STATE)

```python
Vehicle.VEHICLE_STATE.LOCKED                  = 'locked'
Vehicle.VEHICLE_STATE.WILL_BE_UNLOCKED_IN_BATTLE = 'willBeUnlockedInBattle'
Vehicle.VEHICLE_STATE.ROTATION_GROUP_UNLOCKED = 'rotationGroupUnlocked'
Vehicle.VEHICLE_STATE.ROTATION_GROUP_LOCKED   = 'rotationGroupLocked'
Vehicle.VEHICLE_STATE.UNSUITABLE_TO_QUEUE     = 'unsuitableToQueue'
Vehicle.VEHICLE_STATE.NOT_PRESENT             = 'notPresent'
Vehicle.VEHICLE_STATE.IN_PREMIUM_IGR_ONLY     = 'inPremiumIgrOnly'
```

---

## 10. Relevant External Links

| Resource | URL |
|---|---|
| Armagomen/wot_decompiled | https://github.com/Armagomen/wot_decompiled |
| post_progression_common.py | https://github.com/Armagomen/wot_decompiled/blob/main/common/post_progression_common.py |
| CurrentVehicle.py | https://github.com/Armagomen/wot_decompiled/blob/main/client/CurrentVehicle.py |
| gui/veh_post_progression/ | https://github.com/Armagomen/wot_decompiled/tree/main/client/gui/veh_post_progression |
| StatsRequester.py | https://github.com/Armagomen/wot_decompiled/blob/main/client/gui/shared/utils/requesters/StatsRequester.py |
| Vehicle.py (GUI item) | https://github.com/Armagomen/wot_decompiled/blob/main/client/gui/shared/gui_items/Vehicle.py |
