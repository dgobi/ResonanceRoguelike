"""Production ordinary-building orientation orchestration; no substitute simulation."""
import hashlib
import json
import re
from generation.context import GenerationError
from generation.placement import transform, NORMALS, entrance_cells
from generation.structure_preview import preview, receipt_owned, check_access


def transform_limitations(raw):
    """Unknown coordinate metadata stays intact; never guess its transform."""
    def bearing(v):
        return isinstance(v,dict) and (bool(set(v)&{'x','y','position','points','cells','bounds'}) or any(bearing(c) for c in v.values())) or isinstance(v,list) and any(bearing(c) for c in v)
    def row(record,field):
        for key,value in record.items():
            if key not in ('x','y','spawn_table') and bearing(value):
                raise GenerationError(f'Unsupported coordinate-bearing metadata {field}.{key}; transform refused')
        for n,child in enumerate(record.get('spawn_table',[])):
            row(child,f'{field}.spawn_table[{n}]')
    for i,record in enumerate(raw.get('special_tiles',[])):row(record,f'special_tiles[{i}]')
    for key in ('player_start','connection_point','spawn_offset'):
        if key in raw:
            for k,v in raw[key].items():
                if k not in ('x','y') and bearing(v):raise GenerationError(f'Unsupported coordinate metadata {key}.{k}')
    if ('exit_x' in raw)!=('exit_y' in raw):raise GenerationError('Unpaired retained exit coordinate cannot be transformed safely')


def orientations(raw,data,*,seed=20261023,path='<draft>',category=None):
    from engine.pool_authoring import issue
    from engine.save_components import serialize_item
    reports=[];problems=[]
    profile=raw.get('placement')
    choices=list(dict.fromkeys((r,m) for r in profile['rotations'] for m in ([False,True] if profile['mirror_x'] else [False]))) if profile else [(0,False)]
    for rotation,mirror in choices:
        label=f'{rotation}° / mirror {mirror}'
        def problem(code,field,message,xy=None):
            problems.append({**issue(path,code,field,f'{label}: {message}'),'source_xy':xy,'layer':'specials' if field.startswith('special_tiles') else 'terrain','rotation':rotation,'mirror':mirror})
        try:
            if rotation or mirror:transform_limitations(raw)
            oriented=transform(raw,rotation,mirror) if profile else raw
            w,h=len(oriented['layers'][0]),len(oriented['layers'])
            if w>80 or h>43:raise GenerationError(f'Oriented footprint {w} × {h} exceeds scene 80 × 43')
            p=oriented.get('placement',{})
            entries=sorted((e for e in p.get('entrances',[]) if e['required']),key=lambda e:(e['role']!='main',e['id']))
            expectations=None
            if entries:
                e=entries[0];dx,dy=NORMALS[e['normal']]
                targets=[dict(t,name=f'placement.targets[{i}]') for i,t in enumerate(p['targets']) if t['required']]
                targets += [dict(x=x,y=y,kind='floor',name=f'placement.entrances[{i}].span[{n}]') for i,e in enumerate(p['entrances']) if e['required'] for n,(x,y) in enumerate(entrance_cells(e))]
                expectations=dict(entry=dict(x=e['x']+dx,y=e['y']+dy),targets=targets)
            report,m,_=preview(oriented,'ordinary_building',data,seed=seed,path=path,category=category,expectations=expectations,observe_receipts=True)
            ox,oy=report['origin']
            # The population receipt, not coincidental ID/coordinate matches, owns each observation.
            records=report.pop('_population_receipts')
            record_access=[]
            for receipt in records:
                if receipt['kind'] not in ('item','container'):continue
                index=receipt['source_index'];source=raw.get('special_tiles',[])[index]
                if source.get('type',source.get('kind')) not in ('item','container'):continue
                xy=receipt['xy'];kind=receipt['kind'];owned=receipt_owned(receipt,m)
                result=check_access(m,data,dict(expectations,coordinates='map',entry=dict(x=ox+expectations['entry']['x'],y=oy+expectations['entry']['y']),targets=[dict(x=xy[0],y=xy[1],kind=kind,name=f'special_tiles[{index}]')]))[-1] if expectations else None
                passed=owned and (result is None or result['passed'])
                if receipt.get('text_id'):passed=passed and all(getattr(i,'on_use',None)=='read' and getattr(i,'text_id',None)==receipt['text_id'] for i in receipt['objects'])
                row=dict(target=f'special_tiles[{index}]',kind=kind,source_xy=[source['x'],source['y']],transformed_xy=receipt['source_xy'],xy=xy,receipt_owned=owned,relocated=receipt['relocated'],passed=passed,access_verified=bool(expectations),required_gate=kind=='container')
                record_access.append(row)
                if not owned or kind=='container' and not passed:problem('RECORD_ACCESS',row['target'],'Receipt-owned construction/access failed',[source['x'],source['y']])
            serialized=[]
            for r in records:
                row={k:v for k,v in r.items() if k not in ('objects','actors')}
                row['objects']=([dict(decor_id=d,items=[serialize_item(i) for i in values]) for d,values in r['objects']] if r['kind']=='container' else [serialize_item(i) for i in r['objects']])
                row.update(source_xy=[raw['special_tiles'][r['source_index']]['x'],raw['special_tiles'][r['source_index']]['y']],transformed_xy=r.get('source_xy'),actual_count=len(r['objects']))
                serialized.append(row)
            for row in report['access']:
                if not row['passed']:
                    field=row['target'];found=re.match(r'placement\.(targets|entrances)\[(\d+)\]',field)
                    native=raw['placement'][found[1]][int(found[2])] if found else None
                    span=re.search(r'\.span\[(\d+)\]',field)
                    if span and native:
                        # Span order is normalized after transformation. Invert the
                        # failed coordinate, not its index in that normalized span.
                        tx,ty=row['xy'][0]-ox,row['xy'][1]-oy
                        sw,sh=len(raw['layers'][0]),len(raw['layers'])
                        x,y=((tx,ty),(ty,sh-1-tx),(sw-1-tx,sh-1-ty),(sw-1-ty,tx))[rotation//90]
                        if mirror:x=sw-1-x
                        xy=[x,y]
                        native_span=entrance_cells(native).index((x,y))
                        transformed_field=field
                        field=re.sub(r'\.span\[\d+\]',f'.span[{native_span}]',field)
                    else:
                        xy=[native['x'],native['y']] if native else None
                        transformed_field=field
                    problem('ACCESS',field,'Required native goal/span failed at exact declared coordinates',xy)
                    problems[-1].update(transformed_field=transformed_field,transformed_xy=[row['xy'][0]-ox,row['xy'][1]-oy],scene_xy=row['xy'])
            for d in report['source_diagnostics']:
                if d['code']=='DEFERRED_SPECIAL':problem('UNSUPPORTED_PREVIEW_SPECIAL',d['field'],d['message'])
            report.update(rotation=rotation,mirror=mirror,width=80,height=43,valid=True,scene_seed=str(m.generation_context.scene_seed),scene_address=list(m.generation_context.address),
                population_receipts=serialized,record_access=record_access,access_verified=bool(expectations) and all(a['passed'] for a in report['access']),
                orientation_entry=entries[0]['id'] if entries else None,
                legend={k:dict(walkable=bool(v.get('walkable',True)),transparent=bool(v.get('transparent',True))) for k,v in data.terrain.items()},
                candidate_sha256=report['candidate_identity'],terrain_sha256=hashlib.sha256(json.dumps(report['terrain']).encode()).hexdigest(),elapsed_ms=0,
                context=f'Ordinary surface production: {label}; source → transformed → scene origin ({ox},{oy}). '+('Full required spans/goals checked from main/ID-selected exterior approach.' if expectations else 'No required diagnostic entrance: access unverified.'),
                rendering='Revealed initial production preview; no FOV, use, lot fit, road connectivity, natural selection or balance proof.')
            reports.append(report)
        except GenerationError as error:
            match=re.search(r'special\[(\d+)\]',str(error))
            index=int(match[1]) if match else None
            record=raw.get('special_tiles',[])[index] if index is not None and index<len(raw.get('special_tiles',[])) else None
            problem('PRODUCTION_PLACEMENT' if record else 'BUILDING_ORIENTATION',f'special_tiles[{index}]' if record else 'placement',str(error),[record['x'],record['y']] if record else None)
            reports.append(dict(passed=False,rotation=rotation,mirror=mirror,error=str(error)))
    passed=bool(reports) and all(r['passed'] for r in reports) and not problems
    return {**next((r for r in reports if 'terrain' in r),{}),'orientations':reports,'passed':passed,'valid':passed,'profile_present':bool(profile),'legacy_transform_limit':not bool(profile)},problems
