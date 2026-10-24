"""Read-only production probe for an existing valid multi-required-door profile.

The installed house definition is copied in memory. No source/catalog/save file
is changed. Run separately against G3 and G4 to avoid module-cache ambiguity.
"""
from __future__ import annotations
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
parser.add_argument('--plan-output',type=Path)
parser.add_argument('--legacy-plan',type=Path)
parser.add_argument('--world-output',type=Path)
parser.add_argument('--legacy-world',type=Path)
args=parser.parse_args()
sys.path.insert(0,str(args.source.resolve()/'roguelike'))
os.environ.update(SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy',PYGAME_HIDE_SUPPORT_PROMPT='1')
from engine.data_loader import DataLoader
from engine.item_factory import ItemFactory
from engine.creature_factory import CreatureFactory
from engine.scene_generation import create_surface
from generation.structure_contract import compile_structure
from generation.structure_preview import preview
from generation.world_gen import generate_world
from generation.world_plan import address, validate_plan
from generation.context import GENERATION_REVISION
from world.world_map import WorldMap
from engine.save_manager import _serialize_world, _deserialize_world

output={'source':str(args.source.resolve()),'generation_revision':GENERATION_REVISION,
        'scope':'In-memory valid house profile with main south door and required north service door; ordinary production world and one materialized town scene; no persistent saves.'}
with contextlib.redirect_stdout(io.StringIO()):
    data=DataLoader(str(args.source.resolve()/'roguelike/data'))
    original=copy.deepcopy(data.structures['house_small_a'])
    raw=copy.deepcopy(original)
    raw['layers'][0]='####.#####'
    raw['placement']['entrances'].append(dict(id='rear-service',x=4,y=0,normal='N',width=1,role='service',required=True))
    compiled=compile_structure(raw,'ordinary_building',data,category='residential')
    output['compiler_accepted']=True
    checks={'coordinates':'source','entry':dict(x=4,y=7),
            'targets':[dict(x=4,y=0,kind='floor',required=True),dict(x=1,y=6,kind='readable',required=True)]}
    report,_,_=preview(raw,'ordinary_building',data,category='residential',expectations=checks)
    output['direct_preview']={'passed':report['passed'],'access':report['access'],'occupants':report['occupant_diagnostics']}
    data.structures=copy.deepcopy(data.structures)
    data.structures['house_small_a']=raw
    if args.legacy_plan:
        old=json.loads(args.legacy_plan.read_text())
        try:
            validate_plan(old,128,128)
            output['legacy_plan_validation']={'accepted':True,'plan_version':old['version'],'plan_origin':old['generation_revision']}
        except Exception as error:
            output['legacy_plan_validation']={'accepted':False,'plan_version':old['version'],'plan_origin':old['generation_revision'],
                                              'exception':type(error).__name__,'message':str(error)}
    if args.legacy_world:
        saved=json.loads(args.legacy_world.read_text())
        restored=WorldMap(128,128)
        try:
            _deserialize_world(saved,restored)
            output['legacy_world_deserialization']={'accepted':True,'plan_version':restored.plan['version'],'plan_origin':restored.generation_revision}
        except Exception as error:
            output['legacy_world_deserialization']={'accepted':False,'exception':type(error).__name__,'message':str(error),
                                                   'restored_chunk_count':len(restored.chunks)}
    world=WorldMap(128,128);world.seed=20261023
    try:
        generate_world(world,data,random.Random(0))
        output['world_generation']={'accepted':True,'plan_version':world.plan['version'],'placements':len(world.plan['placements'])}
        if args.plan_output:
            args.plan_output.write_text(json.dumps(world.plan,separators=(',',':'))+'\n')
        if args.world_output:
            args.world_output.write_text(json.dumps(_serialize_world(world),separators=(',',':'))+'\n')
        placed=next(p for p in world.plan['placements'] if p['asset']=='house_small_a')
        wx,wy=address(*placed['origin'])[:2]
        result=create_surface(world,world.get(wx,wy),data,ItemFactory(data),CreatureFactory(data),80,43)
        output['materialization']={'accepted':True,'chunk':[wx,wy],'placement':placed['id'],
                                  'approach':placed['approach'],'entrances':placed['entrances'],
                                  'actors':len(result.actors)}
    except Exception as error:
        output['world_generation']={'accepted':False,'exception':type(error).__name__,'message':str(error),
                                    'published_chunk_count':len(world.chunks)}
    output['source_definition_unchanged']=original==DataLoader(str(args.source.resolve()/'roguelike/data')).structures['house_small_a']
args.output.parent.mkdir(parents=True,exist_ok=True)
args.output.write_text(json.dumps(output,indent=2)+'\n')
print(json.dumps(output,indent=2))
