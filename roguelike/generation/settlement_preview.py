"""Complete owner previews through the ordinary planner and scene consumer."""
import copy
import html
import random
import time
from generation.context import GenerationError
from generation.placement import digest,entrance_cells


def preview(data,seed,*,layouts=None,layout=None,selection=None,config=None,form='all'):
    from generation.settlement_layout import validate
    from generation.world_gen import generate_world
    from generation.structure_preview import snapshot,receipt_json
    from engine.scene_generation import create_surface
    from engine.item_factory import ItemFactory
    from engine.creature_factory import CreatureFactory
    from world.world_map import WorldMap
    bound=copy.copy(data);bound.settlement_layouts=validate(layouts or data.settlement_layouts,data)
    if layout:
        choices=[r for r in bound.settlement_layouts['grid'] if r['id']==layout]
        if not choices:raise GenerationError('unknown layout '+layout)
        bound.settlement_layouts['grid']=choices
    bound.settlement_profiles=copy.deepcopy(selection or data.settlement_profiles)
    world=WorldMap(128,128);world.seed=seed;metrics={};started=time.perf_counter()
    generate_world(world,bound,random.Random(seed),planning_settings=config,planning_metrics=metrics)
    if world.plan['version'] not in (6,7):raise GenerationError('settlement preview requires planning settings version 3 or 4 / layout version 1')
    elapsed=time.perf_counter()-started;previews=[];ids=[]
    for s in world.plan['settlements']:
        if form not in ('all',s['form']):continue
        ids.append(s['id'])
        for xy in s['members']:
            result=create_surface(world,world.get(*xy),bound,ItemFactory(bound),CreatureFactory(bound),80,43)
            view=snapshot(result.local_map,result.actors,bound)
            view.update(passed=True,access=[],chunk=xy,settlement=s['id'],layout=s['layout']['id'],receipts=[receipt_json(r) for r in result.receipts])
            previews.append(view)
    return dict(passed=True,kind='controlled layout' if layout else 'ordinary selected layouts',seed=seed,plan=world.plan,plan_identity=digest(world.plan),planning_seconds=elapsed,planning_metrics=metrics,previews=previews,settlement_ids=ids,selection=bound.settlement_profiles,
                limitations='Complete populated diagnostic snapshots, revealed visibility; no personal campaign or installation. Controlled choice is not a frequency estimate.')


def diagram(plan,settlement):
    from generation.world_plan import intersect
    x,y,right,bottom=settlement['bounds'];width=right-x;height=bottom-y
    parts=[f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{x-2} {y-12} {width+4} {height+24}" width="1440"><rect x="{x-2}" y="{y-12}" width="{width+4}" height="{height+24}" fill="#17252b"/>',
           f'<text x="{x}" y="{y-7}" font-size="2.6" fill="white">{html.escape(settlement["id"]+" / "+settlement["layout"]["id"])}</text>',
           f'<text x="{x}" y="{y-3}" font-size="1.6" fill="white">Gold streets; blue civic common; outlined private lots; green occupied; purple fit/cap vacancies; gray planned gardens; red full doors</text>']
    def box(r,color,outline=False):
        a,b,c,d=r;parts.append(f'<rect x="{a}" y="{b}" width="{c-a}" height="{d-b}" fill="{"none" if outline else color}" stroke="{color}" stroke-width=".15"/>')
    for b in plan['blocks']:
        if b['owner']==settlement['id'] and b['purpose']=='garden':box(b['bounds'],'#354749')
    for r in plan['routes']:
        for rect in r['rects']:
            hit=intersect(rect,settlement['bounds'])
            if hit:box(hit,'#b99c60')
    for c in plan['public_spaces']:
        if c['owner']==settlement['id']:
            for rect in c['rects']:box(rect,'#4b7e91')
            for a,b in c['furnishing']:box([a,b,a+1,b+1],'#f2e2b8')
    byid={p['id']:p for p in plan['placements']}
    for plot in plan['plots']:
        if plot['owner']!=settlement['id']:continue
        box(plot['buildable'],'#6d8b86' if plot['placement'] else '#9b75aa',True)
        if plot['placement']:
            p=byid[plot['placement']];box(p['footprint'],'#65a77e');box(p['approach'],'#88babc',True)
            for e in p['entrances']:
                for a,b in entrance_cells(e):box([a,b,a+1,b+1],'#f48370')
        a,b=plot['join'];parts.append(f'<text x="{a}" y="{b}" font-size="1.3" fill="white">{plot["normal"]}</text>')
    a,b=settlement['arrival']['position'];parts.append(f'<circle cx="{a}" cy="{b}" r="1" fill="white"/><text x="{a+2}" y="{b-2}" font-size="2" fill="white">Arrival</text></svg>')
    return '\n'.join(parts)
