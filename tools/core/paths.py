import os

# This module lives at tools/core/paths.py, so the tools package dir (which holds
# the pinned manifest JSONs) is one level up from here, and the repo root is two.
_CORE_DIR = os.path.dirname(os.path.abspath(__file__))
TOOLS_DIR = os.path.dirname(_CORE_DIR)
REPO_ROOT = os.path.dirname(TOOLS_DIR)
MODS_DIR = os.path.join(REPO_ROOT, "mods")
DIST_DIR = os.path.join(REPO_ROOT, "dist")
ENV_PATH = os.path.join(REPO_ROOT, ".env")
WOT_VERSION_MANIFEST_PATH = os.path.join(TOOLS_DIR, "wot_version_manifest.json")
LICENSE_PATH = os.path.join(REPO_ROOT, "LICENSE.md")
