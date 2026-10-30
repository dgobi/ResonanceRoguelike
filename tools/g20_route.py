"""Bounded revealed route planning, separate from the ordinary expedition save.

Full-state assistance materializes disposable preview scenes only. The journey
must replay every crossing and local step normally; these maps are never installed
into that campaign. No new selector or runtime launcher is introduced.
"""
import argparse
from collections import deque
import contextlib
import heapq
import json
import os
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]


def plan(e,targets):
    import numpy as np
    from generation.access import enterable
    maps={};labels={}
    start_chunk=(e.world_x,e.world_y)
    def get(wx,wy):
        if (wx,wy) not in maps:
            assert len(maps)<128,'Finite 128-scene route preview bound'
            prepared=e._prepare_destination(wx,wy);assert prepared is not None,(wx,wy)
            m=prepared[0];maps[wx,wy]=m
            label=np.full((m.width,m.height),-1,dtype=int);component=0
            for x in range(m.width):
                for y in range(m.height):
                    if label[x,y]>=0 or not enterable(m,(x,y),e.data):continue
                    label[x,y]=component;queue=deque([(x,y)])
                    while queue:
                        a,b=queue.popleft()
                        for dx in (-1,0,1):
                            for dy in (-1,0,1):
                                xy=a+dx,b+dy
                                if m.in_bounds(*xy) and label[xy]<0 and enterable(m,xy,e.data):label[xy]=component;queue.append(xy)
                    component+=1
            labels[wx,wy]=label
        return maps[wx,wy],labels[wx,wy]
    m,label=get(*start_chunk);start=(*start_chunk,int(label[e.surface_return_x,e.surface_return_y]))
    answers=[]
    for tx,ty,sid in targets:
        m,label=get(tx,ty)
        sub=next(s for s in e.world_map.get(tx,ty).submaps if s.submap_id==sid)
        goal=(tx,ty,int(label[sub.surface_x,sub.surface_y]));assert goal[2]>=0
        heuristic=lambda x,y:abs(x-tx)*80+abs(y-ty)*43
        best={start:0};parents={start:None};todo=[(heuristic(*start_chunk),0,start)];edge_records={};found=None
        while todo:
            _,cost,node=heapq.heappop(todo)
            if cost!=best[node]:continue
            if node==goal:found=node;break
            wx,wy,component=node;m,label=get(wx,wy)
            for dx,dy in ((-1,0),(1,0),(0,-1),(0,1)):
                nx,ny=wx+dx,wy+dy
                if not e.world_map.in_bounds(nx,ny):continue
                if not (min(start_chunk[0],tx)-2<=nx<=max(start_chunk[0],tx)+2 and min(start_chunk[1],ty)-2<=ny<=max(start_chunk[1],ty)+2):continue
                edge=([(m.width-1 if dx>0 else 0,y) for y in range(m.height)] if dx else [(x,m.height-1 if dy>0 else 0) for x in range(m.width)])
                edge=[xy for xy in edge if label[xy]==component]
                if not edge:continue
                other,other_label=get(nx,ny);groups={}
                for x,y in edge:
                    arrival=(0 if dx>0 else other.width-1,y) if dx else (x,0 if dy>0 else other.height-1)
                    c=int(other_label[arrival])
                    if c>=0:groups.setdefault(c,[]).append([[x,y],list(arrival)])
                for c,pairs in groups.items():
                    target=(nx,ny,c);new=cost+(80 if dx else 43)
                    if new<best.get(target,float('inf')):
                        best[target]=new;parents[target]=node;edge_records[target]=dict(source=[wx,wy],destination=[nx,ny],direction=[dx,dy],pairs=pairs)
                        heapq.heappush(todo,(new+heuristic(nx,ny),new,target))
        if found is None:answers.append(dict(target=[tx,ty,sid],reachable=False));continue
        legs=[]
        while parents[found] is not None:legs.append(edge_records[found]);found=parents[found]
        legs.reverse();answers.append(dict(target=[tx,ty,sid],reachable=True,estimate=best[goal],legs=legs,entrance=[sub.surface_x,sub.surface_y]))
    feasible=[r for r in answers if r['reachable']];assert feasible,'No bounded connected candidate route'
    chosen=min(feasible,key=lambda r:(r['estimate'],r['target']))
    return dict(scope='Revealed static preview in a disposable clone; no preview scene or actor is transferred to the expedition. Exact reciprocal edge pairs, ordinary eight-way/openable-door/decor access. Dynamic actors remain active during replay.',start=list(start_chunk),previews=len(maps),candidates=answers,chosen=chosen)


def main():
    p=argparse.ArgumentParser();p.add_argument('--checkpoint',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    sys.path[:0]=[str(ROOT/'roguelike'),str(ROOT/'tools/critical_fix_regressions/tests')]
    os.environ.update(SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy',PYGAME_HIDE_SUPPORT_PROMPT='1')
    from test_effect_persistence import make_engine,load_data
    from g12_journey import install_checkpoint
    with tempfile.TemporaryDirectory(prefix='g20-route-preview-') as root,patch('engine.save_manager.SAVE_DIR',Path(root)),contextlib.redirect_stdout(sys.stderr):
        install_checkpoint(a.checkpoint,root);e=make_engine(load_data());assert e.save_manager.load(e),e.save_manager.last_error
        r=plan(e,[(68,98,'submap_68_98_0'),(78,100,'submap_78_100_0')])
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(r,indent=2)+'\n')
    print(json.dumps(dict(chosen=r['chosen']['target'],estimate=r['chosen']['estimate'],legs=len(r['chosen']['legs']),previews=r['previews'],candidates=[dict(target=x['target'],reachable=x['reachable'],estimate=x.get('estimate')) for x in r['candidates']]),indent=2))


if __name__=='__main__':main()
