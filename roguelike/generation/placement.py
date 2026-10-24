"""Version-one placement geometry. Coordinates are integer tiles, rectangles half-open.

Legacy metadata is preserved, never implicitly activated by this module.
"""
from __future__ import annotations
import copy
import hashlib
import json
from generation.context import GenerationError

NORMALS={'N':(0,-1),'E':(1,0),'S':(0,1),'W':(-1,0)}
CONTEXTS={'grid','roadside','landmark','civic'}


def entrance_cells(e):
    dx,dy=(1,0) if e['normal'] in ('N','S') else (0,1)
    return [(e['x']+dx*i,e['y']+dy*i) for i in range(e['width'])]


def validate_profile(raw,w,h):
    p=raw.get('placement')
    if p is None: return
    def fail(message): raise GenerationError('placement: '+message)
    if not isinstance(p,dict) or type(p.get('version')) is not int or p.get('version')!=1: fail('version must be 1')
    allowed={'version','contexts','weight','rotations','mirror_x','buffer','approach','entrances','targets','road_relation'}
    if set(p)-allowed: fail('unknown fields: '+', '.join(sorted(set(p)-allowed)))
    if not isinstance(p.get('contexts'),list) or not p['contexts'] or any(c not in CONTEXTS for c in p['contexts']): fail('contexts must name grid, roadside, civic or landmark')
    if type(p.get('weight')) not in (int,float) or not 0<p['weight']<=1000: fail('weight must be positive and at most 1000')
    if not isinstance(p.get('rotations'),list) or not p['rotations'] or any(type(r) is not int or r not in (0,90,180,270) for r in p['rotations']): fail('rotations must contain explicit quarter turns')
    if type(p.get('mirror_x')) is not bool: fail('mirror_x must be boolean')
    for key in ('buffer','approach'):
        if type(p.get(key)) is not int or not 0<=p[key]<=8: fail(key+' must be 0..8 tiles')
    if p['road_relation'] not in ('frontage','spur','remote'): fail('road_relation must be frontage, spur or remote')
    if not isinstance(p.get('entrances'),list) or not p['entrances']: fail('declare entrances; doors are never inferred')
    ids=set()
    for e in p['entrances']:
        if not isinstance(e,dict) or set(e)!={'id','x','y','normal','width','role','required'}: fail('entrance needs id,x,y,normal,width,role,required')
        if not isinstance(e['id'],str) or not e['id'] or e['id'] in ids: fail('duplicate/empty entrance id')
        ids.add(e['id'])
        if e['normal'] not in NORMALS or type(e['width']) is not int or e['width']<1: fail('invalid entrance normal/width')
        if type(e['x']) is not int or type(e['y']) is not int or type(e['required']) is not bool or e['role'] not in ('main','service'): fail('invalid entrance coordinates/role/required')
        for x,y in entrance_cells(e):
            if not (0<=x<w and 0<=y<h): fail('complete entrance span must be inside footprint')
            if {'N':y!=0,'S':y!=h-1,'W':x!=0,'E':x!=w-1}[e['normal']]: fail('entrance normal must point outward from footprint edge')
            terrain=raw['legend'].get(raw['layers'][y][x])
            if terrain in ('wall','rock','tree'): fail('entrance span contains solid terrain')
    if p['road_relation']!='remote' and not any(e['required'] for e in p['entrances']): fail('connected placement needs a required entrance')
    if not isinstance(p.get('targets'),list) or not p['targets']: fail('declare at least one required access target')
    for t in p['targets']:
        if not isinstance(t,dict) or set(t)!={'x','y','kind','required'}: fail('target needs x,y,kind,required')
        if type(t['x']) is not int or type(t['y']) is not int or not 0<=t['x']<w or not 0<=t['y']<h: fail('target outside footprint')
        if t['kind'] not in ('floor','item','readable','container','stairs_down','stairs_up') or type(t['required']) is not bool: fail('invalid access target')


def transform(raw,rotation=0,mirror=False):
    """Transform the whole consumed document; originals and unknown scalars survive."""
    w,h=len(raw['layers'][0]),len(raw['layers']); validate_profile(raw,w,h)
    p=raw.get('placement')
    if p is None or rotation not in p['rotations'] or (mirror and not p['mirror_x']):
        raise GenerationError(f'{raw.get("id")}: transform is not permitted by placement profile')
    known={'layers','decor_layer','special_tiles','player_start','connection_point','spawn_offset','placement','exit_x','exit_y','exit_direction','width','height','legend','legend_weights'}
    def coordinate_metadata(value):
        return isinstance(value,dict) and (bool(set(value)&{'x','y','position','points','cells','bounds'}) or any(coordinate_metadata(v) for v in value.values())) or isinstance(value,list) and any(coordinate_metadata(v) for v in value)
    if rotation or mirror:
        for k,v in raw.items():
            if k not in known and coordinate_metadata(v): raise GenerationError(f'{raw["id"]}: unsupported coordinate-bearing metadata {k}; declare a supported field before transforming')
    def xy(x,y):
        if mirror: x=w-1-x
        return ((x,y),(h-1-y,x),(w-1-x,h-1-y),(y,w-1-x))[rotation//90]
    nw,nh=(h,w) if rotation%180 else (w,h)
    def grid(rows):
        result=[[None]*nw for _ in range(nh)]
        for y,row in enumerate(rows):
            for x,v in enumerate(row):
                a,b=xy(x,y); result[b][a]=v
        return result
    def normal(n):
        dx,dy=NORMALS[n]
        if mirror: dx=-dx
        for _ in range(rotation//90): dx,dy=-dy,dx
        return next(k for k,v in NORMALS.items() if v==(dx,dy))
    result=copy.deepcopy(raw)
    result['layers']=[''.join(row) for row in grid(raw['layers'])]
    if 'decor_layer' in raw: result['decor_layer']=grid(raw['decor_layer'])
    for field in ('player_start','connection_point','spawn_offset'):
        if field in result: result[field]['x'],result[field]['y']=xy(raw[field]['x'],raw[field]['y'])
    for row in result.get('special_tiles',[]): row['x'],row['y']=xy(row['x'],row['y'])
    if 'exit_x' in raw and 'exit_y' in raw: result['exit_x'],result['exit_y']=xy(raw['exit_x'],raw['exit_y'])
    if 'exit_direction' in raw:
        full={'north':'N','south':'S','east':'E','west':'W'}
        result['exit_direction']=next(k for k,v in full.items() if v==normal(full[raw['exit_direction']]))
    for e,old in zip(result['placement']['entrances'],p['entrances']):
        cells=[xy(x,y) for x,y in entrance_cells(old)]
        e['x'],e['y']=min(x for x,y in cells),min(y for x,y in cells); e['normal']=normal(old['normal'])
    for t in result['placement']['targets']: t['x'],t['y']=xy(t['x'],t['y'])
    result['width'],result['height']=nw,nh
    return result


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()


def dependencies(raw,data):
    """Semantic closure for this selected definition, all alternatives and factories.

    Only consumed structure fields count. Factory definitions remain whole because
    item/actor factories consume evolving component fields; unknown source metadata
    on structures and formatting never become generation dependencies.
    """
    result={}
    consumed=('id','layers','legend','decor_layer','special_tiles','placement')
    definition={k:copy.deepcopy(raw[k]) for k in consumed if k in raw}
    def consumed_special(s):
        keys=('type','kind','x','y','item_id','text_id','scene_id','decor_id','loot_pools','weight')
        row={k:s[k] for k in keys if k in s}
        if 'spawn_table' in s: row['spawn_table']=[consumed_special(r) for r in s['spawn_table']]
        return row
    definition['special_tiles']=[consumed_special(s) for s in raw.get('special_tiles',[])]
    definition['legend']={ch:raw['legend'][ch] for ch in sorted(set(''.join(raw['layers'])))}
    # Candidate membership/weights have already been resolved into saved IDs.
    definition['placement'].pop('weight',None);definition['placement'].pop('contexts',None)
    result['structure:'+raw['id']]=digest(definition)
    def add(table,key):
        name=table+':'+key
        if name in result: return
        value=getattr(data,table).get(key)
        if value is None: raise GenerationError('missing generation dependency '+name)
        if table=='loot_pools':
            semantic={'roll_count':value.get('roll_count',[1,1]),'items':[{'item_id':r['item_id'],'weight':r.get('weight',1)} for r in value.get('items',[])]}
        elif table=='scenes': semantic={'floor_objects':[r['item_id'] for r in value.get('floor_objects',[])]}
        elif table=='terrain': semantic={'walkable':value.get('walkable',True),'transparent':value.get('transparent',True)}
        elif table=='decoratives': semantic={k:value.get(k,False) for k in ('blocks_movement','blocks_sight','container')}
        else: semantic=value
        result[name]=digest(semantic)
        if table=='items' and value.get('body_id'): add('bodies',value['body_id'])
        if table=='scenes':
            for row in value.get('floor_objects',[]): add('items',row['item_id'])
        if table=='loot_pools':
            for row in value.get('items',[]): add('items',row['item_id'])
    for ch in sorted(set(''.join(raw['layers']))):
        if raw['legend'][ch] is not None: add('terrain',raw['legend'][ch])
    for row in raw.get('decor_layer',[]):
        for d in row:
            if d: add('decoratives',d)
    def special(s):
        kind=s.get('type',s.get('kind'))
        if kind=='weighted':
            for row in s['spawn_table']: special(row)
        elif kind=='item':
            add('items',s['item_id'])
            if s.get('text_id'):
                text=s['text_id']; mapped=data.text_item_map.get(text,'letter')
                result['text_binding:'+text]=digest(mapped); add('items',mapped)
        elif kind=='scene': add('scenes',s['scene_id'])
        elif kind=='container':
            add('decoratives',s.get('decor_id','crate'))
            for pool in s.get('loot_pools',[]): add('loot_pools',pool)
    for s in raw.get('special_tiles',[]): special(s)
    return result


def check_dependencies(placement,plan,data):
    raw=data.structures.get(placement['asset'])
    if raw is None: raise GenerationError('missing selected asset '+placement['asset'])
    expected=plan['dependencies'][placement['dependency']]
    actual=dependencies(raw,data)
    changed=next((k for k in sorted(set(actual)|set(expected)) if actual.get(k)!=expected.get(k)),None)
    if changed:
        raise GenerationError(f"{placement['id']}: changed dependency {changed}; restore matching definitions or start a fresh world for edited generation content")
    return raw
