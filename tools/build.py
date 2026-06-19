"""
Package mods under mods/<name>/ into .wotmod archives.

Usage:
    wot_mods_build --all                  # build all mods under mods/
    wot_mods_build research-progress-bar  # build one specific mod
    wot_mods_build mod-a mod-b            # build selected mods
    wot_mods_build --no-companion-bundle research-progress-bar
    wot_mods_build --verbose research-progress-bar
    python -m tools.build research-progress-bar

Output: dist/<mod-id>_<version>/mods/<target_wot_version>/<mod-id>_<version>.wotmod

Optional prebuild hooks:
- If mods/<name>/ui/compile_ui.py exists, it is run before packaging that mod.
- Generated packaged assets should land under mods/<name>/ui/build/res/.
- The build tool stages both mods/<name>/res/ and generated ui/build/res/ into the final archive.

Internal .wotmod layout:
    meta.xml                                (authored manifest: id/version/name/description)
    LICENSE.md                              (repo-root license, when present)
    res/scripts/client/gui/mods/<file>.pyc  (compiled from mods/<name>/src/)
    res/scripts/client/gui/mods/<pkg>/_mod_meta.pyc  (generated from meta.xml: MOD_ID/MOD_NAME)
    res/...                                 (from mods/<name>/res/ plus generated ui/build/res/)

Additional release output:
    dist/<mod-id>_<version>/<mod-id>_<version>.zip
    dist/<mod-id>_<version>/mods/<target_wot_version>/<mod-id>_<version>.wotmod
    dist/<mod-id>_<version>/mods/configs/<mod-folder-name>/...

Config files are NOT bundled.
Ship them separately to: <WoT install>/mods/configs/<mod-folder-name>/

Optional authored source layout:
    mods/<name>/config.template.json       →  mods/configs/<mod-folder-name>/config.json
    mods/<name>/i18n/*.yml                 →  res/mods/<meta.id>/text/*.yml
                                            and mods/configs/<mod-folder-name>/i18n/*.yml
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile

from .companion_artifacts import CompanionArtifactError, manifest_defines_bundle, resolve_cached_bundle_artifacts
from .companion_artifacts import load_manifest as load_companion_manifest
from .console import detail, section, success, warning
from .mod_meta import read_meta
from .paths import DIST_DIR, ENV_PATH, LICENSE_PATH, MODS_DIR
from .wot_version import resolve_target_wot_version


def load_env(path):
    env = {}
    if not os.path.isfile(path):
        return env

    with open(path, "r", encoding="utf-8") as fh:
        for raw in fh:
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            env[key.strip()] = value.strip().strip('"').strip("'")
    return env


def compile_py2_to_pyc(py2_exe, src_path, out_pyc_path):
    # WoT runtime for this client/mod stack expects Python 2 bytecode.
    cmd = [
        py2_exe,
        "-c",
        "import py_compile,sys; py_compile.compile(sys.argv[1], sys.argv[2])",
        src_path,
        out_pyc_path,
    ]
    subprocess.check_call(cmd)


def run_optional_prebuild(mod_dir, verbose=False):
    hook_path = os.path.join(mod_dir, "ui", "compile_ui.py")
    if not os.path.isfile(hook_path):
        return

    cmd = [sys.executable, hook_path]
    if not verbose:
        cmd.append("--quiet")
    detail("Running prebuild hook: {}".format(os.path.basename(hook_path)), verbose=verbose)
    subprocess.check_call(cmd)


def copy_tree_contents(src_dir, dst_dir):
    if not os.path.isdir(src_dir):
        return

    os.makedirs(dst_dir, exist_ok=True)
    for name in sorted(os.listdir(src_dir)):
        src_path = os.path.join(src_dir, name)
        dst_path = os.path.join(dst_dir, name)
        if os.path.isdir(src_path):
            shutil.copytree(src_path, dst_path, dirs_exist_ok=True)
        else:
            dst_parent = os.path.dirname(dst_path)
            if dst_parent:
                os.makedirs(dst_parent, exist_ok=True)
            shutil.copy2(src_path, dst_path)


def copy_file(src_path, dst_path):
    dst_parent = os.path.dirname(dst_path)
    if dst_parent:
        os.makedirs(dst_parent, exist_ok=True)
    shutil.copy2(src_path, dst_path)


def directory_has_entries(path):
    return os.path.isdir(path) and bool(os.listdir(path))


def resolve_config_source(mod_dir):
    flat_config_path = os.path.join(mod_dir, "config.template.json")
    legacy_config_dir = os.path.join(mod_dir, "config")

    has_flat_config = os.path.isfile(flat_config_path)
    has_legacy_config_dir = directory_has_entries(legacy_config_dir)

    if has_flat_config and has_legacy_config_dir:
        raise RuntimeError(
            "{} defines both config.template.json and config/; keep exactly one config source.".format(
                os.path.basename(mod_dir)
            )
        )
    if has_flat_config:
        return "file", flat_config_path
    if has_legacy_config_dir:
        return "dir", legacy_config_dir
    return None


def stage_i18n_resources(mod_dir, mod_id, staged_res_dir):
    i18n_dir = os.path.join(mod_dir, "i18n")
    if not os.path.isdir(i18n_dir):
        return

    legacy_text_dir = os.path.join(mod_dir, "res", "mods", mod_id, "text")
    if directory_has_entries(legacy_text_dir):
        raise RuntimeError(
            "{} defines both i18n/ and res/mods/{}/text/; keep exactly one localisation source.".format(
                os.path.basename(mod_dir),
                mod_id,
            )
        )

    copy_tree_contents(i18n_dir, os.path.join(staged_res_dir, "mods", mod_id, "text"))


def stage_resource_trees(mod_dir, mod_id, staged_res_dir):
    copy_tree_contents(os.path.join(mod_dir, "res"), staged_res_dir)
    stage_i18n_resources(mod_dir, mod_id, staged_res_dir)
    copy_tree_contents(os.path.join(mod_dir, "ui", "build", "res"), staged_res_dir)


def copy_config_source(mod_dir, dst_config_dir):
    config_source = resolve_config_source(mod_dir)
    if not config_source:
        return None

    source_kind, source_path = config_source
    if source_kind == "dir":
        copy_tree_contents(source_path, dst_config_dir)
    else:
        copy_file(source_path, os.path.join(dst_config_dir, "config.json"))
    return source_path


def copy_i18n_source(mod_dir, dst_i18n_dir):
    i18n_dir = os.path.join(mod_dir, "i18n")
    if not directory_has_entries(i18n_dir):
        return None

    copy_tree_contents(i18n_dir, dst_i18n_dir)
    return i18n_dir


def write_release_zip(bundle_root, bundle_name):
    mods_dir = os.path.join(bundle_root, "mods")
    zip_path = os.path.join(bundle_root, "{}.zip".format(bundle_name))

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_STORED) as zf:
        for dirpath, dirnames, filenames in os.walk(mods_dir):
            dirnames[:] = sorted(dirnames)
            for filename in sorted(filenames):
                abs_path = os.path.join(dirpath, filename)
                archive_path = os.path.relpath(abs_path, bundle_root).replace(os.sep, "/")
                zf.write(abs_path, archive_path)

    return zip_path


def create_release_bundle(mod_dir, mod_name, target_wot_version, output_path, include_companion_bundle=False):
    archive_name = os.path.basename(output_path)
    bundle_name = os.path.splitext(archive_name)[0]
    bundle_root = os.path.join(DIST_DIR, bundle_name)
    package_dir = os.path.join(bundle_root, "mods", target_wot_version)
    os.makedirs(package_dir, exist_ok=True)

    bundled_output_path = os.path.join(package_dir, archive_name)
    if os.path.normcase(os.path.abspath(output_path)) != os.path.normcase(os.path.abspath(bundled_output_path)):
        shutil.copy2(output_path, bundled_output_path)

    companion_artifacts = []
    if include_companion_bundle:
        companion_artifacts = stage_companion_bundle(package_dir, mod_name)

    bundle_config_dir = os.path.join(bundle_root, "mods", "configs", mod_name)
    copy_config_source(mod_dir, bundle_config_dir)
    copy_i18n_source(mod_dir, os.path.join(bundle_config_dir, "i18n"))

    write_release_zip(bundle_root, bundle_name)
    return bundle_root, companion_artifacts


def stage_companion_bundle(package_dir, mod_name):
    manifest = load_companion_manifest()
    if mod_name not in (manifest.get("bundles") or {}):
        return []

    try:
        companion_artifacts = resolve_cached_bundle_artifacts(mod_name, manifest=manifest)
    except CompanionArtifactError as exc:
        raise RuntimeError(str(exc)) from exc

    for item in companion_artifacts:
        shutil.copy2(item["path"], os.path.join(package_dir, item["artifact"]["filename"]))
    return companion_artifacts


def iter_python_source_files(src_dir):
    for dirpath, dirnames, filenames in os.walk(src_dir):
        dirnames[:] = sorted(name for name in dirnames if name != "__pycache__")
        for filename in sorted(filenames):
            if not filename.endswith(".py"):
                continue
            abs_path = os.path.join(dirpath, filename)
            rel_path = os.path.relpath(abs_path, src_dir)
            yield abs_path, rel_path


def iter_internal_packages(src_dir):
    """Yield immediate sub-package dirs of src/ (those holding an __init__.py)."""
    if not os.path.isdir(src_dir):
        return
    for name in sorted(os.listdir(src_dir)):
        pkg_dir = os.path.join(src_dir, name)
        if os.path.isfile(os.path.join(pkg_dir, "__init__.py")):
            yield name


def render_mod_meta_module(meta):
    return (
        "# -*- coding: utf-8 -*-\n"
        '"""Generated at build time from meta.xml. Do not edit; not committed."""\n'
        "from __future__ import unicode_literals\n"
        "\n"
        "MOD_ID = {id}\n"
        "MOD_NAME = {name}\n"
    ).format(id=json.dumps(meta["id"]), name=json.dumps(meta["name"]))


def bundle_generated_mod_meta(src_dir, meta, temp_dir, py2_exe, zf):
    """Compile a meta-derived _mod_meta module into each internal package.

    Keeps meta.xml the single authored source of MOD_ID/MOD_NAME: the runtime
    imports these from the generated module instead of hardcoding them.
    """
    source = render_mod_meta_module(meta)
    for package in iter_internal_packages(src_dir):
        py_path = os.path.join(temp_dir, "gen", package, "_mod_meta.py")
        os.makedirs(os.path.dirname(py_path), exist_ok=True)
        with open(py_path, "w", encoding="utf-8") as fh:
            fh.write(source)
        pyc_path = "{}c".format(py_path)
        compile_py2_to_pyc(py2_exe, py_path, pyc_path)
        archive_path = "res/scripts/client/gui/mods/{}/_mod_meta.pyc".format(package)
        zf.write(pyc_path, archive_path)


def build_mod(mod_name, py2_exe, target_wot_version, include_companion_bundle=None, verbose=False):
    mod_dir = os.path.join(MODS_DIR, mod_name)
    if not os.path.isdir(mod_dir):
        raise RuntimeError("Mod directory not found: {}".format(mod_dir))

    section("Building {}".format(mod_name))

    run_optional_prebuild(mod_dir, verbose=verbose)

    meta = read_meta(mod_name)
    mod_id = meta["id"]
    version = meta["version"]

    if not mod_id or "yourname" in mod_id:
        warning("WARNING: {} - mod id looks like a placeholder: {}".format(mod_name, mod_id))

    output_name = "{}_{}.wotmod".format(mod_id, version)
    bundle_name = os.path.splitext(output_name)[0]
    bundle_root = os.path.join(DIST_DIR, bundle_name)
    package_dir = os.path.join(bundle_root, "mods", target_wot_version)

    os.makedirs(DIST_DIR, exist_ok=True)
    if os.path.isdir(bundle_root):
        shutil.rmtree(bundle_root)
    os.makedirs(package_dir, exist_ok=True)
    output_path = os.path.join(package_dir, output_name)

    with (
        tempfile.TemporaryDirectory(prefix="wot-build-") as temp_dir,
        zipfile.ZipFile(output_path, "w", zipfile.ZIP_STORED) as zf,
    ):
        # WoT's package loader rejects compressed entries in some client versions.
        # Use store-only zip members for maximum compatibility.
        # meta.xml and LICENSE at archive root (spec: optional utility files).
        zf.write(os.path.join(mod_dir, "meta.xml"), "meta.xml")
        if os.path.isfile(LICENSE_PATH):
            zf.write(LICENSE_PATH, os.path.basename(LICENSE_PATH))

        # src/**/*.py  →  res/scripts/client/gui/mods/<relative-path>.pyc
        src_dir = os.path.join(mod_dir, "src")
        if os.path.isdir(src_dir):
            for abs_path, rel_path in iter_python_source_files(src_dir):
                compiled_rel_path = "{}c".format(rel_path)
                compiled_path = os.path.join(temp_dir, compiled_rel_path)
                compiled_dir = os.path.dirname(compiled_path)
                if compiled_dir:
                    os.makedirs(compiled_dir, exist_ok=True)
                compile_py2_to_pyc(py2_exe, abs_path, compiled_path)
                archive_path = "res/scripts/client/gui/mods/{}".format(compiled_rel_path.replace(os.sep, "/"))
                zf.write(compiled_path, archive_path)
            bundle_generated_mod_meta(src_dir, meta, temp_dir, py2_exe, zf)

        # Stage packaged resources from committed source plus generated build output.
        staged_res_dir = os.path.join(temp_dir, "staged_res")
        stage_resource_trees(mod_dir, mod_id, staged_res_dir)
        if os.path.isdir(staged_res_dir):
            for dirpath, dirnames, filenames in os.walk(staged_res_dir):
                dirnames[:] = sorted(dirnames)
                for filename in sorted(filenames):
                    abs_path = os.path.join(dirpath, filename)
                    archive_path = "res/{}".format(os.path.relpath(abs_path, staged_res_dir).replace(os.sep, "/"))
                    zf.write(abs_path, archive_path)

    success("Package built: {}".format(output_name))
    detail("Path: {}".format(output_path), verbose=verbose)

    release_bundle_dir, companion_artifacts = create_release_bundle(
        mod_dir,
        mod_name,
        target_wot_version,
        output_path,
        include_companion_bundle=should_include_companion_bundle(mod_name, include_companion_bundle),
    )
    success("Release bundle ready")
    detail("Path: {}".format(release_bundle_dir), verbose=verbose)

    if companion_artifacts:
        success("Companion artifacts staged: {}".format(len(companion_artifacts)))
        for item in companion_artifacts:
            detail("Companion: {}".format(item["artifact"]["filename"]), verbose=verbose)

    config_source = resolve_config_source(mod_dir)
    if config_source:
        success("Config staged")
        _, config_source_path = config_source
        detail("Source: {}".format(config_source_path), verbose=verbose)
        detail("Deploy to: <WoT install>/mods/configs/{}/".format(mod_name), verbose=verbose)


def should_include_companion_bundle(mod_name, include_companion_bundle):
    if include_companion_bundle is not None:
        return include_companion_bundle
    try:
        return manifest_defines_bundle(mod_name)
    except CompanionArtifactError as exc:
        raise RuntimeError(str(exc)) from exc


def parse_args(argv):
    include_companion_bundle = None
    run_all = False
    verbose = False
    targets = []
    for arg in argv:
        if arg == "--standalone-config-bundle":
            include_companion_bundle = True
            continue
        if arg == "--no-companion-bundle":
            include_companion_bundle = False
            continue
        if arg == "--all":
            run_all = True
            continue
        if arg == "--verbose":
            verbose = True
            continue
        targets.append(arg)
    return include_companion_bundle, run_all, verbose, targets


def _print_targeting_help(available_mods):
    warning("No mod targets provided")
    success("Use --all to build all mods, or pass one or more mod names")
    if available_mods:
        success("Available mods: {}".format(", ".join(available_mods)))
    else:
        warning("No mods found under mods/")


def _main():
    env = load_env(ENV_PATH)
    py2_exe = env.get("WOT_PYTHON2_EXE", "").strip()
    if not py2_exe:
        raise RuntimeError("WOT_PYTHON2_EXE is required in .env for this repository.")
    if not os.path.isfile(py2_exe):
        raise RuntimeError("WOT_PYTHON2_EXE does not exist: {}".format(py2_exe))
    target_wot_version = resolve_target_wot_version(env, require_game_dir=False)
    include_companion_bundle, run_all, verbose, targets = parse_args(sys.argv[1:])
    if run_all and targets:
        raise RuntimeError("Use either --all or explicit mod names, not both")

    available_mods = []
    if os.path.isdir(MODS_DIR):
        available_mods = sorted(d for d in os.listdir(MODS_DIR) if os.path.isdir(os.path.join(MODS_DIR, d)))
    if run_all:
        mod_names = available_mods
    elif targets:
        mod_names = targets
    else:
        _print_targeting_help(available_mods)
        return

    if not mod_names:
        warning("No mods found under mods/")
        return

    success("Target WoT client version: {}".format(target_wot_version))

    for mod_name in mod_names:
        build_mod(
            mod_name,
            py2_exe,
            target_wot_version,
            include_companion_bundle=include_companion_bundle,
            verbose=verbose,
        )


def main():
    try:
        return _main()
    except RuntimeError as exc:
        raise SystemExit(str(exc)) from None


if __name__ == "__main__":
    main()
