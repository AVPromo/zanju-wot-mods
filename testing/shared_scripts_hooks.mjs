// Resolve hook for testing/shared_scripts_loader.mjs.
//
// Only an import that does not resolve is redirected, and only when the missing file is in the
// Gameface folder of a mod and has the name of a shared script. A mod that ships a file of its
// own with that name resolves normally, and `zwm build` stops on it anyway.
import { existsSync } from 'node:fs';
import { basename, dirname, join } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const SHARED_DIR = join(dirname(fileURLToPath(import.meta.url)), '..', 'mods-common', 'gameface');
const GAMEFACE_SEGMENT = '/res/gui/gameface/mods/';

export async function resolve(specifier, context, nextResolve) {
    try {
        return await nextResolve(specifier, context);
    } catch (error) {
        if (!context.parentURL || !specifier.startsWith('./')) {
            throw error;
        }
        const parentPath = fileURLToPath(context.parentURL).split('\\').join('/');
        if (parentPath.indexOf(GAMEFACE_SEGMENT) < 0) {
            throw error;
        }
        const shared = join(SHARED_DIR, basename(specifier));
        if (!existsSync(shared)) {
            throw error;
        }
        return { url: pathToFileURL(shared).href, shortCircuit: true };
    }
}
