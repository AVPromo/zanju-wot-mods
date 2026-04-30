"""Compile the research progress bar Scaleform SWF."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        '--source-file',
        default=os.path.join(SCRIPT_DIR, 'src', 'ResearchProgressBarLobby.as'),
        help='Path to the ActionScript entrypoint.',
    )
    parser.add_argument(
        '--output-file',
        default=os.path.join(SCRIPT_DIR, '..', 'res', 'gui', 'flash', 'research-progress-bar-lobby.swf'),
        help='Path to the compiled SWF output.',
    )
    parser.add_argument(
        '--stub-source-dir',
        default=os.path.join(SCRIPT_DIR, 'stubs-src'),
        help='Directory containing local ActionScript stub sources.',
    )
    parser.add_argument(
        '--stub-swc',
        default=os.path.join(SCRIPT_DIR, 'build', 'wot-stubs.swc'),
        help='Path to the generated stub SWC.',
    )
    parser.add_argument(
        '--target-player',
        default='32.0',
        help='Flash target player version passed to mxmlc.',
    )
    parser.add_argument(
        '--swf-version',
        default='17',
        help='SWF version passed to mxmlc.',
    )
    return parser.parse_args(argv)


def require_tool(name):
    tool_path = shutil.which(name)
    if not tool_path:
        raise RuntimeError('{} was not found on PATH.'.format(name))
    return tool_path


def run_cmd(cmd):
    print('Running: {}'.format(' '.join(cmd)))
    subprocess.check_call(cmd)


def main(argv=None):
    args = parse_args(argv)
    compc = require_tool('compc')
    mxmlc = require_tool('mxmlc')

    source_dir = os.path.dirname(os.path.abspath(args.source_file))
    output_dir = os.path.dirname(os.path.abspath(args.output_file))
    stub_dir = os.path.dirname(os.path.abspath(args.stub_swc))

    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(stub_dir, exist_ok=True)

    stub_arguments = [
        compc,
        '-output',
        os.path.abspath(args.stub_swc),
        '-source-path={}'.format(os.path.abspath(args.stub_source_dir)),
        '-include-sources={}'.format(os.path.abspath(args.stub_source_dir)),
    ]
    run_cmd(stub_arguments)

    arguments = [
        mxmlc,
        '-output',
        os.path.abspath(args.output_file),
        '-source-path',
        source_dir,
        '-external-library-path+={}'.format(os.path.abspath(args.stub_swc)),
        '-static-link-runtime-shared-libraries=true',
        '-target-player={}'.format(args.target_player),
        '-swf-version={}'.format(args.swf_version),
        '-default-size',
        '420',
        '180',
        '-default-frame-rate',
        '30',
        os.path.abspath(args.source_file),
    ]
    run_cmd(arguments)

    print('Built UI SWF: {}'.format(os.path.abspath(args.output_file)))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())