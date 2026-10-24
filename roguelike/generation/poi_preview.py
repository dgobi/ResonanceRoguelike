"""Directly assigned site previews share production selection and materialization."""
import copy
import random
import time
from generation.context import GenerationError
from generation.placement import digest
from generation.poi_selection import candidates,populate,resolve,single_policy
from generation.world_plan import Reservations,member_chunks,validate_plan,publish_plan


def site_preview(data,seed,raw=None,category='wilderness',policy=None,normal=None):
    from generation.structure_contract import compile_structure
    from generation.world_gen import generate_world
    from generation.structure_preview import snapshot,receipt_json
    from engine.scene_generation import create_surface
    from engine.item_factory import ItemFactory
    from engine.creature_factory import CreatureFactory
    from world.world_map import WorldMap
    bound=copy.copy(data);bound.poi_profiles=copy.deepcopy(policy or data.poi_profiles)
    if normal is not None:bound.poi_profiles=single_policy(bound.poi_profiles)
    if raw is not None:
        entry=compile_structure(raw,'ordinary_building',data,category=category)
        bound.structures=dict(data.structures,**{raw['id']:entry.definition})
        field='choices' if bound.poi_profiles['version']==2 else 'assets'
        if not any(r.get('asset')==raw['id'] for r in bound.poi_profiles[field]):
            bound.poi_profiles[field].append(dict(asset=raw['id'],weight=1,cap=2,**({'kind':'single'} if field=='choices' else {})))
    if normal is not None:
        if raw is None or normal not in 'NESW':raise GenerationError('assigned site preview requires a draft and frontage normal')
        bound.poi_profiles.update(minimum=1,maximum=1,assets=[dict(asset=raw['id'],weight=1,cap=2)])
    desired_policy=copy.deepcopy(bound.poi_profiles);resolve(bound)
    if normal is not None:bound.poi_profiles.update(minimum=0,maximum=0)
    world=WorldMap(128,128);world.seed=seed;started=time.perf_counter()
    generate_world(world,bound,random.Random(seed))
    if normal is not None:
        bound.poi_profiles=desired_policy;plan=copy.deepcopy(world.plan);authority=Reservations()
        authority.rows=copy.deepcopy(plan['reservations'])
        for i,r in enumerate(authority.rows):
            for key in member_chunks(r['rect']):authority.index.setdefault(tuple(key),[]).append(i)
        rows,_=candidates(plan,resolve(bound))
        populate(plan,authority,world,bound,candidate_rows=[r for r in rows if r['normal']==normal])
        plan['reservations']=authority.rows;validate_plan(plan,128,128);publish_plan(world,plan)
    selected=[s for s in world.plan['sites'] if s['kind']!='compound' and (raw is None or next(p for p in world.plan['placements'] if p['id']==s['placement'])['asset']==raw['id'])]
    if raw is not None and not selected:raise GenerationError('eligible site candidate was not selected/fitted; eligibility is not a selection guarantee; inspect --world-plan with --poi-config')
    previews=[]
    for site in selected:
        xy=site['chunk'];result=create_surface(world,world.get(*xy),bound,ItemFactory(bound),CreatureFactory(bound),80,43)
        view=snapshot(result.local_map,result.actors,bound)
        view.update(kind='complete production assigned site',chunk=xy,site=site,passed=True,access=[],
                    receipts=[receipt_json(r) for r in result.receipts],placements=[p for p in world.plan['placements'] if p['id']==site['placement']])
        previews.append(view)
    return dict(passed=True,kind='controlled one-site/one-asset/normal fixture' if normal else 'production additional-site pool preview',
                seed=seed,plan=world.plan,plan_identity=digest(world.plan),previews=previews,materialized_scenes=len(previews),
                seconds=time.perf_counter()-started,assigned_normal=normal)
