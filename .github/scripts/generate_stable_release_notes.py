"""Generate release notes for the rolling stable GitHub release."""

from __future__ import annotations

import argparse
import datetime as dt
import os
import sys
import xml.etree.ElementTree as ET


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(SCRIPT_DIR))
MODS_DIR = os.path.join(REPO_ROOT, "mods")
DIST_DIR = os.path.join(REPO_ROOT, "dist")
WOT_VERSION_MANIFEST_PATH = os.path.join(REPO_ROOT, "tools", "wot_version_manifest.json")


def _default_built_at():
    # Human-readable UTC stamp (e.g. "17 June 2026 21:48 UTC"), matching the
    # day-month-year style used in the mod changelogs. Built without %-d/%#d so it
    # stays portable across the Linux CI runner and local Windows runs.
    now = dt.datetime.now(dt.timezone.utc).replace(microsecond=0)
    return "{day} {month} {year} {time} UTC".format(
        day=now.day,
        month=now.strftime("%B"),
        year=now.year,
        time=now.strftime("%H:%M"),
    )


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        required=True,
        help="Path to the markdown file to write.",
    )
    parser.add_argument(
        "--repo",
        default=os.environ.get("GITHUB_REPOSITORY", "").strip(),
        help="owner/repo used for changelog and commit links.",
    )
    parser.add_argument(
        "--commit",
        default=os.environ.get("GITHUB_SHA", "").strip(),
        help="Commit SHA used to pin source links.",
    )
    parser.add_argument(
        "--built-at",
        default=_default_built_at(),
        help="UTC timestamp to include in the notes.",
    )
    return parser.parse_args(argv)


def read_meta(mod_dir):
    meta_path = os.path.join(mod_dir, "meta.xml")
    root = ET.parse(meta_path).getroot()
    return {
        "id": root.findtext("id", "").strip(),
        "name": root.findtext("name", "").strip(),
        "version": root.findtext("version", "").strip(),
    }


def read_wot_version():
    import json

    with open(WOT_VERSION_MANIFEST_PATH, "r", encoding="utf-8") as fh:
        manifest = json.load(fh)
    return (manifest.get("wotClientVersion") or "").strip()


def iter_release_mods():
    if not os.path.isdir(MODS_DIR):
        return

    for mod_name in sorted(os.listdir(MODS_DIR)):
        mod_dir = os.path.join(MODS_DIR, mod_name)
        if not os.path.isdir(mod_dir):
            continue

        meta_path = os.path.join(mod_dir, "meta.xml")
        if not os.path.isfile(meta_path):
            continue

        meta = read_meta(mod_dir)
        if not meta["id"] or not meta["version"]:
            raise RuntimeError("{} has missing id or version in meta.xml".format(mod_name))

        bundle_name = "{}_{}".format(meta["id"], meta["version"])
        bundle_dir = os.path.join(DIST_DIR, bundle_name)
        zip_path = os.path.join(bundle_dir, "{}.zip".format(bundle_name))
        changelog_path = os.path.join(mod_dir, "CHANGELOG.md")

        if not os.path.isfile(zip_path):
            raise RuntimeError(
                "Expected built release zip for {} at {}. Run zwm build before generating release notes.".format(
                    mod_name,
                    zip_path,
                )
            )
        if not os.path.isfile(changelog_path):
            raise RuntimeError("Missing changelog for {}: {}".format(mod_name, changelog_path))

        yield {
            "mod_name": mod_name,
            "display_name": meta["name"] or mod_name,
            "mod_id": meta["id"],
            "version": meta["version"],
            "bundle_name": bundle_name,
            "bundle_dir": bundle_dir,
            "zip_path": zip_path,
            "changelog_path": changelog_path,
        }


def build_commit_link(repo, commit):
    if not repo or not commit:
        return None
    return "https://github.com/{}/commit/{}".format(repo, commit)


def build_changelog_link(repo, commit, mod_name):
    if not repo or not commit:
        return None
    return "https://github.com/{}/blob/{}/mods/{}/CHANGELOG.md".format(repo, commit, mod_name)


def render_notes(repo, commit, built_at):
    mods = list(iter_release_mods())
    if not mods:
        raise RuntimeError("No releasable mods were found under mods/")

    wot_version = read_wot_version()
    commit_link = build_commit_link(repo, commit)

    lines = [
        "This is an automatically generated stable build of the current `master` branch.",
        "",
        "- Build date: `{}`".format(built_at),
    ]
    if commit and commit_link:
        lines.append("- Reference commit: [{}]({})".format(commit[:7], commit_link))
    elif commit:
        lines.append("- Reference commit: `{}`".format(commit))

    if wot_version:
        lines.append("- Target WoT client version: `{}`".format(wot_version))

    lines.extend(["", "Included mods:"])
    for mod in mods:
        changelog_link = build_changelog_link(repo, commit, mod["mod_name"])
        if changelog_link:
            suffix = " ([CHANGELOG]({}))".format(changelog_link)
        else:
            suffix = ""
        lines.append("- {} `{}`{}".format(mod["display_name"], mod["version"], suffix))

    return "\n".join(lines) + "\n"


def write_output(path, content):
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content)


def main(argv=None):
    args = parse_args(argv)
    content = render_notes(args.repo, args.commit, args.built_at)
    write_output(os.path.abspath(args.output), content)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except RuntimeError as exc:
        raise SystemExit(str(exc)) from None