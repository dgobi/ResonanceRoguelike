"""Compatibility entry point for the shared structure authoring command."""
from pathlib import Path
import argparse
import json
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--game', type=Path, required=True)
    parser.add_argument('--building', type=Path, default=Path(__file__).with_name('author_cottage_a.json'))
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'tools'))
    sys.path.insert(0, str(args.game.resolve()))
    from generation.structure_contract import read_document
    from structure_authoring import main as author
    raw = read_document(args.building)
    command = [str(args.building), '--game', str(args.game), '--route', 'ordinary_building',
               '--category', raw.get('category', 'residential'), '--register']
    if args.output:
        command += ['--output', str(args.output)]
    return author(command)


if __name__ == '__main__':
    raise SystemExit(main())
