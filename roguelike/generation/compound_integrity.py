"""Replay exact narrow reservation permissions from reciprocal saved ownership."""
from generation.context import GenerationError
from generation.placement import entrance_cells


def replay_reservation(row,authority,registries):
    from generation.world_plan import bounds
    owner=row['owner'];purpose=row['purpose'];sid=owner if purpose=='envelope' else row.get('container')
    site=registries['sites'].get(sid)
    if site is None or site['kind']!='compound':raise GenerationError('compound reservation has foreign/missing parent')
    allowed=[sid]+site['paths']+[s['placement'] for s in site['slots'] if s['placement']]
    if owner not in allowed:raise GenerationError('compound reservation owner is not a declared parent member')
    base={'id','owner','purpose','rect'}
    if purpose=='envelope':
        if set(row)!=base|{'members','gate'} or row['members']!=allowed or row['gate']!=bounds(entrance_cells(site['gate'])):
            raise GenerationError('compound envelope has foreign or missing containment permission')
        authority.add(owner,purpose,row['rect'],members=allowed,gate=row['gate'])
    elif purpose=='path':
        path=registries['paths'][owner]
        if set(row)!=base|{'container'} or path['owner']!=sid:raise GenerationError('compound path ownership mismatch')
        authority.add(owner,purpose,row['rect'],(owner,*path['joins']),container=sid)
    elif purpose=='approach' and owner==sid:
        road=registries['routes'][site['attachment']['road']]
        if set(row)!=base|{'container','public_road','shared_path'} or row['public_road']!=road['id'] or row['shared_path']!=site['gate']['path']:
            raise GenerationError('compound external access permission mismatch')
        authority.add(owner,purpose,row['rect'],container=sid,public_road=road['id'],public_rects=road['rects'],shared_path=site['gate']['path'])
    else:
        p=registries['placements'][owner];path=registries['paths'][p['access']['path']]
        if p['parent']!=sid or path['owner']!=sid:raise GenerationError('compound private member/access mismatch')
        if purpose=='structure':
            if set(row)!=base|{'container'}:raise GenerationError('compound private buffer has unsupported permissions')
            authority.add(owner,purpose,row['rect'],container=sid)
        elif purpose=='approach':
            if set(row)!=base|{'container','public_road'} or row['public_road']!=path['id']:raise GenerationError('compound child access permission mismatch')
            authority.add(owner,purpose,row['rect'],(owner,),container=sid,public_road=path['id'],public_rects=path['rects'])
        else:raise GenerationError('unsupported compound reservation purpose')
