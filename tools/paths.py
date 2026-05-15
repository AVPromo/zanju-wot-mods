import os

TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(TOOLS_DIR)
MODS_DIR = os.path.join(REPO_ROOT, "mods")
DIST_DIR = os.path.join(REPO_ROOT, "dist")
ENV_PATH = os.path.join(REPO_ROOT, ".env")
