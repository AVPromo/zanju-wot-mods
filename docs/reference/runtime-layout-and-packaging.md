# Runtime Layout And Packaging

## Typical WoT Runtime Folders

Common runtime locations:

- `mods/<game-version>/`
- `mods/configs/`
- `res_mods/<game-version>/`
- `res_mods/configs/`

## Package Shape

A `.wotmod` commonly contains:

- `res/` — the only required element; everything below lives under it
- compiled Python scripts under `res/scripts/client/gui/mods/*.pyc`
- optional Scaleform assets under `res/gui/flash/*.swf`
- optional Gameface assets under `res/gui/gameface/mods/<namespace>/*` — the HTML/CSS/JS a
  widget injects into a game document
- optional localisation assets under `res/mods/<namespace>/text/*.yml`
- optional `meta.xml` manifest at the archive root (`<id>`, `<version>`, `<name>`, `<description>`)
- optional root `LICENSE.md`

## `gui/gameface` Holds The Documents, `gui/gen_resources` Registers Them

A Gameface mod puts files in two places, for different reasons. Counted across all four `gui-part*.pkg` on 2.4.1.0:

| Path | Contents |
| --- | --- |
| `gui/gameface/` | 664 `.js`, 528 `.css`, 454 `.html` — the compiled documents, under `_dist/` |
| `gui/gen_resources/` | 14 `.json` — the resource registry, with more in the feature packages |
| `gui/unbound/` | 190 `.unbound` (Unbound's declarative view format) and 5 `.dds`, nothing a Gameface mod needs |

**A widget's assets go under `res/gui/gameface/`**, which is also the prefix its `coui://` URLs resolve against.

**The layout registry is every `gui/gen_resources/*.json` file.** The client reads them all when it starts, before it runs any mod Python. It builds the `R` tree from them. `gui.impl.gen.R` is that native tree: `GuiApplication.getInstance().resourceManager.getRootNode()`. The client ships 82 of these files across its packages. Each file is a JSON array, and each entry names its place in `R` with `id`:

```json
{"type": "Layout",
 "id": "R.views.battle.battle_notifier.BattleNotifierView",
 "path": "coui://gui/gameface/_dist/production/battle/battle_notifier/BattleNotifierView/BattleNotifierView.html",
 "parameters": {"entrance": "BattleNotifierView", "impl": "gameface"}}
```

An injected widget never touches the registry: OpenWG puts the mod's assets into a document the client already registered. A **standalone** Gameface view does need an entry, because it is a document the client has never heard of. A mod ships the entry inside its own `.wotmod` at `res/gui/gen_resources/<mod id>.json`. The client reads the files in mod packages too, so no restart is necessary. On 2.4.1.0 the startup log counted 88 files, the client's 82 and the 6 that installed mods shipped:

```text
[WULF] Resource loading stats:
  Loaded 88 files during: 0.284 sec
```

The Campaign Tracker hover card is one such entry:

```json
[
  {
    "type": "Layout",
    "id": "R.mods.zanju.campaigntracker.views.CampaignCard",
    "path": "coui://gui/gameface/mods/zanju_campaigns/CampaignCard.html",
    "parameters": {"entrance": "CampaignCard", "impl": "gameface"}
  }
]
```

The mod gets the numeric layout id from `R` at runtime. The node is callable: `R.mods.zanju.campaigntracker.views.CampaignCard()` gives the id. Mods updated for 2.4.1.0 put their entries under `R.mods` (Poliroid, OldSkool) and under `R.views.mods` (Aslain). The client logs a duplicated `id` and skips the second entry, so the path must be unique to the mod.

## Repository Build Rules

In this repository:

- build and lint run inside the toolchain image (`tools/Dockerfile` → `ghcr.io/przemyslaw-zan/zanju-wot-mods/toolchain`); Docker is the only local prerequisite
- authored Python sources live under `mods/<mod-name>/src/`
- `zwm build` compiles them into the runtime package shape
- config is not shipped: each mod self-creates its config in AppData on first run, so it survives modpack reinstalls
- authored `i18n/*.yml` files are bundled inside the `.wotmod` at `res/mods/<meta.id>/text/*.yml` (the single localisation destination — no loose config copies); the runtime reads them from the mounted package VFS via `ResMgr` at `mods/<meta.id>/text/<lang>.yml`. The build adds the shared keys that a mod uses, from `mods-common/i18n/<lang>.yml`, to the end of those files (see [Shared Modules](#shared-modules))
- `ui/compile_ui.py` is auto-run by `zwm build` when present
- runtime modules that several mods share live in `mods-common/`, and `zwm build` compiles each one into the package of every mod that takes it (see [Shared Modules](#shared-modules))

## Shared Modules

Some runtime modules are the same in several mods. Each of them has one authored copy in `mods-common/<name>.py`. `zwm build` compiles the module into the internal package of each mod that takes it, at `res/scripts/client/gui/mods/<pkg>/<name>.pyc`, the same way it adds `_mod_meta`. A mod imports it as a sibling that is not in its `src/` tree, for example `from .. import view_claim`.

**A Gameface script can be shared too.** `mods-common/gameface/<name>.js` has one authored copy. `zwm build` copies the script into the one Gameface folder of each mod that takes it, `res/gui/gameface/mods/<namespace>/<name>.js`, so the mod's own modules import it as `./<name>.js`. A mod that takes a script must have exactly one folder under `res/gui/gameface/mods/`. A shared script can import another shared script, because the build puts all of them in the same folder.

**A mod takes a shared file by importing it.** No list declares it. `zwm build` and `zwm test` read the imports of each mod (`tools/core/mods_common.py`):

- Python: a relative import that reaches the root of the mod's package and names a shared module, such as `from .. import hangar_child` in a subpackage, or `from .localization import get_text` at the root. An absolute import through the package name counts too.
- Gameface: `import ... from './<name>.js'` or `import './<name>.js'` in a script of the mod's Gameface folder.

**Strings can be shared too.** `mods-common/i18n/` has the strings that several mods use, such as the units of a time left, in the layout of the `i18n/` folder of a mod. A mod takes a shared key when its code, or a shared module that it takes, uses the key (`tools/core/i18n_audit.py`). `zwm build` adds the lines of those keys to the end of each language file of the mod in the package, under a `# Shared strings` comment. A language that the mod does not have gets a file with the shared lines only. The game merges the English file under it, so the other strings of the mod stay in English. The coverage table of a mod counts the shared keys that it takes. Thus a translation in `mods-common/i18n/` shows in the table of each mod that uses it. A key is in the `en.yml` of a mod or in the shared one, never in both. `zwm lint` stops when a key is in both, or when no mod uses a shared key.

The shared files import each other too, so a mod also takes what its shared files import. `countdown.js` imports `helpers.js`, so a mod that imports only `countdown.js` gets both. Only these static forms count. A shared module that a mod loads with `__import__` and a string, or with a dynamic `import()`, does not ship.

Before this rule, `mods-common/manifest.json` listed the mods of each file, apart from the code. Nothing checked that it matched the imports: a mod could import a shared script that the list did not give it, pass the build and its tests, and fail in the game. On 16 October 2026 the imports gave the same sets as the list for all six mods, and the list was deleted.

`zwm shared` prints which mods take each shared file and each shared string, and `zwm shared <mod>` what one mod takes. The shared scripts on 16 October 2026:

| Script | What it holds |
| --- | --- |
| `tray.js` | the banner row beside the vehicle name, see [Sharing the row beside the vehicle name](gameface-mod-widgets.md#sharing-the-row-beside-the-vehicle-name) |
| `helpers.js` | `createLog(tag)`, `unwrap`, `parseJson`, `el` |
| `model_bridge.js` | `createBridge`: find the data model among the sub-views, follow its pushes, poll as a backstop; `invokeCommand` |
| `countdown.js` | `formatRemaining`, the two largest units of a time left |
| `card_host.js` | the document side of a hover card in a window of the mod's own, with hooks for what each mod draws |

`card_window.py`, the Python half of the hover card, is a shared module with a `CardWindow` class that each mod builds once, with the path of its layout.

**Each `.wotmod` stays self-contained.** The module goes into the package of each mod, so the game sees one file per mod at different paths. Python also loads one module per mod, for example `zanju_dh.view_claim` and `zanju_ct.view_claim`. No mod needs another of ours, and we ship no companion package of our own. A player can mix releases from before and after a module moved to `mods-common/`. The packages built after `view_claim` moved hold the same code as the packages built before it.

**A shared module holds no state for more than one mod.** Each mod has its own copy, so a variable at module level belongs to one mod only. If two mods must agree on something, they agree through an object of the client. `view_claim` is the example: the mark that a sub-view is taken is the client's `gf_mod_inject` field. A module that needs one instance for the whole game process cannot live here. It needs a library package of its own, and that brings back version skew between mods that a player updates one at a time.

**A change to a shared module waits in each mod until the next release of that mod.** CI publishes only the mods that have a new version in `meta.xml`. When you change a shared module, decide for each mod that takes it whether to release that mod now. On a partial `zwm build`, a warning names the other mods that take the same shared modules but are not in the build. `view_claim` is also a contract between mods, and old releases stay installed. Thus a change to how a mod decides that a sub-view is taken must still work next to the previous release of every other mod.

**`zwm build`, `zwm test` and `zwm shared` stop on an inconsistent tree.** All three examine the whole repository, also on a partial run. They stop in these cases:

- A mod has a file with the name of a shared module in its package, or a Gameface file with the name of a shared script. This rule also covers mods that do not take the file, so that a private copy cannot start to drift again.
- A shared module imports a name from the package root that is no shared module and not `_mod_meta`, or a shared script imports a script that is not shared.
- A mod takes a shared script, but it does not have exactly one Gameface folder.
- A Python file of a mod does not parse, so its imports are unknown.

**Checked in game on 2.4.1.0, on 14 October 2026.** All four modules ran in PT, RPB, DH and CT, each mod alone and all together. With DH and CT both installed, CT took `MainMenuModel` and DH took `VehicleMenuModel` in every garage build. Each of them alone took `MainMenuModel`. The new DH and CT also each ran next to the other mod's build from before the move. The old and new copies of `view_claim` kept the same split, and the old and new copies of `storage` read the window position that the other one wrote. [Testing](../testing.md#in-game-check-after-a-change-to-a-shared-module) lists the runs.

**Checked again on 25 October 2026, after the move to child views and shared scripts.** DH 1.0.8, PT 1.0.4, CT 1.3.0 and CRT 1.0.0 each ran alone in the garage. No session had a `Traceback` or a script error. Each mod wrote `initialized`, built its own child view or window (`Directives window added to RandomHangar`, `Premium time counter added to LobbyHeader`, `Garage child view at 0x5a4e4354` and `0x5a435254`), and did its work: DH fitted and removed a directive, CT opened a mission and came back, and CRT placed its banner and measured its card.

**Accepted consequences.** An IDE cannot resolve the sibling import in the source of a mod. A traceback in `game.log` names `res/scripts/client/gui/mods/<pkg>/<name>.py`, but the source is `mods-common/<name>.py`.

## Entry Point Rule

For this WoT stack, keep a top-level `mod_*.py` bootstrap in `src/`. A package-only entry point is
not merely unreliable — the loader cannot reach one. The whole discovery rule is four lines of
`gui/mods/__init__.py`:

```python
_MOD_NAME_POSTFIX = '.py' if IS_DEVELOPMENT else '.pyc'

def _isValidMOD(scriptName):
    return scriptName.startswith('mod_') and scriptName.endswith(_MOD_NAME_POSTFIX)

for scriptName in set(map(string.lower, modsFolder.keys())):
```

Two rules follow:

- A package directory carries no `.pyc` suffix, so it is never a candidate.
- The keys are **lower-cased before the import**, so the filename must be lower-case. `mod_Foo.pyc`
  is looked up as `gui.mods.mod_foo` and the import fails.

## Import Safety Rule

Do not use the same module name for both:

- the top-level bootstrap file
- the internal package directory

That pattern can shadow the package in `sys.modules` and break imports.

## A Failure Inside `init()` Can Be Silent

The loader calls a mod's lifecycle methods through one helper:

```python
def _callModMethod(mod, methodName, *args, **kwargs):
    try:
        return getattr(mod, methodName)(*args, **kwargs)
    except AttributeError:
        pass
```

The call sits inside the `try`, not only the lookup. An `AttributeError` raised anywhere inside a
mod's `init()` or `fini()` therefore disappears with **no log line at all**, and the mod reads as
one that never loaded. A wrong hook target after a client update raises exactly that. Catch it
inside the mod so it reaches `game.log`. See [Debugging](../debugging.md).

## Release Output

Build results go to `dist/`.
That output is intended to be disposable build output rather than authored source.

**`meta.xml` ships, trimmed to `id`, `version`, `name` and `description`.** The Wargaming *Mod Packages* spec marks the file optional and requires only `res/`, so this is a choice rather than a rule. `id` and `version` buy a clean load order and let the client de-duplicate two versions of the same mod, which is worth the few bytes. It is also the single source of truth for those values in this repository: the build generates the runtime `_mod_meta` from it, and every script reads it through `tools/mod_meta.py`.
