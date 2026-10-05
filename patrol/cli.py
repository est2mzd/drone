"""Run with python3 -m patrol.cli from repository root."""
import argparse
import json
from pathlib import Path
from .localization import build_map

# USER_SETTINGS
DEFAULT_REFERENCE_END_S = 35.0  # remaining video frames are held out from descriptor map


def main():
    p = argparse.ArgumentParser(description=__doc__)
    commands = p.add_subparsers(dest='command', required=True)
    b = commands.add_parser('build-map')
    for name in ('video', 'poses', 'calibration', 'output'):
        b.add_argument('--'+name, required=True, type=Path)
    b.add_argument('--reference-end', type=float, default=DEFAULT_REFERENCE_END_S)
    demo = commands.add_parser('demo')
    demo.add_argument('--video', required=True, type=Path)
    demo.add_argument('--poses', required=True, type=Path)
    demo.add_argument('--map', required=True, type=Path)
    demo.add_argument('--world', required=True, type=Path)
    demo.add_argument('--output-dir', required=True, type=Path)
    a = p.parse_args()
    if a.command == 'build-map':
        print(json.dumps(build_map(a.video, a.poses, a.calibration, a.output, a.reference_end), indent=2))
    else:
        from .demo import run
        run(a)


if __name__ == '__main__':
    main()
