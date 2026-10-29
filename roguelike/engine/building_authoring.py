"""First-party native surface building documents. No gameplay imports this adapter."""
from pathlib import PurePosixPath
from engine.definition_sources import definition_sources
from engine.pool_authoring import safe_id, locations, issue, container_dependencies, load_authoring_data
from generation.structure_contract import ELIGIBILITY, compile_structure, StructureError, read_document

CONTRACT = 'surface-building-1'
PRODUCTION_ROUTE = 'ordinary_building'
ROOT = 'roguelike/data/buildings/'
OBSERVE_INSPECTION = True
USES_SCENE_SEED = True
VIEWS = ['building-spatial']
PUBLICATION_NOTE = ('Saved definitions affect fresh catalogues/generation. A pending planned surface retains its selected semantic dependencies: '
    'same-ID building, pool or item changes can require restoring matching definitions or starting a fresh world. No replanning/migration. '
    'Generated owned surfaces retain saved maps, contents and mutations; missing required caches still refuse regeneration. '
    'A new variant retains the old source and changes no explicit settlement/POI/compound membership, but legacy folder pools can discover it. '
    'A new building ID does not isolate shared pool/item dependencies from later edits.')
LIMITATIONS = ('Revealed initial production construction and static access in declared orientations. No lot fit, road connectivity, '
    'natural selection, player FOV, ordinary use, safe play or balance proof. Moving/resizing/rotating can change position-derived loot.')
SCHEMA = {'$schema':'https://json-schema.org/draft/2020-12/schema','type':'object','properties':{
    'id':{'type':'string','readOnly':True},'description':{'type':'string','x-control':'multiline'},
    'weight':{'type':'number','minimum':0,'description':'Legacy corner-scatter weight; current planned membership is separate.'}},'additionalProperties':True}


def matches(path):
    p = PurePosixPath(path).parts
    return len(p) >= 5 and p[:3] == ('roguelike','data','buildings') and p[3] in ELIGIBILITY.keys()-{'plaza'} and path.endswith('.json')


def discover_paths(root):
    return [p for p in (root/ROOT).rglob('*.json') if matches(p.relative_to(root).as_posix())]


def source_index(data_root):
    # Structures use strict read_document (including UTF-8 BOM), rather than
    # the item/pool directory loader's different UTF-8 policy. Include every
    # location, even unsupported nested/category/array sources, for authority.
    result={}
    for path in sorted((data_root/'buildings').rglob('*.json')):
        try:raw=read_document(path)
        except StructureError:continue
        for i,row in enumerate(raw if isinstance(raw,list) else [raw]):
            if isinstance(row,dict) and isinstance(row.get('id'),str):
                result.setdefault(row['id'],[]).append(dict(path='roguelike/data/'+path.relative_to(data_root).as_posix(),pointer=f'/{i}' if isinstance(raw,list) else '',definition=row))
    return result


def capability(raw,path,pointer=''):
    p=PurePosixPath(path)
    reason=''
    if not matches(path) or len(p.parts)!=5 or pointer or not isinstance(raw,dict):
        reason='Only immediate single-object buildings/<supported-category>/<safe-id>.json sources are writable; plazas, arrays and nested formats remain inspect-only.'
    elif not safe_id(raw.get('id')) or p.name != raw['id']+'.json':
        reason='Original exact safe ID must match its filename.'
    return dict(editable=not reason,reason=reason,operations=[] if reason else ['edit','variant'],shape='native ordinary building object')


def source_problems(raw,data,path,data_root,*,strict=True):
    identifier=raw.get('id') if isinstance(raw,dict) else None
    entries=locations(source_index(data_root),identifier)
    errors=[]
    if len(entries)!=1 or entries[0]['path']!=path or entries[0]['pointer']:
        errors.append(issue(path,'BUILDING_SOURCE','id','Identity must resolve to this exact single source, including case aliases outside the displayed list: '+', '.join(e['path']+e['pointer'] for e in entries)))
    if hasattr(data,'structure_catalog'):
        from pathlib import Path
        loaded=[e for e in data.structure_catalog.entries if e.route==PRODUCTION_ROUTE and e.raw.get('id')==identifier]
        if len(loaded)!=1 or loaded[0].raw!=raw or Path(loaded[0].path).resolve()!=(data_root/PurePosixPath(path).relative_to('roguelike/data')).resolve():
            errors.append(issue(path,'LOADER_IDENTITY','id','Loader/source identity does not match the exact ordinary building.'))
    elif strict:
        errors.append(issue(path,'CATALOG_REJECTED','','Candidate requires a complete loader-accepted catalogue.'))
    # Case-unambiguous source directories and basenames, not just logical IDs.
    current=data_root
    for part in PurePosixPath(path).relative_to('roguelike/data').parts:
        peers=[p.name for p in current.iterdir() if p.name.casefold()==part.casefold()] if current.is_dir() else []
        if peers!=[part]: errors.append(issue(path,'SOURCE_CASE','','Source path is absent or case-ambiguous at '+str(current/part)))
        current=current/part
    return errors


def authorize_candidate(original,candidate,source,target,*,data=None):
    cap=capability(original,source); errors=[]
    if not cap['editable']: errors.append(issue(source,'SOURCE_ENTITLEMENT','',cap['reason']))
    if not isinstance(candidate,dict): return errors+[issue(target,'BUILDING_SHAPE','','Requires a native object.')]
    identifier=candidate.get('id')
    if source==target:
        if identifier!=original.get('id'): errors.append(issue(target,'IDENTITY_CHANGE','id','Same-ID edits retain exact ID and path.'))
    elif (not safe_id(identifier) or identifier.casefold()==str(original.get('id')).casefold()
          or PurePosixPath(target).parent!=PurePosixPath(source).parent or PurePosixPath(target).name!=identifier+'.json'):
        errors.append(issue(target,'VARIANT_ID','id','Variant requires a distinct safe case-insensitively unique ID matching a filename beside its source.'))
    return errors


def target_problems(candidate,source,target,data_root):
    if source==target:return []
    identifier=candidate.get('id') if isinstance(candidate,dict) else None
    entries=locations(source_index(data_root),identifier)
    directory=data_root/PurePosixPath(target).relative_to('roguelike/data').parent
    collisions=[p.name for p in directory.iterdir() if p.name.casefold()==PurePosixPath(target).name.casefold()] if directory.is_dir() else []
    return [issue(target,'VARIANT_EXISTS','id','New variant identity/path already exists, including case aliases: '+', '.join([e['path']+e['pointer'] for e in entries]+collisions))] if entries or collisions else []


def direct_dependencies(raw,data,path,data_root):
    from engine.item_factory import ItemFactory
    from engine.harvesting import validate_output
    errors=[]; factory=ItemFactory(data)
    indexes={k:definition_sources(data_root,k,('text_item_map.json',) if k=='texts' else ()) for k in ('items','texts')}
    def resolved(table,identifier,field):
        entries=locations(indexes[table],identifier)
        if len(entries)!=1 or identifier not in getattr(data,table) or entries[0]['definition']!=getattr(data,table)[identifier]:
            errors.append(issue(path,'BUILDING_REFERENCE',field,f'{table} {identifier!r} is missing, skipped or case-ambiguous.'));return False
        return True
    def visit(row,field):
        if not isinstance(row,dict):return
        kind=row.get('type',row.get('kind'))
        if kind=='weighted':
            for i,r in enumerate(row.get('spawn_table',[]) if isinstance(row.get('spawn_table'),list) else []):visit(r,f'{field}.spawn_table[{i}]')
        if kind!='item':return
        declared=row.get('item_id');text=row.get('text_id');effective=data.text_item_map.get(text,'letter') if text else declared
        ok=resolved('items',declared,field+'.item_id')
        if effective!=declared:ok=resolved('items',effective,field+'.text_id -> effective carrier') and ok
        if not ok:return
        try:
            obj=validate_output(factory.create(effective),effective)
            if text:obj.text_id=text
            if text and getattr(obj,'on_use',None)!='read':raise ValueError('Effective text carrier is not readable')
            binding=getattr(obj,'text_id',None) if getattr(obj,'on_use',None)=='read' else None
            if binding:resolved('texts',binding,field+'.text_id')
        except Exception as error:errors.append(issue(path,'BUILDING_FACTORY',field,f'Unowned effective factory/ITEM_STATE check failed: {error}'))
    for i,row in enumerate(raw.get('special_tiles',[]) if isinstance(raw,dict) and isinstance(raw.get('special_tiles',[]),list) else []):visit(row,f'special_tiles[{i}]')
    return errors


def authoring_validate(raw,data,path,data_root):
    errors=source_problems(raw,data,path,data_root)
    try:errors += [d.json() for d in compile_structure(raw,PRODUCTION_ROUTE,data,path=path,category=PurePosixPath(path).parent.name).diagnostics]
    except StructureError as error:errors += [d.json() for d in error.diagnostics]
    errors += container_dependencies(raw,data,path,data_root)+direct_dependencies(raw,data,path,data_root)
    return errors


def authoring_context(raw,data,path,data_root,identity,digest,observe=False,**kwargs):
    from generation.building_preview import orientations
    from generation.authored_rooms import catalog
    cap=capability(raw,path)
    authority=source_problems(raw,data,path,data_root,strict=False)
    if authority:cap=dict(cap,editable=False,operations=[],reason='; '.join(d['message'] for d in authority))
    diagnostics=authoring_validate(raw,data,path,data_root)
    generated=None
    if observe and not any(d['severity']=='error' for d in diagnostics):
        generated,problems=orientations(raw,data,seed=kwargs.get('seed',20261023),path=path,category=PurePosixPath(path).parent.name)
        diagnostics+=problems
        for report in generated['orientations']:
            report.update(source=identity,source_path=path,source_sha256=digest,draft_sha256=digest,layout_contract=CONTRACT)
        generated.update(source=identity,source_path=path,source_sha256=digest,draft_sha256=digest,layout_contract=CONTRACT)
    return dict(records=[dict(id=raw.get('id','') if isinstance(raw,dict) else '',definition=raw if isinstance(raw,dict) else {},capability=cap,diagnostics=diagnostics)],catalog={**catalog(data,data_root),'text_item_map':data.text_item_map},preview=generated)


def reference_options(context):return {}


def authoring_evidence(context):
    report=context.get('preview') if context else None
    passed=bool(report and report['passed'])
    return dict(semantic_verified=passed,placement_verified=passed,population_verified=passed,preview=report)
