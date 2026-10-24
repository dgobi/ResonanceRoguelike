"""Bounded fresh-selection ordering probe; no source or campaign changes."""
from __future__ import annotations
import argparse
import contextlib
import copy
import io
import json
import os
from pathlib import Path
import sys

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--source',type=Path,required=True)
parser.add_argument('--output',type=Path,required=True)
args=parser.parse_args()
os.environ.update(SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy',PYGAME_HIDE_SUPPORT_PROMPT='1')
sys.path.insert(0,str(args.source.resolve()/'roguelike'))
from engine.data_loader import DataLoader
from generation.world_plan import Reservations,bands,settings
from generation.settlement_selection import populate_settlement,resolve
with contextlib.redirect_stdout(io.StringIO()):
    original=DataLoader(str(args.source.resolve()/'roguelike/data'))

def run(reverse):
    data=copy.copy(original)
    data.settlement_profiles=copy.deepcopy(original.settlement_profiles)
    if reverse:
        for rows in data.settlement_profiles['profiles']['roadside']['roles'].values():
            rows.reverse()
    road=dict(id='assigned',width=3,points=[[0,21],[79,21]])
    road['rects']=bands(road['points'],3)
    settlement=dict(id='fixture',form='roadside',plots=[],civic=None)
    plan=dict(seed=20261023,settings=settings(data),routes=[road],plots=[],placements=[],dependencies={},
              selection=resolve(data),settlements=[settlement],diagnostics=[])
    authority=Reservations()
    for rect in road['rects']:authority.add('assigned','road',rect)
    slots=[(0,0,26,21,'S','assigned',0),(0,0,26,21,'N','assigned',1),
           (0,0,44,21,'S','assigned',2),(0,0,44,21,'N','assigned',3)]
    populate_settlement(plan,authority,data,settlement,slots)
    return dict(reversed_eligible_list_order=reverse,placements=[
        {k:p[k] for k in ('asset','rotation','mirror','origin','required','role')}
        for p in plan['placements']])

results=[run(False),run(True)]
out=dict(scope='Bounded production-selection fixture; only role entry list ordering changes, no weight/membership/geometry change.',
         source_commit='6f255435f567b99f172e20c38ca2e2d660ff629e',results=results,
         required_choices_equal=[[p['asset'] for p in r['placements'] if p['required']] for r in results][0]
         ==[[p['asset'] for p in r['placements'] if p['required']] for r in results][1])
args.output.parent.mkdir(parents=True,exist_ok=True)
args.output.write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(out,indent=2))
