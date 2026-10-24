"""Drafts use ordinary country candidates, shared fitting and final population."""
import copy
import random
import time
from generation.context import GenerationError


def preview(data,seed,recipe,*,children=(),policy=None,normal=None,rotation=None):
    from generation.structure_contract import compile_structure
    from generation.structure_preview import snapshot,receipt_json
    from generation.world_gen import generate_world
    from generation.world_plan import Reservations,member_chunks,validate_plan,publish_plan
    from generation.poi_selection import populate,candidates,resolve
    from generation.placement import digest
    from engine.scene_generation import create_surface
    from engine.item_factory import ItemFactory
    from engine.creature_factory import CreatureFactory
    from world.world_map import WorldMap
    bound=copy.copy(data);bound.structures=dict(data.structures);bound.compounds=copy.deepcopy(data.compounds)
    for raw in children:
        entry=compile_structure(raw,'ordinary_building',bound,category=raw.get('category'))
        bound.structures[raw['id']]=entry.definition
    recipe=copy.deepcopy(recipe)
    if rotation is not None:
        if normal is None or rotation not in recipe['rotations']:raise GenerationError('compound assigned rotation must be permitted and include --assigned-compound')
        recipe['rotations']=[rotation]
    bound.compounds[recipe['id']]=recipe;bound.poi_profiles=copy.deepcopy(policy or data.poi_profiles)
    if bound.poi_profiles.get('version')!=2:raise GenerationError('compound preview requires a complete version-two parent policy')
    if not any(r.get('recipe')==recipe['id'] for r in bound.poi_profiles['choices']):bound.poi_profiles['choices'].append(dict(kind='compound',recipe=recipe['id'],weight=1,cap=2))
    if normal:
        bound.poi_profiles.update(minimum=1,maximum=1,kind_minimum=dict(single=0,compound=1),choices=[dict(kind='compound',recipe=recipe['id'],weight=1,cap=2)])
    resolve(bound);desired=copy.deepcopy(bound.poi_profiles)
    if normal:bound.poi_profiles.update(minimum=0,maximum=0,kind_minimum=dict(single=0,compound=0))
    config=copy.deepcopy(bound.g3_config)
    delayed_network=normal and config['version']==4
    if delayed_network:config['version']=3;config.pop('country_network_version')
    world=WorldMap(128,128);world.seed=seed;started=time.perf_counter();generate_world(world,bound,random.Random(seed),planning_settings=config)
    if normal:
        bound.poi_profiles=desired;plan=copy.deepcopy(world.plan);authority=Reservations();authority.rows=copy.deepcopy(plan['reservations'])
        for i,r in enumerate(authority.rows):
            for xy in member_chunks(r['rect']):authority.index.setdefault(tuple(xy),[]).append(i)
        rows,_=candidates(plan,resolve(bound));populate(plan,authority,world,bound,candidate_rows=[r for r in rows if r['normal']==normal])
        plan['reservations']=authority.rows;validate_plan(plan,128,128)
        if delayed_network:
            from generation.country_network import augment
            plan=augment(world,plan,bound)
        publish_plan(world,plan)
    selected=[s for s in world.plan['sites'] if s['kind']=='compound' and s['recipe']==recipe['id']];previews=[]
    for site in selected:
        xy=site['chunk'];result=create_surface(world,world.get(*xy),bound,ItemFactory(bound),CreatureFactory(bound),80,43)
        view=snapshot(result.local_map,result.actors,bound)
        view.update(kind='complete populated compound diagnostic',chunk=xy,site=site,passed=True,access=[],receipts=[receipt_json(r) for r in result.receipts],placements=[p for p in world.plan['placements'] if p.get('parent')==site['id']])
        previews.append(view)
    return dict(passed=True,status='placed' if selected else 'valid but unselected',kind='assigned compound fixture' if normal else 'ordinary compound selection',seed=seed,
                plan=world.plan,plan_identity=digest(world.plan),previews=previews,materialized_scenes=len(previews),assigned_normal=normal,seconds=time.perf_counter()-started)
