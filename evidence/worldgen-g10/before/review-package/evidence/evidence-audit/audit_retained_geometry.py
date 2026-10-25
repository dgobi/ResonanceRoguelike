"""Independently measure retained G9 plans without importing game code."""
import argparse
import collections
import copy
import hashlib
import json
from pathlib import Path

ap=argparse.ArgumentParser();ap.add_argument('--repo',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args()
root=a.repo.resolve();out=a.output.resolve();out.parent.mkdir(parents=True,exist_ok=True);e=root/'evidence/worldgen-g9';diagnostic=json.loads((e/'final-b/diagnostic/results/run.json').read_text())
def read(p):return json.loads(p.read_text())
def sha(b):return hashlib.sha256(b).hexdigest()
def identity(p):return sha(json.dumps(p,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode())
def rects_cells(rects):return {(x,y) for x0,y0,x1,y1 in rects for x in range(x0,x1) for y in range(y0,y1)}
def road(p):return rects_cells(r for route in p['routes'] for r in route['rects'])
def deck(p):return rects_cells(r for crossing in p['crossings'] for r in crossing['deck'])
def physical(p):
    return road(p)|deck(p)|rects_cells([v['approach'] for v in p['placements']]+[r for path in p['paths'] for r in path['rects']]+[s['approach'] for s in p['sites'] if s['kind']=='compound'])
def edges(p):
    result=set()
    for route in p['routes']:
        if route['kind']!='country':continue
        for (x,y),(u,v) in zip(route['points'],route['points'][1:]):
            assert x==u or y==v
            if x==u:result.update(((x,q),(x,q+1)) for q in range(min(y,v),max(y,v)))
            else:result.update(((q,y),(q+1,y)) for q in range(min(x,u),max(x,u)))
    return result
def distances(p):
    cells=physical(p);nodes=sorted((v for v in p['nodes'] if v['id'] in ('start','capital-gateway','landmark') or v['id'].startswith('settlement-')),key=lambda v:v['id']);result={}
    for i,node in enumerate(nodes[:-1]):
        source=tuple(node['xy']);pending={tuple(v['xy']):v['id'] for v in nodes[i+1:]};seen={source:0};queue=collections.deque([source]);assert source in cells
        while queue and pending:
            point=queue.popleft();d=seen[point]
            if point in pending:result['|'.join(sorted((node['id'],pending.pop(point))))]=d
            x,y=point
            for q in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)):
                if q in cells and q not in seen:seen[q]=d+1;queue.append(q)
        assert not pending
    return result
rows=[]
for seed in (0,20261023,29417):
    original=read(e/f'before/baseline/results/plan-{seed}.json');final=read(e/f'final-b/diagnostic/results/plan-{seed}.json');saved=read(e/f'final-b/diagnostic/results/baseline-plan-{seed}.json');declared=next(r for r in diagnostic['g9_network'] if r['seed']==seed)
    q=copy.deepcopy(final);accepted={v['route'] for v in q.pop('network')['accepted']}
    for key,field in [('routes','id'),('crossings','road'),('reservations','owner')]:q[key]=[v for v in q[key] if v[field] not in accepted]
    q['version']=6;q['generation_revision']='wg8';q['settings']['version']=3;q['settings'].pop('country_network_version')
    assert q==original==saved
    before,after=distances(original),distances(final);cmp=declared['comparison'];declared_before={v['id']:v['physical_steps'] for v in cmp['before']};declared_after={v['id']:v['physical_steps'] for v in cmp['after']}
    assert before==declared_before and after==declared_after and all(after[k]<=v for k,v in before.items())
    old_edges,new_edges=edges(original),edges(final);added=len(new_edges-old_edges);new_roads=len(road(final)-road(original));new_decks=len(deck(final)-deck(original))
    assert added==cmp['added_unique_centerline_steps'] and new_roads==cmp['new_full_width_road_cells'] and new_decks==cmp['new_physical_bridge_cells']
    rows.append(dict(seed=seed,baseline_exact=True,baseline_identity=identity(original),current_identity=identity(final),pairs=len(before),all_pair_distances_match=True,all_distances_nonincreasing=True,baseline_unique_edges=len(old_edges),added_unique_edges=added,added_fraction=added/len(old_edges),new_full_width_road_cells=new_roads,new_physical_bridge_cells=new_decks,accepted_routes=sorted(accepted),named_pair=dict(before=before.get('capital-gateway|settlement-1'),after=after.get('capital-gateway|settlement-1')),before=before,after=after))
omissions=read(e/'omitted-disposable-saves.json');omission_map={v['path']:v for v in omissions['files']};missing=[];issues=[]
for gate in read(e/'release-summary.json')['gates']:
    receipt_path=e/gate['receipt'];receipt=read(receipt_path)
    for name,v in receipt['outputs'].items():
        p=receipt_path.parent/name
        if p.is_file():continue
        key=p.relative_to(root).as_posix();missing.append(key)
        if omission_map.get(key)!={'path':key,**v}:issues.append(key)
result=dict(scope='Independent analysis of retained JSON plans; no game code imported, no scenes or campaign created.',plans=rows,omissions=dict(indexed_files=len(omissions['files']),indexed_bytes=sum(v['bytes'] for v in omissions['files']),declared_bytes=omissions['bytes'],missing_gate_outputs=len(missing),all_missing_gate_output_metadata_matches_index=not issues,issues=issues))
assert sum(v['bytes'] for v in omissions['files'])==omissions['bytes'] and not issues
out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({**result,'plans':[{k:v for k,v in row.items() if k not in ('before','after')} for row in rows]},indent=2))
