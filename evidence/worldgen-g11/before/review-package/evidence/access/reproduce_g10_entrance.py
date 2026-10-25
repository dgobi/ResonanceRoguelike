#!/usr/bin/env python3
"""Bounded G10 entrance-access review probe; no tracked files or campaigns edited.

Usage: python reproduce_g10_entrance.py --repo PATH --out PATH [--sample]
Run with the repository's dependency interpreter. The default produces one
before/after witness, a current G9-route comparison, and controlled real handlers.
--sample repeats the disclosed 60-scene discovery sample (not a prevalence study).
"""
import argparse
import contextlib
import copy
import gzip
import io
import json
import os
from pathlib import Path
import platform
import random
import subprocess
import sys
import tempfile
from types import SimpleNamespace
from unittest.mock import patch


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--sample', action='store_true')
    args = parser.parse_args()
    root = args.repo.resolve()
    out = args.out.resolve()
    if not (root / 'roguelike/generation/wilderness.py').is_file():
        parser.error('--repo must be a G10-or-later Resonance checkout')
    if out == root or root in out.parents:
        parser.error('--out must be outside the repository')
    out.mkdir(parents=True, exist_ok=True)
    sys.path[:0] = [str(root / 'roguelike'), str(root / 'tools'),
                   str(root / 'tools/critical_fix_regressions/tests')]
    os.environ.update(SDL_VIDEODRIVER='dummy', SDL_AUDIODRIVER='dummy',
                      PYGAME_HIDE_SUPPORT_PROMPT='1', PYTHONDONTWRITEBYTECODE='1')
    sys.dont_write_bytecode = True

    import numpy
    import pygame
    import tcod
    from engine.data_loader import DataLoader
    from engine.save_manager import _deserialize_world
    from engine.scene_generation import create_surface
    from engine.item_factory import ItemFactory
    from engine.creature_factory import CreatureFactory
    from world.world_map import WorldMap
    from generation.wilderness import make_policy, BIOMES
    from generation.access import reachable, enterable
    from g1_support import fingerprint
    from g10_play import boot, status, render

    log = io.StringIO()
    with contextlib.redirect_stdout(log):
        data = DataLoader(str(root / 'roguelike/data'))
        world = WorldMap(128, 128)
        before_path = root / 'evidence/worldgen-g10/before/world-20261023.json.gz'
        _deserialize_world(json.loads(gzip.decompress(before_path.read_bytes())), world)
        world.surface_schema = 1
        world.surface_policy = make_policy(data.wilderness_profiles, data)
    items = ItemFactory(data)
    creatures = CreatureFactory(data)

    def describe(local_map, anchor):
        cells = reachable(local_map, anchor, data)
        edge = {(x, y) for x in range(80) for y in range(43)
                if (x in (0, 79) or y in (0, 42))
                and enterable(local_map, (x, y), data)}
        exterior = set()
        for xy in sorted(edge):
            if xy not in exterior:
                exterior.update(reachable(local_map, xy, data))
        return dict(anchor=anchor, component_cells=len(cells),
                    boundary_cells=sorted(cells & edge),
                    all_exterior_reachable_cells=len(exterior),
                    stairs=[dict(xy=xy, from_anchor=xy in cells,
                                 from_any_exterior=xy in exterior)
                            for xy in local_map.submap_links],
                    required_access_anchors=getattr(local_map, 'required_access_anchors', None),
                    scene_fingerprint=fingerprint(local_map, []))

    chunk = world.get(44, 8)
    report = dict(seed=world.seed, chunk=[44, 8], biome=chunk.biome_id,
                  head=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip(),
                  runtime=dict(python=platform.python_version(), platform=platform.platform(),
                               pygame=pygame.version.ver, tcod=tcod.__version__, numpy=numpy.__version__),
                  comparison_scope='Current G10 and supported G9 routes over genuine pre-edit G9 coarse metadata; not execution of the historical G9 checkout.',
                  stages=[])
    snapshots = {}
    from generation import region_gen
    original = region_gen._place_submap_entrance

    def entrance(local_map, *values, **kwargs):
        anchor = local_map.required_access_anchors[0]
        report['stages'].append(dict(stage='before-entrance', **describe(local_map, anchor)))
        snapshots['before-entrance'] = copy.deepcopy(local_map), anchor
        original(local_map, *values, **kwargs)
        report['stages'].append(dict(stage='after-entrance', **describe(local_map, anchor)))
        snapshots['after-entrance'] = copy.deepcopy(local_map), anchor

    with contextlib.redirect_stdout(log), patch('generation.region_gen._place_submap_entrance', side_effect=entrance):
        result = create_surface(world, chunk, data, items, creatures, 80, 43)
    report['final'] = describe(result.local_map, result.spawn)
    snapshots['final'] = result.local_map, result.spawn
    old_route = copy.copy(world)
    old_route.surface_schema, old_route.surface_policy = 0, None
    with contextlib.redirect_stdout(log):
        legacy = create_surface(old_route, chunk, data, items, creatures, 80, 43)
    report['legacy'] = describe(legacy.local_map, legacy.spawn)
    report['base_terrain_receipt'] = result.local_map.wilderness_generation
    report['actors'] = [dict(id=getattr(actor, '_creature_id', None), x=actor.x, y=actor.y)
                        for actor in result.actors]
    report['final_metadata_submaps'] = [vars(submap) for submap in result.metadata.submaps]
    report['defect_observed'] = any(not row['from_any_exterior'] for row in report['final']['stairs'])
    (out / 'entrance-isolation.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')

    from engine.display_config import DisplayConfig
    from rendering.tile_registry import TileRegistry
    from entities.actor import Actor
    player = Actor(0, 0, 'player', 'Review anchor')
    preview = SimpleNamespace(data=data, player=player,
                              registry=TileRegistry(str(root / 'roguelike/data/tiles.json')),
                              display=DisplayConfig.from_config())
    with contextlib.redirect_stdout(log):
        for name, (local_map, anchor) in snapshots.items():
            preview.local_map, preview.entities = local_map, [player]
            player.x, player.y = anchor
            render(preview, out / (name + '.png'),
                   'seed 20261023 (44,8) ' + name, revealed=True)

    handlers = dict(seed=20261023, chunk=[44, 8],
                    controls='Disposable ordinary boot; explicit fixture teleport to adjacent scene and positioning for one real boundary movement. Separate explicit positioning onto the inaccessible stair tests real descent/ascent. Native actors retained, AI/survival enabled, invincibility off. Not an ordinary-play route to the cave.')
    with tempfile.TemporaryDirectory(prefix='resonance-g10-access-review-') as tmp, \
            patch('engine.save_manager.SAVE_DIR', Path(tmp)), contextlib.redirect_stdout(log):
        engine = boot(Path(tmp))
        engine.debug = False
        target, actors = engine._prepare_destination(44, 8)
        stair = next(iter(target.submap_links))
        engine.overmap_cursor_x, engine.overmap_cursor_y = 43, 8
        engine._teleport_to_overmap_cursor()
        occupied = {(actor.x, actor.y) for actor in engine.entities[1:]}
        target_occupied = {(actor.x, actor.y) for actor in actors}
        ys = [y for y in range(1, 42)
              if enterable(engine.local_map, (79, y), engine.data)
              and enterable(target, (0, y), engine.data)
              and (79, y) not in occupied and (0, y) not in target_occupied]
        assert ys, 'No matching unoccupied west border cell in this revision'
        engine.player.x, engine.player.y = 79, ys[0]
        engine._update_fov()
        start = status(engine)
        engine._handle_key_local(pygame.K_RIGHT)
        assert (engine.world_x, engine.world_y) == (44, 8)
        cells = reachable(engine.local_map, (engine.player.x, engine.player.y), engine.data)
        handlers['boundary_entry'] = dict(before=start, after=status(engine), stair=stair,
                                          stair_reachable=stair in cells,
                                          reachable_cells=len(cells),
                                          has_boundary=any(x in (0, 79) or y in (0, 42) for x, y in cells))
        render(engine, out / 'boundary-entry-normal-fov.png',
               'CONTROLLED boundary entry at seed 20261023 (44,8)')
        engine.player.x, engine.player.y = stair
        engine._update_fov()
        engine._handle_key(pygame.K_PERIOD, '>')
        handlers['descended'] = status(engine)
        assert engine.current_submap_id == 'submap_44_8_0'
        up = next((x, y) for x in range(80) for y in range(43)
                  if str(engine.local_map.tiles[x, y]['terrain']) == 'stairs_up')
        handlers['ascent_fixture_positioning'] = (engine.player.x, engine.player.y) != up
        if handlers['ascent_fixture_positioning']:
            engine.player.x, engine.player.y = up
            engine._update_fov()
        engine._handle_key(pygame.K_COMMA, '<')
        assert engine.current_submap_id is None
        cells = reachable(engine.local_map, (engine.player.x, engine.player.y), engine.data)
        handlers['ascended'] = dict(status=status(engine), component_cells=len(cells),
                                    has_boundary=any(x in (0, 79) or y in (0, 42) for x, y in cells))
        render(engine, out / 'cave-return-normal-fov.png',
               'CONTROLLED cave return at seed 20261023 (44,8)')
        before = fingerprint(engine.local_map, engine.entities[1:])
        engine._handle_key_local(pygame.K_F5)
        assert engine.save_manager.last_error is None
        engine._handle_key_local(pygame.K_F9)
        cells = reachable(engine.local_map, (engine.player.x, engine.player.y), engine.data)
        handlers['f5_f9'] = dict(scene_same=before == fingerprint(engine.local_map, engine.entities[1:]),
                                 position=[engine.player.x, engine.player.y], component_cells=len(cells),
                                 has_boundary=any(x in (0, 79) or y in (0, 42) for x, y in cells),
                                 error=engine.save_manager.last_error)
    (out / 'entrance-handlers.json').write_text(json.dumps(handlers, indent=2) + '\n', encoding='utf-8')

    if args.sample:
        chooser, rows = random.Random(1025), []
        for biome in BIOMES:
            for has_submap in (False, True):
                candidates = sorted((ch.wx, ch.wy) for ch in world.chunks.values()
                                    if ch.biome_id == biome and bool(ch.submaps) == has_submap)
                for xy in chooser.sample(candidates, min(4, len(candidates))):
                    row = dict(biome=biome, chunk=xy, submaps=len(world.get(*xy).submaps))
                    try:
                        with contextlib.redirect_stdout(log):
                            scene = create_surface(world, world.get(*xy), data, items, creatures, 80, 43)
                        cells = reachable(scene.local_map, scene.spawn, data)
                        row.update(passed=True, reachable=len(cells), actors=len(scene.actors),
                                   roads=len(scene.local_map.road_cells), stairs=len(scene.local_map.submap_links),
                                   all_stairs_reachable=all(p in cells for p in scene.local_map.submap_links),
                                   boundary_reached=any(x in (0, 79) or y in (0, 42) for x, y in cells))
                    except Exception as error:
                        row.update(passed=False, error=repr(error))
                    rows.append(row)
        sampling = dict(head=report['head'], conditions='Random(1025), up to four sorted candidates per eight-biome/submap-presence stratum, seed 20261023. All original current defaults, no hand selection. This is bounded defect discovery, not prevalence.', samples=rows)
        (out / 'sample.json').write_text(json.dumps(sampling, indent=2) + '\n', encoding='utf-8')
    (out / 'probe-output.txt').write_text(log.getvalue(), encoding='utf-8')
    print(json.dumps(dict(defect_observed=report['defect_observed'], output=str(out),
                          evidence='entrance-isolation.json and entrance-handlers.json')))


if __name__ == '__main__':
    main()
