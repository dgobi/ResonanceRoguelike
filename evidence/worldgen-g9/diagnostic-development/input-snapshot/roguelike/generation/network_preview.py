"""Safe disposable network analysis and exact-coordinate overlay exports."""
import copy
from html import escape
import io
import random
import time
from generation.country_network import baseline,policy
from generation.network_metrics import terminals,centerline_edges,topology,physical_cells,distances,pair_rows,road_cells
from generation.placement import digest


def comparison(plan):
    old=baseline(plan);nodes=terminals(plan);before=distances(physical_cells(old),nodes);after=distances(physical_cells(plan),nodes)
    original=centerline_edges(r for r in old['routes'] if r['kind']=='country');current=centerline_edges(r for r in plan['routes'] if r['kind']=='country')
    old_topology=topology(original,[n['xy'] for n in nodes]);new_topology=topology(current,[n['xy'] for n in nodes])
    # Large run point lists remain in the explicit diagnostic graph only when
    # requested by the release diagnostic. Owner reports retain reconciled counts.
    for value in (old_topology,new_topology):value['contracted_runs']=len(value.pop('runs'))
    old_decks=road_cells([dict(rects=c['deck']) for c in old['crossings']]);new_decks=road_cells([dict(rects=c['deck']) for c in plan['crossings']])
    return dict(primary_nodes=nodes,pair_denominator=len(before),before=pair_rows(old,before),after=pair_rows(plan,after),
                all_primary_distances_nonincreasing=all(after[k]<=v for k,v in before.items()),baseline_identity=digest(old),
                baseline_country=old_topology,augmented_country=new_topology,added_unique_centerline_steps=len(current-original),
                new_full_width_road_cells=len(road_cells(plan['routes'])-road_cells(old['routes'])),new_physical_bridge_cells=len(new_decks-old_decks),
                crossing_ownership_records_added=len(plan['crossings'])-len(old['crossings']),
                physical_components_before=len(__import__('generation.road_network',fromlist=['PhysicalRoads']).PhysicalRoads(old).component_sizes),
                physical_components_after=len(__import__('generation.road_network',fromlist=['PhysicalRoads']).PhysicalRoads(plan).component_sizes),
                units='Construction: distinct cardinal unit country-centerline edges. Travel: shortest four-neighbour tile steps on full-width road/deck/access. Manhattan is only a lower bound. Graph cut edges are not river bridge objects.')


def preview(data,seed,override=None,config=None):
    from generation.world_gen import generate_world
    from world.world_map import WorldMap
    bound=copy.copy(data);bound.country_network=policy(override if override is not None else data.country_network)
    effective=copy.deepcopy(config if config is not None else data.g3_config)
    if effective['version']!=4:raise ValueError('network preview requires complete current planning settings version 4')
    world=WorldMap(128,128);world.seed=seed;metrics={};start=time.perf_counter();generate_world(world,bound,random.Random(seed),planning_settings=effective,planning_metrics=metrics)
    return dict(passed=True,kind='disposable geometry-only network preview; no campaign or policy installation',seed=seed,policy=bound.country_network,plan=world.plan,
                status=world.plan['network']['outcome'],planning_seconds=time.perf_counter()-start,materialized_scenes=sum(c.visited for c in world.chunks.values()),
                network=metrics['network'],comparison=comparison(world.plan))


def overlay_svg(plan):
    scale=.1;width=plan['world_size'][0]*80*scale;height=plan['world_size'][1]*43*scale
    n=plan['network'];parts=[f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height+85}" width="1024"><rect width="100%" height="100%" fill="#15242b"/>']
    for water in plan['waters']:
        for a,b,c,d in water['rects']:parts.append(f'<rect x="{a*scale}" y="{b*scale}" width="{(c-a)*scale}" height="{(d-b)*scale}" fill="#326b8b"/>')
    for r in plan['routes']:
        points=' '.join(f'{x*scale},{y*scale}' for x,y in r['points']);color='#61e1bc' if r.get('network_role') else '#c8ac78'
        parts.append(f'<polyline points="{points}" fill="none" stroke="{color}" stroke-width="{2 if r.get("network_role") else .8}"><title>{escape(r["id"])}</title></polyline>')
    for node in terminals(plan):
        x,y=node['xy'];parts.append(f'<circle cx="{x*scale}" cy="{y*scale}" r="3" fill="#edf3dd"/><text x="{x*scale+5}" y="{y*scale-5}" font-size="10" fill="#edf3dd">{escape(node["id"])}</text>')
    labels=[f'G9 seed {plan["seed"]} | {n["outcome"]} | gold: intact baseline | green: accepted connection (including reused portions)',
            f'{len(n["accepted"])} / {n["policy"]["max_shortcuts"]} optional connections; {n["added_unique_steps"]} / {n["construction_limit_steps"]} new unique centerline steps; no new physical bridge cells',
            f'Construction denominator {n["baseline_unique_steps"]} baseline steps. Travel uses four-neighbour road/deck/access cells, not macro hops.',
            'Exact resolved geometry diagram; not a populated gameplay screenshot. See JSON for fixed endpoints, all pairs and bounded rejection reasons.']
    for i,line in enumerate(labels):parts.append(f'<text x="12" y="{height+18+i*18}" fill="#edf3dd" font-family="sans-serif" font-size="11">{escape(line)}</text>')
    return '\n'.join(parts+['</svg>'])


def overlay_png(plan):
    import pygame
    pygame.font.init();width=1024;height=round(plan['world_size'][1]*43/10);canvas=pygame.Surface((width,height+70));canvas.fill('#15242b')
    for water in plan['waters']:
        for a,b,c,d in water['rects']:pygame.draw.rect(canvas,'#326b8b',(a/10,b/10,max(1,(c-a)/10),max(1,(d-b)/10)))
    for r in plan['routes']:pygame.draw.lines(canvas,'#61e1bc' if r.get('network_role') else '#c8ac78',False,[(x/10,y/10) for x,y in r['points']],2 if r.get('network_role') else 1)
    font=pygame.font.Font(None,16)
    for n in terminals(plan):
        x,y=n['xy'];pygame.draw.circle(canvas,'#edf3dd',(x/10,y/10),3);canvas.blit(font.render(n['id'],True,'#edf3dd'),(x/10+5,y/10-12))
    n=plan['network']
    for i,text in enumerate([f'G9 seed {plan["seed"]}: {n["outcome"]}. Gold: intact G8 baseline. Green: accepted connections, including reused portions.',f'New unique centerline: {n["added_unique_steps"]} / {n["construction_limit_steps"]} budget. No new physical bridges.', 'Exact-coordinate plan diagram; see JSON for four-neighbour physical distances and candidate decisions.']):canvas.blit(font.render(text,True,'#edf3dd'),(12,height+10+i*18))
    output=io.BytesIO();pygame.image.save(canvas,output,'network.png');return output.getvalue()
