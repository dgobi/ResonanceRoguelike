"""Reservation-aware functional passes on finalized shared infrastructure."""
from generation.context import GenerationError


def dress(m, chunk, world, data, context, native, spawn):
    from generation.region_gen import _scatter_dead_wood,_scatter_flint,_scatter_clay,_place_waystones
    from generation.access import reachable
    from generation.decor_utils import place_decor
    from world.world_map import RegionType
    reserved=set(m.protected_cells)
    for xy in m.submap_links:
        reserved.update((xy[0]+dx,xy[1]+dy) for dx in (-1,0,1) for dy in (-1,0,1))
    def allowed(x,y):
        return ((x,y) not in reserved and (x,y) not in m.decor and
                (x,y) not in m.floor_objects and (x,y) not in m.container_state and m.walkable[x,y])
    start=(chunk.wx,chunk.wy)==(world.start_wx,world.start_wy)
    civic=bool(native and native['waystone'])
    specs=[]; waystone=None
    if chunk.region_type not in (RegionType.TOWN,RegionType.CAPITAL):
        _scatter_dead_wood(m,data.terrain,context.rng('dead-wood'),allowed=allowed)
        rate=data.biomes.get(chunk.biome_id,{}).get('flint_scatter_rate',0)
        if rate: _scatter_flint(m,data.terrain,context.rng('flint'),rate,allowed=allowed)
        _scatter_clay(m,data.terrain,context.rng('river-clay'),allowed=allowed)
        # Count physical sides once, regardless of coincident route records.
        sides={side for x,y in m.road_cells for side,hit in
               (('W',x==0),('E',x==m.width-1),('N',y==0),('S',y==m.height-1)) if hit}
        if not start:
            _place_waystones(m,data.terrain,chunk,context.rng('road-waystones'),allowed=allowed,road_edges=sorted(sides))
    if start or civic:
        reached=reachable(m,spawn,data)
        candidates=[]
        for x in range(1,m.width-1):
            for y in range(1,m.height-1):
                if not allowed(x,y) or (x,y) not in reached: continue
                if not any((x+dx,y+dy) in m.road_cells for dx,dy in ((1,0),(-1,0),(0,1),(0,-1))): continue
                if civic and (not allowed(x+1,y) or (x+1,y) not in reached): continue
                candidates.append((abs(x-m.width//2)+abs(y-m.height//2),x,y))
        # A start without a road still needs its reachable interaction.
        if start and not candidates:
            candidates=[(abs(x-spawn[0])+abs(y-spawn[1]),x,y) for x,y in sorted(reached)
                        if 0<x<m.width-1 and 0<y<m.height-1 and allowed(x,y)]
        if not candidates:
            raise GenerationError('required starting/town waystone has no legal reachable site in saved geometry')
        _,x,y=min(candidates); waystone=(x,y)
        place_decor(m,x,y,'waystone_plinth'); reserved.add(waystone)
        if civic:
            specs.append(dict(kind='item',item_id='lab_note',text_id='waystone_prayer_a',x=x+1,y=y))
            reserved.add((x+1,y))
    m.protected_cells=reserved
    counts={tid:sum(str(m.tiles[x,y]['terrain'])==tid for x in range(m.width) for y in range(m.height))
            for tid in ('dead_wood','flint_rock','clay_deposit')}
    m.functional_generation={'policy':'planned-dressing-v1','resources':counts,
        'resource_absence':{tid:('town/capital policy excludes wilderness resources' if chunk.region_type in (RegionType.TOWN,RegionType.CAPITAL)
                               else 'no legal selected site under biome, proximity and reservation policy') for tid,count in counts.items() if not count},
        'waystone_policy':'required-start' if start else 'required-civic' if civic else 'optional-physical-road' if chunk.region_type not in (RegionType.TOWN,RegionType.CAPITAL) else 'not-applicable-member',
        'waystones':sum(v=='waystone_plinth' for v in m.decor.values())}
    return specs,waystone
