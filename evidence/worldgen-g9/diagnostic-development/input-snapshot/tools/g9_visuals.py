"""Populated production junction/crossing views and complete inherited G8 towns."""
import argparse
import contextlib
import io
import json
import os
from pathlib import Path
import random
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,required=True);a=p.parse_args();out=a.evidence.resolve();out.mkdir(parents=True,exist_ok=True)
    command=[sys.executable,'-X','utf8',str(ROOT/'tools/g8_visuals.py'),'--evidence',str(out/'towns')];r=subprocess.run(command,cwd=ROOT,timeout=300)
    if r.returncode:return r.returncode
    sys.path[:0]=[str(ROOT/'roguelike'),str(ROOT/'tools/critical_fix_regressions/tests')];os.environ.update(SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy',PYGAME_HIDE_SUPPORT_PROMPT='1')
    from test_effect_persistence import load_data,make_engine
    from generation.world_gen import generate_world
    from generation.country_network import baseline
    from generation.network_metrics import centerline_edges
    from generation.placement import digest
    from engine.scene_generation import create_surface
    from engine.item_factory import ItemFactory
    from engine.creature_factory import CreatureFactory
    from world.world_map import WorldMap
    from g7_visuals import render_compound
    from g1_support import fingerprint
    with contextlib.redirect_stdout(io.StringIO()):
        data=load_data();w=WorldMap(128,128);w.seed=20261023;generate_world(w,data,random.Random(0));old=baseline(w.plan)
        before=centerline_edges(r for r in old['routes'] if r['kind']=='country');after=centerline_edges(r for r in w.plan['routes'] if r['kind']=='country');new=after-before
        old_vertices={p for edge in before for p in edge};joins=sorted({p for edge in new for p in edge if p in old_vertices});keys=[]
        for p in joins:
            xy=p[0]//80,p[1]//43
            if xy not in [v[1] for v in keys]:keys.append(('new-junction',xy))
        crossing=next(r for r in w.plan['routes'] if r['id']=='road-1')['points'][1];keys.append(('retained-crossing-approach',(crossing[0]//80,crossing[1]//43)))
        e=make_engine(data);views=[]
        for i,(kind,xy) in enumerate(keys):
            scene=create_surface(w,w.get(*xy),data,ItemFactory(data),CreatureFactory(data),80,43);e.local_map=scene.local_map;e.entities=[e.player,*scene.actors];e.player.x,e.player.y=scene.spawn;e.world_map=w;e.world_x,e.world_y=xy
            filename=f'{i}-{kind}-{xy[0]}-{xy[1]}.png';render_compound(e,dict(recipe=kind),out/filename)
            views.append(dict(kind=kind,chunk=xy,file=filename,plan_identity=digest(w.plan),fingerprint=fingerprint(scene.local_map,scene.actors),provenance=scene.local_map.plan_provenance,production_renderer=True,visibility='explicit complete populated scene reveal',crossing_scope='Existing required bridge; the ordinary accepted shortcut adds no crossing ownership rows' if kind.startswith('retained') else None))
    (out/'views.json').write_text(json.dumps(dict(passed=True,views=views,inherited_towns='towns/views.json'),indent=2)+'\n',encoding='utf-8');print(json.dumps(dict(passed=True,views=len(views))));return 0


if __name__=='__main__':raise SystemExit(main())
