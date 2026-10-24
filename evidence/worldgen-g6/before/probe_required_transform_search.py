"""Bounded production-selection fixture for backtracking over legal transforms.

Two in-memory role candidates and two same-side assigned slots. No installed
definition, source, checkpoint or campaign is changed. A forced legal transform
order supplies an explicit feasibility witness; it is not ordinary sampling.
"""
from __future__ import annotations
import argparse
import contextlib
import copy
import io
import json
import os
from pathlib import Path
import sys
from unittest.mock import patch

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--source',type=Path,required=True)
parser.add_argument('--output',type=Path,required=True)
args=parser.parse_args()
os.environ.update(SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy',PYGAME_HIDE_SUPPORT_PROMPT='1')
sys.path.insert(0,str(args.source.resolve()/'roguelike'))
from engine.data_loader import DataLoader
from generation.context import GenerationError
from generation.placement import transform
from generation.structure_contract import compile_structure
from generation.structure_preview import preview
from generation.world_plan import Reservations,bands,settings
from generation.settlement_selection import populate_settlement,resolve

with contextlib.redirect_stdout(io.StringIO()):
    original=DataLoader(str(args.source.resolve()/'roguelike/data'))
data=copy.copy(original);data.structures=copy.deepcopy(original.structures)
data.settlement_profiles=copy.deepcopy(original.settlement_profiles)
# Add only exterior wall columns, shifting the original contents/door together.
# These 16x8 and 17x7 footprints fit the actual default 18-tile slot spacing.
def pad(raw,left,right):
    raw=copy.deepcopy(raw)
    raw['layers']=['#'*left+row+'#'*right for row in raw['layers']]
    raw['width']=len(raw['layers'][0])
    if 'decor_layer' in raw:
        raw['decor_layer']=[[None]*left+row+[None]*right for row in raw['decor_layer']]
    for row in raw.get('special_tiles',[]):
        row['x']+=left
        for child in row.get('spawn_table',[]):
            if 'x' in child:child['x']+=left
    for row in raw['placement']['entrances']+raw['placement']['targets']:row['x']+=left
    return raw

commercial=pad(original.structures['house_small_a'],3,3)
commercial['id']='market_stall_a'
commercial['placement']['rotations']=[0]
commercial['placement']['mirror_x']=True
commercial['placement']['buffer']=1
data.structures['market_stall_a']=commercial
residential=pad(original.structures['house_small_b'],5,4)
residential['placement']['rotations']=[0]
residential['placement']['mirror_x']=False
residential['placement']['buffer']=1
data.structures['house_small_b']=residential
profile=data.settlement_profiles['profiles']['roadside']
profile['roles']['commercial']=[dict(asset='market_stall_a',weight=1,max_per_settlement=2)]
profile['roles']['residential']=[dict(asset='house_small_b',weight=1,max_per_settlement=2)]

previews=[]
for role,raw in [('commercial',commercial),('residential',residential)]:
    compile_structure(raw,'ordinary_building',data,category=role)
    for mirror in ([False,True] if raw['placement']['mirror_x'] else [False]):
        moved=transform(raw,0,mirror);entry=moved['placement']['entrances'][0]
        report,_,_=preview(moved,'ordinary_building',data,category=role,expectations={
            'entry':dict(x=entry['x'],y=entry['y']),
            'targets':moved['placement']['targets']})
        previews.append(dict(role=role,mirror=mirror,passed=report['passed']))
        assert report['passed'],report['access']

def run(seed,mirror_first=False):
    c=settings(data)
    road=dict(id='assigned',width=3,points=[[0,21],[79,21]])
    road['rects']=bands(road['points'],3)
    settlement=dict(id='fixture',form='roadside',plots=[],civic=None)
    plan=dict(seed=seed,settings=c,routes=[road],plots=[],placements=[],dependencies={},
              selection=resolve(data),settlements=[settlement],diagnostics=[])
    authority=Reservations()
    for r in road['rects']:authority.add('assigned','road',r)
    # A preexisting narrow reservation clips only the taller commercial asset
    # at the second plot. The shorter residential buffer begins one row below.
    authority.add('fixed-prior-structure','structure',[43,9,46,10])
    slots=[(0,0,26,21,'S','assigned',0),(0,0,44,21,'S','assigned',1)]
    result=dict(seed=seed,forced_legal_mirror_first=mirror_first,
                slots=[dict(join=[s[2],s[3]],normal=s[4]) for s in slots])
    # The only patched operation in the witness is legal transform trial order.
    # Production fitting, reservations and required-role search stay unchanged.
    def mirrored_first(rng,rows):rows.sort(key=lambda row:not row[2])
    manager=patch('random.Random.shuffle',mirrored_first) if mirror_first else contextlib.nullcontext()
    try:
        with manager:populate_settlement(plan,authority,data,settlement,slots)
        result.update(accepted=True,placements=[{k:p[k] for k in ('asset','role','mirror','origin','footprint','clearance','approach','join')} for p in plan['placements']],diagnostics=plan['diagnostics'])
    except GenerationError as error:
        result.update(accepted=False,exception=type(error).__name__,message=str(error),
                      published_placements=len(plan['placements']),published_plots=len(plan['plots']))
    return result

rows=[run(seed) for seed in (0,20261023,29417)]
witness=run(0,True)
assert witness['accepted']
assert witness['placements'][0]['mirror'] is True
assert witness['placements'][0]['clearance'][2] <= witness['placements'][1]['clearance'][0]
out=dict(source_commit='6f255435f567b99f172e20c38ca2e2d660ff629e',
    scope='Small production settlement-selection/fitter fixture, not an ordinary shipped-world failure.',
    source_modified=False,personal_saves_used=False,previews=previews,
    fixture_geometry=dict(plot_spacing_tiles=18,commercial_size=[16,8],residential_size=[17,7],
                          prior_reserved_rectangle=[43,9,46,10],buffer_tiles=1),
    ordinary_rng_order=rows,feasible_transform_witness=witness,
    explanation='Required-role search branches over slots and assets. Each _plot call exposes only its first fitting transform, so it cannot revisit a legal earlier transform after a later required role fails.')
args.output.parent.mkdir(parents=True,exist_ok=True)
args.output.write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(out,indent=2))
