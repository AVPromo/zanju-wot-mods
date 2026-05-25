"""Download the manifest-pinned companion artifacts into the ignored local cache."""

from __future__ import annotations

import sys

from .companion_artifacts import CompanionArtifactError, fetch_manifest_artifacts, load_manifest


def parse_args(argv):
    force = False
    for arg in argv:
        if arg == "--force":
            force = True
            continue
        raise RuntimeError("Unknown argument: {}".format(arg))
    return force


def main():
    force = parse_args(sys.argv[1:])
    manifest = load_manifest()
    results = fetch_manifest_artifacts(manifest=manifest, force=force)

    for result in results:
        status = "downloaded" if result["downloaded"] else "verified"
        artifact = result["artifact"]
        print("{}: {} -> {}".format(status, artifact["filename"], result["path"]))

    print("Done. Companion artifact cache is ready.")


if __name__ == "__main__":
    try:
        main()
    except CompanionArtifactError as exc:
        raise SystemExit(str(exc)) from exc
