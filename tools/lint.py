from __future__ import print_function

import argparse
import glob
import io
import os
import subprocess
import sys

from .paths import ENV_PATH, REPO_ROOT

try:
    from shutil import which as find_executable
except ImportError:
    from distutils.spawn import find_executable  # type: ignore


SAFE_AUTOPEP8_SELECT = "E1,E2,E3,W291,W292,W293,W391"
ALIAS_COMMANDS = {
    "py3-check": ("check", {"py3_only": True}),
    "py3-format-check": ("py3-format", {"check": True}),
    "py27-format-check": ("py27-format", {"check": True}),
}


def load_env(path):
    env = {}
    if not os.path.isfile(path):
        return env

    with io.open(path, "r", encoding="utf-8") as fh:
        for raw in fh:
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            env[key.strip()] = value.strip().strip('"').strip("'")
    return env


def quote_arg(value):
    if any(ch in value for ch in (" ", "\t")):
        return '"{}"'.format(value)
    return value


def format_command(cmd):
    return " ".join(quote_arg(part) for part in cmd)


def run_command(cmd):
    print("Running: {}".format(format_command(cmd)))
    try:
        subprocess.check_call(cmd, cwd=REPO_ROOT)
    except OSError as exc:
        raise RuntimeError("Failed to run {}: {}".format(cmd[0], exc))


def expand_patterns(patterns):
    paths = []
    seen = set()
    for pattern in patterns:
        abs_pattern = os.path.join(REPO_ROOT, pattern)
        matches = glob.glob(abs_pattern)
        if not matches and not any(ch in pattern for ch in ("*", "?", "[")) and os.path.exists(abs_pattern):
            matches = [abs_pattern]
        for abs_path in sorted(matches):
            rel_path = os.path.relpath(abs_path, REPO_ROOT)
            if rel_path in seen:
                continue
            seen.add(rel_path)
            paths.append(rel_path)
    return paths


def get_py3_targets():
    return expand_patterns(
        [
            os.path.join("tools", "*.py"),
            os.path.join("mods", "*", "ui", "compile_ui.py"),
        ]
    )


def get_py27_targets():
    return expand_patterns([os.path.join("mods", "*", "src")])


def resolve_command_path(value, label):
    if os.path.isabs(value) or os.path.isfile(value):
        if not os.path.exists(value):
            raise RuntimeError("{} does not exist: {}".format(label, value))
        return value

    resolved = find_executable(value)
    if not resolved:
        raise RuntimeError("{} was not found: {}".format(label, value))
    return resolved


def resolve_py27_python(override):
    if override:
        return resolve_command_path(override, "Python 2.7 executable override")

    env = load_env(ENV_PATH)
    py27_python = env.get("WOT_PYTHON2_EXE", "").strip()
    if not py27_python:
        raise RuntimeError("WOT_PYTHON2_EXE is required in .env for Python 2.7 lint commands.")
    return resolve_command_path(py27_python, "WOT_PYTHON2_EXE")


def require_targets(targets, label):
    if targets:
        return targets
    print("No {} targets found.".format(label))
    return []


def run_py3_format(check):
    targets = require_targets(get_py3_targets(), "Python 3")
    if not targets:
        return

    cmd = [sys.executable, "-m", "black"]
    if check:
        cmd.append("--check")
    cmd.extend(targets)
    run_command(cmd)


def run_py3_lint(fix):
    targets = require_targets(get_py3_targets(), "Python 3")
    if not targets:
        return

    cmd = [sys.executable, "-m", "ruff", "check"]
    if fix:
        cmd.append("--fix")
    cmd.extend(targets)
    run_command(cmd)


def run_py27_lint(py27_python):
    targets = require_targets(get_py27_targets(), "Python 2.7")
    if not targets:
        return

    cmd = [py27_python, "-m", "flake8", "--config", ".flake8"]
    cmd.extend(targets)
    run_command(cmd)


def run_py27_format(check):
    targets = require_targets(get_py27_targets(), "Python 2.7")
    if not targets:
        return

    cmd = [
        sys.executable,
        "-m",
        "autopep8",
        "--recursive",
        "--max-line-length",
        "120",
        "--select",
        SAFE_AUTOPEP8_SELECT,
    ]
    if check:
        cmd.extend(["--diff", "--exit-code"])
    else:
        cmd.append("--in-place")
    cmd.extend(targets)
    run_command(cmd)


def parse_args(argv):
    parser = argparse.ArgumentParser(
        description=(
            'Run the repository Python format and lint workflow. The default "check" command '
            "runs Python 3 format-check and lint plus Python 2.7 lint and format-check."
        )
    )
    parser.add_argument(
        "command",
        nargs="?",
        default="check",
        choices=(
            "check",
            "fix",
            "py3-check",
            "py3-format",
            "py3-format-check",
            "py3-lint",
            "py27-lint",
            "py27-format",
            "py27-format-check",
        ),
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="For format commands, check formatting instead of rewriting files.",
    )
    parser.add_argument(
        "--py3-only",
        action="store_true",
        help="Restrict composite commands such as check or fix to the Python 3 surface.",
    )
    parser.add_argument(
        "--py27-only",
        action="store_true",
        help="Restrict composite commands such as check to the Python 2.7 surface.",
    )
    parser.add_argument(
        "--py27-python",
        help="Override the Python 2.7 executable used for flake8, for example python inside a CI container.",
    )
    return parser.parse_args(argv)


def normalize_args(args):
    alias = ALIAS_COMMANDS.get(args.command)
    if not alias:
        return args

    command, overrides = alias
    args.command = command
    for name, value in overrides.items():
        setattr(args, name, value)
    return args


def validate_args(args):
    if args.py3_only and args.py27_only:
        raise RuntimeError("Choose only one of --py3-only or --py27-only.")

    if args.check and args.command not in ("py3-format", "py27-format"):
        raise RuntimeError("--check is only valid with py3-format or py27-format.")

    if args.command in ("py3-format", "py3-lint") and args.py27_only:
        raise RuntimeError("{} does not support --py27-only.".format(args.command))

    if args.command in ("py27-format", "py27-lint") and args.py3_only:
        raise RuntimeError("{} does not support --py3-only.".format(args.command))

    if args.command == "fix" and args.py27_only:
        raise RuntimeError("fix only applies Python 3 auto-fixes. Use py27-format explicitly.")


def run_check(args):
    if not args.py27_only:
        run_py3_format(check=True)
        run_py3_lint(fix=False)

    if not args.py3_only:
        run_py27_lint(resolve_py27_python(args.py27_python))
        run_py27_format(check=True)


def run_fix(args):
    run_py3_lint(fix=True)
    run_py3_format(check=False)

    if not args.py3_only:
        run_py27_lint(resolve_py27_python(args.py27_python))
        print(
            "Note: Python 2.7 autoformatting stays explicit for now. "
            'Use "wot_mods_lint py27-format-check" or "python -m tools.lint py27-format-check" '
            "to review that diff first."
        )


def main(argv=None):
    args = normalize_args(parse_args(argv or sys.argv[1:]))
    validate_args(args)

    if args.command == "check":
        run_check(args)
        return 0

    if args.command == "fix":
        run_fix(args)
        return 0

    if args.command == "py3-format":
        run_py3_format(check=args.check)
        return 0

    if args.command == "py3-lint":
        run_py3_lint(fix=False)
        return 0

    if args.command == "py27-lint":
        run_py27_lint(resolve_py27_python(args.py27_python))
        return 0

    if args.command == "py27-format":
        run_py27_format(check=args.check)
        return 0

    raise RuntimeError("Unsupported command: {}".format(args.command))


if __name__ == "__main__":
    try:
        sys.exit(main())
    except RuntimeError as exc:
        print("ERROR: {}".format(exc), file=sys.stderr)
        sys.exit(1)
