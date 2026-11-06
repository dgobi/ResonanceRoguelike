"""Narrow registered authoring adapter for captured fastening profiles."""
from pathlib import PurePosixPath
from engine.access_profiles import validate, DEFAULTS, FIELDS
from engine.definition_sources import definition_sources
from engine.pool_authoring import locations, issue, safe_id

CONTRACT='access-profile-1'
ROOT='roguelike/data/access_profiles/'
PRODUCTION_ROUTE='access_profile'
VIEWS=[]
PUBLICATION_NOTE=('Publish a profile before placing references. Freshly generated objects capture saved requirements, methods and yields. '
    'Existing and partially worked objects keep their captured settings. Reset keeps its immutable Test capture; latest saved captures current saved files. Unpublished drafts are excluded.')
LIMITATIONS='Finite secured-container and one-cell screen responses only. Validation proves configuration/references, not ordinary play or tactical safety.'
SCHEMA={'$schema':'https://json-schema.org/draft/2020-12/schema','type':'object','properties':{
    'id':dict(type='string',readOnly=True),'version':dict(type='integer',readOnly=True),
    'name':dict(type='string',title='Fastening name'),
    'description':dict(type='string',title='Visible fastening',**{'x-control':'multiline'}),
    'host_container':dict(type='boolean',title='Supports secured containers',default=True),
    'host_screen':dict(type='boolean',title='Supports removable screens',default=True),
    'allow_careful':dict(type='boolean',title='Allow careful cutting',default=True),
    'cutting_tier':dict(type='integer',title='Equipped cutting tier',minimum=1,maximum=5,default=1),
    'work_steps':dict(type='integer',title='Careful work steps',minimum=1,maximum=12,default=3,
        description='One paid player action and quiet strength-2 pulse per step; no automatic progress.'),
    'allow_force':dict(type='boolean',title='Allow quick force',default=True,description='One action, dismantle sound strength 8, no salvage.'),
    'allow_dissolution':dict(type='boolean',title='Allow Dissolution',default=True,description='One whole qualifying captured dose and one action; no access sound or salvage.'),
    'dissolution_threshold':dict(type='number',title='Minimum Dissolution strength',minimum=.01,maximum=1,default=.4),
    'screen_careful_yield':dict(type='string',title='Careful screen yield',default='wood_bundle',
        description='One wood_bundle exactly once, or empty for no output. Containers never yield salvage.',**{'x-reference':'yields'})},
    'additionalProperties':False}


def capability(raw,path,pointer=''):
    reason=''
    if (PurePosixPath(path).parent.as_posix()!=ROOT.rstrip('/') or pointer or not isinstance(raw,dict)
            or not safe_id(raw.get('id')) or PurePosixPath(path).name!=raw.get('id','')+'.json'):
        reason='Requires one profile object with exact filename identity directly in access_profiles/.'
    elif type(raw.get('version',1)) is not int or raw.get('version',1)!=1 or set(raw)-FIELDS:
        reason='Original source has unsupported version or behavior fields; editing cannot upgrade its authority.'
    return dict(editable=not reason,operations=[] if reason else ['edit','variant'],reason=reason)


def authoring_validate(raw,data,path,data_root):
    errors=[]
    try:validate(raw,data)
    except (ValueError,KeyError,TypeError) as error:errors.append(issue(path,'ACCESS_PROFILE','',str(error)))
    entries=locations(definition_sources(data_root,'access_profiles'),raw.get('id') if isinstance(raw,dict) else None)
    if len(entries)!=1 or entries[0]['path']!=path or entries[0]['pointer']:
        errors.append(issue(path,'ACCESS_SOURCE','id','Profile identity must resolve to this exact single source, including case aliases.'))
    return errors


def authorize_candidate(original,candidate,source,target,*,data=None):
    cap=capability(original,source);errors=[]
    if not cap['editable']:errors.append(issue(source,'SOURCE_ENTITLEMENT','',cap['reason']))
    if not isinstance(candidate,dict):return errors+[issue(target,'ACCESS_PROFILE','','Requires one profile object.')]
    identifier=candidate.get('id')
    if source==target:
        if identifier!=original.get('id'):errors.append(issue(target,'IDENTITY_CHANGE','id','Same-file editing retains the original ID.'))
    elif (not safe_id(identifier) or identifier.casefold()==str(original.get('id')).casefold()
          or PurePosixPath(target).parent!=PurePosixPath(source).parent or PurePosixPath(target).name!=identifier+'.json'):
        errors.append(issue(target,'VARIANT_ID','id','Use a distinct safe identity beside the source.'))
    if candidate.get('version',1)!=original.get('version',1):errors.append(issue(target,'ACCESS_VERSION','version','Retain the supported original version.'))
    return errors


def authoring_context(raw,data,path,data_root,identity,digest,**kwargs):
    diagnostics=authoring_validate(raw,data,path,data_root);cap=capability(raw,path);references=[]
    if any(d['code']=='ACCESS_SOURCE' for d in diagnostics):cap=dict(cap,editable=False,operations=[],reason='Ambiguous original source.')
    for folder in ('buildings','layouts'):
        for entries in definition_sources(data_root,folder).values():
            for entry in entries:
                for n,r in enumerate(entry['definition'].get('special_tiles',[])):
                    if isinstance(r,dict) and r.get('access_profile')==raw.get('id'):
                        references.append(dict(id=entry['definition']['id'],path=entry['path'],family='room' if folder=='layouts' else 'building',
                            field=f'special_tiles[{n}].access_profile'))
    return dict(records=[dict(id=raw.get('id',''),definition=raw,capability=cap,diagnostics=diagnostics)],references=references)


def reference_options(context):
    return dict(yields=[dict(id='',label='No salvage'),dict(id='wood_bundle',label='One wood bundle (careful screen removal only)')])


def authoring_evidence(context):
    return dict(semantic_verified=bool(context and not any(d['severity']=='error' for r in context['records'] for d in r['diagnostics'])))
