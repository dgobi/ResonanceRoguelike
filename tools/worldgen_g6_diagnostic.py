"""G6 installed-policy plans, complete sites, physical network and real journey."""
from html import escape


def site_svg(plan,site):
    from generation.world_plan import intersect
    p=next(p for p in plan['placements'] if p['id']==site['placement'])
    x,y=site['chunk'][0]*80,site['chunk'][1]*43;rect=[x,y,x+80,y+43]
    title=f'{site["id"]}: {p["asset"]}; {p["road"]} segment {site["attachment"]["segment"]}; plan diagram'
    parts=[f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{x-2} {y-10} 84 58" width="1008"><rect x="{x-2}" y="{y-10}" width="84" height="58" fill="#18252b"/>',
           f'<text x="{x}" y="{y-6}" font-size="1.5" fill="white">{escape(title)}</text>',
           f'<text x="{x}" y="{y-3}" font-size="1.4" fill="white">Gold parent; teal buffer; green footprint; blue access; white join; red entrances; pink goals</text>']
    def box(r,color,opacity=1):
        a,b,c,d=r;parts.append(f'<rect x="{a}" y="{b}" width="{c-a}" height="{d-b}" fill="{color}" opacity="{opacity}"/>')
    for road in plan['routes']:
        for r in road['rects']:
            hit=intersect(r,rect)
            if hit:box(hit,'#dfbd63' if road['id']==p['road'] else '#716b56')
    for key,color in [('clearance','#357979'),('footprint','#63bc91'),('approach','#78b9ef')]:box(p[key],color,.7)
    for row in p['entrances']:box([row['x'],row['y'],row['x']+1,row['y']+1],'#ef7766')
    for row in p['targets']:box([row['x'],row['y'],row['x']+1,row['y']+1],'#e1a2df')
    parts.append(f'<circle cx="{p["join"][0]+.5}" cy="{p["join"][1]+.5}" r=".5" fill="white"/>')
    plot=next(row for row in plan['plots'] if row['id']==site['plot'])
    parts.append(f'<text x="{x}" y="{y+46}" font-size="1.3" fill="white">Prior fit rejections: {escape(str(plot["rejected"]))}</text></svg>')
    return '\n'.join(parts)


if __name__=='__main__':
    from worldgen_g3_diagnostic import main
    raise SystemExit(main())
