"""Compile the research progress bar Scaleform SWF."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source-file",
        default=os.path.join(SCRIPT_DIR, "ResearchProgressBarLobby.as"),
        help="Path to the ActionScript entrypoint.",
    )
    parser.add_argument(
        "--output-file",
        default=os.path.join(
            SCRIPT_DIR,
            "build",
            "res",
            "gui",
            "flash",
            "research-progress-bar-lobby.swf",
        ),
        help="Path to the compiled SWF output.",
    )
    parser.add_argument(
        "--api-source-dir",
        default=os.path.join(SCRIPT_DIR, "wot-api"),
        help="Directory containing local ActionScript WoT API mirror sources.",
    )
    parser.add_argument(
        "--api-swc",
        default=os.path.join(SCRIPT_DIR, "build", "wot-api.swc"),
        help="Path to the generated WoT API mirror SWC.",
    )
    parser.add_argument(
        "--target-player",
        default="32.0",
        help="Flash target player version passed to mxmlc.",
    )
    parser.add_argument(
        "--swf-version",
        default="17",
        help="SWF version passed to mxmlc.",
    )
    return parser.parse_args(argv)


def require_tool(name):
    tool_path = shutil.which(name)
    if not tool_path:
        raise RuntimeError("{} was not found on PATH.".format(name))
    return tool_path


def run_cmd(cmd):
    print("Running: {}".format(" ".join(cmd)))
    subprocess.check_call(cmd)


def main(argv=None):
    args = parse_args(argv)
    compc = require_tool("compc")
    mxmlc = require_tool("mxmlc")

    source_dir = os.path.dirname(os.path.abspath(args.source_file))
    output_dir = os.path.dirname(os.path.abspath(args.output_file))
    api_dir = os.path.dirname(os.path.abspath(args.api_swc))

    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(api_dir, exist_ok=True)

    api_arguments = [
        compc,
        "-output",
        os.path.abspath(args.api_swc),
        "-source-path={}".format(os.path.abspath(args.api_source_dir)),
        "-include-sources={}".format(os.path.abspath(args.api_source_dir)),
    ]
    run_cmd(api_arguments)

    arguments = [
        mxmlc,
        "-output",
        os.path.abspath(args.output_file),
        "-source-path",
        source_dir,
        "-external-library-path+={}".format(os.path.abspath(args.api_swc)),
        "-static-link-runtime-shared-libraries=true",
        "-target-player={}".format(args.target_player),
        "-swf-version={}".format(args.swf_version),
        "-default-size",
        "1920",
        "220",
        "-default-frame-rate",
        "30",
        os.path.abspath(args.source_file),
    ]
    run_cmd(arguments)

    print("Built UI SWF: {}".format(os.path.abspath(args.output_file)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
