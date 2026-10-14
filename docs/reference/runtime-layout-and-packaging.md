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

## `gui/gameface` And `gui/unbound` Hold Different Halves

The client ships both, and a Gameface mod touches each for a different reason. Counted across all
four `gui-part*.pkg` on 2.3.1.3:

| Path | Contents |
| --- | --- |
| `gui/gameface/` | 614 `.js`, 515 `.css`, 448 `.html` — the compiled documents, under `_dist/` |
| `gui/unbound/` | 192 `.unbound` (Unbound's declarative view format), 5 `.dds`, and `res_map.json` |

**A widget's assets go under `res/gui/gameface/`**, which is also the prefix its `coui://` URLs
resolve against.

**The layout registry that makes an asset reachable lives at `gui/unbound/res_map.json`.** It is
one JSON object of 131,570 entries, keyed by hex id, mapping each id to a resource:

```json
"47": {"type": "Layout",
       "path": "coui://gui/gameface/_dist/production/battle/battle_notifier/BattleNotifierView/BattleNotifierView.html",
       "parameters": {"entrance": "BattleNotifierView", "extension": "", "impl": "gameface"}}
```

An injected widget never touches it: OpenWG puts the mod's assets into a document the client
already registered. A **standalone** Gameface view does need an entry, because it is a document
the client has never heard of. `net.openwg.gameface` builds one by reading the shipped map out of
the `gui-part*` packages, merging every `mods/configs/res_map/*.json` it finds, and writing the
result to `res_mods/<version>/gui/unbound/res_map.json`. It then calls `BigWorld.restartGame()`
once, because the client reads the map at startup.

A mod ships its entry inside its own `.wotmod` at `res/mods/configs/res_map/<mod>.json`. OpenWG
reads that directory from the game VFS as well as from disk, so no loose file is needed. One
verified entry, from a standalone panel that loaded on 2.3.1.3:

```json
[
  {
    "itemID": "mods/vendor/MyPanel/panelLayoutID",
    "type": "Layout",
    "path": "coui://gui/gameface/mods/vendor/MyPanel/MyPanel.html",
    "parameters": {"entrance": "MyPanel", "extension": "", "impl": "gameface"}
  }
]
```

The mod resolves `itemID` to a numeric layout id at runtime with `openwg_gameface.res_id_by_key`,
after `on_ready` reports the map validated.

Community guides that point at `gui/unbound/` for Gameface work are therefore right about the
resource map and wrong only if they send *assets* there.

## Repository Build Rules

In this repository:

- build and lint run inside the toolchain image (`tools/Dockerfile` → `ghcr.io/przemyslaw-zan/zanju-wot-mods/toolchain`); Docker is the only local prerequisite
- authored Python sources live under `mods/<mod-name>/src/`
- `zwm build` compiles them into the runtime package shape
- config is not shipped: each mod self-creates its config in AppData on first run, so it survives modpack reinstalls
- authored `i18n/*.yml` files are bundled inside the `.wotmod` at `res/mods/<meta.id>/text/*.yml` (the single localisation destination — no loose config copies); the runtime reads them from the mounted package VFS via `ResMgr` at `mods/<meta.id>/text/<lang>.yml`
- `ui/compile_ui.py` is auto-run by `zwm build` when present
- runtime modules that several mods share live in `mods-common/`, and `zwm build` compiles each one into the package of every mod that takes it (see [Shared Modules](#shared-modules))

## Shared Modules

Some runtime modules are the same in several mods. Each of them has one authored copy in `mods-common/<name>.py`, and `mods-common/manifest.json` says which mods take it. `zwm build` compiles the module into the internal package of each of those mods, at `res/scripts/client/gui/mods/<pkg>/<name>.pyc`, the same way it adds `_mod_meta`. A mod imports it as a sibling that is not in its `src/` tree, for example `from .. import view_claim`.

**Each `.wotmod` stays self-contained.** The module goes into the package of each mod, so the game sees one file per mod at different paths. Python also loads one module per mod, for example `zanju_dh.view_claim` and `zanju_ct.view_claim`. No mod needs another of ours, and we ship no companion package of our own. A player can mix releases from before and after a module moved to `mods-common/`. The packages built after `view_claim` moved hold the same code as the packages built before it.

**A shared module holds no state for more than one mod.** Each mod has its own copy, so a variable at module level belongs to one mod only. If two mods must agree on something, they agree through an object of the client. `view_claim` is the example: the mark that a sub-view is taken is the client's `gf_mod_inject` field. A module that needs one instance for the whole game process cannot live here. It needs a library package of its own, and that brings back version skew between mods that a player updates one at a time.

**A change to a shared module waits in each mod until the next release of that mod.** CI publishes only the mods that have a new version in `meta.xml`. When you change a shared module, decide for each mod that takes it whether to release that mod now. On a partial `zwm build`, a warning names the other mods that take the same shared modules but are not in the build. `view_claim` is also a contract between mods, and old releases stay installed. Thus a change to how a mod decides that a sub-view is taken must still work next to the previous release of every other mod.

**`zwm build` and `zwm test` stop on an inconsistent manifest.** Both examine the whole repository, also on a partial run. They stop in these cases:

- The manifest names a module or a mod that does not exist.
- A file in `mods-common/` is not in the manifest.
- A mod has a file with the name of a shared module in its package. This rule also covers mods that do not take the module, so that a private copy cannot start to drift again.

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
