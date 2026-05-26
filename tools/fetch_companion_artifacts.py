"""Download the manifest-pinned companion artifacts into the ignored local cache."""

from __future__ import annotations

import sys

from .companion_artifacts import CompanionArtifactError, fetch_manifest_artifacts, load_manifest
from .console import detail, section, success


def parse_args(argv):
    force = False
    verbose = False
    for arg in argv:
        if arg == "--force":
            force = True
            continue
        if arg == "--verbose":
            verbose = True
            continue
        raise RuntimeError("Unknown argument: {}".format(arg))
    return force, verbose


def main():
    force, verbose = parse_args(sys.argv[1:])
    section("Fetch companion artifacts")
    manifest = load_manifest()
    results = fetch_manifest_artifacts(manifest=manifest, force=force)

    downloaded_count = 0
    verified_count = 0
    for result in results:
        if result["downloaded"]:
            downloaded_count += 1
        else:
            verified_count += 1
        if verbose:
            status = "downloaded" if result["downloaded"] else "verified"
            artifact = result["artifact"]
            detail("{}: {} -> {}".format(status, artifact["filename"], result["path"]), verbose=True)

    success(
        "Companion artifact cache ready (downloaded: {}, verified: {})".format(
            downloaded_count,
            verified_count,
        )
    )


if __name__ == "__main__":
    try:
        main()
    except CompanionArtifactError as exc:
        raise SystemExit(str(exc)) from exc
