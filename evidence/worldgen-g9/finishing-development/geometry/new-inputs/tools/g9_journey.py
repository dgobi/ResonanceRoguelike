"""Real-handler shortcut, old-corridor and fixed-endpoint itinerary extension."""
import time
from generation.country_network import baseline
from generation.road_network import PhysicalRoads,corners


def country(e,route,position,report):
    plan=e.world_map.plan;old=baseline(plan);network=PhysicalRoads(plan);backbone=PhysicalRoads(old);origin=position();runs=[]
    nodes={n['id']:n['xy'] for n in plan['nodes']}
    def travel(graph,a,b,label):
        path=graph.path(a,b);steps=report['steps'];boundaries=len(report['crossings']);start=time.perf_counter();visited=sum(c.visited for c in e.world_map.chunks.values())
        route(dict(id=label,points=corners(path)))
        assert position()==tuple(b)
        result=dict(label=label,start=a,end=b,seconds=time.perf_counter()-start,newly_visited_scenes=sum(c.visited for c in e.world_map.chunks.values())-visited,physical_four_neighbour_steps=len(path)-1,movement_inputs=report['steps']-steps,boundary_inputs=len(report['crossings'])-boundaries)
        runs.append(result);return result
    for accepted in plan['network']['accepted']:
        new=next(r for r in plan['routes'] if r['id']==accepted['route'])
        travel(network,position(),nodes[new['a']],'to-shortcut-start')
        for reverse in (False,True):
            count=report['steps'];crossings=len(report['crossings']);route(new,reverse=reverse)
            runs.append(dict(label='accepted-reverse' if reverse else 'accepted-forward',route=new['id'],movement_inputs=report['steps']-count,boundary_inputs=len(report['crossings'])-crossings,actual_complete_route=True))
        travel(backbone,nodes[new['a']],nodes[new['b']],'surviving-original-country-corridor')
    # Fixed named pair, same endpoints and same gameplay handler on both unions.
    # The baseline union is derived from the exact preserved G8 records; scenes
    # in this full coverage journey use G9 creation and may already be cached.
    a,b=nodes['settlement-1'],nodes['capital-gateway']
    travel(network,position(),a,'to-comparable-start')
    before=travel(backbone,a,b,'fixed-pair-original')
    after=travel(network,b,a,'fixed-pair-augmented-reverse')
    travel(network,position(),origin,'resume-inherited-journey')
    return dict(passed=True,runs=runs,fixed_pair=dict(before=before,after=after),
                controls='No positioning or teleports. Inherited real movement/door/boundary handlers; invincible player, stationary native actors, paused AI/survival. Local handler routes may use diagonals; physical BFS counts remain four-neighbour. Baseline itinerary uses exactly preserved G8 road geometry in G9-created scenes. Both directions and the surviving original corridor are actually walked; this is separate from pre-edit G8 journey timing.')
