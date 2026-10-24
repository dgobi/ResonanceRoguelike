"""Bounded authoring validation probe; only in-memory candidate metadata changes."""
import argparse
import contextlib
import copy
import io
import json
import os
from pathlib import Path
import random
import sys

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--source',type=Path,required=True)
parser.add_argument('--output',type=Path,required=True)
args=parser.parse_args()
source=args.source.resolve()
sys.path.insert(0,str(source/'roguelike'))
os.environ.update(SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy',PYGAME_HIDE_SUPPORT_PROMPT='1')
from engine.data_loader import DataLoader
from generation.structure_contract import compile_structure
from generation.structure_preview import preview
from generation.poi_preview import site_preview
from generation.world_gen import generate_world
from world.world_map import WorldMap

log=io.StringIO()
with contextlib.redirect_stdout(log):
    data=DataLoader(str(source/'roguelike/data'))
raw=copy.deepcopy(data.structures['roadside_shrine_a'])
for target in raw['placement']['targets']:
    target['required']=False
result={'source_commit':'4d7a7892e1afffb8d872ed4a8fd442984d14e7d5',
        'scope':'Valid-shape authoring fixture with all target.required flags false; no installed data or campaign changes.',
        'source_modified':False,'personal_saves_used':False,'asset':raw['id'],
        'fixture_targets':raw['placement']['targets']}
with contextlib.redirect_stdout(log):
    entry=compile_structure(raw,'ordinary_building',data,category='wilderness')
    result['compile_accepted']=True
    entrance=raw['placement']['entrances'][0]
    report,_,_=preview(raw,'ordinary_building',data,category='wilderness',expectations={
        'entry':dict(x=entrance['x'],y=entrance['y']),'targets':raw['placement']['targets']})
    result['direct_preview_passed']=report['passed']
    try:
        assigned=site_preview(data,20261023,raw,normal='S')
        result['assigned']={'accepted':True,'passed':assigned['passed']}
    except Exception as error:
        result['assigned']={'accepted':False,'exception':type(error).__name__,'message':str(error)}
    bound=copy.copy(data);bound.structures=dict(data.structures,**{raw['id']:raw})
    bound.poi_profiles=copy.deepcopy(data.poi_profiles)
    bound.poi_profiles.update(minimum=2,maximum=2,assets=[dict(asset=raw['id'],weight=1,cap=2)])
    world=WorldMap(128,128);world.seed=20261023;before=copy.deepcopy(vars(world))
    try:
        generate_world(world,bound,random.Random(20261023))
        result['new_world']={'accepted':True,'sites':len(world.plan['sites'])}
    except Exception as error:
        result['new_world']={'accepted':False,'exception':type(error).__name__,'message':str(error),
                             'world_unchanged':vars(world)==before}
args.output.parent.mkdir(parents=True,exist_ok=True)
args.output.write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
