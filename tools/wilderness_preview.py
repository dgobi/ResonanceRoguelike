"""Headless bounded multi-chunk preview of actual saved-policy surface creation."""
from __future__ import annotations
import argparse
from collections import Counter
import contextlib
import io
import json
import os
from pathlib import Path
import random
import sys
import tempfile
import time
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]


def scene_summary(scene, data):
    from generation.access import reachable
    from generation.placement import digest
    m = scene.local_map
    reached = reachable(m,scene.spawn,data)
    resources = []
    for x in range(m.width):
        for y in range(m.height):
            terrain = str(m.tiles[x,y]['terrain'])
            td = data.terrain.get(terrain,{})
            dd = data.decoratives.get(m.decor.get((x,y)),{})
            if any(td.get(k) or dd.get(k) for k in ('gatherable','harvestable','drinkable')):
                resources.append(dict(x=x,y=y,terrain=terrain,decor=m.decor.get((x,y)),
                    reachable=(x,y) in reached or any((x+dx,y+dy) in reached for dx,dy in ((1,0),(-1,0),(0,1),(0,-1))),
                    drinkable=bool(td.get('drinkable')),harvestable=bool(td.get('harvestable') or dd.get('harvestable')),gatherable=bool(td.get('gatherable'))))
    return dict(terrain=dict(Counter(m.tiles['terrain'].flat)),decor=dict(Counter(m.decor.values())),
        actors=len(scene.actors),native_ids=[getattr(a,'_creature_id','') for a in scene.actors],
        static_reachable_cells=len(reached),road_cells=len(m.road_cells),
        protected_cells=len(m.protected_cells),surface_provenance=getattr(m,'surface_provenance',None),
        wilderness=getattr(m,'wilderness_generation',None),resources=resources,
        reachable_resource_opportunities=sum(r['reachable'] for r in resources),
        complete_terrain_identity=digest(m.tiles['terrain'].tolist()))


def render_area(world, data, x, y, columns, rows, *, image_path=None, label='G10'):
    from engine.scene_generation import create_surface
    from engine.item_factory import ItemFactory
    from engine.creature_factory import CreatureFactory
    from engine.display_config import DisplayConfig
    from rendering.tile_registry import TileRegistry
    from entities.actor import Actor
    from g10_play import render
    import pygame
    scenes=[];pictures={}
    item_factory=ItemFactory(data);creature_factory=CreatureFactory(data)
    player=Actor(0,0,'player','Preview marker')
    e=SimpleNamespace(data=data,player=player,registry=TileRegistry(str(ROOT/'roguelike/data/tiles.json')),
                      display=DisplayConfig.from_config())
    with tempfile.TemporaryDirectory(prefix='resonance-wilderness-render-') as temp:
        for dy in range(rows):
            for dx in range(columns):
                chunk=world.get(x+dx,y+dy)
                if chunk is None:
                    raise ValueError('preview rectangle leaves saved geography')
                start=time.perf_counter()
                r=create_surface(world,chunk,data,item_factory,creature_factory,80,43)
                seconds=time.perf_counter()-start
                scenes.append(dict(chunk=[chunk.wx,chunk.wy],biome=chunk.biome_id,
                                   seconds=seconds,**scene_summary(r,data)))
                if image_path is not None:
                    e.local_map=r.local_map;e.entities=[player,*r.actors];player.x,player.y=r.spawn
                    p=Path(temp)/f'{dx}-{dy}.png'
                    render(e,p,f'{label} seed {world.seed} ({chunk.wx},{chunk.wy}) {chunk.biome_id}',revealed=True)
                    pictures[dx,dy]=pygame.image.load(str(p))
        if pictures:
            pw,ph=pictures[0,0].get_size()
            sheet=pygame.Surface((pw*columns,(ph-42)*rows+42))
            sheet.fill((16,18,22))
            # Natural tile pixels abut without inserted labels at storage seams.
            for (dx,dy),im in pictures.items():
                sheet.blit(im,(dx*pw,dy*(ph-42)+42),pygame.Rect(0,42,pw,ph-42))
            sheet.blit(pictures[0,0],(0,0),pygame.Rect(0,0,pw,42))
            pygame.image.save(sheet,str(image_path))
    return scenes


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--seed',type=int,default=20261023)
    p.add_argument('--chunk',type=int,nargs=2,required=True,metavar=('X','Y'))
    p.add_argument('--size',type=int,nargs=2,default=[2,2],metavar=('COLUMNS','ROWS'))
    p.add_argument('--profile',type=Path,help='Draft complete profile; never installed by preview')
    p.add_argument('--data-root',type=Path,help='Optional disposable data catalog for installation/recovery rehearsal')
    p.add_argument('--output',type=Path,required=True,help='JSON report; image defaults to same stem .png')
    p.add_argument('--image',type=Path,help='Optional explicit PNG target')
    a=p.parse_args(argv)
    if not all(1<=v<=3 for v in a.size):p.error('--size dimensions must be 1..3')
    if a.output.suffix.lower()!='.json':p.error('--output must be .json')
    image=a.image or a.output.with_suffix('.png')
    if image.suffix.lower()!='.png':p.error('--image must be .png')
    sys.path[:0]=[str(ROOT/'roguelike'),str(ROOT/'tools')]
    os.environ.update(SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy',PYGAME_HIDE_SUPPORT_PROMPT='1')
    from authoring_outputs import Destinations
    inputs=[('draft profile',a.profile)]
    boundary=Destinations(inputs,[ROOT/'roguelike',a.data_root or ROOT/'roguelike/data'])
    outputs=[('report',a.output,'diagnostic'),('image',image,'diagnostic')]
    log=io.StringIO()
    try:
        boundary.validate(outputs)
        with contextlib.redirect_stdout(log):
            from engine.data_loader import DataLoader
            from generation.world_gen import generate_world
            from generation.structure_contract import read_document
            from generation.placement import digest
            from world.world_map import WorldMap
            data=DataLoader(str(a.data_root or ROOT/'roguelike/data'))
            if a.profile:data.wilderness_profiles=read_document(a.profile)
            w=WorldMap(128,128);w.seed=a.seed
            started=time.perf_counter();generate_world(w,data,random.Random(a.seed));planning=time.perf_counter()-started
            with tempfile.TemporaryDirectory(prefix='resonance-wilderness-preview-') as temp:
                staged=Path(temp)/'preview.png'
                scenes=render_area(w,data,*a.chunk,*a.size,image_path=staged)
                report=dict(passed=True,seed=a.seed,chunk=a.chunk,size=a.size,
                    profile=str(a.profile) if a.profile else 'installed defaults',policy_identity=w.surface_policy['identity'],
                    policy=w.surface_policy,plan_identity=digest(w.plan),scenes_at_planning_completion=0,
                    materialized_scenes=len(scenes),visited_scenes=sum(c.visited for c in w.chunks.values()),
                    planning_seconds=planning,scenes=scenes,image=str(image),
                    visibility='REVEALED production comparison; not normal-FOV play evidence',
                    access_scope='Complete populated scene validation; reachable static access and resource opportunities. Actors are counted, not treated as permanently impassable.')
                boundary.publish([('report',a.output,'diagnostic',(json.dumps(report,indent=2)+'\n').encode()),
                                  ('image',image,'diagnostic',staged.read_bytes())])
        print(json.dumps(dict(passed=True,report=str(a.output),image=str(image),policy=report['policy_identity'])))
        return 0
    except (ValueError,OSError) as error:
        print(str(error),file=sys.stderr)
        return 1


if __name__=='__main__':raise SystemExit(main())
