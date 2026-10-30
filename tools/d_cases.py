"""D behavioral contracts on real factories, combat, turns and checkpoint owners.

Fixtures edit only disposable in-process worlds/definitions; no resolver or AI mock.
"""
import copy
from c_cases import fixture as c_fixture, make
from b1_support import read, hashes


def fixture(e):
    c_fixture(e)
    e._live_pursuers=[];e._pending_pursuer_arrivals=[]
    e.player.fighter.hp=e.player.fighter.max_hp=500
    e.player.fighter._dead=False;e.player.is_alive=True;e.player.dodge_chance=0
    e.player_move_accumulator=0;e.sprint_turns_remaining=0
    e.player_speed_bonus=0;e.player_speed_bonus_turns=0
    e.true_sight_turns=0;e.player.true_sight=False
    e.local_map.disruption_zones=[]
    equip(e,'tallow_torch')  # Keep targets actually visible in the underground lab.
    for x in range(12,30):
        for y in range(12,30):
            e.local_map.set_tile(x,y,'flagstone',True,True)
            e.local_map.decor.pop((x,y),None)
    e._update_fov()


def equip(e,iid,**kw):
    i=make(e,iid,**kw);e.player.inventory.add(i);e.item_system.use(i,e)
    return i


def enemy(e,iid='hollow_revenant',x=21,y=20):
    a=e.creature_factory.spawn(iid,x,y);assert a
    a.fighter.hp=a.fighter.max_hp=1000;a.fighter._dead=False
    e.data.entities[iid]['speed']=1.0
    a._last_known_px=e.player.x;a._last_known_py=e.player.y
    e.entities.append(a)
    return a


def use(e,iid):
    i=make(e,iid);e.player.inventory.add(i)
    return i,e.item_system.use(i,e)


def run_case(e,ev):
    import pygame
    from engine.item_transfers import drop,take_floor,consume
    from components.ai import _monster_attack_entity,AIState
    from engine.creature_abilities import process_abilities
    from engine.effect_lifecycle import knight_disruption,valid_throw
    if ev.job['scenario']=='roundtrip':return roundtrip(e,ev)
    fixture(e);p=e.player;v=ev.job['variant']
    if v=='armor':
        armor=equip(e,'leather_jack');base=p.fighter.effective_av
        seal,used=use(e,'marrow_seal');consume(e,seal)
        ev.check('D-01','seal immediately contributes mitigation',[True,base+1,20],[used,p.fighter.effective_av,armor._temp_av_hits])
        use(e,'marrow_seal')
        ev.check('D-01','reapplication refreshes without stacking',base+1,p.fighter.effective_av)
        a=enemy(e);e.data.entities[a._creature_id]['damage_dice']='10d1'
        p.fighter.body_limbs=[dict(id='torso',size=1,damage_multiplier=1)]
        armor._temp_av_hits=2
        p.dodge_chance=1;e.rng.seed(53);_monster_attack_entity(a,p,e)
        ev.check('D-01','dodge spends no armor charge',2,armor._temp_av_hits)
        p.dodge_chance=0;e.player_invincible=True;_monster_attack_entity(a,p,e);e.player_invincible=False
        ev.check('D-01','invincibility spends no armor charge',2,armor._temp_av_hits)
        e.entities=[p];e._advance_turn()
        ev.check('D-01','waiting spends no contact charge',2,armor._temp_av_hits)
        losses=[]
        for _ in range(3):
            hp=p.fighter.hp;e.rng.seed(53);_monster_attack_entity(a,p,e);losses.append(hp-p.fighter.hp)
        ev.check('D-01','last charge protects its hit, next hit loses one AV',[losses[0],losses[0]+1],losses[1:])
        ev.check('D-01','expiry clears bonus and recomputes AV',[0,0,base],[armor._temp_av_hits,armor._temp_av_bonus,p.fighter.effective_av])
        use(e,'marrow_seal');drop(e,armor)
        ev.check('D-01','drop removes active armor benefit',[0,20],[p.fighter.effective_av,armor._temp_av_hits])
        take_floor(e,armor);e.item_system.use(armor,e)
        ev.check('D-01','re-equip restores remaining exact-item effect',base+1,p.fighter.effective_av)
    elif v=='coating':
        blade=equip(e,'binding_knife');a=enemy(e)
        definition=e.data.items[blade.item_id];definition['damage_dice']='8d1';definition['crit_chance']=-1
        a.fighter.body_limbs=[dict(id='torso',size=1,damage_multiplier=1)];a.fighter.effective_av=0
        e.data.entities[a._creature_id]['essence_modifiers']={'Revelation':2.0,'Binding':1.0}
        e.data.entities[a._creature_id]['dodge_chance']=0
        pristine=copy.deepcopy(definition)
        for moveset in (False,True):
            blade.temporary_essence=[dict(essence='Revelation',strength=1.0,hits_remaining=1)]
            hp=a.fighter.hp;e.moveset_cooldowns.clear()
            if moveset:e._try_moveset_action(e.display.MOVESET_KEY_1)
            else:e._player_attack(a)
            ev.check('D-02','coating changes real '+('moveset' if moveset else 'normal')+' damage',18,hp-a.fighter.hp)
            ev.check('D-02','connecting attack expires coating',[],blade.temporary_essence)
            ev.check('D-02','shared weapon definition remains unchanged',pristine,definition)
        blade.temporary_essence=[dict(essence='Revelation',strength=1.0,hits_remaining=2)]
        e.data.entities[a._creature_id]['dodge_chance']=1
        e._player_attack(a);e.moveset_cooldowns.clear();e._try_moveset_action(e.display.MOVESET_KEY_1)
        ev.check('D-02','normal and moveset misses retain charges',2,blade.temporary_essence[0]['hits_remaining'])
        e.data.entities[a._creature_id]['dodge_chance']=0;a.fighter.effective_av=999
        e._player_attack(a)
        ev.check('D-02','fully mitigated contact still spends a charge',1,blade.temporary_essence[0]['hits_remaining'])
        a.x=a.y=21;e.local_map.set_tile(21,20,'stone_wall',False,False);e.local_map.set_tile(20,21,'stone_wall',False,False)
        hp=a.fighter.hp;e.moveset_cooldowns.clear()
        e._player_attack(a);spent=e._try_moveset_action(e.display.MOVESET_KEY_1)
        ev.check('D-02','sealed corner blocks both attacks without spending coating',[False,hp,1,{}],[spent,a.fighter.hp,blade.temporary_essence[0]['hits_remaining'],e.moveset_cooldowns])
        a.y=20;e.local_map.set_tile(21,20,'flagstone',True,True);e.local_map.set_tile(20,21,'flagstone',True,True)
        # Sprint damage is scaled before lethal state is committed, including overkill.
        a.fighter.effective_av=0;a.fighter.hp=5;e.sprint_turns_remaining=1
        e.display.SPRINT_HIT_PENALTY=-.9;blade.temporary_essence=[]
        e._player_attack(a)
        ev.check('D-02','sprint reduction cannot leave a living HP pool marked dead',[5,False,True],[a.fighter.hp,a.fighter.is_dead,a.is_alive])
    elif v=='suppression':
        a=enemy(e,'barrow_wight');e.data.entities['barrow_wight']['speed']=0
        a._ability_suppressed_turns=2;p.corruption.value=0
        for left in (1,0):
            e._advance_turn()
            ev.check('D-03','suppressed passive cannot apply through its final turn',[left,0],[a._ability_suppressed_turns,p.corruption.value])
        e._advance_turn()
        ev.check('D-03','passive resumes on following turn',.005,p.corruption.value)
        blade=equip(e,'binding_knife');e._try_moveset_action(e.display.MOVESET_KEY_1)
        ev.check('D-03','authored moveset applies suppression',5,a._ability_suppressed_turns)
        before=p.corruption.value;e._advance_turn()
        ev.check('D-03','application turn ages once and suppresses passive',[4,before],[a._ability_suppressed_turns,p.corruption.value])
    elif v=='disruption':
        a=enemy(e);a.ai.state=AIState.ATTACKING;a._disrupted_turns=2
        pos=(a.x,a.y);hp=p.fighter.hp;acc=a.ai.move_accumulator
        for left in (1,0):
            e._advance_turn()
            ev.check('D-04','disruption blocks actions without banking AI steps',[left,pos,hp,acc],[a._disrupted_turns,(a.x,a.y),p.fighter.hp,a.ai.move_accumulator])
        e._advance_turn()
        ev.check('D-04','normal attack resumes after expiry',True,p.fighter.hp<hp)
        blade=equip(e,'severance_blade');other=enemy(e,x=23);other.tile='rock'
        ev.check('D-04','authored blade is usable through normal item action',True,p.equipment.slots['weapon'] is blade)
        e._try_moveset_action(e.display.MOVESET_KEY_2)
        ev.check('D-04','disconnect matches stable identity, preserves AI state',3,getattr(other,'_disrupted_turns',0))
    elif v=='auras':
        near=enemy(e,'hollow_knight',22);far=enemy(e,'hollow_knight',29)
        for order in ([p,near,far],[p,far,near]):
            e.entities=order
            for a in order[1:]:process_abilities(a,e)
            ev.check('D-05','all knight sources aggregate independent of order',True,p._hollow_knight_disruption)
        near._ability_suppressed_turns=1
        ev.check('D-05','suppressed knight ceases disrupting',False,knight_disruption(e))
        near._ability_suppressed_turns=0;near.is_alive=False
        ev.check('D-05','dead knight ceases disrupting',False,knight_disruption(e))
        e.entities=[p];w=enemy(e,'bog_wraith');w.tile='rock'
        e._update_wraith_aura();e._update_wraith_aura()
        ev.check('D-05','stable wraith identity participates in aura',2,e._wraith_aura_state.get(id(w)))
        w._ability_suppressed_turns=1;e._update_wraith_aura()
        ev.check('D-05','suppression clears wraith penalty immediately',{},e._wraith_aura_state)
        w._ability_suppressed_turns=0;w.is_alive=False;e._update_wraith_aura()
        ev.check('D-05','dead wraith has no aura',{},e._wraith_aura_state)
    elif v=='confirmation':
        item,_=use(e,'wight_concentrate');start=e.world_time.turn
        for key in (pygame.K_n,pygame.K_ESCAPE):
            e.item_system.use(item,e);e._handle_key(key)
            ev.check('D-06','cancel retains exact item and spends no turn',[True,start,None],[p.inventory.contains(item),e.world_time.turn,e._pending_consume])
        e.item_system.use(item,e);e._handle_key(pygame.K_RIGHT)
        ev.check('D-06','pending prompt blocks unrelated movement',[20,20,start],[p.x,p.y,e.world_time.turn])
        e._handle_key(pygame.K_y)
        ev.check('D-06','confirmation consumes once and starts sight',[False,True,19,start+1],[p.inventory.contains(item),p.true_sight,e.true_sight_turns,e.world_time.turn])
        ev.check('D-06','explicit corruption cost applied',True,p.corruption.value>=.05)
        ev.check('D-06','resonance cost applied',True,e.resonance_exposure>.39)
        ev.check('D-06','consumed selection cannot start another dose',False,e.item_system.use(item,e))
        ev.check('D-06','confirmed command cleared',None,e._pending_consume)
        for _ in range(19):e._advance_turn()
        ev.check('D-06','true sight expires exactly',[0,False],[e.true_sight_turns,p.true_sight])
        stale,_=use(e,'wight_concentrate');consume(e,stale);start=e.world_time.turn;e._handle_key(pygame.K_y)
        ev.check('D-06','stale pending owner gives no free effect',[start,False],[e.world_time.turn,p.true_sight])
    elif v=='targeting':
        item,_=use(e,'musk_pellet');start=e.world_time.turn
        ev.check('D-07','throw opens existing placement mode','placement_cursor',e.mode.value)
        e._handle_key(pygame.K_ESCAPE)
        ev.check('D-07','throw cancel keeps pellet and time',[True,start,'local'],[p.inventory.contains(item),e.world_time.turn,e.mode.value])
        e.item_system.use(item,e);e.local_map.visible[:]=True
        for xy in [(-1,20),(27,20)]:ev.check('D-07','out of bounds/range rejected '+str(xy),False,valid_throw(e,*xy))
        e.local_map.set_tile(21,20,'stone_wall',False,False)
        ev.check('D-07','blocked flight rejected',False,valid_throw(e,22,20))
        e.local_map.set_tile(21,20,'flagstone',True,True);e.local_map.visible[22,20]=False
        ev.check('D-07','unseen target rejected',False,valid_throw(e,22,20))
        e._placement_cursor_x=27;e._placement_cursor_y=20;e._handle_key(pygame.K_RETURN)
        ev.check('D-07','invalid confirmation preserves owner and time',[True,start],[p.inventory.contains(item),e.world_time.turn])
        e.local_map.visible[:]=True;e._placement_cursor_x=21;e._placement_cursor_y=20
        a=enemy(e);hp=p.fighter.hp;e._handle_key(pygame.K_RETURN)
        ev.check('D-07','throw consumes once and zone covers application turn',[False,start+1,5,hp],[p.inventory.contains(item),e.world_time.turn,e.local_map.disruption_zones[0]['turns_remaining'],p.fighter.hp])
        for _ in range(5):e._advance_turn()
        ev.check('D-07','zone blocks six phases then disappears',[[],hp],[e.local_map.disruption_zones,p.fighter.hp])
        e._advance_turn();ev.check('D-07','enemy resumes after zone expiry',True,p.fighter.hp<hp)
        stale,_=use(e,'musk_pellet');consume(e,stale)
        ev.check('D-07','stale pellet owner rejected',False,valid_throw(e,20,20))
        e._handle_key(pygame.K_ESCAPE)
    elif v=='movement':
        e.player_speed_bonus=.2;e.player_speed_bonus_turns=100
        start=e.world_time.turn
        for key in [pygame.K_RIGHT,pygame.K_LEFT]*3:e._handle_key(key)
        ev.check('D-08','six moves at 1.2 speed simulate five turns',5,e.world_time.turn-start)
        start=e.world_time.turn;e._handle_key(pygame.K_z)
        ev.check('D-08','wait always advances time',1,e.world_time.turn-start)
        e.player_move_accumulator=0;e.player_speed_bonus=0;e.player_speed_bonus_turns=0;e.sprint_turns_remaining=2
        start=e.world_time.turn
        for key in (pygame.K_RIGHT,pygame.K_LEFT):e._handle_key(key)
        ev.check('D-08','last sprint move retains speed benefit',[1,0],[e.world_time.turn-start,e.sprint_turns_remaining])
        e.player_move_accumulator=0;e.player_speed_bonus=.2;e.player_speed_bonus_turns=1
        start=e.world_time.turn;e._handle_key(pygame.K_RIGHT)
        ev.check('D-08','salve expiry clears speed bonus',[0,0],[e.player_speed_bonus_turns,e.player_speed_bonus])
        e._handle_key(pygame.K_LEFT)
        ev.check('D-08','normal movement after expiry advances',2,e.world_time.turn-start)
        e.local_map.set_tile(21,20,'stone_wall',False,False);start=e.world_time.turn;e.sprint_turns_remaining=2
        e._handle_key(pygame.K_RIGHT)
        ev.check('D-08','blocked move spends neither turn nor sprint charge',[start,2],[e.world_time.turn,e.sprint_turns_remaining])
        e.local_map.set_tile(21,20,'flagstone',True,True);e.player_move_accumulator=0
        e.sprint_turns_remaining=20;e.player_speed_bonus=.2;e.player_speed_bonus_turns=100;start=e.world_time.turn
        for key in ([pygame.K_RIGHT,pygame.K_LEFT]*6)[:11]:e._handle_key(key)
        ev.check('D-08','sprint plus salve composes at 2.2 speed',5,e.world_time.turn-start)
    elif v=='owners':
        # Active-map alias is a real cache pattern; its zone must age once.
        zone=dict(x=20,y=20,radius=3,turns_remaining=3);e.local_map.disruption_zones=[zone]
        e.save_manager.cache.store_submap('d-alias',e.local_map,[])
        coldmap=copy.deepcopy(e.local_map);e.save_manager.cache.store_submap('d-other',coldmap,[])
        a=enemy(e,x=25);a._ability_suppressed_turns=3
        e.entities=[p];e._pending_pursuer_arrivals=[dict(entity=a,entry_x=0,entry_y=20,delay=1)]
        e._advance_turn()
        ev.check('D-09','pending-to-active promotion ages actor once',[True,2],[a in e.entities,a._ability_suppressed_turns])
        ev.check('D-09','active map alias and inactive hot map each age once',[2,2],[zone['turns_remaining'],coldmap.disruption_zones[0]['turns_remaining']])
        e.entities=[p];a._ability_suppressed_turns=3;a.ai.state=AIState.WANDERING
        e._live_pursuers=[(a,e.world_x,e.world_y,'d-other')];e._advance_turn()
        from engine.save_manager import _deserialize_entities
        cached=e.save_manager.cache.load_submap('d-other')
        restored=_deserialize_entities(cached.entities,e)
        ev.check('D-09','retiring live owner serializes aged counter',2,restored[0]._ability_suppressed_turns)
        e._advance_turn()
        restored=_deserialize_entities(cached.entities,e)
        ev.check('D-09','inactive actor records freeze; hot zone expires',[2,[]],[restored[0]._ability_suppressed_turns,coldmap.disruption_zones])
    else:raise AssertionError(v)


def state(e):
    a=next(a for a in e.entities if a is not e.player)
    armor=e.player.equipment.slots['armor_torso'];blade=e.player.equipment.slots['weapon']
    return dict(armor=[armor._temp_av_bonus,armor._temp_av_hits,e.player.fighter.effective_av],coating=blade.temporary_essence,
        actors=[a._ability_suppressed_turns,a._disrupted_turns],zones=e.local_map.disruption_zones,
        timers=[e.true_sight_turns,e.player.true_sight,e.player_speed_bonus,e.player_speed_bonus_turns,e.player_move_accumulator])


def roundtrip(e,ev):
    from components.ai import _monster_attack_entity
    from engine.item_transfers import drop
    phase=ev.job['phase']
    if phase!='read':
        fixture(e);armor=equip(e,'leather_jack');use(e,'marrow_seal');armor._temp_av_hits=2
        blade=equip(e,'binding_knife');blade.temporary_essence=[dict(essence='Revelation',strength=.5,hits_remaining=2)]
        a=enemy(e);a._ability_suppressed_turns=3;a._disrupted_turns=2
        e.local_map.disruption_zones=[dict(x=26,y=26,radius=1,turns_remaining=3)]
        e.true_sight_turns=2;e.player.true_sight=True;e.player_speed_bonus=.2;e.player_speed_bonus_turns=2;e.player_move_accumulator=.5
        ev.record['d_expected']=copy.deepcopy(state(e))
        ev.check('D-10','effect checkpoint published',True,e.save_manager.save(e));ev.record['checkpoint']=hashes(e.save_manager.save_path)
        if phase=='write':return
        use(e,'wight_concentrate');e.local_map.disruption_zones=[]
        ev.check('D-10','same-process reload succeeds',True,e.save_manager.load(e))
        expected=ev.record['d_expected']
    else:expected=read(ev.job['expected'])['d_expected']
    ev.check('D-10','restored instance effects, zones, clocks, credit',expected,state(e))
    ev.check('D-10','unfinished commands cleared',[None,None,'local'],[e._pending_consume,e._pending_throw,e.mode.value])
    a=next(a for a in e.entities if a is not e.player);armor=e.player.equipment.slots['armor_torso']
    # G19 validates direct resolver eligibility too: a disrupted creature
    # cannot spend contact charges. Retain restored timer expiry, then strike.
    e.player.dodge_chance=0
    ev.check('D-10','disrupted direct attack rejected',False,_monster_attack_entity(a,e.player,e))
    ev.check('D-10','rejected contact retains armor charge',2,armor._temp_av_hits)
    for _ in range(2):e._advance_turn()
    ev.check('D-10','restored timers actually expire',[0,False,0,0,1,0],[e.true_sight_turns,e.player.true_sight,e.player_speed_bonus_turns,e.player_speed_bonus,a._ability_suppressed_turns,a._disrupted_turns])
    _monster_attack_entity(a,e.player,e)
    ev.check('D-10','restored armor charge actually consumed',1,armor._temp_av_hits)
    ev.check('D-10','restored zone ages once',1,e.local_map.disruption_zones[0]['turns_remaining'])
    drop(e,armor);ev.check('D-10','restored item still obeys transfer ownership',0,e.player.fighter.effective_av)
