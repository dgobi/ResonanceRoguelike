"""Controlled initial neighbor position, then real inputs for a complete cave trip."""
import argparse
import contextlib
import hashlib
import heapq
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]


def walk(e, goals, inputs):
    from engine.engine import MOVE_KEYS
    from generation.access import enterable
    from g10_play import status
    keys={v:k for k,v in MOVE_KEYS.items()};goals=set(goals)
    for _ in range(250):
        start=(e.player.x,e.player.y)
        if start in goals:return
        occupied={(a.x,a.y) for a in e.entities if a is not e.player and a.blocks_movement}
        parents={start:None};costs={start:0};todo=[(0,start)];target=None
        while todo:
            cost,p=heapq.heappop(todo)
            if cost!=costs[p]:continue
            if p in goals:target=p;break
            for dx,dy in keys:
                q=p[0]+dx,p[1]+dy
                if q in occupied or not enterable(e.local_map,q,e.data):continue
                terrain=str(e.local_map.tiles[q]['terrain'])
                threat=sum(max(0,6-max(abs(q[0]-a),abs(q[1]-b)))*3 for a,b in occupied)
                value=cost+e.data.terrain.get(terrain,{}).get('move_cost',1)+threat
                if value<costs.get(q,float('inf')):
                    costs[q]=value;parents[q]=p;heapq.heappush(todo,(value,q))
        assert target is not None,'No real eight-way route'
        while parents[target]!=start:target=parents[target]
        before=status(e);key=keys[target[0]-start[0],target[1]-start[1]]
        e._handle_key_local(key)
        inputs.append(dict(key=key,before=before,after=status(e)))
        assert e.player.fighter.hp>0,'Journey died'
    raise AssertionError('Finite input budget exceeded')


def snapshot(e, addresses):
    from g1_support import fingerprint
    from engine.save_manager import _serialize_player, _serialize_world
    from generation.placement import digest
    scenes=[dict(address=list(a),fingerprint=fingerprint(*e._prepare_destination(*a))) for a in addresses]
    return dict(player=digest(_serialize_player(e)),world=digest(_serialize_world(e.world_map)),scenes=scenes)


def run(out):
    import pygame
    from g10_play import boot,status,render
    from g10_expedition import inventory_use
    from engine.scene_generation import create_surface
    from generation.access import enterable
    from g1_support import fingerprint
    from test_effect_persistence import make_engine
    out.mkdir(parents=True,exist_ok=True)
    report=dict(passed=False,seed=20261023,inputs=[],events=[],
        controls='One initial disclosed fixture position in normal neighbor (44,7). From first boundary input: real eight-way movement, doors, stairs and inventory only. Native actors, AI, survival, normal FOV, no invincibility or supplied items. Full-state path selection avoids moving actors; not a normal-start expedition or unaided discovery.')
    with tempfile.TemporaryDirectory(prefix='resonance-g11-journey-') as tmp,patch('engine.save_manager.SAVE_DIR',Path(tmp)):
        e=boot(tmp)
        try:
            target=create_surface(e.world_map,e.world_map.get(44,8),e.data,e.item_factory,e.creature_factory,80,43)
            contract=target.local_map.wilderness_access
            assert contract['neighbor']==[44,7]
            report['contract']=contract
            # Pure scene preview determines the witness; target remains pending.
            e.overmap_cursor_x,e.overmap_cursor_y=contract['neighbor'];e._teleport_to_overmap_cursor()
            e.player.x,e.player.y=contract['reciprocal'];e._update_fov()
            assert enterable(e.local_map,tuple(contract['reciprocal']),e.data)
            assert all((a.x,a.y)!=tuple(contract['reciprocal']) for a in e.entities[1:])
            assert not e.player_invincible
            render(e,out/'01-approach-normal-fov.png','G11 controlled initial neighbor approach')
            inventory_use(e,'crude_blade');inventory_use(e,'leather_jack')
            report['start']=status(e)
            e._handle_key_local(pygame.K_DOWN)
            assert (e.world_x,e.world_y,e.current_submap_id)==(44,8,None)
            assert [e.player.x,e.player.y]==contract['edge']
            report['events'].append(dict(action='real boundary entry',state=status(e)))
            stair=next(xy for xy,sid in e.local_map.submap_links.items() if sid=='submap_44_8_0')
            walk(e,{stair},report['inputs'])
            render(e,out/'02-entrance-normal-fov.png','G11 actual Arnevel Vault entrance')
            render(e,out/'entrance-revealed.png','G11 completed scene comparison',revealed=True)
            e._handle_key(pygame.K_PERIOD,'>')
            assert e.current_submap_id=='submap_44_8_0'
            report['events'].append(dict(action='descend',state=status(e)))
            ups={(x,y) for x in range(80) for y in range(43) if str(e.local_map.tiles[x,y]['terrain'])=='stairs_up'}
            walk(e,ups,report['inputs'])
            e._handle_key(pygame.K_COMMA,'<')
            assert e.current_submap_id is None and (e.player.x,e.player.y)==stair
            report['events'].append(dict(action='ascend to owned return',state=status(e)))
            render(e,out/'03-return-normal-fov.png','G11 surface return from Arnevel Vault')
            inventory_use(e,'water_flask')
            assert 'water_flask' not in status(e)['inventory'] and 'empty_water_skin' in status(e)['inventory']
            report['events'].append(dict(action='consume starting flask',state=status(e)))
            walk(e,{tuple(contract['edge'])},report['inputs'])
            e._handle_key_local(pygame.K_UP)
            assert [e.world_x,e.world_y]==contract['neighbor']
            assert [e.player.x,e.player.y]==contract['reciprocal']
            report['final']=status(e)
            render(e,out/'04-exit-normal-fov.png','G11 completed reciprocal exit')
            e._handle_key_local(pygame.K_F5);assert e.save_manager.last_error is None
            checkpoint=e.save_manager.checkpoint_path()
            addresses=[(44,7,None),(44,8,None),(44,8,'submap_44_8_0')]
            expected=snapshot(e,addresses)
            pending=(45,8)
            assert not e.world_map.get(*pending).visited
            r=create_surface(e.world_map,e.world_map.get(*pending),e.data,e.item_factory,e.creature_factory,80,43)
            pending_fp=fingerprint(r.local_map,r.actors)
            reader=make_engine(e.data);assert reader.save_manager.load(reader),reader.save_manager.last_error
            assert snapshot(reader,addresses)==expected
            e._handle_key_local(pygame.K_z);e._handle_key_local(pygame.K_F9)
            assert snapshot(e,addresses)==expected
            for owner in (e,reader):
                m,actors=owner._prepare_destination(*pending)
                assert fingerprint(m,actors)==pending_fp and m.wilderness_access['revision']==1
            with zipfile.ZipFile(out/'journey-checkpoint.zip','w',zipfile.ZIP_DEFLATED) as z:
                for p in sorted(checkpoint.rglob('*')):
                    if p.is_file():z.write(p,p.relative_to(checkpoint).as_posix())
            report.update(passed=True,restore=dict(F5=True,cold_engine=True,F9=True,expected=expected,
                pending=dict(chunk=pending,fingerprint=pending_fp),post_outing_wait_only_for_F9=True),
                turns=report['final']['turn']-report['start']['turn'],movement_inputs=len(report['inputs']))
            # Fresh process loads the actual checkpoint and checks full exercised
            # terrain/actors/links, mutation/inventory, transport and RNG record.
            (out/'journey.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
            result=subprocess.run([sys.executable,'-X','utf8',str(Path(__file__).resolve()),'--cold',str(out)],
                capture_output=True,text=True,timeout=120)
            (out/'cold-output.txt').write_text(result.stdout+result.stderr,encoding='utf-8')
            assert result.returncode==0,result.stdout+result.stderr
            report['restore']['fresh_process']=True
        except Exception as error:
            report.update(passed=False,error=repr(error),failure_state=status(e))
            render(e,out/'failure-normal-fov.png','G11 failed attempt')
            raise
        finally:
            report['log']=[m.text for m in e.log.messages]
            (out/'journey.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    return report


def cold(out):
    from test_effect_persistence import load_data,make_engine
    from g1_support import fingerprint
    report=json.loads((out/'journey.json').read_text());expected=report['restore']['expected']
    with tempfile.TemporaryDirectory(prefix='resonance-g11-cold-') as tmp,patch('engine.save_manager.SAVE_DIR',Path(tmp)):
        slot=Path(tmp)/'slot_0'
        with zipfile.ZipFile(out/'journey-checkpoint.zip') as z:
            manifest=json.loads(z.read('manifest.json'));z.extractall(slot/'generations'/manifest['generation'])
        (slot/'HEAD.json').write_text(json.dumps(dict(checkpoint_version=1,current=manifest['generation'],previous=None)))
        e=make_engine(load_data());assert e.save_manager.load(e),e.save_manager.last_error
        assert snapshot(e,[r['address'] for r in expected['scenes']])==expected
        pending=report['restore']['pending']
        assert fingerprint(*e._prepare_destination(*pending['chunk']))==pending['fingerprint']
        (out/'cold.json').write_text(json.dumps(dict(passed=True,checkpoint_sha256=hashlib.sha256((out/'journey-checkpoint.zip').read_bytes()).hexdigest(),
            full_player_world_scenes_and_pending_match=True),indent=2)+'\n')


def main():
    p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path);p.add_argument('--cold',type=Path);a=p.parse_args()
    sys.path[:0]=[str(ROOT/'roguelike'),str(ROOT/'tools'),str(ROOT/'tools/critical_fix_regressions/tests')]
    os.environ.update(SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy',PYGAME_HIDE_SUPPORT_PROMPT='1')
    if a.cold:cold(a.cold.resolve());return
    out=a.evidence.resolve();out.mkdir(parents=True,exist_ok=True)
    with (out/'output.txt').open('w',encoding='utf-8') as log,contextlib.redirect_stdout(log):run(out)
    print(json.dumps(dict(passed=True,evidence=str(out))))


if __name__=='__main__':main()
