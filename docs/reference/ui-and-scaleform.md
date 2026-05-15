# UI And Scaleform

## Preferred UI Pattern In This Repo

For custom lobby UI, the stable pattern is:

- compile ActionScript externally
- register the SWF through WoT view settings
- use a WoT-compatible root such as `net.wg.infrastructure.base.AbstractView`
- let WoT own the display tree attachment

A plain `Sprite` root is not enough for this load path.

## Build Hook

If a mod has `ui/compile_ui.py`, `build.py` runs it automatically before packaging.
Generated SWF output belongs in ignored build folders under `ui/build/`.

## Window Lifetime

This repository uses a pragmatic rule:

- keep the custom window persistent for ordinary hide/show cases when that is stable
- dispose it completely when a route or UI context proves that a hidden window still interferes with native behavior

## Hangar Visibility Rules

Default hangar visibility is not only a matter of one container alias.
In practice, route changes and container-layer changes both matter.
Some hangar-local overlays announce themselves only through lobby-state-machine route changes.

## Input And Focus Notes

Hidden custom windows can still interfere with native UI behavior if they remain part of WoT's active window stack.
When that happens, hiding the SWF is not enough; the view must be disposed and recreated on return to the safe context.

## Measured Layout Data

When native UI geometry is unstable across resolution changes, use measured resolution buckets instead of parsing display-tree bounds every frame.
That tradeoff is acceptable when the target anchor is effectively static for a given width bucket.
