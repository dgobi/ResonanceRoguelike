"""Fixed assignment profile authoring; gameplay owns the policy and selector."""
import hashlib
import json
import random
from generation.authored_submap_selection import CONTRACT, IDENTITY, PROFILE, TYPES, validate, issue

PUBLICATION_NOTE = ("Save/reopen rooms and linked contents first, then validate and apply this one profile. Parked drafts are excluded. "
    "Assignment changes apply to newly created worlds. Same-ID room edits still apply on first construction of pending rooms in existing worlds; "
    "generated scenes keep their saved contents. Use a new room variant to preserve the old definition's meaning.")
LIMITATIONS = "Assignment metadata only; room preview checks construction/static access, and Test room uses a staged foyer. Neither proves natural travel or entrance use."
VIEWS = ["world-assignment"]
SCHEMA = {"$schema":"https://json-schema.org/draft/2020-12/schema", "type":"object", "properties":{
    "id":{"type":"string","readOnly":True}, "version":{"type":"integer","readOnly":True},
    "enabled":{"type":"boolean","title":"Enabled","description":"Deliberate opt-in for later new worlds only."},
    "target_type":{"type":"string","title":"Target underground type","x-reference":"underground-types"},
    "authored_chance":{"type":"number","minimum":0,"maximum":1,"title":"Authored-interior chance","description":"Conditional on an ordinary matching dungeon occurring; 0 keeps it procedural, 1 always chooses a candidate."},
    "candidates":{"type":"array","title":"Layout candidates","x-control":"ordered-records","items":{"type":"object","properties":{
        "layout_id":{"type":"string","title":"Saved room","x-reference":"saved-rooms","x-initial":""},
        "weight":{"type":"number","title":"Relative weight","minimum":0,"x-initial":1}},"required":["layout_id","weight"]}}},
    "required":["id","version","enabled","target_type","authored_chance","candidates"],"additionalProperties":True}


def capability(raw, path, pointer=""):
    supported=path==PROFILE and not pointer and isinstance(raw,dict) and raw.get('id')==IDENTITY and type(raw.get('version')) is int and raw['version']==1
    return dict(editable=supported,reason="Fixed edit-only assignment profile; validate saved room dependencies." if supported else "Requires the fixed authored_submap_selection version-1 object.")


def authoring_validate(raw,data,path,data_root):
    if path!=PROFILE: return [issue('', 'Assignment publication has one fixed target.')]
    return validate(raw,data)[1]


def source_index(data_root):
    path=data_root/'generation/authored_submap_selection.json'
    try: raw=json.loads(path.read_text(encoding='utf-8-sig'))
    except (OSError,ValueError): raw={}
    return {str(raw.get('id',IDENTITY)):[dict(path=PROFILE,pointer='',definition=raw)]} if isinstance(raw,dict) else {}


def authoring_context(raw,data,path,data_root,identity,digest,observe=False):
    from generation.authored_rooms import source_index, locations, capability as room_capability, authoring_validate as room_validate
    index=source_index(data_root); rooms=[]
    for identifier,entries in sorted(index.items()):
        source=entries[0]; cap=room_capability(source['definition'],source['path'])
        reason=cap['reason']
        eligible=len(locations(index,identifier))==1 and 'edit' in cap['operations'] and identifier in data.layouts
        if eligible:
            errors=[d for d in room_validate(source['definition'],data,source['path'],data_root) if d['severity']=='error']
            if errors: eligible=False; reason='; '.join(d['message'] for d in errors)
        if len(locations(index,identifier))!=1: reason='Ambiguous saved room identity.'
        if not eligible and not reason: reason='Publish the documentation template as an ordinary room first.'
        rooms.append(dict(id=identifier,label=str(source['definition'].get('name',source['definition'].get('description',identifier.replace('_',' ').title())))+' · '+identifier,
                          path=source['path'],eligible=eligible,reason=reason))
    return dict(records=[dict(id=IDENTITY,definition=raw if isinstance(raw,dict) else {},capability=capability(raw,path),diagnostics=authoring_validate(raw,data,path,data_root))],rooms=rooms)


def reference_options(context):
    return {'underground-types':[dict(id=t,label=t.title()) for t in TYPES],
            'saved-rooms':[dict(id=r['id'],label=r['label']) for r in context['rooms'] if r['eligible']]}


def authorize_candidate(original,candidate,source,target,*,data=None):
    if source!=PROFILE or target!=PROFILE or not capability(candidate,target)['editable']: return [issue('id','Keep the fixed profile identity, version and target.')]
    editable={'enabled','target_type','authored_chance','candidates'}
    if {k:v for k,v in original.items() if k not in editable}!={k:v for k,v in candidate.items() if k not in editable}:
        return [issue('','Preserve fixed identity/version and unknown profile metadata.')]
    return []


def authoring_evidence(context):
    return dict(semantic_verified=bool(context and not any(d['severity']=='error' for d in context['records'][0]['diagnostics'])))


def authoring_preview(raw,data,root,inputs):
    from engine.data_loader import DataLoader
    from generation.world_gen import generate_world
    from generation.authored_submap_selection import resolve
    from world.world_map import WorldMap
    from main import WORLD_WIDTH, WORLD_HEIGHT
    if set(inputs)!={'seed'} or type(inputs['seed']) is not int or not 0 <= inputs['seed'] <= 2147483647: raise ValueError('Use an integer preview seed from 0 to 2147483647.')
    saved=(root/PROFILE).read_bytes()
    if json.loads(saved.decode('utf-8-sig'))!=raw: raise ValueError('Preview uses saved assignments only. Apply and reopen this profile first.')
    data=DataLoader(str(root/'roguelike/data')); policy=resolve(data)
    world=WorldMap(WORLD_WIDTH,WORLD_HEIGHT);world.seed=inputs['seed']
    generate_world(world,data,random.Random(world.seed))
    from generation.authored_rooms import source_index as room_sources
    rooms=room_sources(data.root); rows=[];matching=authored=0
    for (wx,wy),chunk in sorted(world.chunks.items()):
        for sm in chunk.submaps:
            if sm.submap_type!=policy.target_type: continue
            matching+=1
            if not sm.layout_id: continue
            authored+=1
            if len(rows)<100:
                rows.append(dict(chunk=[wx,wy],submap_id=sm.submap_id,type=sm.submap_type,seed=sm.seed,layout_id=sm.layout_id,path=rooms[sm.layout_id][0]['path']))
    return dict(kind='assignment-preview',inputs=inputs,seed=world.seed,width=world.width,height=world.height,
                plan_mode=world.plan_mode,generation_revision=world.generation_revision,profile_path=PROFILE,profile_sha256=hashlib.sha256(saved).hexdigest(),
                target_type=policy.target_type,authored_chance=policy.chance,enabled=policy.enabled,matching_count=matching,authored_count=authored,
                procedural_count=matching-authored,rows=rows,truncated=authored-len(rows),
                configuration=dict(planning_settings='ordinary defaults',surface_policy=world.surface_policy),
                setup='Saved profile and dependencies; ordinary new-game dimensions/mode/configuration; production generate_world. No local rooms constructed or campaign saves read.',
                dependencies='Saved room definitions, references, generation data and game code',consumer='generation.world_gen.generate_world → _assign_submaps → Policy.choose')
