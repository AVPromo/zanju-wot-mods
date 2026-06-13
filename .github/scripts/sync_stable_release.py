"""Create or update the rolling stable GitHub release in place."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys

from generate_stable_release_notes import iter_release_mods


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag", default="stable", help="Git tag backing the rolling release.")
    parser.add_argument("--title", default="Stable build", help="GitHub release title.")
    parser.add_argument(
        "--notes-file",
        required=True,
        help="Path to the markdown file containing release notes.",
    )
    parser.add_argument(
        "--target",
        default=os.environ.get("GITHUB_SHA", "").strip(),
        help="Commit SHA the rolling tag should point at.",
    )
    parser.add_argument(
        "--repo",
        default=os.environ.get("GITHUB_REPOSITORY", "").strip(),
        help="Optional owner/repo override for gh commands.",
    )
    return parser.parse_args(argv)


def build_asset_paths():
    assets = []
    for mod in iter_release_mods():
        assets.append(os.path.abspath(mod["zip_path"]))
    if not assets:
        raise RuntimeError("No release assets were found for the current mods/")
    return assets


def run_command(cmd, check=True):
    result = subprocess.run(cmd, check=False, capture_output=True, text=True)
    if check and result.returncode != 0:
        message = ["Command failed: {}".format(" ".join(cmd))]
        if result.stdout:
            message.append(result.stdout.rstrip())
        if result.stderr:
            message.append(result.stderr.rstrip())
        raise RuntimeError("\n".join(message))
    return result


def gh_command(args, repo):
    cmd = ["gh"]
    if repo:
        cmd.extend(["-R", repo])
    cmd.extend(args)
    return cmd


def get_release(repo, tag):
    result = run_command(gh_command(["release", "view", tag, "--json", "assets,name"], repo), check=False)
    if result.returncode == 0:
        return json.loads(result.stdout)

    combined_output = "\n".join(part for part in (result.stdout, result.stderr) if part).lower()
    if "not found" in combined_output:
        return None

    message = ["Could not inspect release '{}'".format(tag)]
    if result.stdout:
        message.append(result.stdout.rstrip())
    if result.stderr:
        message.append(result.stderr.rstrip())
    raise RuntimeError("\n".join(message))


def push_tag(tag, target):
    if not target:
        raise RuntimeError("--target or GITHUB_SHA is required")

    run_command(["git", "tag", "-f", tag, target])
    run_command(["git", "push", "origin", "refs/tags/{}".format(tag), "--force"])


def create_release(repo, tag, title, notes_file, target, asset_paths):
    push_tag(tag, target)
    cmd = gh_command(
        ["release", "create", tag] + asset_paths + ["--title", title, "--notes-file", notes_file, "--latest"],
        repo,
    )
    run_command(cmd)


def update_release(repo, tag, title, notes_file, target, asset_paths, release_info):
    existing_assets = {asset["name"] for asset in release_info.get("assets") or []}
    desired_assets = {os.path.basename(path) for path in asset_paths}

    upload_cmd = gh_command(["release", "upload", tag] + asset_paths + ["--clobber"], repo)
    run_command(upload_cmd)

    stale_assets = sorted(existing_assets - desired_assets)
    for asset_name in stale_assets:
        delete_cmd = gh_command(["release", "delete-asset", tag, asset_name, "--yes"], repo)
        run_command(delete_cmd)

    push_tag(tag, target)

    edit_cmd = gh_command(
        [
            "release",
            "edit",
            tag,
            "--title",
            title,
            "--notes-file",
            notes_file,
            "--latest",
        ],
        repo,
    )
    run_command(edit_cmd)


def main(argv=None):
    args = parse_args(argv)
    notes_file = os.path.abspath(args.notes_file)
    if not os.path.isfile(notes_file):
        raise RuntimeError("Release notes file was not found: {}".format(notes_file))

    asset_paths = build_asset_paths()
    release_info = get_release(args.repo, args.tag)

    if release_info is None:
        create_release(args.repo, args.tag, args.title, notes_file, args.target, asset_paths)
    else:
        update_release(args.repo, args.tag, args.title, notes_file, args.target, asset_paths, release_info)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except RuntimeError as exc:
        raise SystemExit(str(exc)) from None