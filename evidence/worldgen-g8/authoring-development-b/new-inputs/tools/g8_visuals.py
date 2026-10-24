"""Complete populated production views of both controlled grids and roadside."""
import argparse
import copy
import contextlib
import io
import json
import os
from pathlib import Path
import random
import sys

ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,required=True);a=p.parse_args();out=a.evidence.resolve();out.mkdir(parents=True,exist_ok=True)
    sys.path[:0]=[str(ROOT/'roguelike'),str(ROOT/'tools/critical_fix_regressions/tests')];os.environ.update(SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy',PYGAME_HIDE_SUPPORT_PROMPT='1')
    import pygame
    from test_effect_persistence import load_data,make_engine
    from generation.world_gen import generate_world
    from generation.settlement_preview import diagram
    from generation.placement import digest
    from engine.scene_generation import create_surface
    from engine.item_factory import ItemFactory
    from engine.creature_factory import CreatureFactory
    from world.world_map import WorldMap
    from g7_visuals import render_compound
    records=[];data=load_data()
    with contextlib.redirect_stdout(io.StringIO()):
        for name in ('cross-market','linked-courts','roadside'):
            d=copy.copy(data);d.settlement_layouts=copy.deepcopy(data.settlement_layouts);d.settlement_profiles=copy.deepcopy(data.settlement_profiles)
            if name!='roadside':
                d.settlement_layouts['grid']=[r for r in d.settlement_layouts['grid'] if r['id']==name]
                d.settlement_profiles['profiles']['grid']['schedule']=['residential','commercial']
            w=WorldMap(128,128);w.seed=20261023;generate_world(w,d,random.Random(20261023));s=next(s for s in w.plan['settlements'] if s['form']==('roadside' if name=='roadside' else 'grid'));e=make_engine(d);members=[]
            for xy in s['members']:
                result=create_surface(w,w.get(*xy),d,ItemFactory(d),CreatureFactory(d),80,43);e.local_map=result.local_map;e.entities=[e.player,*result.actors];e.player.x,e.player.y=result.spawn;e.world_map=w;e.world_x,e.world_y=xy
                path=out/f'{name}-{xy[0]}-{xy[1]}.png';render_compound(e,dict(recipe=name),path);members.append((xy,path))
            images=[pygame.image.load(str(path)) for xy,path in members];width,height=images[0].get_size();canvas=pygame.Surface((2*width,(2 if name!='roadside' else 1)*height));x0=min(xy[0] for xy,path in members);y0=min(xy[1] for xy,path in members)
            for (xy,path),img in zip(members,images):canvas.blit(img,((xy[0]-x0)*width,(xy[1]-y0)*height))
            pygame.image.save(canvas,str(out/(name+'-complete.png')));(out/(name+'-plan.svg')).write_text(diagram(w.plan,s),encoding='utf-8')
            records.append(dict(layout=name,seed=w.seed,plan_identity=digest(w.plan),members=s['members'],normals=sorted({p['normal'] for p in w.plan['plots'] if p['owner']==s['id'] and p['placement']}),production_renderer=True,visibility='controlled reveal of entire populated scene',selection_control='grid optional schedule residential/commercial, installed assets; roadside ordinary policy',plan=s))
    (out/'views.json').write_text(json.dumps(dict(passed=True,views=records),indent=2)+'\n',encoding='utf-8')


if __name__=='__main__':main()
