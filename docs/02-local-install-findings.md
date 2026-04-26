# Local Install Findings (C:\\Games\\World_of_Tanks_EU)

## 1. Current Version Snapshot

Observed folder version:

- `2.2.1.1`

Observed top-level mod directories:

- `mods/2.2.1.1`
- `mods/configs`
- `res_mods/2.2.1.1`
- `res_mods/configs`

## 2. Installed Mod Footprint (Examples)

Detected many active mods including:

- `me.kurzdor.battleequipment_3.4.12.wotmod`
- `me.poliroid.pmod_1.81.03.wotmod`
- `me.poliroid.tomatogg_1.7.18.wotmod`
- `champi.settingsgui_1.66.wotmod`
- `izeberg.modssettingsapi_1.7.0.wotmod`
- `OpenModsCore.wotmod`
- `com.modxvm.xvm_13.1.0.0017.wotmod`

This is a real-world mixed ecosystem with shared APIs and overlapping hooks.

## 3. Verified Example Package Layout

From `me.kurzdor.battleequipment_3.4.12.wotmod`:

- `meta.xml`
- `res/scripts/client/gui/mods/mod_battleequipment.pyc`
- `res/gui/flash/battleEquipment.swf`
- `res/mods/me.kurzdor.battleequipment/text/{en,ru,pl,de,uk}.yml`

Takeaway: one mod may combine Python, Flash, and localization assets in one package.

## 4. Useful Existing Config Areas

Found in local install:

- `mods/configs/pmod/`
- `mods/configs/kurzdor/`
- `mods/configs/PYmods/`
- `res_mods/configs/xvm/xvm.xc`

These are good references for schema style and user override patterns.

## 5. Logging Reality Check

Recent `python.log` sample showed mostly normal activity and mod info lines.
One recurring warning was an HTTP 409 from an auto-claim flow (`AvailableRewardDoesNotExist`), which appears service/state related, not necessarily a fatal mod crash.

Recommendation:

- Separate noise/info logs from true traceback errors before debugging.
