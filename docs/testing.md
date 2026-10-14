# Testing

Unit tests here belong to the **mods**, not to the repository tooling. Their job is to keep shipped runtime behaviour stable: the logic that renders a label, parses a translation file, or decides when a subscription has lapsed. Tooling breakage surfaces immediately to whoever is running it, so it is fixed as it appears rather than guarded by tests.

Run them with:

```bash
zwm test --all          # every mod
zwm test premium-time   # one mod
zwm test --all --verbose
```

CI runs `zwm test --all` as part of the lint workflow, so mod tests gate releases.

## Opting a mod in

A mod has tests when it has a `tests/` directory. There is nothing to register: `zwm test` discovers by convention, the same way `zwm build` picks up an optional `ui/compile_ui.py`.

| File in `mods/<name>/tests/` | Runs under | Notes |
| --- | --- | --- |
| `test_*.py` | Python 2.7 `unittest` | Same interpreter the WoT client uses |
| `*.test.js` | `node --test` | Node's built-in runner; no npm dependencies |
| `run_tests.py` | Python 3 | Escape hatch: takes over the whole run for that mod |

Suites are reported per mod, and the command exits non-zero if any of them fail.

## Python 2.7 tests

Mod runtime code cannot simply be imported outside the game, for three reasons:

- every package imports `._mod_meta`, which `zwm build` generates from `meta.xml` and which therefore does not exist in the source tree;
- the shared modules are in `mods-common/`, and only `zwm build` puts them into the package (see [Shared Modules](reference/runtime-layout-and-packaging.md#shared-modules));
- some modules import client APIs (`BigWorld`, `ResMgr`, `gui.*`) at module scope.

`testing/run_py27_tests.py` handles all three before discovery: it puts the mod's `src/` on the path, synthesizes `_mod_meta` from the mod's own `meta.xml`, loads into the package the shared modules that `mods-common/manifest.json` gives the mod, and installs the stub modules listed in `testing/zwm_test_env.py`. Test files therefore import mod modules directly:

```python
from zanju_pt import formatting


class ServerTimeTest(unittest.TestCase):
    def test_offset_is_zero_without_a_client(self):
        self.assertAlmostEqual(formatting.server_time_offset(), 0.0, delta=1)
```

Write tests as plain `unittest.TestCase` classes so they stay runnable by any unittest-compatible runner rather than being tied to `zwm test`.

**Keep the stubs thin.** They exist so that *import* succeeds for modules whose logic is pure. A stub that quietly returns plausible client data turns a failing test green — if a test needs client behaviour, fake it explicitly in the test.

**Non-ASCII source needs `# -*- coding: utf-8 -*-`.** Python 2 defaults to ASCII source, so a stray en dash in a docstring makes the module unimportable. This is easy to miss because neither other gate reports it: flake8 stays quiet, and `py_compile` — what `zwm build` uses — accepts the file and emits a working `.pyc`, so the mod still runs in-game. It surfaces only when something imports the source, i.e. the moment you write a test for it. `zwm lint py27-lint` now fails on it directly.

Both `mods/*/tests` and `testing/` are linted as Python 2.7 (`zwm lint py27-lint`), so test code is held to the same standard as the runtime it covers. `mods-common/` is linted with the same rules.

## Shared module tests

The tests for a shared module live once, in `mods-common/tests/test_*.py`, not in each mod that takes the module. They belong to no mod, so the runner loads the shared modules into a stand-in package, `mods_common`, that exists only during the run:

```python
from mods_common import view_claim
```

`zwm test` runs this suite once, after the mods, when at least one of the mods in the run takes a shared module. Thus `zwm test directives-helper` also runs the tests for `view_claim`, and a test run of one mod after a change to a shared module does not skip them.

### In-game check after a change to a shared module

Unit tests cannot show how a module behaves next to the client or next to another mod. After a change to a shared module, run the game in these combinations, with a fresh `game.log` for each (`zwm cycle --fresh-log` clears it):

| Run | Mods of ours installed | What it can catch |
| --- | --- | --- |
| Together | All mods, new builds | A fault in the changed module, and two mods on the same sub-view |
| Alone | Each mod that takes the module, by itself | A missing manifest entry, or a hidden dependency on another of our mods |
| Mixed | The new build of one mod next to the last release of another mod that takes the module, in both directions | A change that breaks a contract between mods (`view_claim`) or a shared file format (`storage`) |

Each mod already writes the log lines that decide a run:

- No `Traceback` or `ImportError` from a `zanju.*` logger, and each installed mod writes `initialized`.
- `route_gate`: DH and CT write `Garage is the visible route: False` on a screen over the garage, and `True` back in the garage.
- `view_claim`: the `subscribed to model updates on sub-view N` lines of DH and CT show two different values of N.
- `storage`: RPB writes `Mode selection state saved` and `Config saved to`. DH writes `placed the window at L,T from the stored X,Y`.

DH writes no line when it saves the window position. To see a save, drag the window, then open a screen that rebuilds the garage: the shop, the account dashboard, the campaign selector or personal missions. The directives and equipment screens do not rebuild it. Back in the garage, DH places the window from the stored position, and the log line shows that position.

## JavaScript tests

Gameface-side JavaScript is plain ES modules, which Node can import directly. A mod with JS tests carries a minimal `package.json` (`{"type": "module"}`) so Node parses `res/` and `tests/` the same way Gameface does. It declares no dependencies and is not packaged into the `.wotmod`.

Modules under test must not start themselves on import. The header patch guards its bootstrap on the presence of the Gameface view registry:

```js
if (typeof window !== 'undefined' && window.subViews) {
    start();
}

export { formatRemaining, overrides, newState, tick, start, setLabel, updateSubscription };
```

Importing it under Node is then side-effect free, and each test drives the exported functions against its own fake model, DOM and clock.

Node is optional: mods without JavaScript never need it. If JS tests exist but Node is missing, those suites are reported as **skipped** rather than failing, so the command still works on a toolchain image built before Node was added. Pass `--strict` to turn such a skip into a failure.

## What is worth testing

Favour logic that is pure, that users see, and that has already gone wrong once:

- string and time formatting (label widths, date/offset rendering);
- parsers fed by hand-edited files, such as `i18n/*.yml`;
- state machines around client events, such as what a header button shows between a subscription expiring and the server confirming it.

Deeply client-coupled code (inventory walks, view construction) is not worth faking — the stubs needed to reach it would encode more assumptions than the test verifies.

ActionScript is not covered: executing a SWF test suite needs a Flash Player, which has been end-of-life since 2020. `mxmlc` compiling during `zwm build` is the practical check there, so logic worth testing is better placed in Python or JavaScript.
