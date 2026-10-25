"""Serial current-legacy/new-policy real-handler boundary cost pairs.

Uses genuine pre-edit coarse metadata. This is controlled timing evidence, not
another ordinary expedition and not a claim that these timings were pre-edit.
"""
import argparse
import contextlib
import gzip
import io
import json
import os
from pathlib import Path
import random
import sys
import tempfile
import time
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'roguelike'),str(ROOT/'tools'),str(ROOT/'tools/critical_fix_regressions/tests')]
os.environ.update(SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy',PYGAME_HIDE_SUPPORT_PROMPT='1')


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    from verify_g10 import inputs
    from test_effect_persistence import load_data,make_engine
    from world.world_map import WorldMap
    from engine.save_manager import _deserialize_world
    from engine.scene_generation import create_surface,publish_metadata
    from engine.item_factory import ItemFactory
    from engine.creature_factory import CreatureFactory
    from generation.wilderness import make_policy
    from generation.access import enterable
    from generation.placement import digest
    from g1_support import fingerprint
    import pygame
    source=inputs();data=load_data()
    original=json.loads(gzip.decompress((ROOT/'evidence/worldgen-g10/before/world-20261023.json.gz').read_bytes()))
    def world(mode):
        w=WorldMap(128,128);_deserialize_world(original,w)
        if mode=='new':w.surface_schema=1;w.surface_policy=make_policy(data.wilderness_profiles,data)
        return w
    origin=(73,99);modes=('legacy','new');references={};items=ItemFactory(data);creatures=CreatureFactory(data)
    for mode in modes:
        w=world(mode)
        for xy in (origin,(74,99),(73,100)):
            references[mode,xy]=create_surface(w,w.get(*xy),data,items,creatures,80,43)
    candidates={}
    for axis,destination,points in (
        ('x',(74,99),[((79,y),(0,y)) for y in range(43)]),
        ('y',(73,100),[((x,42),(x,0)) for x in range(80)])):
        valid=[]
        for start,end in points:
            if all(enterable(references[mode,origin].local_map,start,data) and
                   enterable(references[mode,destination].local_map,end,data) and
                   start not in {(a.x,a.y) for a in references[mode,origin].actors} and
                   end not in {(a.x,a.y) for a in references[mode,destination].actors}
                   for mode in modes):valid.append((start,end))
        assert valid,axis
        candidates[axis]=min(valid,key=lambda pair:(abs(pair[0][0]-40)+abs(pair[0][1]-21),pair))
    rows=[]
    for axis,key,destination in (('x',pygame.K_RIGHT,(74,99)),('y',pygame.K_DOWN,(73,100))):
        start,end=candidates[axis]
        for repetition in range(2):
            for mode in modes:
                with tempfile.TemporaryDirectory(prefix='resonance-g10-boundary-') as tmp,patch('engine.save_manager.SAVE_DIR',Path(tmp)):
                    e=make_engine(data);e.world_map=world(mode);e.world_x,e.world_y=origin
                    e.rng=random.Random(e.world_map.seed);e.debug=False;e.player_invincible=True
                    ch=e.world_map.get(*origin)
                    r=create_surface(e.world_map,ch,data,e.item_factory,e.creature_factory,80,43)
                    e.local_map=r.local_map;e.entities=[e.player,*r.actors];e.player.x,e.player.y=start
                    publish_metadata(ch,r.metadata);ch.visited=True;ch.generation_revision=r.local_map.generation_revision
                    e._update_fov()
                    with patch.object(type(e),'_advance_turn',lambda engine:engine.world_time.advance()):
                        began=time.perf_counter();e._handle_key_local(key);seconds=time.perf_counter()-began
                    assert (e.world_x,e.world_y)==destination and (e.player.x,e.player.y)==end
                    generated=sum(bool(getattr(c,'generation_revision',None)) for c in e.world_map.chunks.values())
                    assert generated==2
                    rows.append(dict(axis=axis,repetition=repetition,mode=mode,start=start,end=end,origin=origin,destination=destination,
                        seconds=seconds,destination_fingerprint=fingerprint(e.local_map,e.entities[1:]),
                        road_departure=start in r.local_map.road_cells,native_actors=len(e.entities)-1,materialized_scene_owners=generated,
                        policy_identity=getattr(e.world_map,'surface_policy',None) and e.world_map.surface_policy['identity'],
                        wilderness=getattr(e.local_map,'wilderness_generation',None),plan_identity=digest(e.world_map.plan)))
    assert inputs()==source
    result=dict(passed=True,source=source,source_stable=True,rows=rows,
        scope='Two serial repetitions per mode and axis on identical genuine pre-edit coarse metadata. Legacy route is current supported G9 code; its eight representative scene fingerprints were separately matched to the genuine pre-edit sample. These boundary times are current legacy/new-policy pairs, not mislabeled pre-edit execution.',
        controls='Fixture positioning on the same already legal source boundary cell; real movement/boundary/destination publication handlers. Destination scenes are uncached at measurement. AI/survival paused by a turn-clock-only override, invincibility on, ordinary native scene population retained. No terrain rewrites or neighbor materialization by the sampler. Separate ordinary live evidence retains normal rules.')
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')


if __name__=='__main__':main()
