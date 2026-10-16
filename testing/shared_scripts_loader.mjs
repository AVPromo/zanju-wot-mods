// Node `--import` entry for the JavaScript tests of a mod that takes a shared Gameface script.
//
// The build copies each script in mods-common/gameface/ into the Gameface folder of each mod
// that takes it, so the game finds `./tray.js` beside the module that imports it. The source
// tree has no such copy. This hook resolves such an import to the one authored copy, which is
// the same thing the build does, at test time. `zwm test` passes it to Node for every mod.
import { register } from 'node:module';

register('./shared_scripts_hooks.mjs', import.meta.url);
