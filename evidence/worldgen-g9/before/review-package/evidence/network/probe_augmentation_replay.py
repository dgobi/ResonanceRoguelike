"""In-memory feasibility probe, not a delivered G9 implementation.

Add the independent witness route to a copy of each retained G8 plan using current
route/crossing/reservation vocabulary. Test current exact validators. No game code
or campaign is changed. A real new policy still needs a new versioned contract.
"""
import argparse
import copy
from hashlib import sha256
import json
from pathlib import Path
import sys


def main():
    p=argparse.ArgumentParser();p.add_argument('--repo',type=Path,required=True);p.add_argument('--witnesses',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    repo=a.repo.resolve();sys.path.insert(0,str(repo/'roguelike'))
    from generation.world_plan import bands,cells,expand,intersect,validate_plan
    from check_macro_corridors import physical,physical_distance
    results=[]
    for witness in json.loads(a.witnesses.read_text())['plans']:
        seed=witness['seed'];raw=(repo/f'evidence/worldgen-g8/final-b/diagnostic/results/plan-{seed}.json').read_bytes();plan=json.loads(raw);candidate=copy.deepcopy(plan)
        rid='review-only-shortcut'
        road=dict(id=rid,a=witness['a'],b=witness['b'],required=False,travel_class='player-and-creature',kind='country',width=3,points=witness['candidate_tile_points'],rects=bands(witness['candidate_tile_points'],3),search_nodes=witness['candidate_expanded_nodes'])
        candidate['routes'].append(road)
        waters={}
        for rect in road['rects']:
            for row in plan['reservations']:
                if row['purpose']=='water' and (hit:=intersect(rect,row['rect'])):
                    waters.setdefault(row['owner'],[]).append(hit)
        for i,(water,rects) in enumerate(sorted(waters.items())):
            candidate['crossings'].append(dict(id=f'review-only-crossing-{i}',road=rid,water=water,kind='bridge',travel_class='player-and-creature',deck=rects,approaches=[expand(r,2) for r in rects]))
        extra_rows=[dict(id=f'review-only-reservation-{i}',owner=rid,purpose='road',rect=r) for i,r in enumerate(road['rects'])]
        # New infrastructure before old private rows lets old exact public-road
        # permissions replay. IDs/contents/order of old rows are not rewritten.
        insertion=next(i for i,r in enumerate(candidate['reservations']) if r['purpose']!='water')
        candidate['reservations'][insertion:insertion]=extra_rows
        road_cells=set().union(*(cells(r) for r in road['rects']))
        old_road_cells=set().union(*(cells(r) for road in plan['routes'] for r in road['rects']))
        new_cells=road_cells-old_road_cells
        protected_rects=[s['bounds'] for s in plan['settlements']]+[s['envelope'] for s in plan['sites'] if s['kind']=='compound']+[p['clearance'] for p in plan['placements']]+[p['approach'] for p in plan['placements']]+[s['approach'] for s in plan['sites'] if s['kind']=='compound']+[r for s in plan['public_spaces'] for r in s['rects']]
        protected=set().union(*(cells(r) for r in protected_rects))
        old_decks=set().union(*(cells(r) for c in plan['crossings'] for r in c['deck']))
        extra_decks=set().union(*(cells(r) for c in candidate['crossings'][len(plan['crossings']):] for r in c['deck'])) if waters else set()
        unchanged=[k for k in plan if k not in ('routes','crossings','reservations') and plan[k]==candidate[k]]
        preserved={k:plan[k]==[r for r in candidate[k] if not r['id'].startswith('review-only-')] for k in ('routes','crossings','reservations')}
        result=dict(seed=seed,source_sha256=sha256(raw).hexdigest(),new_road_cells=len(new_cells),new_cells_in_protected_rects=len(new_cells&protected),new_physical_deck_cells=len(extra_decks-old_decks),new_route_crossing_ownership_rows=len(waters),unchanged_top_level_subtrees=unchanged,preserved_original_records=preserved,notes='Validation uses current format-6 shape only as a feasibility probe. No policy or campaign is changed; no local scenes materialized.')
        nodes={n['id']:n for n in plan['nodes']}
        result['physical_union_tiles_after']=physical_distance(physical(candidate),tuple(nodes[witness['a']]['xy']),tuple(nodes[witness['b']]['xy']))
        result['physical_union_tiles_before']=witness['physical_union_tiles']
        result['physical_union_reduction_fraction']=1-result['physical_union_tiles_after']/result['physical_union_tiles_before']
        try:validate_plan(candidate,*candidate['world_size']);result['normal_validate_plan_passed']=True
        except Exception as error:result['normal_validate_plan_passed']=False;result['error']=f'{type(error).__name__}: {error}'
        appended=copy.deepcopy(candidate);appended['reservations']=copy.deepcopy(plan['reservations'])+extra_rows
        try:validate_plan(appended,*appended['world_size']);result['naive_append_passed']=True
        except Exception as error:result['naive_append_passed']=False;result['naive_append_error']=f'{type(error).__name__}: {error}'
        results.append(result)
    a.output.write_text(json.dumps(dict(schema=1,scope=__doc__,plans=results),indent=2)+'\n')
    for row in results:print(json.dumps(row))


if __name__=='__main__':main()
