"""G7 ordinary mixed parents, complete children, geometry and real journey."""
from html import escape


def compound_svg(plan,site):
    from generation.world_plan import intersect
    from generation.placement import entrance_cells
    x,y=site['chunk'][0]*80,site['chunk'][1]*43;outer=[x,y,x+80,y+43]
    title=f'{site["id"]}: {site["recipe"]}; {site["attachment"]["road"]} segment {site["attachment"]["segment"]}; plan diagram'
    parts=[f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{x-2} {y-11} 84 65" width="1008"><rect x="{x-2}" y="{y-11}" width="84" height="65" fill="#18252b"/>',
           f'<text x="{x}" y="{y-7}" font-size="1.3" fill="white">{escape(title)}</text>',
           f'<text x="{x}" y="{y-4}" font-size="1.2" fill="white">Gold country road; blue common paths; teal private buffer; green buildings; red full doors; pink goals</text>']
    def box(r,color,opacity=.7,outline=False):
        a,b,c,d=r;parts.append(f'<rect x="{a}" y="{b}" width="{c-a}" height="{d-b}" fill="{"none" if outline else color}" stroke="{color}" stroke-width=".12" opacity="{opacity}"/>')
    for road in plan['routes']:
        for r in road['rects']:
            hit=intersect(r,outer)
            if hit:box(hit,'#dfbd63')
    box(site['envelope'],'#ced9cf',1,True);box(site['approach'],'#78b9ef')
    for path in plan['paths']:
        if path['owner']==site['id']:
            for r in path['rects']:box(r,'#78b9ef')
    for index,slot in enumerate(site['slots']):
        box(slot['buildable'],'#9890b9',.8,True)
        parts.append(f'<text x="{x}" y="{y+46+index*2}" font-size="1.15" fill="white">{escape(slot["id"]+": "+(slot["placement"] or slot["omission"]))}</text>')
    for p in plan['placements']:
        if p.get('parent')!=site['id']:continue
        for field,color in [('clearance','#357979'),('footprint','#63bc91'),('approach','#78b9ef')]:box(p[field],color)
        for e in p['entrances']:
            for a,b in entrance_cells(e):box([a,b,a+1,b+1],'#ef7766',1)
        for t in p['targets']:box([t['x'],t['y'],t['x']+1,t['y']+1],'#e1a2df',1)
    for a,b in entrance_cells(site['gate']):box([a,b,a+1,b+1],'#ffffff',1)
    jx,jy=site['attachment']['join'];parts.append(f'<circle cx="{jx+.5}" cy="{jy+.5}" r=".6" fill="white"/></svg>')
    return '\n'.join(parts)


if __name__=='__main__':
    from worldgen_g3_diagnostic import main
    raise SystemExit(main())
