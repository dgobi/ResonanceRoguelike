"""G4 wrapper: three declared ordinary seeds, complete scene checks and journey."""
from collections import Counter
from html import escape


def conditional_counts(plan,data):
    from generation.placement import transform
    owners={s['id']:s['form'] for s in plan['settlements']};owners['landmark']='landmark'
    placements={p['id']:p for p in plan['placements']}; slots=Counter();outcomes=Counter();reasons=Counter()
    for plot in plan['plots']:
        form=owners[plot['owner']];normal=plot['normal'];slots[form,normal,plot['status']]+=1
        if plot['placement']:
            p=placements[plot['placement']];outcomes[form,normal,p['asset'],p['rotation'],p['mirror'],'accepted']+=1
        for r in plot['rejected']:
            outcomes[form,normal,r['asset'],r['rotation'],r.get('mirror',False),'rejected']+=1
            reasons[form,normal,r['reason']]+=1
    eligible=[]
    for context,pool in plan['settings']['pools'].items():
        for asset in pool:
            raw=data.structures[asset];profile=raw['placement']
            for normal in 'NESW':
                count=sum(any(e['required'] and e['normal']==normal for e in transform(raw,r,m)['placement']['entrances'])
                          for r in profile['rotations'] for m in ((False,True) if profile['mirror_x'] else (False,)))
                eligible.append(dict(context=context,asset=asset,normal=normal,eligible_transforms_per_slot=count))
    return {'denominator':'slots: all proposed slots. candidate rows: attempted eligible transforms, terminating at first success; zeros retained, not a frequency estimate.',
            'eligibility':eligible,
            'slots':[dict(form=f,normal=n,status=s,count=slots[f,n,s]) for f in ('grid','roadside','landmark') for n in 'NESW' for s in ('occupied','vacant-garden')],
            'candidate_trials':[dict(form=f,normal=n,asset=a,rotation=r,mirror=m,status=s,count=outcomes[f,n,a,r,m,s])
                                for f in ('grid','roadside','landmark') for n in 'NESW' for a in sorted(set(p['asset'] for p in plan['placements'])|{r['asset'] for p in plan['plots'] for r in p['rejected']})
                                for r in (0,90,180,270,None) for m in (False,True,None) for s in ('accepted','rejected')],
            'reasons':[dict(form=k[0],normal=k[1],reason=k[2],count=v) for k,v in sorted(reasons.items())]}


def detail_svg(plan,settlement):
    from generation.world_plan import intersect
    x,y,x1,y1=settlement['bounds'];rect=[x,y,x1,y1]
    parts=[f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{x-2} {y-9} {x1-x+4} {y1-y+12}" width="960"><rect x="{x-2}" y="{y-9}" width="100%" height="100%" fill="#18252b"/>',
           f'<text x="{x}" y="{y-3}" fill="white" font-size="3">{settlement["form"]}: plan diagnostic; gold roads, green occupied, red vacant, blue approaches</text>']
    def box(r,color,opacity=1):
        a,b,c,d=r;parts.append(f'<rect x="{a}" y="{b}" width="{c-a}" height="{d-b}" fill="{color}" opacity="{opacity}"/>')
    for road in plan['routes']:
        for r in road['rects']:
            if (hit:=intersect(r,rect)):box(hit,'#d4bc72')
    for plot in plan['plots']:
        if plot['owner']!=settlement['id']:continue
        parts.append('<g><title>'+escape(plot['id']+' role='+plot.get('role','historical')+': '+str(plot['rejected']))+'</title>')
        if plot['placement']:
            p=next(p for p in plan['placements'] if p['id']==plot['placement']);box(p['approach'],'#81c8ea',.6);box(p['footprint'],'#68bd92')
            parts.append(f'<circle cx="{p["join"][0]+.5}" cy="{p["join"][1]+.5}" r=".8" fill="white"/>')
            parts.append(f'<text x="{p["footprint"][0]}" y="{p["footprint"][1]+2}" fill="#07130d" font-size="1.8">{escape(p.get("role",""))}</text>')
            parts.append(f'<text x="{p["footprint"][0]}" y="{p["footprint"][1]+4}" fill="#07130d" font-size="1.4">{escape(p["asset"])}</text>')
        else:box(plot['buildable'],'#d37b78',.18)
        parts.append('</g>')
    return '\n'.join(parts+['</svg>'])


if __name__=='__main__':
    from worldgen_g3_diagnostic import main
    raise SystemExit(main())
