"""Short scripted ordinary expedition; no positioning, supplies or AI overrides."""
import argparse
from collections import Counter
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import time
import zipfile
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]


def inventory_use(e,item_id):
    import pygame
    from engine.inventory_screen import _group_items, _flat_list
    e._handle_key(pygame.K_i)
    e.inventory_screen.init(e.display)
    # Use the UI's own row construction; the main drawing loop is intercepted
    # headlessly, so it has not yet populated the inventory's cached rows.
    e.inventory_screen._flat=_flat_list(_group_items(e.player.inventory.items,e),e.inventory_screen._collapsed)
    rows=e.inventory_screen._flat
    selected=next(i for i,(item,header,_) in enumerate(rows) if not header and item.item_id==item_id)
    while e.inventory_screen.selected>selected:e._handle_key(pygame.K_UP)
    while e.inventory_screen.selected<selected:e._handle_key(pygame.K_DOWN)
    e._handle_key(pygame.K_RETURN)
    if e._pending_consume:e._handle_key(pygame.K_y)
    if e.inventory_screen.open:e._handle_key(pygame.K_i)


def run(out):
    import pygame
    from g10_play import boot,status,leave_lab,walk,interact,path,render,KEYS
    from generation.access import reachable
    from generation.placement import digest
    from engine.save_manager import _serialize_player
    from g1_support import fingerprint
    from test_effect_persistence import make_engine
    from engine.scene_generation import create_surface
    out.mkdir(parents=True,exist_ok=True)
    report=dict(passed=False,selection='Known seed 20261023. Script selects real paths from full state, avoids occupied cells, prefers low movement costs and distance from threats. This is not unaided discovery or an exploration AI.',
        controls='Normal fresh-start route, normal inventory/FOV, native AI and survival active, invincibility off. No teleports, actor removal, injected items, or health/thirst restoration during the outing. Gameplay RNG is the unchanged ordinary seed.',inputs=[],events=[],boundaries=[],terrain_choices=[])
    with tempfile.TemporaryDirectory(prefix='resonance-g10-expedition-') as tmp,patch('engine.save_manager.SAVE_DIR',Path(tmp)):
        e=boot(tmp);report['start']=status(e)
        try:
            # Use the ordinary inventory handlers and their own UI row ordering.
            render(e,out/'01-lab-normal-fov.png','G10 ordinary start')
            inventory_use(e,'crude_blade');inventory_use(e,'leather_jack')
            report['events'].append(dict(action='equip normal starting blade and jacket',state=status(e)))
            leave_lab(e,report['inputs'])
            start=(e.world_x,e.world_y)
            render(e,out/'02-surface-normal-fov.png','G10 ordinary surface arrival')
            stone=next(xy for xy,value in e.local_map.decor.items() if value=='waystone_plinth')
            interact(e,stone,report['inputs'])
            assert stone in e.local_map.interacted_waystones
            report['events'].append(dict(action='starting waystone',chunk=start,xy=stone))
            # Pick the nearest accessible off-road living plant, then harvest via E.
            plants=[xy for xy,value in e.local_map.decor.items() if e.data.decoratives.get(value,{}).get('harvestable') and xy not in e.local_map.protected_cells]
            choices=[]
            for xy in plants:
                try:route=path(e,{(xy[0]+dx,xy[1]+dy) for dx,dy in KEYS},prefer_firm=True)
                except AssertionError:continue
                choices.append((len(route),xy))
            assert choices,'No accessible off-road plant'
            _,plant=min(choices);decor=e.local_map.decor[plant];before=list(report['start']['inventory'])
            interact(e,plant,report['inputs'])
            assert e.local_map.decor.get(plant)!=decor
            report['events'].append(dict(action='harvest through interaction cursor',chunk=start,xy=plant,decor=decor,inventory=status(e)['inventory']))
            render(e,out/'03-harvest-normal-fov.png','G10 harvested off-road resource')
            for direction in ((0,1),(1,0),(0,-1),(-1,0)):
                dx,dy=direction;m=e.local_map
                candidates=[(x,y) for x in range(m.width) for y in range(m.height)
                    if ((dx==1 and x==79) or (dx==-1 and x==0) or (dy==1 and y==42) or (dy==-1 and y==0))
                    and (x,y) not in m.road_cells]
                # The script chooses a natural crossing by reachable firm ground;
                # destination preparation happens only through the real boundary key.
                shortest=path(e,candidates);firm=path(e,candidates,prefer_firm=True)
                def route_cost(route):return sum(e.data.terrain.get(str(m.tiles[xy]['terrain']),{}).get('move_cost',1) for xy in route[1:])
                report['terrain_choices'].append(dict(direction=direction,origin=[e.player.x,e.player.y],
                    shortest_steps=len(shortest)-1,initial_firm_steps=len(firm)-1,
                    shortest_movement_cost=route_cost(shortest),initial_firm_movement_cost=route_cost(firm),
                    initial_firm_surfaces=dict(Counter(str(m.tiles[xy]['terrain']) for xy in firm)),
                    note='Initial comparison before each leg; each actual input replans for moving native actors. Blocking stands are impassable; wet/tall ground costs and threat proximity influence the firm route.'))
                walk(e,candidates,report['inputs'],limit=300,prefer_firm=True)
                before=status(e);began=time.perf_counter();e._handle_key(KEYS[direction]);seconds=time.perf_counter()-began
                assert (e.world_x,e.world_y)==(before['chunk'][0]+dx,before['chunk'][1]+dy)
                report['boundaries'].append(dict(direction=direction,start=before,end=status(e),seconds=seconds,off_road_departure=True))
                report['events'].append(dict(action='natural boundary crossing',state=status(e)))
                render(e,out/f'boundary-{len(report["boundaries"])}-normal-fov.png',f'G10 natural boundary {direction}')
                if e.player.needs.thirst>.18 and any(i.item_id=='water_flask' for i in e.player.inventory.items):
                    old=e.player.needs.thirst;inventory_use(e,'water_flask');report['events'].append(dict(action='drink starting flask through inventory handler',before_thirst=old,after_thirst=e.player.needs.thirst))
            assert (e.world_x,e.world_y)==start
            # Complete the outing by rejoining its real road and useful return point.
            walk(e,e.local_map.road_cells,report['inputs'],prefer_firm=True)
            interact(e,stone,report['inputs'])
            report['final']=status(e)
            assert e.player.fighter.hp>0 and not e.player_invincible
            render(e,out/'04-return-normal-fov.png','G10 completed ordinary expedition')
            e._handle_key_local(pygame.K_F5);assert e.save_manager.last_error is None
            checkpoint=e.save_manager.checkpoint_path()
            with zipfile.ZipFile(out/'explored-checkpoint.zip','w',zipfile.ZIP_DEFLATED) as z:
                for p in sorted(checkpoint.rglob('*')):
                    if p.is_file():z.write(p,p.relative_to(checkpoint).as_posix())
            keys=[(c.wx,c.wy) for c in e.world_map.chunks.values() if c.visited]
            scenes={str(xy):fingerprint(*e._prepare_destination(*xy)) for xy in keys}
            pending=(start[0]+2,start[1]+2)
            assert not e.world_map.get(*pending).visited
            r=create_surface(e.world_map,e.world_map.get(*pending),e.data,e.item_factory,e.creature_factory,80,43)
            pending_expected=fingerprint(r.local_map,r.actors)
            state=digest(_serialize_player(e))
            reader=make_engine(e.data);assert reader.save_manager.load(reader),reader.save_manager.last_error
            assert digest(_serialize_player(reader))==state
            # This extra wait is only a disclosed F9 reconstruction check after
            # the final outing measurements and successful F5 checkpoint.
            e._handle_key_local(pygame.K_z);e._handle_key_local(pygame.K_F9)
            assert digest(_serialize_player(e))==state
            for owner in (e,reader):
                for xy in keys:assert fingerprint(*owner._prepare_destination(*xy))==scenes[str(xy)]
                assert fingerprint(*owner._prepare_destination(*pending))==pending_expected
            report.update(passed=True,visited=scenes,pending=dict(chunk=pending,fingerprint=pending_expected),
                restore=dict(F5=True,cold_load=True,F9=True,player_and_supplies=True,actors_terrain_and_mutations=True,
                             post_outing_wait_rewound_only_for_explicit_F9_test=True),
                turns=report['final']['turn']-report['start']['turn'],movement_inputs=len(report['inputs']),
                checkpoint_sha256=hashlib.sha256((out/'explored-checkpoint.zip').read_bytes()).hexdigest())
            report['visible_threats']=sorted({n['name'] for row in report['inputs'] for n in row['visible_natives']})
        except Exception as error:
            report.update(error=repr(error),failure_state=status(e))
            render(e,out/'failure-normal-fov.png','Unsuccessful ordinary G10 attempt')
            raise
        finally:
            report['log']=[m.text for m in e.log.messages]
            (out/'expedition.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    return report


def main():
    p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,required=True);a=p.parse_args()
    sys.path[:0]=[str(ROOT/'roguelike'),str(ROOT/'tools'),str(ROOT/'tools/critical_fix_regressions/tests')]
    os.environ.update(SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy',PYGAME_HIDE_SUPPORT_PROMPT='1')
    a.evidence.mkdir(parents=True,exist_ok=True)
    with (a.evidence/'output.txt').open('w',encoding='utf-8') as log,contextlib.redirect_stdout(log):run(a.evidence)
    print(json.dumps(dict(passed=True,evidence=str(a.evidence))))


if __name__=='__main__':main()
