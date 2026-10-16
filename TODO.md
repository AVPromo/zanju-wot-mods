# TODO

Open work only. When an item is finished, delete it from here and put whatever is worth keeping in [the technical reference](docs/reference/README.md) — the backlog is not a changelog, and a finished item left in it reads as a thing still to do.

## Format-And-Lint Follow-Up

- Rerun `zwm lint check` after the `research-progress-bar` cleanup and reassess whether `max-complexity = 25` should stay as-is or be tightened further.

## General Refactor Backlog

- Broad runtime splitting for `research-progress-bar` is mostly complete; only reopen it if `mods/research-progress-bar/src/zanju_rpb/main.py` or `mods/research-progress-bar/src/zanju_rpb/scaleform/modes.py` grow enough to justify another targeted slice.

## Campaign Tracker: Input And Notification Report (open)

A player reported two faults on 1.1.1 over Discord, on 10 September 2026. They named `campaign-tracker` after they disabled every other mod one at a time. No GitHub issue carries this yet. Ask them to open one before it goes cold. Nothing ties the two faults to one cause, so treat them apart.

1. A notification about a newly researched vehicle that never clears. The wording fits both the garage menu badge and the achievements popup. Closed below as the client's own, but see the open question.
2. After about an hour of play, the radial menu quick commands stop working. Escape and Tab sometimes stop as well.

**Fault 2 has a proven mechanism, and 1.2.0 closes it.** `held_keys` subscribed to `gui.InputHandler.g_instance`, a process-global bus that fires in battle. It called its consumer with no guard. `game.handleKeyEvent` runs `GUI.handleKeyEvent`, the messenger and the avatar's own input handler after that dispatch. One exception therefore costs the whole key press. See [Events And Callbacks](docs/reference/events-and-callbacks.md#guiinputhandler-is-the-worst-event-to-raise-in). The mod now guards the callback and does the work only while its banners are on screen.

**What that fix does not prove.** No log shows the mod raising there, so the trigger is still unknown. The change is hardening, not the repair of a fault we watched happen. Wait for the reporter to say whether 1.2.0 helps them, and treat this entry as open until they do.

**Two more suspects for fault 2, if it survives 1.2.0.**

- `_models` in `widgets_inject` grew with no bound. A 2.4.0 game.log shows 50 entries after a few minutes of walking in and out of the garage, and every entry took a full `setSnapshot` write per refresh. 1.2.0 trims the list to the newest four. `ViewModel` carries no liveness test, so the trim goes by age. `directives-helper` shares the pattern and the same log shows it at 50 as well, so it needs the same trim.
- The hover card window may accumulate. `card_window.install` builds a new window per garage build when the old one is not alive. It trusts the client to destroy the old one with the lobby. A stale window on `TOP_WINDOW` is a hit-test rectangle on the band that also holds `ingameMenu`. The reporter's log answers this. It carries `The hover card window was destroyed with the lobby; rebuilding` on each rebuild. Count those lines against the garages they visited.

**Fault 1 is not ours. Closed.** The popup is the achievements 2.0 notification, `3 Achievements Unlocked! France: Fauteur and more`, with the trophy score beside it. `AchievementsEarningController` builds it as a `NotificationCommand` when `AchievementsController.onNewAchievementsEarned` fires. That event comes from `__dossierUpdateCallBack`, and its input comes from `__onChatMessageReceived`, which reads service channel messages of type `achievementReceived`.

The loop is in the client. `__dossierUpdateCallBack` calls `__addUnseenAdvancedAchievements` on the same pass that fires the popup, so the popup path puts the achievement back in the unseen set every time it runs. A click in the achievements menu clears that set, but the set is not what gates the popup. The service channel message is. The seen state also only reaches disk in `AdvancedAchievementsSettingsManager.stop()`, on `onAccountBecomeNonPlayer`.

Our side is clear. A grep over all five mods for `AccountSettings`, dossier, achievement and the account lifecycle hooks returns one hit, and it is a comment in `campaigns.py` about campaign numbering. We neither read nor write that state, and we subscribe to nothing on the account teardown path. Reproduced on our own account on 10 September 2026, and a clean quit at 19:46:52 did not stop it.

**One question stays open.** The `MainMenuModel` badge, `MenuItemModel.notification`, is a different component from this popup. The Discord wording covers both. Ask the reporter which one they saw. Only the badge could ever have been ours, and even that was never more than a suspicion.

**1.2.0 is free to ship.** Fault 1 no longer holds it. The changelog carries the input fix and the trimmed model list, and neither mentions fault 1, which is correct.

**The candidate list no longer holds `campaign-tracker`.** From 1.3.0 the banners ride on a child sub-view of the mod's own, so `directives-helper` is the only mod of ours that takes one of the client's garage sub-views. See the next section.

## Gameface Mods: A Sub-View Of Their Own

`directives-helper` takes one of the client's own garage sub-views through `view_claim`. `premium-time` takes `UserAccountModel` in the header document, with no check at all. `view_claim` protects only against mods that check too, and two faults stay open:

- A third-party mod that writes to a fixed sub-view with no check replaces our `ModInjectModel`, because the last writer wins. Our widget then goes away, and nothing in the log says why.
- A third-party mod that needs one exact sub-view finds it taken by one of ours.

A child sub-view of our own closes both, and the 2.4.1.0 probe proved it in `main`. See [Getting code into a document](docs/reference/gameface-mod-widgets.md#getting-code-into-a-document).

- `directives-helper`: the window also shows in mode garages, and each mode garage is a separate document with a root view of its own. Add a child to `RandomHangar` and to the root view of each mode where the window shows. Keep `view_claim` as the fallback for a root view that the mod does not know.
- `premium-time`: the bar probe of `directives-helper` already has a child in `LobbyHeader` at `0x5A4E4448`. Give `premium-time` a position ID of its own: two children of one parent need two IDs.

`campaign-tracker` and `crucible-tracker` already have a child of their own, through `mods-common/hangar_child.py`. Both show in the random garage only, so a child of `RandomHangar` covers every place they show. The reference lists the position IDs of all our mods. Remove `view_claim` from `mods-common/` only when no mod uses it as a fallback.

## Gameface Mods: Shared Scripts For The Plumbing

`mods-common/gameface/` can now share a script between mods: `tray.js` was the first, and the in-game check passed for it. Four mods hold copies of the same plumbing, and it should move there too. Each mod would keep only what it draws.

- **The bridge to the data model**: `modelOn`, `findDataModel`, `bindModelPush`, `onPush`, `invokeCommand` and the adaptive poll (`setPollRate`, `pollRateFor`). Copies are in `widgets.js` of `campaign-tracker` and `crucible-tracker`, and in `window.js` of `directives-helper`. `bar_probe.js` of `directives-helper` has a part of it. The flags on `document` carry a prefix for each mod. The shared script must thus take the prefix and the data property as arguments.
- **The small helpers**: `log`, `unwrap`, `parseJson` and `el`. Copies are in the four mods, `header_patch.js` of `premium-time` too. `log` must take the tag of the mod.
- **The countdown format**: `formatRemaining`, the two largest units of a time left. `premium-time` has it in `header_patch.js`, and `crucible-tracker` has a copy in `common.js`. The unit labels (`UNIT_DAY_SHORT` and the others) are in the i18n files of both mods.
- **The standalone card window**: `card_panel.js` (`readModel`, `scheduleMeasure`, `publishSize`, `waitForDomBuilt`, `nextFrame`) and `gameface/card_window.py`. `crucible-tracker` has a near copy of both from `campaign-tracker`. Move the window lifecycle into `mods-common/`, as a script and as a Python module. Each mod then keeps only its payload.

Each move changes a mod that works now. Do one piece at a time, with an in-game check of every mod that takes it. A shared script can import another shared script, because the build puts all of them in the same folder.

## Testing Backlog

Scaffolding is in place (`zwm test`, `testing/`, see [Testing](docs/testing.md)). `premium-time`
and `directives-helper` are covered; `research-progress-bar` has one suite so far.

- Broaden `mods/research-progress-bar/tests/`. `panel_watch.py` is tested because it keeps every
  client import inside a function; most of the mod does not, and `constants.py` pulls in
  `gui.Scaleform.daapi.settings.views` at module scope — so reaching the rest needs client stub
  modules added to `GAME_STUB_MODULES` in `testing/zwm_test_env.py`. Good next targets: the
  `config.py` normalizers (mode/bool coercion, legacy-key migration), `mode_state.py`, and the
  percent/label formatting in `scaleform/modes.py`. Skip `collector.py`: faking enough of the
  client to reach it would encode more assumptions than the tests verify.
  - Worth applying deliberately when splitting modules: "no client import at module scope" is
    what decides whether something can be tested at all.

## CI / Toolchain Backlog

- Restore a "WoT is running" guard for deploy/cleanup/cycle. It was removed in the Docker migration because a Linux container can't enumerate Windows host processes (`tasklist`). Viable options: (a) a host **PowerShell** wrapper that runs the `tasklist` check before invoking the container (no install needed — PowerShell is built in); (b) a file-lock probe on a known WoT-held file; (c) a `--force`/`--skip-running-check` opt-out if a host check is reintroduced. Until then, deploy relies on file-lock `PermissionError` handling (in-use files are skipped) — close WoT manually.

## Release And Distribution Backlog

- Add a `research-progress-bar` release checklist for wgmods.net and modpack submission: standalone companion bundle contents, config/i18n copy requirements, no-optional-UI-API smoke test, and re-test expectations for each WoT version even when no code change is planned.

## Localization / Font Coverage

- Current state: text outside the embedded Roboto Mono range (Korean, Greek, Cyrillic, etc.) falls back to the `Malgun Gothic` device font. This is wired centrally through `ResearchProgressBarFonts.setText` / `setHtmlText`, so every text field — tooltips, mode buttons, counters, markers, status line — picks it up. Fixes issue #3 (Korean) and covers European scripts.
- Gap: Malgun Gothic does not cover Japanese (kana/kanji), Chinese (Han), Thai, Arabic, or Hebrew, which still render as boxes. WoT ships clients in several of those languages, but no single guaranteed-present Windows font covers all of CJK.
- Universal fix to investigate: instead of hardcoding an OS font, point the fallback at one of WoT's own registered Scaleform fonts (GFx `$`-prefixed, e.g. `$FieldFont`), whose per-locale glyph fallback Wargaming already configures. GFx would then resolve whatever the active client language needs, covering every WoT-supported language at once — the genuinely universal solution.
- Why it is not a quick swap: the code change is one line (`FALLBACK_FONT_NAME` in `ResearchProgressBarFonts.as`, now centralized), but the validation is the real work:
  - Confirm the exact WoT font name in-game; it may differ between client versions.
  - Verify a mod-loaded SWF can resolve WoT's `$`-named GFx fonts from its own context.
  - `embedFonts` semantics differ for GFx font-lib fonts (likely `embedFonts = true` with the `$` name, not the `embedFonts = false` device-font path used for Malgun Gothic).
  - Add a graceful chain (WoT font -> Malgun Gothic -> `_sans`) so a wrong/missing name degrades instead of showing boxes.
  - Needs an in-game test cycle per target language.
- Keep the Malgun Gothic fallback as the shipped baseline until the WoT-font approach is validated.

## Hangar Loadout Bar Blanking (unfinished investigation)

The original symptom is still unexplained: researching a field modification from the progress
bar's overlay makes the hangar's ammo/loadout bar disappear until the vehicle is switched. The
existing refresh recipe (see [Events And Callbacks](docs/reference/events-and-callbacks.md))
ran and reported success in the log, and the panel blanked anyway — so the recipe is either
insufficient for that flow or fixing the wrong thing.

- `zanju_rpb/panel_watch.py` was written to settle it and has never produced a reading. It
  samples the panel either side of a repair and on a 1s timer, and logs only when its answer
  changes; a `WARNING` line names which of three stories is true (stale vehicle copy / sections
  emptied / sections gone). **Reproduce the blanking once with it enabled and read the log.**
- The probe ships **off** — it is a diagnostic for a bug nobody is actively hunting, and a
  release should not carry its timer and log stream idling. **Arm it before attempting a
  reproduction**, or the steps above produce nothing at all. Arming needs no code change:

      %APPDATA%\zanju_wot_mods_cache\research-progress-bar\probe.on

  Create that file (empty — only its existence is read), restart the client, and `Loadout bar
  probe armed by probe.on` appears in `game.log`. Delete it to disarm. The build stays
  byte-identical to the one users get, and nothing is left sitting in the working tree waiting
  to be committed by accident. `ShippedStateTest` pins the source default off.
- Candidate lead if the probe exonerates the stale copy: the repair fires
  `wrapper.onItemUpdated(None)`, which lands on `_updateAmmunitionGroupsController(recreate=False)`
  and updates the section models *in place*. `InteractingItem` also has `onAcceptComplete`,
  whose handler passes `recreate=True` and rebuilds them — the path the game itself uses after
  an accepted change. A field-mod research can change the panel's shape (it is how the second
  loadout is unlocked), so a full recreate may be the correct repair.

## Research Progress Bar Dynamic Coloring

- Done so far: marker **icons**, Field Mods **level labels**, and tooltip **prerequisite icons** are recoloured at runtime to their marker's state via a single per-state colour table in `ResearchProgressBarIconTint.as` (multiply `ColorTransform` on each `Bitmap`, not the shared `BitmapData`; prestige badges excluded). The exact-vs-brighter design question is settled as **exact dash colour** (constants sampled from the dash PNGs: default `0x9CA4AB`, green `0x9CCB68`, yellow `0xE4B55A`, white `0xF6F1E7`).
- Follow-up: extend the same runtime tint to the **marker dashes** and the **progress-bar fills**, retiring the per-colour PNGs so the whole bar's palette lives in one code table.
  - **Marker dashes (4 → 1):** `marker_default/green/yellow/white.png` (4×14) share a pixel-identical alpha; they differ only in hue. Collapse to one greyscale master tinted per `markerState` in `ResearchProgressBarMarkers.createMarkerBitmap`. `marker_white` already works as the near-white master (white = identity tint). The four tint colours are the same constants already in `ResearchProgressBarIconTint`.
  - **Progress-bar fills (4 → 2):** `progress_bar_green/yellow/white.png` (80×8) share an identical alpha (full rect), hue-only difference → one greyscale master. `progress_bar_base.png` has a **different** alpha (the empty track) → keep it a separate asset. The three colour fills are stacked (`ResearchProgressBarViewFactory` lines ~66-73) but each is masked to a **disjoint** horizontal slice (`completedMaskShape`/`combatMaskShape`/`freeMaskShape`), so they never blend — keep the three `Bitmap` instances, embed the one master, and apply a **different `ColorTransform` per instance**; masks stay untouched.
  - Both plug into the existing `ResearchProgressBarIconTint` colour table (single source of truth); build a shared `tintBitmap(bitmap, color)` helper so dashes and fills reuse the icon path.
  - Caveat: multiply-tint needs a near-white master; if a specific green/yellow must read deeper than `white × tint` can reach, that one master needs a brightness lift (same as the filter-icon pass).
- Verifier: `scratchpad/png_probe.py` (pure-Python PNG decoder, no PIL) reports per-variant alpha match / hue / peak and samples dash peak RGB — rerun it if the assets change before wiring.

## Research Progress Bar: Is A Gameface Bar Worth It?

Open question, not started. The bar sits on `WindowLayer.WINDOW` (7) and draws over the x5 counter mod. To get under that counter costs either the dimming of band 3 or a rewrite of the bar as a Gameface view. Two cheap measurements decide it. Take both before you write any Gameface code.

Context: no band below 7 works for a Scaleform mod view. `MARKER` (3) draws under the garage document, but that band composites with the scene, so the whole view goes dim. `VIEW` (4) gives an empty garage. `SUB_VIEW` (5) is the garage document.

`TOP_SUB_VIEW` (6) belongs to the legacy Scaleform lobby. A view there makes the legacy page call `setRequiresOldStyle`. The lobby header then gains a background, and the container pushes the view down the screen. See [Window Layers](docs/reference/ui-and-scaleform.md#window-layers).

**Measurement 1: does a Gameface view escape the legacy chrome on band 6?** The claim is that `OLD_STYLE_VIEW` triggers the chrome, and that a Wulf view lacks that flag. That is an inference from the name of a constant. The legacy lobby SWF makes the decision, and we did not decompile it. The trigger could instead be an occupied sub-view container.

Test this without a rewrite. The campaign tracker card is already a working standalone Gameface window. Change `_layer()` in `mods/campaign-tracker/src/zanju_ct/gameface/card_window.py` to return `WindowLayer.TOP_SUB_VIEW`. Run `zwm cycle campaign-tracker`, then open the garage and look at the top bar. If the header keeps its transparent hangar style, the inference holds.

**Measurement 2: which band holds the x5 counter?** Nobody knows yet, and the answer decides whether band 6 helps at all. If the counter sits on `SUB_VIEW` (5), no band above it helps, and the rewrite buys nothing.

The mod is `oldskool.x5counter_1.0.1.wotmod`. It ships a standalone Gameface view under the item ID `OldSkoolX5CounterView`, with an empty `extension`, so it is not a hangar injection. The mod also obfuscates its Python with pjorion, behind a zlib and marshal payload, and it mangles the inner names. The file therefore does not give up the band. Dump the Wulf window manager instead. Log the layer and the layout ID of every window.

Our earlier band log named `GUIFlash`, `xfw_injector`, `ModsListButton`, `TomatoGGLobbyUI` and `ExpectedVehicleValueGarage` on band 7. It did not name this counter.

**Cost if both measurements pass.** The bar is the largest ActionScript surface in the repo. A rewrite must carry the embedded fonts, the bitmap masks, the marker hit tests, the keyboard pick stack and the mode buttons. Weigh that against the dimming of band 3, which costs one constant and no new code.

## Research Progress Bar Guardrails

- Garage layering, settled for now. The bar sits on `WindowLayer.WINDOW` (7). Every band below it charges something, and [Window Layers](docs/reference/ui-and-scaleform.md#window-layers) records the price of each. The bar therefore draws over the Gameface garage document, and over every mod widget inside it. To lower it further needs a Gameface rewrite. Read the section above first.
- Evaluate whether tank research totals should include the cost of prerequisite modules before a tank unlock.
- Check which upgrade is actually reachable right now and list all currently missing upgrades.
- Turn `research-progress-bar` `configVersion` into a real migration hook: add versioned forward migrations, defaults for new keys, and pruning for renamed/removed keys instead of only carrying `configVersion = 1` forward on save.
- Out of scope unless explicitly requested: changing mode semantics.
- Out of scope unless explicitly requested: redesigning the Scaleform layout.
- Out of scope unless explicitly requested: removing the production garage visibility-probe behavior.
- Future AS3 naming/package cleanup: build a second fake test mod and use it to collision-test default-package class names, helper names, and source/output path overlap before renaming `ResearchProgressBar*.as` files or introducing an AS3 package tree; the earlier unique-path finding justifies this test method, but file-path collisions and class-name collisions need to be validated separately.
- Future refactor guardrail: treat reflective prestige/elite adapter helpers in `zanju_rpb.main` as load-bearing runtime-contract code, not obvious dead code; before deleting or simplifying them, validate in-game across elite non-tier XI vehicles, tier XI vehicles, `eliteMode=customization_only`, and repeated vehicle switches.

## Research Progress Bar: Where The Bar Is Allowed To Show

Checked at client 2.4.0.0. Nothing changed yet. The bar has **no battle-mode condition**. Every rule it has asks where the player stands in the lobby. The Onslaught hide then falls out of one of those rules by accident, not by intent.

`_get_scaleform_block_reason` in `mods/research-progress-bar/src/zanju_rpb/scaleform/gate.py` asks six questions in order. The first failure names the block reason in the log:

1. `is_active` — the mod is running.
2. `scaleformPrototypeEnabled` — the config kill switch.
3. `preview_present` — a vehicle preview is up.
4. `vehicle_present` — a tank is in the garage.
5. The lobby route is exactly `subScope/subLayer/hangar` or `subScope/subLayer/hangar/{root}`.
6. The SUB_VIEW and TOP_SUB_VIEW aliases are a hangar view or the bar itself.

A `None` payload then hides the bar as `populated_no_modes`, outside the gate.

Rule 5 is the one that hides the bar in Onslaught. It also hides it in Frontline, Steel Hunter, Last Stand and Fun Random. Ranked, Mapbox and Maps Training share the plain `hangar` route, so the bar remains there. That is the wanted answer, reached by accident.

### Two faults, separable

**Rule 5 is an exact match of two strings.** Any garage with a lobby state of its own loses the bar, whatever the mode. This is the stricter form of the fault the campaign tracker fixed in 1.1.0. A seasonal garage is the case to worry about, and one is live already. `VIEW_ALIAS.LEGACY_LOBBY_HANGAR` is `legacyHangar`. Rule 6 accepts it through `_HANGAR_VIEW_ALIASES`, and rule 5 rejects the route `subScope/subLayer/legacyHangar`. Rule 5 runs first, so the legacy garage loses the bar that rule 6 means to allow.

**The route comes out of log text, and the gate fails open.** `main.py` attaches a `logging.Handler` to the logger `gui.lobby_state_machine.lobby_state_machine`. It matches the prefixes `Visible route changed to: ` and `Navigating to `. Reword either line, or quiet that logger, and `_current_lobby_route_path` stays `None`. Rule 5 reads `if current_lobby_route_path is not None`, so a missing route skips the rule rather than fails it. The bar then shows in Onslaught, with nothing in the log to say why. The campaign tracker instead subscribes to `LobbyStateMachine.onVisibleRouteChanged` and reads `getStateID()`. That needs no text, and it fails closed.

### What to do

- Replace the log scraping with the `onVisibleRouteChanged` subscription in the shared `mods-common/route_gate.py`: add `research-progress-bar` to `mods-common/manifest.json`. Same signal, no parsing.
- Then settle the rule itself. **Decide this first, it is not obvious.** One option matches a trailing `hangar` segment the way the tracker does, then subtracts Onslaught by name, because the reason to hide there is the shape of that mode's UI. The other gates on the battle mode.
- Do not copy the tracker's mode gate. It answers "random battles alone". Ranked earns vehicle XP and must keep the bar.
