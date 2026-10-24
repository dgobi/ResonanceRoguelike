"""G8 extensions to the established actual-handler journey; no positioning."""
import time


def town(e,walk,route,position):
    import pygame
    from engine.engine import GameMode
    from engine.interaction_cursor import InteractionCursor
    from generation.placement import frontage_entrance
    from generation.road_network import PhysicalRoads,corners
    from generation.access import enterable
    plan=e.world_map.plan;s=plan['settlements'][0];start=position();network=PhysicalRoads(plan)
    report=dict(settlement=s['id'],layout=s['layout']['id'],contents=[],axes=[],common=None)
    e.player.inventory.capacity=1000
    def travel(join,label):
        path=network.path(position(),join);route(dict(id=label,points=corners(path)))
    def interact(goal):
        goal=(goal[0]%80,goal[1]%43);ok=False
        for dx,dy in ((0,1),(1,0),(-1,0),(0,-1)):
            try:walk((goal[0]+dx,goal[1]+dy))
            except AssertionError:continue
            e._update_fov()
            if InteractionCursor.can_reach(e,*goal):ok=True;break
        assert ok,('town target inaccessible',goal)
        before=len(e.player.inventory.items);container=e.local_map.container_state.get(goal);count=len(container['items']) if container else None
        e.mode=GameMode.INTERACTION_CURSOR;e.interaction_cursor._cursor_x,e.interaction_cursor._cursor_y=goal;e.interaction_cursor.candidates=[goal];e._handle_key(pygame.K_RETURN)
        if container is not None:
            assert e.interaction_cursor._selection_prompt is not None
            if count:e._handle_key(pygame.K_RETURN)
        e.text_reader.close();e.mode=GameMode.LOCAL;e.interaction_cursor._selection_prompt=None
        return dict(target=goal,inventory_before=before,inventory_after=len(e.player.inventory.items),container_before=count,container_after=len(container['items']) if container else None)
    plots=[p for p in plan['plots'] if p['owner']==s['id'] and p['placement']];ids={p['placement'] for p in plots};placements=[p for p in plan['placements'] if p['id'] in ids]
    for role in ('residential','commercial'):
        p=next(p for p in placements if p['role']==role and any(t['kind']=='container' for t in p['targets']))
        travel(p['join'],'town-'+role);entry=frontage_entrance(p);walk((entry['x']%80,entry['y']%43))
        target=next(t for t in p['targets'] if t['kind']=='container');used=interact((target['x'],target['y']));assert used['inventory_after']>used['inventory_before']
        report['contents'].append(dict(role=role,placement=p['id'],asset=p['asset'],interaction=used));walk((p['join'][0]%80,p['join'][1]%43))
    for normals,axis in [('NS','horizontal'),('EW','vertical')]:
        plot=next(p for p in plots if p['normal'] in normals);p=next(p for p in placements if p['id']==plot['placement']);travel(p['join'],'town-axis-'+axis)
        road=next(r for r in plan['routes'] if r['id']==plot['road']);a,b=road['points'][plot['frontage']['segment']:plot['frontage']['segment']+2]
        # Walk a real five-tile centerline interval adjacent to this occupied join.
        dx=(b[0]>a[0])-(b[0]<a[0]);dy=(b[1]>a[1])-(b[1]<a[1]);point=p['join'];end=[point[0]+5*dx,point[1]+5*dy]
        path=network.path(point,end);route(dict(id='along-'+axis,points=corners(path)));travel(p['join'],'back-'+axis)
        report['axes'].append(dict(axis=axis,normal=plot['normal'],road=road['id'],join=point,walked_to=end))
    civic=next(p for p in placements if p['role']=='civic');travel(civic['join'],'town-civic');entry=frontage_entrance(civic);walk((entry['x']%80,entry['y']%43))
    floor=next(t for t in civic['targets'] if t['required']);walk((floor['x']%80,floor['y']%43));assert any('bell_dead'==str(e.local_map.tiles[x,y]['terrain']) for x in range(80) for y in range(43))
    common=next(c for c in plan['public_spaces'] if c['owner']==s['id']);rect=common['rects'][0];goal=[(rect[0]+rect[2])//2,(rect[1]+rect[3])//2];walk((goal[0]%80,goal[1]%43))
    stone,prayer=common['furnishing'];stone_use=interact(stone);assert (stone[0]%80,stone[1]%43) in e.local_map.interacted_waystones
    prayer_use=interact(prayer);assert any(getattr(i,'text_id',None)=='waystone_prayer_a' for i in e.player.inventory.items)
    report['common']=dict(id=common['id'],walked_to=goal,spent_bell_present=True,stone=stone_use,prayer=prayer_use)
    walk((civic['join'][0]%80,civic['join'][1]%43));travel(start,'return-to-country-arrival')
    return report


def explored_checkpoint(e):
    import pygame
    from test_effect_persistence import make_engine
    from g1_support import fingerprint
    keys=sorted((c.wx,c.wy) for c in e.world_map.chunks.values() if c.visited)
    expected={str(k):fingerprint(*e._prepare_destination(*k)) for k in keys}
    t=time.perf_counter();e._handle_key_local(pygame.K_F5);saved=time.perf_counter()-t;assert e.save_manager.last_error is None
    reader=make_engine(e.data);t=time.perf_counter();assert reader.save_manager.load(reader),reader.save_manager.last_error;cold=time.perf_counter()-t
    for k in keys:assert fingerprint(*reader._prepare_destination(*k))==expected[str(k)]
    assert [i.item_id for i in reader.player.inventory.items]==[i.item_id for i in e.player.inventory.items]
    path=e.save_manager.checkpoint_path()
    return dict(scope='Actually explored journey: G8 town contents/common, compound child mutations, single-site, other settlement, bridge and landmark; actual F5 and cold SaveManager load',save_seconds=saved,cold_load_seconds=cold,scene_count=len(list((path/'chunks').glob('*.pkl'))),bytes=sum(p.stat().st_size for p in path.rglob('*') if p.is_file()),surface_fingerprints=expected,inventory_ids=[i.item_id for i in e.player.inventory.items])
