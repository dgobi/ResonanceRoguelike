"""Exact-coordinate review figure; this draws evidence, not proposed art."""
import argparse
from collections import deque
import json
import os
from pathlib import Path
os.environ.setdefault('MPLCONFIGDIR','/tmp/resonance-review-matplotlib')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from matplotlib.lines import Line2D
from measure_country_network import graph_for


def path_for(graph,start,goal):
    parent={start:None};queue=deque([start])
    while queue:
        p=queue.popleft()
        if p==goal:break
        for q in sorted(graph[p]):
            if q not in parent:parent[q]=p;queue.append(q)
    path=[goal]
    while parent[path[-1]] is not None:path.append(parent[path[-1]])
    return path[::-1]


def corners(path):
    return [path[0]]+[b for a,b,c in zip(path,path[1:],path[2:]) if (b[0]-a[0],b[1]-a[1])!=(c[0]-b[0],c[1]-b[1])]+[path[-1]]


def main():
    p=argparse.ArgumentParser();p.add_argument('--repo',type=Path,required=True);p.add_argument('--witnesses',type=Path,required=True);p.add_argument('--replay',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    plan=json.loads((a.repo/'evidence/worldgen-g8/final-b/diagnostic/results/plan-20261023.json').read_text())
    witness=next(r for r in json.loads(a.witnesses.read_text())['plans'] if r['seed']==20261023)
    replay=next(r for r in json.loads(a.replay.read_text())['plans'] if r['seed']==20261023)
    nodes={n['id']:n for n in plan['nodes']};routes=[r for r in plan['routes'] if r['kind']=='country'];graph,_=graph_for(routes)
    current=corners(path_for(graph,tuple(nodes[witness['a']]['xy']),tuple(nodes[witness['b']]['xy'])))
    candidate=witness['candidate_tile_points'];plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10})
    fig=plt.figure(figsize=(14,10),facecolor='#f8fafc');ax=fig.add_axes((.075,.27,.88,.60),facecolor='#f8fafc')
    water_segments=[]
    for water in plan['waters']:
        for x,y,r,b in water['rects']:
            water_segments.append([(x,(y+b)/2),(r,(y+b)/2)] if r-x>b-y else [((x+r)/2,y),((x+r)/2,b)])
    ax.add_collection(LineCollection(water_segments,colors='#a6d3e3',linewidths=2,alpha=.65,zorder=1))
    ax.add_collection(LineCollection([r['points'] for r in routes],colors='#8994a4',linewidths=2.1,zorder=2))
    ax.plot(*zip(*current),color='#c97012',linewidth=4,zorder=3)
    ax.plot(*zip(*candidate),color='#087f8c',linewidth=3,linestyle=(0,(5,2.8)),zorder=4)
    labels={'start':'Start','landmark':'Landmark','capital-gateway':'Capital gateway',**{f'settlement-{i}':f'Town {i}' for i in range(4)}}
    offsets={'start':(-57,-18),'settlement-0':(10,-6),'settlement-1':(-70,-6),'settlement-2':(9,5),'settlement-3':(8,4),'capital-gateway':(-100,8),'landmark':(10,-6)}
    for key,label in labels.items():
        n=nodes[key];x,y=n['xy'];focus=key in (witness['a'],witness['b'])
        ax.scatter(x,y,s=70 if focus else 38,color='#0d3b46' if focus else '#273445',edgecolor='white',linewidth=1.4,zorder=5)
        ax.annotate(label,(x,y),xytext=offsets[key],textcoords='offset points',fontsize=10,weight='bold' if focus else 'normal',bbox=dict(boxstyle='round,pad=.25',fc='#f8fafc',ec='none',alpha=.92),zorder=6)
    ax.set(xlim=(0,10240),ylim=(5504,0),xlabel='World tile x',ylabel='World tile y')
    ax.set_aspect('equal');ax.grid(color='#e3e9ef',linewidth=.6,zorder=0)
    for spine in ax.spines.values():spine.set_color('#cbd5e1')
    fig.text(.075,.955,'A bounded shortcut can remove a large country-road detour',fontsize=20,weight='bold',color='#132b3b')
    fig.text(.075,.922,'Seed 20261023 · G8 retained final plan · conservative feasibility witness, not an installed road',fontsize=11,color='#44576b')
    legend=[Line2D([0],[0],color='#8994a4',lw=2,label='Existing country network'),Line2D([0],[0],color='#c97012',lw=4,label='Existing shortest centerline path'),Line2D([0],[0],color='#087f8c',lw=3,ls='--',label='Conservative candidate corridor'),Line2D([0],[0],color='#a6d3e3',lw=2,label='Saved waterways')]
    fig.legend(handles=legend,loc='lower left',bbox_to_anchor=(.07,.18),ncol=4,frameon=False,fontsize=9)
    columns=[(.075,'CURRENT ROAD TRAVEL',f'{witness["physical_union_tiles"]:,} tiles'),(.38,'WITH WITNESS CORRIDOR',f'{replay["physical_union_tiles_after"]:,} tiles'),(.685,'ADDED COUNTRY CENTERLINE',f'{witness["candidate_new_unique_centerline_tiles"]:,} tiles  (+{100*witness["candidate_new_centerline_fraction_of_existing"]:.1f}%)')]
    for x,header,value in columns:
        fig.text(x,.153,header,fontsize=9,weight='bold',color='#60758a')
        fig.text(x,.122,value,fontsize=20,weight='bold',color='#132b3b')
    fig.text(.075,.079,'Travel figures use shortest four-neighbour paths on the full-width road/deck/access union; the orange line shows its centerline analogue.',fontsize=9,color='#44576b')
    fig.text(.075,.059,'The candidate preserves existing places and roads, adds no physical bridge deck, and passes current plan validation. It has not been materialized or walked.',fontsize=9,color='#44576b')
    fig.text(.075,.039,'Source: evidence/worldgen-g8/final-b/diagnostic/results/plan-20261023.json; independent scripts and exact source hashes accompany this figure.',fontsize=8,color='#60758a')
    a.out.parent.mkdir(parents=True,exist_ok=True)
    fig.savefig(a.out.with_suffix('.png'),dpi=150,facecolor=fig.get_facecolor())
    fig.savefig(a.out.with_suffix('.svg'),facecolor=fig.get_facecolor())
    plt.close(fig)


if __name__=='__main__':main()
