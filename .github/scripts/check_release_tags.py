"""Check what the publish step would refuse, with no access to GitHub.

The publish step on master refuses two faults: two mods with the same release acronym, and a
mod at 1.0.0 or higher with no changelog section for its current version. It finds them only
after the merge, and there a fault stops the release of every mod, not only the one at fault.
This script runs in the pull-request checks, so these faults show before the merge.
"""

from __future__ import annotations

from release_lib import extract_changelog_section, is_published_version, iter_mods


def main():
    for mod in iter_mods():
        if is_published_version(mod["version"]):
            extract_changelog_section(mod["changelog_path"], mod["version"])
            print("{:<12} {}".format(mod["tag"], mod["mod_name"]))
        else:
            print("{:<12} {} (pre-1.0, not released)".format(mod["tag"], mod["mod_name"]))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as exc:
        raise SystemExit(str(exc)) from None
