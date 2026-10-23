"""Finite G1 terrain/access diagnostic; production imports, no save access."""
from __future__ import annotations
import argparse
from collections import Counter
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import random
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
GAME = ROOT / 'roguelike'
sys.path[:0] = [str(GAME), str(ROOT / 'tools/critical_fix_regressions/tests')]
os.environ.update(SDL_VIDEODRIVER='dummy', SDL_AUDIODRIVER='dummy', PYGAME_HIDE_SUPPORT_PROMPT='1')
os.chdir(GAME)
import pygame
from test_generation_g1 import reachable, edge_cells
from test_effect_persistence import load_data
from generation.region_gen import generate_region
from generation.world_gen import generate_world
from world.world_map import WorldMap


def color(m, x, y):
    t = str(m.tiles[x, y]['terrain'])
    if t == 'dirt_path': return '#e6b874'
    if t.startswith('road_') or t in ('flagstone', 'cobblestone'): return '#cbd2d1'
    if t in ('river_water', 'water', 'shallow_water', 'river_bank', 'puddle'): return '#448b9b'
    if 'door' in t: return '#d49c53'
    if not m.walkable[x, y]: return '#252c39'
    if t in ('floor', 'worn_stone', 'wood_floor'): return '#d0bd96'
    if t in ('grass', 'varied_grass', 'tall_grass'): return '#496c4a'
    return '#8f795a'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=True)
    captured = io.StringIO()
    with contextlib.redirect_stdout(captured):
        data = load_data()
        world = WorldMap(128, 128)
        world.seed = 20261020
        generate_world(world, data, random.Random(world.seed))
        maps, rows = {}, []
        for tid, coords in world.town_groups.items():
            for xy in coords:
                c = world.get(*xy)
                m, _ = generate_region(c, 80, 43, data.terrain, data=data)
                maps[xy] = m
                access = reachable(m, data)
                bad = []
                occupied = set()
                overlaps = []
                for b in c.town_data.buildings:
                    footprint = {(x, y) for x in range(b['x'], b['x'] + b['w'])
                                 for y in range(b['y'], b['y'] + b['h'])}
                    if occupied & footprint: overlaps.append(b['id'])
                    occupied |= footprint
                    for s in b.get('item_specs', []):
                        if s.get('text_id') and (s['x'], s['y']) not in access:
                            bad.append({'id': b['id'], 'spec': s})
                rows.append({'xy': xy, 'role': c.town_role, 'unreachable_notes': bad,
                             'overlaps': overlaps, 'buildings': [b['id'] for b in c.town_data.buildings]})
        seam = [generate_region(world.get(*xy), 80, 43, data.terrain, data=data)[0]
                for xy in [(65, 73), (65, 74)]]
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    summary = {'commit': commit, 'world_seed': world.seed, 'hashseed': os.getenv('PYTHONHASHSEED'),
               'python': sys.version, 'town_chunks': rows,
               'seam': [sorted(edge_cells(seam[0], 'south')), sorted(edge_cells(seam[1], 'north'))],
               'source_sha256': {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                                 for p in sorted((GAME / 'generation').glob('*.py'))}}
    (out / 'terrain-diagnostic.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    (out / 'terrain-diagnostic.log').write_text(captured.getvalue(), encoding='utf-8')
    pygame.font.init()
    canvas = pygame.Surface((1320, 700))
    canvas.fill('#10171e')
    font = pygame.font.SysFont('Arial', 17)
    def label(text, x, y):
        canvas.blit(font.render(text, True, '#edf3f5'), (x, y))
    label('G1 actual terrain arrays | seed 20261020 | ' + commit[:12], 20, 12)
    label('Terrain only; functional decor, items and actors omitted. Red lines are chunk borders.', 20, 40)
    coords = world.town_groups[0]
    minx, miny = min(x for x, y in coords), min(y for x, y in coords)
    for xy in coords:
        m = maps[xy]
        tile = pygame.Surface((80, 43))
        for x in range(80):
            for y in range(43): tile.set_at((x, y), color(m, x, y))
        ox, oy = 20 + (xy[0] - minx) * 320, 85 + (xy[1] - miny) * 172
        canvas.blit(pygame.transform.scale(tile, (320, 172)), (ox, oy))
        pygame.draw.rect(canvas, '#ff7469', (ox, oy, 320, 172), 1)
        label(world.get(*xy).town_role + ' ' + str(xy), ox + 5, oy + 3)
    label('(65,73) south / (65,74) north', 995, 85)
    crop = pygame.Surface((17, 12))
    for x in range(17):
        for y in range(12): crop.set_at((x, y), color(seam[int(y >= 6)], x + 32, y + 37 if y < 6 else y - 6))
    canvas.blit(pygame.transform.scale(crop, (306, 216)), (995, 120))
    pygame.draw.line(canvas, '#ff7469', (995, 228), (1300, 228), 3)
    label('South: ' + str(summary['seam'][0]), 995, 350)
    label('North: ' + str(summary['seam'][1]), 995, 378)
    label('Road continuity diagnostic;', 995, 416)
    label('not a player hard-lock test.', 995, 442)
    label('Grey: roads/plaza | Brown: ground | Sand: tracks | Green: grass | Dark: solid | Tan: floor | Gold: doors | Blue: water', 20, 625)
    pygame.image.save(canvas, str(out / 'terrain-atlas.png'))
    print(json.dumps({'town_chunks': len(rows), 'seam': summary['seam'],
                      'unreachable_notes': dict(Counter(b['id'] for r in rows for b in r['unreachable_notes'])),
                      'overlaps': sum(len(r['overlaps']) for r in rows)}))


if __name__ == '__main__':
    main()
