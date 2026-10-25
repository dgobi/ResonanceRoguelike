"""Production realization of one authoritative world-plan slice."""
from __future__ import annotations
import copy
from config import MAP_WIDTH as W, MAP_HEIGHT as H
from generation.context import GenerationContext,GenerationError
from generation.world_plan import slice_plan,intersect,cells,expand
from generation.placement import check_dependencies,transform,entrance_cells,digest,frontage_entrance


def create_planned_surface(world,chunk,data,item_factory,creature_factory,width,height):
    from engine.scene_generation import SceneResult,populate,validate_scene
    from generation.region_gen import generate_region,_place_submap_entrance
    from generation.town_gen import _stamp_building_at
    from generation.access import reachable,arrival_anchor
    from world.world_map import RegionType,TownData
    from generation.structure_preview import check_access,receipt_owned
    if (width,height)!=(W,H): raise GenerationError('planned scene dimensions differ from world plan')
    from generation.settlement_context import effective_context
    settlement,native=effective_context(world,chunk,data)
    section=slice_plan(world.plan,chunk.wx,chunk.wy)
    # Check only pending selected placements. Cached scenes bypass this function.
    definitions={p['id']:check_dependencies(p,world.plan,data) for p in section['placements']}
    for public in section.get('public_spaces',[]):
        surface=data.terrain.get(public['surface'])
        if surface is None or digest({k:surface.get(k,True) for k in ('walkable','transparent')})!=public['surface_dependency']:
            raise GenerationError(public['id']+': changed dependency terrain:'+public['surface'])
    staged=copy.deepcopy(chunk); base=copy.deepcopy(chunk); base.submaps=[]; base.town_data=None
    base.edges={e:[] for e in base.edges}; base.town_id=-1; base.town_role=''
    if base.region_type==RegionType.TOWN: base.region_type=RegionType.PLAINS
    context=GenerationContext(world.seed,chunk.seed,(chunk.wx,chunk.wy,None))
    from generation.wilderness import world_policy, eligible, materialize, provenance
    policy = world_policy(world, data)
    if policy is not None and eligible(chunk):
        m,spawn=materialize(world,chunk,data,context,width,height)
    else:
        m,spawn=generate_region(base,width,height,data.terrain,data=data,context=context,base_only=True)
        if policy is not None:
            m.surface_provenance=provenance(world,chunk)
    x0,y0=chunk.wx*W,chunk.wy*H; rect=[x0,y0,x0+W,y0+H]
    protected=set(); road_cells=set(); water_cells=set(); specs=[]; receipts=[]
    def local(rectangle):
        clipped=intersect(rectangle,rect)
        return {(x-x0,y-y0) for x,y in cells(clipped)} if clipped else set()
    def paint(points,terrain):
        td=data.terrain[terrain]
        for xy in sorted(points):
            m.decor.pop(xy,None)
            m.set_tile(*xy,terrain,td.get('walkable',True),td.get('transparent',True))
    # Reservation order: biome/dressing, water banks/channel, assigned bridges and
    # roads, plots/approaches, contents, protected stair entrances, final validation.
    for water in section['waters']:
        for r in water['rects']:
            bank=local(expand(r,2)); core=local(r)
            paint(bank-water_cells,'river_bank'); paint(core,'river_water')
            protected.update(bank); water_cells.update(core)
    deck=set()
    for crossing in section['crossings']:
        for r in crossing['deck']: deck.update(local(r))
    for road in section['routes']:
        for r in road['rects']: road_cells.update(local(r))
    if (road_cells&water_cells)-deck: raise GenerationError('road crosses water without an assigned bridge')
    paint(road_cells-water_cells,'road_0'); paint(deck,'cobblestone'); protected.update(road_cells)
    m.civic_furnishing=[]
    for public in section.get('public_spaces',[]):
        common=set().union(*(local(r) for r in public['rects']))
        paint(common,public['surface']);protected.update(common)
        if all(rect[0]<=a<rect[2] and rect[1]<=b<rect[3] for a,b in public['furnishing']):
            m.civic_furnishing=[(a-x0,b-y0) for a,b in public['furnishing']]
    for site in section.get('sites',[]):
        common=local(site['approach'])
        for path in section['paths']:
            if path['owner']==site['id']:
                for r in path['rects']:common.update(local(r))
        paint(common-road_cells,'dirt_path');protected.update(common)
    buildings=[]
    for p in section['placements']:
        raw=transform(definitions[p['id']],p['rotation'],p['mirror']); ox,oy=p['origin'][0]-x0,p['origin'][1]-y0
        expected_entrances=[dict(e,x=p['origin'][0]+e['x'],y=p['origin'][1]+e['y']) for e in raw['placement']['entrances']]
        expected_targets=[dict(t,x=p['origin'][0]+t['x'],y=p['origin'][1]+t['y']) for t in raw['placement']['targets']]
        if (p['entrances']!=expected_entrances or p['targets']!=expected_targets or
            p['footprint']!=[p['origin'][0],p['origin'][1],p['origin'][0]+raw['width'],p['origin'][1]+raw['height']]):
            raise GenerationError(f'{p["id"]}: saved placement geometry is incompatible with its supported transformed definition; restore compatible definitions/checkpoint')
        paint(local(p['clearance']),'grass'); paint(local(p['approach'])-road_cells,'dirt_path')
        rows=_stamp_building_at(m,raw,ox,oy,data.terrain,data=data)
        for row in rows: row['record_id']=p['id']+':'+row['record_id']
        specs.extend(rows); protected.update(local(p['clearance'])|local(p['approach']))
        buildings.append(dict(id=p['asset'],placement_id=p['id'],x=ox,y=oy,item_specs=rows))
    actors=populate(data,item_factory,creature_factory,m,specs,map_text=True,receipts=receipts)
    if any(not receipt_owned(r,m) for r in receipts): raise GenerationError('planned content failed initial ownership verification')
    m.road_cells=road_cells; m.protected_cells=protected
    spawn=next(iter(sorted(road_cells)),arrival_anchor(m,spawn,data))
    m.required_access_anchors=[spawn]+sorted(p for p in road_cells if p[0] in (0,W-1) or p[1] in (0,H-1))
    if policy is not None and policy.get('access_revision') == 1 and eligible(chunk):
        from generation.exterior_access import bind_exterior
        spawn=bind_exterior(m,world,chunk,policy,data,spawn,section)
    for submap in staged.submaps: _place_submap_entrance(m,submap,data.terrain,data=data)
    from generation.planned_dressing import dress
    functional,waystone=dress(m,staged,world,data,context,native,spawn)
    actors.extend(populate(data,item_factory,creature_factory,m,functional,map_text=True,receipts=receipts))
    def legal_native(x,y):
        return ((x,y)!=spawn and (x,y) not in m.protected_cells and
                (x,y) not in m.decor and (x,y) not in m.floor_objects and
                data.terrain.get(str(m.tiles[x,y]['terrain']),{}).get('creature_passable',True) and
                not any(a.x==x and a.y==y for a in actors))
    # Native profiles resolve only while preparing an unseen scene.
    if chunk.region_type!=RegionType.TOWN:
        for i,(zone,_) in enumerate(staged.zones):
            actors.extend(creature_factory.spawn_for_zone(zone,m,context.rng('native-population',zone,i),max_count=3,allowed=legal_native))
    if chunk.region_type==RegionType.TOWN:
        from generation.town_gen import _compute_creature_spawns
        spawns=_compute_creature_spawns(m,[(native['district'],(0,0,W,H))],'spent',
                    context.rng('town-population',settlement['id'],native['role']),allowed=legal_native)
        actors.extend(populate(data,item_factory,creature_factory,m,[dict(s,kind='creature') for s in spawns]))
        staged.town_data=TownData(chunk.name or native['name'],'small',[native['district']],'spent',False,waystone,
                                 buildings=[],item_spawns=[],creature_spawns=spawns)
        # World plan is the only owner of buildings/civic blueprint; no duplicate rows.
        civic=settlement['civic']
        if civic:
            owner=next((p for p in section['placements'] if p['id']==civic['placement']),None)
            if owner:
                bells=[xy for xy in local(owner['footprint']) if str(m.tiles[xy]['terrain'])=='bell_dead']
                if len(bells)!=1: raise GenerationError('planned spent bell physical state disagrees with civic metadata')
                staged.town_data.bell_tower_pos=bells[0]
    validate_scene(m,staged.submaps,data)
    validate_access(m,section,data,chunk.wx,chunk.wy)
    if waystone:
        reached=reachable(m,spawn,data)
        if not any((waystone[0]+dx,waystone[1]+dy) in reached for dx,dy in ((1,0),(-1,0),(0,1),(0,-1))):
            raise GenerationError('required waystone has no reachable interaction position')
    if functional:
        goals={'coordinates':'map','entry':dict(x=spawn[0],y=spawn[1]),
               'targets':[dict(x=s['x'],y=s['y'],kind='readable',required=True) for s in functional]}
        if not all(r['passed'] for r in check_access(m,data,goals)):
            raise GenerationError('required civic prayer is not interactable after dressing/population')
    if any(not receipt_owned(r,m) for r in receipts):raise GenerationError('final restored content ownership failed')
    from generation.scene_adapters import adapter
    m.plan_provenance={'mode':'shared-v1','routes':[r['id'] for r in section['routes']],
                       'crossings':[r['id'] for r in section['crossings']],
                       'placements':[p['id'] for p in section['placements']],
                       'plan_revision':world.plan['generation_revision'],'plan_version':world.plan['version'],
                       'plan_identity':digest(world.plan),
                       'dependency_projection':'structure-v1','adapter':adapter('wg9',world.plan['version'])}
    if world.plan['version']>=5:
        m.plan_provenance.update(paths=[p['id'] for p in section['paths']],compounds=[s['id'] for s in section['sites']])
    if world.plan['version'] in (6,7):m.plan_provenance['public_spaces']=[c['id'] for c in section['public_spaces']]
    # These are actual first-creation inputs, not invented historical G3 hashes.
    m.native_input_provenance={f'entities:{a._creature_id}':digest(data.entities[a._creature_id]) for a in actors}
    m.native_input_provenance.update({f'terrain:{tid}':digest(data.terrain[tid]) for tid in ('dead_wood','flint_rock','clay_deposit')})
    m.native_input_provenance['biome:'+chunk.biome_id]=digest(data.biomes.get(chunk.biome_id,{}))
    m.native_input_provenance['terrain-catalog']=digest(data.terrain)
    m.native_input_provenance['decor-catalog']=digest(data.decoratives)
    m.native_input_provenance.update({f'zones:{zone}':digest(data.zones.get(zone,{})) for zone,_ in (native['zones'] if native else chunk.zones)})
    if functional:
        mapped=data.text_item_map.get('waystone_prayer_a','letter')
        m.native_input_provenance['prayer-item:'+mapped]=digest(data.items[mapped])
    m.native_generation_context=native
    m.generation_revision='wg9'; m.generation_complete=True
    return SceneResult(m,actors,spawn,staged,receipts)


def validate_access(m,section,data,wx,wy):
    from generation.access import reachable,enterable
    from generation.structure_preview import check_access
    x0,y0=wx*W,wy*H
    road=set(m.road_cells)
    for public in section.get('public_spaces',[]):
        clear={(x-x0,y-y0) for r in public['rects'] for x,y in cells(r)}-{(a-x0,b-y0) for a,b in public['furnishing']}
        reached=reachable(m,min(road),data) if road else set()
        if not clear<=reached or any(not enterable(m,xy,data) for xy in clear):raise GenerationError(public['id']+': public common circulation blocked after contents/dressing/population')
    for site in section.get('sites',[]):
        reached=reachable(m,(site['attachment']['join'][0]-x0,site['attachment']['join'][1]-y0),data)
        needed=cells(site['approach'])
        for path in section['paths']:
            if path['owner']==site['id']:
                for r in path['rects']:needed|=cells(r)
        if not {(x-x0,y-y0) for x,y in needed}<=reached:raise GenerationError(site['id']+': final gate/common path is blocked')
    for p in section['placements']:
        join=p['join'][0]-x0,p['join'][1]-y0
        frontage_entrance(p)
        internal=p.get('access',{}).get('kind')=='internal'
        assigned=next((r for r in section.get('paths',[]) if r['id']==p['access']['path'] and r['owner']==p['access']['parent']),None) if internal else next((r for r in section['routes'] if r['id']==p['road']),None)
        if assigned is None or not any(r[0]<=p['join'][0]<r[2] and r[1]<=p['join'][1]<r[3] for r in assigned['rects']): raise GenerationError(f'{p["id"]}: assigned frontage missing')
        reached=reachable(m,join,data)
        approach={(x-x0,y-y0) for x,y in cells(p['approach'])}
        if not approach<=reached: raise GenerationError(f'{p["id"]}: final approach is blocked')
        for entrance in p['entrances']:
            if entrance['required'] and not {(x-x0,y-y0) for x,y in entrance_cells(entrance)}<=reached: raise GenerationError(f'{p["id"]}: complete entrance span is inaccessible')
        targets=[]
        for target in p['targets']:
            if not target['required']: continue
            if target['kind']=='floor':
                if (target['x']-x0,target['y']-y0) not in reached: raise GenerationError(f'{p["id"]}: required interior goal inaccessible')
            else: targets.append(dict(target,x=target['x']-x0,y=target['y']-y0))
        access=check_access(m,data,{'coordinates':'map','entry':dict(x=join[0],y=join[1]),'targets':targets})
        if not all(r['passed'] for r in access): raise GenerationError(f'{p["id"]}: required content access failed: {access}')
    # Every declared route cell remains usable after content, also without submaps.
    if any(not enterable(m,p,data) for p in road): raise GenerationError('final content/dressing blocks mandatory road')
    if road:
        reached=reachable(m,min(road),data)
        if not road<=reached: raise GenerationError('mandatory road slice is disconnected after population')
