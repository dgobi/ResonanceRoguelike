"""Bounded app-local G3 journey. Uses production movement, doors, stairs and travel.

The declared controlled fixture freezes AI/survival turn updates while preserving
generated native actors as obstacles. No teleport or arrival correction is used.
"""
from collections import deque
import contextlib
import io
import json
import os
from pathlib import Path
import time
from unittest.mock import patch


def journey(seed,save_root,progress=None):
    import pygame
    import main
    from engine.engine import Engine,MOVE_KEYS,GameMode
    from generation.access import enterable
    from generation.placement import digest
    from engine.save_manager import _serialize_world
    from engine.interaction_cursor import InteractionCursor
    from g1_support import fingerprint
    report={'seed':seed,'fixture':'ordinary production world; native actors retained as stationary obstacles; AI/survival turn updates paused; movement, doors, stairs, interactions, travel and save handlers unchanged','steps':0,'crossings':[],'destinations':[],'interaction':None}
    bridge_steps=set()
    def retain():
        if progress:Path(progress).write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    captured=[];slot=Path(save_root)/'slot_0';slot.mkdir(parents=True);(slot/'world.json').write_text(json.dumps({'seed':seed}))
    # Rendering is not needed to dispatch the actual app-local input handlers.
    with patch('engine.save_manager.SAVE_DIR',Path(save_root)),patch.object(Engine,'run',lambda e:captured.append(e)),patch.object(Engine,'_advance_turn',lambda e:e.world_time.advance()):
        main.main();e=captured[0];e.debug=False;e.player_invincible=True
        def position():return e.world_x*80+e.player.x,e.world_y*43+e.player.y
        def observe_bridge():
            if e.current_submap_id is not None:return
            x,y=position()
            for crossing in e.world_map.plan['crossings']:
                if any(r[0]<=x<r[2] and r[1]<=y<r[3] for r in crossing['deck']):bridge_steps.add(crossing['id'])
        def walk(target,roads=False):
            start=(e.player.x,e.player.y);target=tuple(target);m=e.local_map
            blocked={(a.x,a.y) for a in e.entities if a is not e.player and a.blocks_movement}
            parent={start:None};queue=deque([start])
            while queue and target not in parent:
                x,y=queue.popleft()
                for dx,dy in ((0,-1),(-1,0),(1,0),(0,1),(-1,-1),(1,-1),(-1,1),(1,1)):
                    q=x+dx,y+dy
                    if q in parent or q in blocked or not enterable(m,q,e.data):continue
                    if roads and q not in m.road_cells:continue
                    parent[q]=(x,y);queue.append(q)
            if target not in parent:raise AssertionError(f'no movement path {position()} to {target}, roads={roads}')
            path=[];q=target
            while q!=start:path.append(q);q=parent[q]
            for q in reversed(path):
                delta=q[0]-e.player.x,q[1]-e.player.y;key=next(k for k,v in MOVE_KEYS.items() if v==delta)
                if str(m.tiles[q]['terrain'])=='door_closed':e._handle_key_local(key)
                e._handle_key_local(key);report['steps']+=1
                observe_bridge()
                if (e.player.x,e.player.y)!=q:raise AssertionError(f'movement failed {q}')
        stair=next((x,y) for x in range(80) for y in range(43) if str(e.local_map.tiles[x,y]['terrain'])=='stairs_up')
        walk(stair);e._handle_key(pygame.K_COMMA,text='<')
        if e.current_submap_id is not None:raise AssertionError('normal lab ascent failed')
        report['destinations'].append('start-surface-exit')
        plan=e.world_map.plan
        t=time.perf_counter();e._handle_key_local(pygame.K_F5);head=e.save_manager.store.token()
        report['checkpoint_seconds']=time.perf_counter()-t
        checkpoint_plan=digest(plan);checkpoint_world=digest(_serialize_world(e.world_map))
        checkpoint_scene=fingerprint(e.local_map,e.entities[1:]);checkpoint_position=position()
        def route(row,reverse=False):
            points=list(reversed(row['points'])) if reverse else row['points']
            first=points[0];assert (first[0]//80,first[1]//43)==(e.world_x,e.world_y),(row['id'],position(),first)
            walk((first[0]%80,first[1]%43))
            for a,b in zip(points,points[1:]):
                dx=0 if a[0]==b[0] else (1 if b[0]>a[0] else -1);dy=0 if a[1]==b[1] else (1 if b[1]>a[1] else -1)
                while (e.world_x,e.world_y)!=(b[0]//80,b[1]//43):
                    target=(79 if dx>0 else 0 if dx<0 else b[0]%80,42 if dy>0 else 0 if dy<0 else b[1]%43)
                    walk(target,roads=True);before=position();t=time.perf_counter()
                    key=next(k for k,v in MOVE_KEYS.items() if v==(dx,dy));e._handle_key_local(key)
                    after=position();elapsed=time.perf_counter()-t
                    if after!=(before[0]+dx,before[1]+dy):raise AssertionError(f'arrival correction or blocked planned crossing {before}->{after}')
                    if (e.player.x,e.player.y) not in e.local_map.road_cells:raise AssertionError('arrival left planned band')
                    report['crossings'].append(dict(route=row['id'],before=list(before),after=list(after),seconds=elapsed))
                    report['steps']+=1
                    observe_bridge()
                walk((b[0]%80,b[1]%43),roads=True)
            if e.save_manager.store.token()!=head:raise AssertionError('travel published a checkpoint')
            retain()
        country=[r for r in plan['routes'] if r['kind']=='country']
        for n in range(4):
            row=next(r for r in country if r['id']==f'road-{n}');route(row)
            report['destinations'].append(row['b'])
            if row['b']=='settlement-0':
                local=[p for p in plan['placements'] if p['origin'][0]//80==e.world_x and p['origin'][1]//43==e.world_y]
                p=next(p for p in local if any(t['kind']=='container' for t in p['targets']))
                target=next(t for t in p['targets'] if t['kind']=='container');xy=(target['x']%80,target['y']%43)
                approaches=[(xy[0]+dx,xy[1]+dy) for dx in (-1,0,1) for dy in (-1,0,1) if enterable(e.local_map,(xy[0]+dx,xy[1]+dy),e.data)]
                walk(approaches[0]);e._update_fov()
                assert InteractionCursor.can_reach(e,*xy)
                e.mode=GameMode.INTERACTION_CURSOR;e.interaction_cursor._cursor_x,e.interaction_cursor._cursor_y=xy;e.interaction_cursor.candidates=[xy]
                e._handle_key(pygame.K_RETURN)
                if e.interaction_cursor._selection_prompt is None:raise AssertionError('authored container interaction did not open')
                state=e.local_map.container_state[xy];contents=len(state['items'])
                if contents:e._handle_key(pygame.K_RETURN)
                e.mode=GameMode.LOCAL;e.interaction_cursor._selection_prompt=None
                report['interaction']=dict(placement=p['id'],target=xy,initial_items=contents,remaining_items=len(state['items']))
        route(next(r for r in country if r['id']=='road-3'),reverse=True)
        landmark_route=next(r for r in country if r['b']=='landmark');route(landmark_route)
        landmark=next(p for p in plan['placements'] if p['context']=='landmark')
        walk((landmark['join'][0]%80,landmark['join'][1]%43))
        report['destinations'].append('landmark')
        report['bridge_ids_walked']=sorted(bridge_steps)
        assert any(c['road']=='road-1' and c['id'] in bridge_steps for c in plan['crossings'])
        # Crossing may be interior; route-1 explicitly traverses the required channel.
        assert any(r['route']=='road-1' for r in report['crossings'])
        report['materialized_scenes_before_f9']=sum(c.visited for c in e.world_map.chunks.values())
        retain()
        t=time.perf_counter();e._handle_key_local(pygame.K_F9)
        report['restore_seconds']=time.perf_counter()-t
        assert digest(e.world_map.plan)==checkpoint_plan
        assert digest(_serialize_world(e.world_map))==checkpoint_world,'F9 world state differs from saved checkpoint'
        assert position()==checkpoint_position and fingerprint(e.local_map,e.entities[1:])==checkpoint_scene
        assert e.save_manager.store.token()==head
        report['f9_restored_coherent_start_checkpoint']=True
        report['worst_transition_seconds']=max(c['seconds'] for c in report['crossings'])
        report['checkpoint_bytes']=sum(p.stat().st_size for p in e.save_manager.checkpoint_path().rglob('*') if p.is_file())
        report['passed']=True
        retain()
    return report
