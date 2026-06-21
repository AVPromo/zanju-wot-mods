"""Resolve repo tooling configuration from the environment, overlaid on .env.

`os.environ` takes precedence over the repo-root `.env` file, so the Dev
Container's container environment (e.g. `WOT_GAME_DIR=/game`) is authoritative
without a hand-written `.env`, while a local `.env` still works outside
containers.
"""

import io
import os

from .paths import ENV_PATH


def _read_env_file(path):
    env = {}
    if not path or not os.path.isfile(path):
        return env
    with io.open(path, "r", encoding="utf-8") as fh:
        for raw in fh:
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            env[key.strip()] = value.strip().strip('"').strip("'")
    return env


def load_env(path=ENV_PATH):
    env = _read_env_file(path)
    env.update(os.environ)
    return env
