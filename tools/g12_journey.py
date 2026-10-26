"""Bounded G12 demonstrations using the established original-loop event driver."""
import argparse
import contextlib
import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import zipfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def snapshot(e):
    from engine.save_manager import _serialize_player, _serialize_world
    from generation.placement import digest
    from g1_support import fingerprint
    m=e.local_map
    return dict(player=digest(_serialize_player(e)), world=digest(_serialize_world(e.world_map)),
        scene=fingerprint(m,[a for a in e.entities if a is not e.player]),
        processing=sorted([list(xy),copy.deepcopy(v)] for xy,v in m.processing_layer.items()),
        zones=copy.deepcopy(m.disruption_zones), load=e.player.inventory.current_weight,
        knowledge=copy.deepcopy(e.creature_knowledge),
        words=sorted(e.player.language.known_deep_words),
        read=sorted(e.player.language.taught_texts),
        recovered={str(k):v for k,v in e.player.language.recovered_text.items()})


def archive_checkpoint(e,out,name):
    path=out/(name+'.zip')
    with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED) as z:
        for p in sorted(e.save_manager.checkpoint_path().rglob('*')):
            if p.is_file():z.write(p,p.relative_to(e.save_manager.checkpoint_path()).as_posix())
    (out/(name+'.json')).write_text(json.dumps(snapshot(e),indent=2)+'\n',encoding='utf-8')
    return path


def install_checkpoint(archive,root):
    slot=Path(root)/'slot_0'
    with zipfile.ZipFile(archive) as z:
        manifest=json.loads(z.read('manifest.json'))
        z.extractall(slot/'generations'/manifest['generation'])
    (slot/'HEAD.json').write_text(json.dumps(dict(checkpoint_version=1,current=manifest['generation'],previous=None)))


def cold(archive):
    from test_effect_persistence import load_data,make_engine
    with tempfile.TemporaryDirectory(prefix='resonance-g12-cold-') as root,patch('engine.save_manager.SAVE_DIR',Path(root)):
        install_checkpoint(archive,root)
        e=make_engine(load_data())
        assert e.save_manager.load(e),e.save_manager.last_error
        expected=json.loads(archive.with_suffix('.json').read_text())
        assert snapshot(e)==expected,(snapshot(e),expected)
        archive.with_suffix('.cold.json').write_text(json.dumps(dict(passed=True,pid=os.getpid(),
            checkpoint_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),state=expected),indent=2)+'\n')


def verify_cold(archive):
    result=subprocess.run([sys.executable,'-X','utf8',str(Path(__file__).resolve()),'--cold',str(archive)],
        capture_output=True,text=True,timeout=90,env=dict(os.environ))
    assert result.returncode==0,result.stdout+result.stderr


def run_stage(out,name,actions,checkpoint=None,**loop_limits):
    from b1_support import Evidence
    from b1_journey import run_journey
    stage=out/name;stage.mkdir()
    job=dict(run_id='g12-'+name,scenario='journey',phase='loop',flavor='candidate',variant=name,result=str(stage/'result.json'))
    ev=Evidence(job)
    old=Path.cwd()
    with tempfile.TemporaryDirectory(prefix='resonance-g12-'+name+'-') as root,patch('engine.save_manager.SAVE_DIR',Path(root)):
        if checkpoint:install_checkpoint(checkpoint,root)
        else:
            slot=Path(root)/'slot_0';slot.mkdir()
            (slot/'world.json').write_text('{"seed":20261023}')
        try:
            os.chdir(ROOT/'roguelike')
            run_journey(ev,lambda e,key,capture,choose:actions(e,key,capture,choose,ev,stage),**loop_limits)
            ev.bind_sources(ROOT/'roguelike')
            ev.record['passed']=True
        finally:
            os.chdir(old)
            (stage/'result.json').write_text(json.dumps(ev.record,indent=2)+'\n',encoding='utf-8')
    return ev.record


def walk_to(e,goals,key):
    from g10_play import path,KEYS
    goals=set(goals)
    for _ in range(100):
        if (e.player.x,e.player.y) in goals:return
        route=path(e,goals);a,b=route[:2]
        yield key(KEYS[b[0]-a[0],b[1]-a[1]])
    raise AssertionError('G12 movement budget')


def inventory(e,item,key,choose):
    import pygame
    yield key(pygame.K_i,'i')
    yield from choose(e,item)
    yield key(pygame.K_RETURN,'\r')
    if e.inventory_screen.open and not e.text_reader.open and not e._pending_throw:
        yield key(pygame.K_i,'i')


def interact(e,xy,key):
    import pygame
    yield key(pygame.K_e,'e')
    while e.interaction_cursor.cursor_x!=xy[0]:
        yield key(pygame.K_RIGHT if e.interaction_cursor.cursor_x<xy[0] else pygame.K_LEFT)
    while e.interaction_cursor.cursor_y!=xy[1]:
        yield key(pygame.K_DOWN if e.interaction_cursor.cursor_y<xy[1] else pygame.K_UP)
    yield key(pygame.K_RETURN,'\r')


def select_prompt(e,item_id,key):
    import pygame
    prompt=e.interaction_cursor._selection_prompt
    assert prompt
    target=len(prompt['items']) if item_id is None else next(n for n,i in enumerate(prompt['items']) if i.item_id==item_id)
    while prompt['selected']!=target:
        yield key(pygame.K_DOWN if prompt['selected']<target else pygame.K_UP)
    yield key(pygame.K_RETURN,'\r')


def recipe(e,iid,key):
    import pygame
    yield key(pygame.K_c,'c')
    screen=e.craft_screen
    flat=screen._build_flat_items(screen._get_recipes(e))
    target=next(n for n,row in enumerate(flat) if row.get('recipe',{}).get('id')==iid)
    while screen.selected!=target:
        yield key(pygame.K_DOWN if screen.selected<target else pygame.K_UP)
    yield key(pygame.K_RETURN,'\r')
    while screen._choosing:
        prompt=screen._choice_prompts[screen._choice_index]
        # The actual material prompt explicitly says that the chosen item is spent.
        target=next(n for n,opt in enumerate(prompt['options']) if opt['item_id']=='wood_bundle')
        while screen._choice_selected!=target:
            yield key(pygame.K_DOWN if screen._choice_selected<target else pygame.K_UP)
        yield key(pygame.K_RETURN,'\r')


def lab(e,key,capture,choose,ev,out):
    import pygame
    from generation.access import enterable
    ev.record['controls']='Normal start at seed 20261023. Existing generated laboratory document and Lens, no item insertion or repositioning. Full-state cardinal path selection. Driver seeds gameplay RNGs to the established 20261020 test seed; native AI, survival, normal FOV, no invincibility. A single disclosed native Hollow Knight is added only after acquisition to demonstrate the existing Lens actions.'
    ev.record['start']=dict(position=[e.player.x,e.player.y],turn=e.world_time.turn,hp=e.player.fighter.hp)
    rows=[(xy,i) for xy,items in e.local_map.floor_objects.items() for i in items]
    doc_xy,doc=next((xy,i) for xy,i in rows if i.text_id=='lab_label_sarcophagus')
    lens_xy,lens=next((xy,i) for xy,i in rows if i.item_id=='revelation_lens')
    yield from walk_to(e,[doc_xy],key)
    yield key(pygame.K_COMMA,',')
    if e.interaction_cursor._selection_prompt:yield from select_prompt(e,doc.item_id,key)
    assert e.player.inventory.contains(doc)
    yield from inventory(e,doc,key,choose)
    assert e.text_reader.open
    r=e.text_reader;seen=set(r._visible_rows);before=e.world_time.turn
    while r._scroll<r._max_scroll:
        yield key(pygame.K_PAGEDOWN);seen.update(r._visible_rows)
    assert seen==set(range(len(r._layout_rows)))
    assert 'do not ring the bells.' in ''.join(f['text'] for row in r._layout_rows for f in row)
    assert e.world_time.turn==before
    capture('g12-complete-lab-warning')
    # Additional production-renderer diagnostic at a constrained display. The
    # ordinary journey above uses the real event loop at its normal resolution.
    constrained=pygame.Surface((480,320))
    r.handle_key(pygame.K_HOME);r.render(constrained,e)
    seen=set(r._visible_rows)
    for _ in range(100):
        if r._scroll==r._max_scroll:break
        r.handle_key(pygame.K_PAGEDOWN);r.render(constrained,e);seen.update(r._visible_rows)
    assert seen==set(range(len(r._layout_rows))) and e.world_time.turn==before
    pygame.image.save(constrained,str(out/'g12-warning-480x320.png'))
    ev.record['constrained_reader']=dict(size=[480,320],all_visual_rows_reached=True,
        turns_spent=0,method='Production TextReader.render and read-only modal navigation diagnostic')
    r.render(pygame.display.get_surface(),e)
    yield key(pygame.K_ESCAPE)
    if e.inventory_screen.open:yield key(pygame.K_i,'i')
    yield from walk_to(e,[lens_xy],key)
    yield key(pygame.K_COMMA,',')
    if e.interaction_cursor._selection_prompt:yield from select_prompt(e,lens.item_id,key)
    assert e.player.inventory.contains(lens)
    yield from inventory(e,lens,key,choose)
    assert e.player.equipment.equipped_in('weapon') is lens
    capture('g12-acquired-lens-normal-fov')
    positions=[(e.player.x+dx,e.player.y+dy) for dx,dy in ((1,0),(0,1),(-1,0),(0,-1))
               if enterable(e.local_map,(e.player.x+dx,e.player.y+dy),e.data)]
    target=e.creature_factory.spawn('hollow_knight',*positions[0]);e.entities.append(target);e._update_fov()
    ev.record['encounter_setup']=dict(creature='hollow_knight',position=positions[0],unmodified_definition=True)
    before=e.world_time.turn
    for _ in range(3):
        yield key(pygame.K_q,'q')
        if e.creature_knowledge.get('hollow_knight'):break
    assert e.creature_knowledge.get('hollow_knight')
    hp=target.fighter.hp
    yield key(pygame.K_r,'r')
    assert target.fighter.hp<hp and e.moveset_cooldowns.get('true_strike',0)>0
    ev.record['lens_actions']=dict(knowledge=copy.deepcopy(e.creature_knowledge),
        true_strike_damage=hp-target.fighter.hp,turns=e.world_time.turn-before,hp=e.player.fighter.hp)
    capture('g12-lens-reveal-true-strike')
    yield key(pygame.K_F5)
    archive=archive_checkpoint(e,out,'lab-checkpoint');expected=snapshot(e);verify_cold(archive)
    yield key(pygame.K_z,'z')
    yield key(pygame.K_F9)
    assert snapshot(e)==expected
    ev.record['restoration']=dict(f5=True,cold_process=True,f9=True,state=expected)


def integration(e,key,capture,choose,ev,out):
    import pygame
    import random
    from test_effect_persistence import make_engine
    from generation.floor_object_utils import place_container,place_floor_object
    fixture=make_engine(e.data)
    # Initial disclosed scene fixture; retain the actual starting possessions,
    # health and needs. No resets or grants occur after this setup block.
    e.world_map=fixture.world_map;e.world_x=e.world_y=0;e.current_submap_id=None
    e.local_map=fixture.local_map;e.entities=[e.player]
    e.player.x=e.player.y=12
    e.surface_return_x=e.surface_return_y=None
    contents=[e.item_factory.create(i) for i in ('component_satchel','dissolution_blade')]
    contents += [e.item_factory.create('wood_bundle') for _ in range(18)]
    decor=next(k for k,v in e.data.decoratives.items() if v.get('interactable')=='container')
    place_container(e.local_map,13,12,decor,contents)
    corpse=e.item_factory.create('corpse',11,12);corpse.source_creature='heath_stalker';corpse.name='remains of Heath Stalker'
    corpse.decay_timer=e.data.entities['heath_stalker']['butcher_yield']['decay_turns']
    place_floor_object(e.local_map,11,12,corpse)
    e._update_fov()
    ev.record['controls']='Initial controlled 1x1 grass scene, container with component satchel, pitted blade and 18 ordinary wood bundles; Heath Stalker remains. Actual normal-start inventory, HP and needs retained. Native source definition, butchery RNG seed 0 explicitly fixed at the source action, real pickups/equip/craft/placement/ignition/turns, no finished pellet injected. Native survival/AI/FOV, no invincibility. Not a normal-start hunt, unaided discovery or balance test.'
    ev.record['fixture_items']=[i.item_id for i in contents]+['corpse:heath_stalker']
    yield from interact(e,(13,12),key)
    yield from select_prompt(e,'component_satchel',key)
    bag=e.player.inventory.get_by_id('component_satchel')
    yield from inventory(e,bag,key,choose)
    yield from interact(e,(13,12),key)
    yield from select_prompt(e,None,key)
    inv=e.player.inventory
    assert len([i for i in inv.items if i.item_id=='wood_bundle'])==18
    assert sum(i.weight for i in inv.items)>inv.capacity and inv.current_weight<inv.capacity
    ev.record['carrying']=dict(raw=sum(i.weight for i in inv.items),effective=inv.current_weight,capacity=inv.capacity)
    capture('g12-satchel-normal-fov')
    blade=inv.get_by_id('dissolution_blade')
    yield from inventory(e,blade,key,choose)
    # Native butchery uses the module RNG; the source yield is controlled,
    # never a granted gland or a repeated until-success hidden attempt.
    random.seed(0)
    yield from interact(e,(11,12),key)
    assert not any(i is corpse for items in e.local_map.floor_objects.values() for i in items)
    yield from interact(e,(11,12),key)
    yield from select_prompt(e,'stalker_musk_gland',key)
    gland=inv.get_by_id('stalker_musk_gland');assert gland
    ev.record['gland_source']=dict(source='heath_stalker tier-2 native butchery',item=gland.item_id,turn=e.world_time.turn)
    torch=inv.get_by_id('tallow_torch')
    yield from inventory(e,torch,key,choose)
    woods=sum(i.item_id=='wood_bundle' for i in inv.items)
    yield from recipe(e,'campfire',key)
    assert e.mode.value=='placement_cursor'
    fire=(e._placement_cursor_x,e._placement_cursor_y)
    yield key(pygame.K_RETURN,'\r')
    assert e.local_map.decor[fire]=='campfire_unlit'
    assert sum(i.item_id=='wood_bundle' for i in inv.items)==woods-2
    assert inv.contains(blade) and blade.equipped
    yield from interact(e,fire,key)
    assert e.local_map.decor[fire]=='campfire_lit'
    yield from recipe(e,'musk_pellet',key)
    assert e.mode.value=='placement_cursor'
    spot=(e._placement_cursor_x,e._placement_cursor_y)
    before=e.world_time.turn
    yield key(pygame.K_RETURN,'\r')
    assert not inv.contains(gland) and e.local_map.processing_layer[spot]['turns_remaining']==9
    capture('g12-paid-preparation-normal-fov')
    # A separate controlled recovered span exercises durable language state.
    e.player.language.recover_span('g12-compatibility-fixture',0,1,'remembered preparation')
    yield key(pygame.K_F5)
    archive=archive_checkpoint(e,out,'processing-checkpoint');expected=snapshot(e);verify_cold(archive)
    yield key(pygame.K_z,'z')
    yield key(pygame.K_F9)
    assert snapshot(e)==expected
    inv=e.player.inventory
    for _ in range(9):yield key(pygame.K_z,'z')
    assert spot not in e.local_map.processing_layer
    assert e.world_time.turn-before==10
    yield from interact(e,spot,key)
    pellet=inv.get_by_id('musk_pellet');assert pellet
    ev.record['preparation']=dict(fire=fire,spot=spot,wood_spent=2,gland_spent=1,
        processing_turns=10,placement_phase_included=True,output=pellet.item_id,
        in_progress_f5_cold_f9=True,turn=e.world_time.turn,hp=e.player.fighter.hp)
    capture('g12-crafted-pellet-normal-fov')
    # The paired scenario begins with this acquired, genuinely crafted pellet.
    target=e.creature_factory.spawn('heath_stalker',11,12);e.entities.append(target);e._update_fov()
    ev.record['retreat_setup']=dict(creature='heath_stalker',position=[11,12],player=[e.player.x,e.player.y],
        native_definition=True,obstacles=dict(fire=fire,container=[13,12]))
    yield key(pygame.K_F5)
    archive=archive_checkpoint(e,out,'retreat-base');verify_cold(archive)
    ev.record['retreat_base']=str(archive)


def retreat(prepared):
    def actions(e,key,capture,choose,ev,out):
        import pygame
        target=next(a for a in e.entities if getattr(a,'_creature_id','')=='heath_stalker')
        start=e.world_time.turn;hp=e.player.fighter.hp
        ev.record['start']=snapshot(e)
        def state():
            return dict(phase=e.world_time.turn-start,player=[e.player.x,e.player.y],hp=e.player.fighter.hp,
                creature=[target.x,target.y],ai=target.ai.state.name,zones=copy.deepcopy(e.local_map.disruption_zones),
                pellet=e.player.inventory.has('musk_pellet'))
        ev.record['phases']=[state()]
        if prepared:
            pellet=e.player.inventory.get_by_id('musk_pellet')
            yield from inventory(e,pellet,key,choose)
            assert e._pending_throw
            while e._placement_cursor_x!=target.x:
                yield key(pygame.K_LEFT if e._placement_cursor_x>target.x else pygame.K_RIGHT)
            while e._placement_cursor_y!=target.y:
                yield key(pygame.K_UP if e._placement_cursor_y>target.y else pygame.K_DOWN)
            yield key(pygame.K_RETURN,'\r')
            assert not e.player.inventory.has('musk_pellet') and e.local_map.disruption_zones[0]['turns_remaining']==5
            yield key(pygame.K_F5)
            archive=archive_checkpoint(e,out,'active-disruption');expected=snapshot(e);verify_cold(archive)
            yield key(pygame.K_F9)
            assert snapshot(e)==expected
            target=next(a for a in e.entities if getattr(a,'_creature_id','')=='heath_stalker')
        else:
            yield key(pygame.K_z,'z')  # Same one-phase opportunity cost as throwing.
        ev.record['phases'].append(state())
        for k in (pygame.K_DOWN,pygame.K_DOWN,pygame.K_z,pygame.K_z,pygame.K_z):
            yield key(k);ev.record['phases'].append(state())
        assert e.world_time.turn-start==6 and not e.local_map.disruption_zones
        if prepared:
            assert [target.x,target.y]==[11,12] and e.player.fighter.hp==hp
        capture('g12-retreat-'+('prepared' if prepared else 'control'))
        before=[target.x,target.y]
        for _ in range(2):yield key(pygame.K_z,'z');ev.record['phases'].append(state())
        assert [target.x,target.y]!=before or e.player.fighter.hp<hp
        ev.record.update(prepared=prepared,phases_elapsed=e.world_time.turn-start,hp_spent=hp-e.player.fighter.hp,
            consumed=not e.player.inventory.has('musk_pellet'),normal_behavior_resumed=True)
    return actions


def run(out):
    out.mkdir(parents=True,exist_ok=True)
    assert not (out/'journey.json').exists(),'Use a fresh evidence directory'
    report=dict(passed=False,controls='Existing b1_journey original Engine.run event.post/get driver, bounded actions, dummy SDL, native renderer/AI/survival. Full-state route and UI row selection; disclosed initial controlled fixtures. No desktop control or personal saves.')
    try:
        report['lab']=run_stage(out,'lab',lab)
        report['integration']=run_stage(out,'integration',integration)
        base=Path(report['integration']['retreat_base'])
        report['control']=run_stage(out,'control',retreat(False),base)
        report['prepared']=run_stage(out,'prepared',retreat(True),base)
        assert report['control']['start']==report['prepared']['start']
        assert report['control']['hp_spent']>report['prepared']['hp_spent']
        report['passed']=True
    finally:
        (out/'journey.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    return report


def main():
    p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path);p.add_argument('--cold',type=Path);a=p.parse_args()
    sys.path[:0]=[str(ROOT/'roguelike'),str(ROOT/'tools'),str(ROOT/'tools/critical_fix_regressions/tests')]
    os.environ.update(SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy',PYGAME_HIDE_SUPPORT_PROMPT='1',PYTHONHASHSEED='20261020')
    import config
    config.DEBUG_MODE=False
    if a.cold:cold(a.cold.resolve());return
    out=a.evidence.resolve();out.mkdir(parents=True,exist_ok=True)
    with (out/'output.txt').open('w',encoding='utf-8') as log,contextlib.redirect_stdout(log):run(out)
    print(json.dumps(dict(passed=True,evidence=str(out))))


if __name__=='__main__':main()
