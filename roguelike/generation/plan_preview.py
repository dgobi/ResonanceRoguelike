"""Author previews that call the ordinary world planner and complete materializer."""
import copy
import html
import json
import random
import time
from generation.context import GenerationError
from generation.world_gen import generate_world
from generation.world_plan import address
from generation.structure_contract import compile_structure
from generation.structure_preview import snapshot,receipt_json
from generation.placement import digest


def planned_preview(data,seed,raw=None,category=None,context='grid',config=None):
    from world.world_map import WorldMap
    from engine.scene_generation import create_surface
    from engine.item_factory import ItemFactory
    from engine.creature_factory import CreatureFactory
    bound=copy.copy(data); effective=copy.deepcopy(config or data.g3_config)
    if raw is not None:
        entry=compile_structure(raw,'ordinary_building',data,category=category)
        if context not in raw.get('placement',{}).get('contexts',[]): raise GenerationError('candidate needs explicit placement eligibility for '+context)
        bound.structures=dict(data.structures,**{raw['id']:entry.definition})
        if raw['id'] not in effective['pools'][context]: effective['pools'][context].append(raw['id'])
    world=WorldMap(128,128);world.seed=seed;t=time.perf_counter()
    generate_world(world,bound,random.Random(seed),planning_settings=effective)
    elapsed=time.perf_counter()-t
    selected=[p for p in world.plan['placements'] if raw is not None and p['asset']==raw['id']]
    if raw is not None and not selected: raise GenerationError('eligible candidate was not selected/fitted; inspect world-plan rejected candidates or choose another explicit seed')
    previews=[]
    for xy in sorted({address(*p['origin'])[:2] for p in selected}):
        result=create_surface(world,world.get(*xy),bound,ItemFactory(bound),CreatureFactory(bound),80,43)
        view=snapshot(result.local_map,result.actors,bound)
        view.update(kind='production planned placement',chunk=list(xy),passed=True,access=[],receipts=[receipt_json(r) for r in result.receipts],placements=[p for p in selected if address(*p['origin'])[:2]==xy])
        previews.append(view)
    return {'passed':True,'kind':'production world-plan diagnostic; not played-game screenshot',
            'seed':seed,'plan':world.plan,'plan_identity':digest(world.plan),'planning_seconds':elapsed,
            'preserved_pools':data.g3_config['pools'],'previews':previews,'materialized_scenes':len(previews)}


def plan_svg(plan):
    scale=.10; width=plan['world_size'][0]*80*scale;height=plan['world_size'][1]*43*scale
    parts=[f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height+32}" width="1024"><rect width="100%" height="100%" fill="#172026"/>']
    for water in plan['waters']:
        for x,y,x1,y1 in water['rects']: parts.append(f'<rect x="{x*scale}" y="{y*scale}" width="{(x1-x)*scale}" height="{(y1-y)*scale}" fill="#458bab"/>')
    for route in plan['routes']:
        points=' '.join(f'{x*scale},{y*scale}' for x,y in route['points'])
        parts.append(f'<polyline points="{points}" fill="none" stroke="#d2bd83" stroke-width="1"><title>{route["id"]}</title></polyline>')
    for s in plan['settlements']:
        x,y,x1,y1=s['bounds']; parts.append(f'<rect x="{x*scale}" y="{y*scale}" width="{(x1-x)*scale}" height="{(y1-y)*scale}" fill="none" stroke="#90d798"/><text x="{x*scale}" y="{y*scale-3}" fill="#90d798" font-size="7">{s["id"]} {s["form"]}</text>')
    for n in plan['nodes']:
        x,y=n['xy'];parts.append(f'<circle cx="{x*scale}" cy="{y*scale}" r="2" fill="#e7a59c"><title>{n["id"]}</title></circle>')
    parts.append(f'<text x="8" y="{height+20}" fill="white" font-size="10">{plan["generation_revision"]} seed {plan["seed"]}: shared plan diagnostic, not a played-game screenshot. Hover routes/nodes for IDs.</text></svg>')
    return '\n'.join(parts)
