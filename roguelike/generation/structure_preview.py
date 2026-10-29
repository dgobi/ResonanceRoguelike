"""Disposable authoring previews using production consumers and factories."""
from __future__ import annotations
import copy
import hashlib
import html
import json
from types import SimpleNamespace
from generation.context import GenerationContext, GENERATION_REVISION, GenerationError, stable_seed
from generation.structure_contract import compile_structure, ELIGIBILITY
from generation.access import reachable, enterable


def preview(raw, route, data, *, category=None, seed=20261023, flip_v=False, path='<draft>', expectations=None, derive_access=False):
    from engine.item_factory import ItemFactory
    from engine.creature_factory import CreatureFactory
    from engine.scene_generation import populate, create_submap
    from generation.town_gen import _stamp_building_at, _stamp_plaza_def, BuildingLoader
    from generation.layout_stamper import stamp_layout_interior
    from world.local_map import LocalMap, make_tile
    from world.world_map import SubMap
    entry=compile_structure(raw,route,data,path=path,category=category)
    if route == 'authored_submap' and flip_v:
        raise GenerationError(f'{path}: authored_submap supports centering/translation only; vertical mirroring is unsupported')
    context=GenerationContext(seed,stable_seed(data.structure_catalog.identity,json.dumps(raw,sort_keys=True)),
                              ('preview',route,raw['id'],flip_v))
    m=LocalMap(80,43,generation_context=context)
    m.tiles[:]=make_tile('grass',True,True)
    ox,oy=40-entry.width//2,21-entry.height//2
    actors=[]; specs=[]; spawn=None; receipts=[]; owned_access=[]; authored_start=None
    factory,creatures=ItemFactory(data),CreatureFactory(data)
    if route=='ordinary_building':
        specs=_stamp_building_at(m,entry.definition,ox,oy,data.terrain,flip_v=flip_v,data=data)
        actors=populate(data,factory,creatures,m,specs,map_text=True)
    elif route=='plaza':
        _stamp_plaza_def(m,BuildingLoader.from_definition(entry.definition,'plaza'),ox,oy,data.terrain)
    elif route=='interior_entrance':
        stair=stamp_layout_interior(m,entry.definition,40,21,data.terrain,rng=context.rng('interior-preview'))
        if str(m.tiles[stair]['terrain']) != 'stairs_down':
            raise GenerationError(f'{path}: entrance has no realized stairs_down')
        m.submap_links[stair]='preview-return'
    else:
        bound=copy.copy(data)
        bound.layouts=dict(data.layouts,**{raw['id']:entry.definition})
        submap=SubMap('preview-submap','laboratory' if raw['id']=='starting_lab' else 'cave','Author preview',context.scene_seed,layout_id=raw['id'])
        world=SimpleNamespace(seed=seed)
        result=create_submap(world,0,0,submap,bound,ItemFactory(bound),CreatureFactory(bound),80,43)
        m,actors,spawn=result.local_map,result.actors,result.spawn
        authored_start=result.authored_start
        if derive_access: owned_access=direct_access(m,data,result.receipts,spawn)
        from engine.save_manager import _serialize_entity
        from engine.save_components import serialize_item
        for receipt in result.receipts:
            row = dict(receipt, source_asset=raw['id'], source_path=str(path))
            row['objects'] = ([dict(decor_id=d, items=[serialize_item(i) for i in items])
                               for d, items in receipt['objects']] if receipt['kind'] == 'container'
                              else [serialize_item(i) for i in receipt['objects']])
            row['actors'] = [_serialize_entity(a) for a in receipt.get('actors', [])]
            row['actual_count'] = (1 if receipt['kind']=='decor' and receipt_owned(receipt,m) else len(row['actors']) if receipt['kind']=='creature' else len(row['objects']))
            row['actor_classes'] = [type(a).__name__ for a in receipt.get('actors', [])]
            receipts.append(row)
    m.generation_revision=GENERATION_REVISION
    report=snapshot(m,actors,data)
    report.update(route=route,asset=raw['id'],seed=seed,catalog_identity=data.structure_catalog.identity,
                  candidate_identity=hashlib.sha256(json.dumps(raw,sort_keys=True).encode()).hexdigest(),
                  kind='direct production consumer preview',flip_v=flip_v,origin=[ox,oy],
                  source_diagnostics=[d.json() for d in entry.diagnostics])
    if route == 'authored_submap':
        report.update(population_receipts=receipts, scene_seed=m.generation_context.scene_seed,
                      authored_start=list(authored_start) if authored_start else None,
                      scene_address=list(m.generation_context.address),
                      inspection='Revealed static authoring geometry and initial occupancy; hostile actors remain hostile. No encounter balance claim.')
    if spawn is not None: report['spawn']=list(spawn)
    report['access']=owned_access if derive_access else check_access(m,data,expectations,origin=(ox,oy),height=entry.height,flip_v=flip_v,spawn=spawn)
    report['passed']=all(row['passed'] for row in report['access']) and not report['occupant_diagnostics']
    return report,m,actors


def direct_access(m,data,receipts,spawn):
    """Bounded static access to these exact population-owned objects, not ID matches."""
    from engine.interaction_cursor import InteractionCursor
    reached=reachable(m,spawn,data)
    results=[dict(target='actual arrival',kind='arrival',xy=list(spawn),passed=tuple(spawn) in reached)]
    visible=m.visible.copy()
    try:
        m.visible[:]=True
        for receipt in receipts:
            kind=receipt['kind']
            if kind not in ('item','container','decor'): continue
            xy=tuple(receipt['xy']); approaches=[]; owned=receipt_owned(receipt,m)
            if kind in ('container','decor'):
                for point in sorted(reached):
                    if max(abs(point[0]-xy[0]),abs(point[1]-xy[1]))>1: continue
                    proxy=SimpleNamespace(local_map=m,player=SimpleNamespace(x=point[0],y=point[1]))
                    if InteractionCursor.can_reach(proxy,*xy): approaches.append(list(point))
                passed=owned and bool(approaches)
            else:
                passed=owned and xy in reached
                if receipt.get('text_id'):
                    passed=passed and all(getattr(i,'on_use',None)=='read' and getattr(i,'text_id',None)==receipt['text_id'] for i in receipt['objects'])
            results.append(dict(target=receipt['record_id'],kind=kind,source_xy=receipt['source_xy'],xy=list(xy),receipt_owned=owned,
                                relocated=receipt.get('relocated',False),passed=passed,approaches=approaches))
        stairs=[(x,y) for x in range(m.width) for y in range(m.height) if str(m.tiles[x,y]['terrain'])=='stairs_up']
        results.append(dict(target='usable return stair',kind='stairs_up',passed=any(xy in reached for xy in stairs),stairs=[list(xy) for xy in stairs]))
    finally: m.visible[:]=visible
    return results


def snapshot(m,actors,data):
    from engine.save_components import serialize_item
    floor=[{'x':x,'y':y,'items':[serialize_item(i) for i in items]} for (x,y),items in sorted(m.floor_objects.items())]
    containers=[{'x':x,'y':y,'decor_id':state['decor_id'],'state':state['state'],
                 'items':[serialize_item(i) for i in state['items']]} for (x,y),state in sorted(m.container_state.items())]
    diagnostics=[]; occupied={}
    for actor in actors:
        xy=actor.x,actor.y
        if not enterable(m,xy,data): diagnostics.append({'code':'BLOCKED_ACTOR','xy':list(xy),'id':actor._creature_id})
        if xy in occupied: diagnostics.append({'code':'OVERLAPPING_ACTORS','xy':list(xy),'ids':[occupied[xy],actor._creature_id]})
        occupied[xy]=actor._creature_id
    for (x,y),items in m.floor_objects.items():
        if not enterable(m,(x,y),data): diagnostics.append({'code':'BLOCKED_ITEM','xy':[x,y],'count':len(items)})
    return {'terrain':[[str(m.tiles[x,y]['terrain']) for x in range(m.width)] for y in range(m.height)],
            'decor':[{'x':x,'y':y,'id':d,'blocking':bool(data.decoratives.get(d,{}).get('blocks_movement'))} for (x,y),d in sorted(m.decor.items())],
            'items':floor,'containers':containers,'actors':[{'x':a.x,'y':a.y,'id':a._creature_id} for a in actors],
            'stairs':[{'x':x,'y':y,'terrain':str(m.tiles[x,y]['terrain']),'link':m.submap_links.get((x,y))}
                      for x in range(m.width) for y in range(m.height) if str(m.tiles[x,y]['terrain']) in ('stairs_up','stairs_down')],
            'occupant_diagnostics':diagnostics,'generation_revision':GENERATION_REVISION}


def check_access(m,data,expectations,*,origin=(0,0),height=0,flip_v=False,spawn=None):
    """Sidecar source coordinates may include exterior negative offsets.

    Movement allows diagonals through corners. Physical interaction additionally
    uses the engine's visibility, one-cell range and sealed-corner rule.
    """
    if expectations is None: return []
    from engine.interaction_cursor import InteractionCursor
    if not isinstance(expectations,dict) or not isinstance(expectations.get('targets'),list):
        raise GenerationError('access sidecar: expected entry and targets array')
    if expectations.get('coordinates','source') not in ('source','map'):
        raise GenerationError('access sidecar: coordinates must be source or map')
    def point(row):
        if not isinstance(row,dict) or type(row.get('x')) is not int or type(row.get('y')) is not int:
            raise GenerationError('access sidecar: coordinates must be integers')
        x,y=row['x'],row['y']
        if expectations.get('coordinates','source')=='map': return x,y
        return origin[0]+x,origin[1]+(height-1-y if flip_v else y)
    entry=point(expectations['entry']) if 'entry' in expectations else spawn
    if entry is None:
        return [{'target':'entry','passed':False,'diagnostic':'Scene context required: this route has no generated arrival; supply an explicit validation entry.'}]
    reached=reachable(m,entry,data)
    results=[{'target':'entry','xy':list(entry),'passed':entry in reached}]
    # All visibility is explicitly granted only for this static reach diagnostic;
    # actual action tests also update FOV and use the real engine handlers.
    visible=m.visible.copy()
    try:
        m.visible[:]=True
        for n,target in enumerate(expectations['targets']):
            xy=point(target); kind=target.get('kind'); ok=False; approaches=[]
            if kind in ('item','readable'):
                objects=m.floor_objects.get(xy,[])
                ok=xy in reached and bool(objects) and (kind!='readable' or any(getattr(i,'text_id','') for i in objects))
            elif kind=='container':
                for p in sorted(reached):
                    if max(abs(p[0]-xy[0]),abs(p[1]-xy[1]))>1: continue
                    proxy=SimpleNamespace(local_map=m,player=SimpleNamespace(x=p[0],y=p[1]))
                    if InteractionCursor.can_reach(proxy,*xy): approaches.append(list(p))
                ok=xy in m.container_state and bool(approaches)
            elif kind=='floor': ok=xy in reached
            elif kind in ('stairs_up','stairs_down','arrival'):
                ok=xy in reached and (xy==spawn if kind=='arrival' else str(m.tiles[xy]['terrain'])==kind)
            else: raise GenerationError(f'access targets[{n}]: unsupported kind {kind!r}')
            results.append({'target':target.get('name',f'{kind}[{n}]'),'kind':kind,'xy':list(xy),'passed':ok,'approaches':approaches})
    finally: m.visible[:]=visible
    return results


def receipt_owned(receipt,m):
    """Transient identities prove initial ownership, never search for a same-ID substitute."""
    kind=receipt['kind']
    if kind in ('empty','body','stele'): return True
    xy=tuple(receipt['xy']); values=receipt['objects']
    if kind=='decor':
        return m.decor.get(xy)==receipt['decor_id'] and xy not in m.container_state
    if kind=='container':
        state=m.container_state.get(xy)
        return bool(state is not None and len(values)==1 and state['decor_id']==values[0][0]
                    and len(state['items'])==len(values[0][1])
                    and all(a is b for a,b in zip(state['items'],values[0][1])))
    owned=m.floor_objects.get(xy,[])
    return bool(values) and all(any(o is value for o in owned) for value in values)


def receipt_json(receipt):
    from engine.save_components import serialize_item
    result={k:v for k,v in receipt.items() if k!='objects'}
    result['objects']=([{'decor_id':d,'items':[serialize_item(i) for i in items]} for d,items in receipt['objects']]
                       if receipt['kind']=='container' else [serialize_item(i) for i in receipt['objects']])
    return result


def registration(raw,data,category,*,seed=20261023,max_seeds=32):
    """Positive existing-pool fixture; retain every unrelated installed candidate."""
    from world.world_map import WorldMap,Chunk,RegionType
    from engine.item_factory import ItemFactory
    from engine.creature_factory import CreatureFactory
    from engine.scene_generation import create_surface
    entry=compile_structure(raw,'ordinary_building',data,category=category)
    bound=copy.copy(data)
    bound.buildings={cat:list(rows) for cat,rows in data.buildings.items()}
    existing=[b for rows in bound.buildings.values() for b in rows if b['id']==raw['id']]
    if existing and existing[0]!=entry.definition: raise GenerationError('registration: ID already installed with different content')
    if not existing: bound.buildings.setdefault(category,[]).append(entry.definition)
    world=WorldMap(1,1); world.seed=seed; world.start_wx=world.start_wy=-1
    role=ELIGIBILITY[category][0]
    for offset in range(max_seeds):
        chunk=Chunk(0,0,RegionType.TOWN,seed+offset,town_id=1,town_role=role)
        result=create_surface(world,chunk,bound,ItemFactory(bound),CreatureFactory(bound),80,43)
        matches=[b for b in result.metadata.town_data.buildings if b['id']==raw['id']]
        if matches:
            realized=[]
            for b in matches:
                objects=[]
                for spec in b['item_specs']:
                    xy=spec['x'],spec['y']; kind=spec['kind']
                    receipt=next((r for r in result.receipts if r['record_id']==spec['record_id']),None)
                    if receipt is None or not receipt_owned(receipt,result.local_map):
                        raise GenerationError(f'registration: missing realized {kind} for {spec["record_id"]} at {xy}')
                    objects.append(receipt_json(receipt))
                realized.append({'x':b['x'],'y':b['y'],'objects':objects})
            return {'passed':True,'kind':'controlled existing-pool selection; not world frequency','category':category,
                    'eligible_roles':ELIGIBILITY[category],'role':role,'seed':seed+offset,'world_seed':seed,
                    'candidate_count':sum(map(len,bound.buildings.values())),'preserved_installed_candidates':sum(map(len,data.buildings.values())),
                    'placements':realized,'realized_scene':snapshot(result.local_map,result.actors,bound)}
    raise GenerationError(f'registration: no fitting placement in {max_seeds} bounded seeds; inspect dimensions/category')


def render_svg(report):
    """Diagnostic glyphs, explicitly not a game-renderer screenshot."""
    rows=report['terrain']; size=12; w=len(rows[0]); h=len(rows)
    parts=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{w*size}" height="{h*size+60}" viewBox="0 0 {w*size} {h*size+60}">',
           '<rect width="100%" height="100%" fill="#11151b"/>',
           '<g font-family="monospace" font-size="10" text-anchor="middle">']
    for y,row in enumerate(rows):
        for x,terrain in enumerate(row):
            solid=terrain in ('wall','rock','old_wall','tree')
            color='#48535e' if solid else '#263a34'
            if 'water' in terrain: color='#244c70'
            if terrain=='door_closed': color='#866546'
            glyph='>' if terrain=='stairs_down' else '<' if terrain=='stairs_up' else '+' if terrain=='door_closed' else '#' if solid else '·'
            parts.append(f'<rect x="{x*size}" y="{y*size}" width="12" height="12" fill="{color}"><title>{html.escape(terrain)}</title></rect><text x="{x*size+6}" y="{y*size+10}" fill="#a9b7b4">{glyph.replace("<","&lt;")}</text>')
    for layer,glyph,color in [('decor','D','#c6a2e7'),('items','!','#f3e39c'),('containers','C','#ffba75'),('actors','A','#ed8996')]:
        for obj in report[layer]:
            parts.append(f'<text x="{obj["x"]*size+6}" y="{obj["y"]*size+10}" fill="{color}"><title>{html.escape(json.dumps(obj))}</title>{glyph}</text>')
    if 'spawn' in report:
        x,y=report['spawn']
        parts.append(f'<text x="{x*size+6}" y="{y*size+10}" fill="#ffffff"><title>Generated arrival</title>@</text>')
    for target in report.get('access',[]):
        if 'xy' not in target: continue
        x,y=target['xy']; color='#81dda1' if target['passed'] else '#ff5b57'
        parts.append(f'<rect x="{x*size}" y="{y*size}" width="12" height="12" fill="none" stroke="{color}" stroke-width="2"><title>{html.escape(json.dumps(target))}</title></rect>')
    from generation.placement import entrance_cells,NORMALS
    cx,cy=report.get('chunk',[0,0]);x0,y0=cx*80,cy*43
    for p in report.get('placements',[]):
        for key,color in [('clearance','#80a0c0'),('approach','#71e1d6'),('footprint','#e6bc64')]:
            x,y,x1,y1=p[key]
            assigned=p['access']['path'] if p.get('access',{}).get('kind')=='internal' else p['road']
            parts.append(f'<rect x="{(x-x0)*size}" y="{(y-y0)*size}" width="{(x1-x)*size}" height="{(y1-y)*size}" fill="none" stroke="{color}"><title>{html.escape(p["id"]+" "+key+" assigned "+assigned)}</title></rect>')
        for e in p['entrances']:
            for x,y in entrance_cells(e):
                parts.append(f'<text x="{(x-x0)*size+6}" y="{(y-y0)*size+10}" fill="#ffffff"><title>Entrance {e["id"]}, outward {e["normal"]}</title>{e["normal"]}</text>')
    parts.append('</g><g font-family="monospace" font-size="12" fill="#e4ebf3">')
    parts.append(f'<text x="8" y="{h*size+19}">Diagnostic preview (not game renderer): # solid, + door, &lt;/&gt; stairs, D decor, ! item, C container, A actor.</text>')
    failures=[r['target'] for r in report.get('access',[]) if not r['passed']]
    status='Failed targets: '+', '.join(failures) if failures else ('Targets passed (green); @ only for generated arrival.' if report.get('access') else 'No access targets supplied; @ only for generated arrival.')
    parts.append(f'<text x="8" y="{h*size+39}">{html.escape(status)} Hover for IDs/contents. Full diagnostics in JSON.</text></g></svg>')
    return '\n'.join(parts)
