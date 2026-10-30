"""G21 controlled boundaries. Factory stats unchanged except disclosed lethal HP/RNG.

Ordinary native formation and prepared tool comparisons live in verify_g21_play.
"""
import copy
import json
import pickle
import random
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
import pygame
import test_gameplay_g20 as g20
from test_gameplay_g20 import snapshot
from test_effect_persistence import load_data, make_engine
from components.ai import AIState, _monster_attack_entity
from components.perception import Perception
from engine.local_rivals import allocate, owner, revalidate, supported
from engine.save_manager import _serialize_entity, _deserialize_entities, _validate_entities
from engine.sound import emit
from world.local_map import LocalMap, make_tile
from world.world_map import Chunk, RegionType, SubMap


class LocalRivalTests(unittest.TestCase):
    setUpClass = classmethod(g20.AudibleEncounterTests.setUpClass.__func__)
    setUp = g20.AudibleEncounterTests.setUp
    actor = g20.AudibleEncounterTests.actor
    decision = g20.AudibleEncounterTests.decision
    def pair(self, a=(12,12), b=(16,12)):
        return self.actor('highland_bandit',*a),self.actor('heath_stalker',*b)

    def test_defaults_empty_and_fresh_exact_directional_definitions(self):
        source=[];p=Perception(hostile_to=source);source.append('player')
        self.assertEqual([],p.hostile_to);self.assertEqual(['player'],Perception().hostile_to)
        a,b=self.pair();self.assertEqual(['player','stalker'],a.perception.hostile_to)
        self.assertEqual(('stalker',['player','outlaw']),(b.perception.faction,b.perception.hostile_to))
        a.perception.hostile_to=[];self.decision(a)
        self.assertIsNone(getattr(a.ai,'local_target',None));self.assertIsNone(getattr(a,'_last_known_px',None))
        b.perception.hostile_to=['unmatched'];self.decision(b)
        self.assertIsNone(getattr(b.ai,'local_target',None))
        a.perception.hostile_to=['stalker'];self.decision(a)
        self.assertEqual(b._individual_id,a.ai.local_target['id'])

    def test_preedit_rows_keep_old_directionality_and_empty_across_factory_restore(self):
        e=self.e;a,b=self.pair()
        for actor in (a,b):
            path=f'roguelike/data/entities/creatures/{actor._creature_id}.json'
            original=json.loads(subprocess.check_output(['git','show','checkpoint/gameplay-g21-start-20261030-a:'+path]))
            actor.perception.faction=original['perception']['faction']
            actor.perception.hostile_to=original['perception']['hostile_to']
        rows=[_serialize_entity(a),_serialize_entity(b)]
        self.assertTrue(all('individual_id' not in r and 'local_target' not in r for r in rows))
        rows[0]['hostile_to']=[]
        e.entities=[e.player]+_deserialize_entities(rows,e)
        for a in e.entities[1:]:self.decision(a)
        self.assertEqual([[],['player']],[a.perception.hostile_to for a in e.entities[1:]])
        self.assertEqual('predator',e.entities[2].perception.faction)
        self.assertTrue(all(getattr(a.ai,'local_target',None) is None for a in e.entities[1:]))

    def test_observe_nearest_stable_tie_retention_and_immediate_contact_switch(self):
        e=self.e;a,b=self.pair(b=(16,11));c=self.actor('heath_stalker',16,13)
        self.decision(a);chosen=a.ai.local_target['id'];self.assertEqual(b._individual_id,chosen)
        e.entities.reverse();e.player.x,e.player.y=14,15;self.decision(a)
        self.assertEqual(chosen,a.ai.local_target['id']) # player does not steal observed rival
        e.player.x,e.player.y=a.x,a.y+1;self.decision(a)
        self.assertIsNone(a.ai.local_target);self.assertEqual(e.player.x,a._last_known_px)
        e.player.x,e.player.y=40,40;b.x,b.y=a.x+1,a.y
        self.decision(a);self.assertEqual(b._individual_id,a.ai.local_target['id'])
        self.assertIsNone(a._last_known_px);self.assertIsNone(a._pending_stair_use)

    def test_sight_darkness_cover_wall_and_player_mask_are_separate(self):
        e=self.e;a,b=self.pair();e.local_map.visible[:]=False
        self.decision(a);self.assertEqual(b._individual_id,a.ai.local_target['id'])
        from engine.local_rivals import clear
        clear(a);a.x,a.y=12,12;e.local_map.set_tile(14,12,'wall',False,False)
        self.decision(a);self.assertIsNone(a.ai.local_target)
        e.local_map.set_tile(14,12,'grass',True,True)
        a.ai.take_turn(a,e.local_map,e.entities,e.player,e.log,random.Random(1),0,engine=e)
        self.assertIsNone(a.ai.local_target)
        a.perception.sees_in_dark=True;self.decision(a);self.assertIsNotNone(a.ai.local_target)
        clear(a);a.x,a.y=12,12;b.x=21
        e.local_map.set_tile(21,12,'tall_grass',True,True)
        self.assertEqual('concealment',e.data.terrain['tall_grass']['secondary_effect'])
        self.decision(a);self.assertIsNone(a.ai.local_target)

    def test_sound_never_identifies_and_selected_target_discards_displaced_intents(self):
        e=self.e;a,b=self.pair(b=(18,12));e.local_map.set_tile(15,12,'wall',False,False)
        emit(e,14,14,'flint',maker=b);self.decision(a)
        self.assertIsNone(getattr(a.ai,'local_target',None));self.assertEqual(AIState.INVESTIGATING,a.ai.state)
        e.local_map.set_tile(15,12,'grass',True,True);self.decision(a)
        self.assertEqual(AIState.RIVAL,a.ai.state);self.assertIsNone(a.ai.sound_interest)
        emit(e,13,13,'combat');self.assertIsNone(a.ai.sound_interest)
        b.is_alive=False;self.decision(a)
        self.assertIsNone(a.ai.local_target);self.assertIsNone(a.ai.sound_interest)

    def test_hidden_trail_uses_last_observation_inclusive_world_deadline(self):
        e=self.e;a,b=self.pair();self.decision(a);trail=copy.deepcopy(a.ai.local_target)
        b.x,b.y=35,35;e.world_time.turn=trail['deadline']
        self.assertIs(b,revalidate(e,a));self.decision(a)
        if a.ai.local_target:self.assertEqual(trail,a.ai.local_target)
        # A paused actor expires without speed/decisions; FOV is not a clock.
        a.ai.local_target=trail;a.ai.state=AIState.RIVAL;a._disrupted_turns=6
        e.world_time.turn=trail['deadline']+1;e._update_fov()
        self.assertIsNone(a.ai.local_target)
        self.assertIsNone(a._last_known_px)

    def test_current_observed_hostile_wins_over_hidden_trail(self):
        e=self.e;a,b=self.pair();self.decision(a);b.x,b.y=35,35
        e.player.x,e.player.y=a.x,a.y+3;self.decision(a)
        self.assertIsNone(a.ai.local_target);self.assertEqual(e.player.x,a._last_known_px)

    def test_missing_dead_foreign_and_sibling_references_clear_without_substitution(self):
        e=self.e;a,b=self.pair();c=self.actor('heath_stalker',30,30);self.decision(a)
        saved=copy.deepcopy(a.ai.local_target)
        for mutation in ('missing','dead','foreign'):
            a.ai.local_target=copy.deepcopy(saved);a.ai.state=AIState.RIVAL
            b.is_alive=mutation!='dead'
            e.entities=[e.player,a,c]+([] if mutation=='missing' else [b])
            if mutation=='foreign':a.ai.local_target['owner']='1,0/'
            self.assertIsNone(revalidate(e,a));self.assertIsNone(a.ai.local_target)

    def test_candidate_boundary_self_items_special_unsupported_and_phantom(self):
        e=self.e;a,b=self.pair();b.perception.faction='stalker';b.ai=None
        specials=[self.actor(i,14,14) for i in ('stone_lurker','briar_lurker','plague_crow')]
        for s in specials:s.perception.faction='stalker';self.assertFalse(supported(s))
        self.decision(a);self.assertIsNone(getattr(a.ai,'local_target',None))
        self.assertIsNone(getattr(a,'_individual_id',None))
        # Display name does not turn a rival into the player.
        b.ai=e.creature_factory.spawn('heath_stalker',0,0).ai;b.name='Player'
        self.decision(a);self.assertIsNotNone(a.ai.local_target)
        position=(a.x,a.y);e.ai_system.process_single(a,e.local_map,12,12,e.entities,e.log,engine=e)
        self.assertEqual(position,(a.x,a.y))

    def test_commit_rechecks_instance_door_death_and_disrupted_roles(self):
        e=self.e;a,b=self.pair(b=(13,12));b.fighter.hp=100;self.decision(a)
        # Disclosed high HP isolates commit legality without lethal interference. Disruption of the defender doesn't make it immune.
        b._disrupted_turns=6
        with patch('engine.sound.emit',wraps=emit) as sounds:
            self.assertTrue(_monster_attack_entity(a,b,e));self.assertEqual(1,sounds.call_count)
            for setup in ('door','dead','stale','attacker_pause'):
                b.is_alive=True;e.local_map.set_tile(b.x,b.y,'grass',True,True);a._disrupted_turns=0
                a.ai.local_target['id']=b._individual_id
                if setup=='door':e.local_map.set_tile(b.x,b.y,'door_closed',False,False)
                if setup=='dead':b.is_alive=False
                if setup=='stale':a.ai.local_target['id']='0,0/:99999999'
                if setup=='attacker_pause':a._disrupted_turns=1
                count=sounds.call_count;self.assertFalse(_monster_attack_entity(a,b,e));self.assertEqual(count,sounds.call_count)
                if a.ai.local_target is None:
                    a.ai.local_target=dict(id=b._individual_id,owner=owner(e),x=b.x,y=b.y,deadline=e.world_time.turn+10)

    def test_creature_fatal_physical_once_no_assist_credit_or_hidden_feedback(self):
        e=self.e;a,b=self.pair(b=(13,12));self.decision(a)
        b.fighter.hp=1;e.rng=random.Random(4);e.local_map.visible[:]=False
        start=len(e.log.messages);xp=e.player.level.exp
        for _ in range(30):
            if not b.is_alive:break
            _monster_attack_entity(a,b,e)
        self.assertFalse(b.is_alive);self.assertFalse(b.blocks_movement)
        corpse=e.local_map.floor_objects[b.x,b.y][0]
        self.assertEqual(('corpse','heath_stalker',150),(corpse.item_id,corpse.source_creature,corpse.decay_timer))
        self.assertEqual(xp,e.player.level.exp);self.assertEqual(start,len(e.log.messages))
        e._on_entity_death(b,killer=e.player)
        self.assertEqual(xp,e.player.level.exp);self.assertEqual(1,len(e.local_map.floor_objects[b.x,b.y]))

    def test_unknown_killer_neutral_player_direct_and_moveset_preserved(self):
        e=self.e;a,b=self.pair();xp=e.player.level.exp
        e._on_entity_death(a);self.assertEqual(xp,e.player.level.exp)
        e._on_entity_death(b,killer=e.player);self.assertGreater(e.player.level.exp,xp)

    def test_observed_rival_feedback_never_addresses_the_player_or_hidden_victim(self):
        e=self.e;a,b=self.pair(b=(13,12));e.local_map.visible[:]=True
        self.decision(a)
        text=' '.join(m.text for m in e.log.messages)
        self.assertIn('strikes at the Heath Stalker',text);self.assertNotIn('at thee',text)
        self.assertNotRegex(text,r'\b(thy|thou|thee)\b')
        e.local_map.visible[b.x,b.y]=False;before=len(e.log.messages)
        _monster_attack_entity(a,b,e);self.assertEqual(before,len(e.log.messages))

    def test_save_f9_cold_individual_siblings_and_legacy_neutral(self):
        e=self.e;a,b=self.pair();c=self.actor('heath_stalker',24,24);self.decision(a)
        identity=a._individual_id;chosen=b._individual_id
        self.assertTrue(e.save_manager.save(e),e.save_manager.last_error);saved=snapshot(e)
        a.ai.local_target=None;b.x=35;e.world_time.turn+=3
        self.assertTrue(e.save_manager.load(e),e.save_manager.last_error)
        self.assertEqual(saved,snapshot(e));a=next(a for a in e.entities if getattr(a,'_individual_id',None)==identity)
        self.assertEqual(chosen,a.ai.local_target['id'])
        code='from test_gameplay_g20 import cold;import json,sys;print(json.dumps(cold(sys.argv[1])))'
        r=subprocess.run([sys.executable,'-B','-c',code,str(self.root)],capture_output=True,text=True)
        self.assertEqual(0,r.returncode,r.stderr)
        self.assertEqual(json.loads(json.dumps(saved)),json.loads(r.stdout.strip().splitlines()[-1]))
        row=_serialize_entity(a);row.pop('local_target');row.pop('individual_id');row['ai_state']='wandering'
        restored=_deserialize_entities([row],e)[0]
        self.assertIsNone(restored.ai.local_target);self.assertIsNone(restored._individual_id)
        from engine.save_components import restore_actor_runtime
        a.ai.state=AIState.RIVAL;a.ai.local_target=dict(id=chosen,owner=owner(e),x=0,y=0,deadline=e.world_time.turn+10)
        restore_actor_runtime(a,row)
        self.assertIsNone(a.ai.local_target);self.assertEqual(AIState.WANDERING,a.ai.state)


    def test_malformed_state_duplicate_types_bounds_and_conflicting_intent_reject(self):
        e=self.e;a,b=self.pair();self.decision(a);row=_serialize_entity(a)
        for field,value in (('id',True),('owner',[]),('x',True),('y',43),('deadline',-1)):
            bad=copy.deepcopy(row);bad['local_target'][field]=value
            with self.assertRaises(ValueError):_validate_entities([bad],e.data,e.local_map)
        for key,value in (('individual_id',3),('ai_state','hunting'),('ai_type','AmbushAI')):
            bad=copy.deepcopy(row);bad[key]=value
            with self.assertRaises(ValueError):_validate_entities([bad],e.data,e.local_map)
        bad=copy.deepcopy(row);bad['component_state']['actor']['_last_known_px']=0
        with self.assertRaises(ValueError):_validate_entities([bad],e.data,e.local_map)
        with self.assertRaises(ValueError):_validate_entities([row,row],e.data,e.local_map)
        row['local_target'].update(x=0,y=0);_validate_entities([row],e.data,e.local_map)

    def test_rival_edge_and_stairs_stay_local_hot_then_cold_revisit_expires(self):
        e=self.e;a,b=self.pair(a=(76,12),b=(76,16));e.player.x,e.player.y=79,12
        a.perception.hostile_to=['stalker'];b.perception.hostile_to=['outlaw'];self.decision(a)
        e.world_map.width=2;e.world_map.set(Chunk(1,0,RegionType.PLAINS,29418,visited=True))
        m=LocalMap();m.tiles[:]=make_tile('grass',True,True);e.save_manager.cache.store(1,0,m,[])
        position=(a.x,a.y);e._handle_key(pygame.K_RIGHT)
        self.assertEqual([],e._live_pursuers);self.assertEqual([],e._pending_pursuer_arrivals)
        self.assertEqual([e.player],e.entities)
        e.world_time.turn+=20;self.assertTrue(e.save_manager.save(e),e.save_manager.last_error)
        self.assertTrue(e.save_manager.load(e),e.save_manager.last_error)
        e._transition_chunk(-1,0)
        a=next(a for a in e.entities if getattr(a,'_creature_id',None)=='highland_bandit')
        self.assertEqual(position,(a.x,a.y));self.assertIsNone(a.ai.local_target)
        # Adjacent stairs with an active rival intent cannot extract either actor.
        b=next(a for a in e.entities if getattr(a,'_creature_id',None)=='heath_stalker')
        e.player.x,e.player.y=a.x,a.y-1;self.decision(a)
        sid='g21-stair';sub=SubMap(sid,'cave','G21 controlled',19,generated=True,entry_x=12,entry_y=12)
        e.world_map.get(0,0).submaps.append(sub)
        e.local_map.submap_links[e.player.x,e.player.y]=sid;e.local_map.set_tile(e.player.x,e.player.y,'stairs_down',True,True)
        e.save_manager.cache.store_submap(sid,m,[]);e._descend_to_submap(sid)
        self.assertEqual([],e._live_pursuers);self.assertEqual([],e._pending_pursuer_arrivals)

    def test_malformed_real_checkpoint_rejects_before_installing_any_state(self):
        e=self.e;a,b=self.pair();self.decision(a)
        self.assertTrue(e.save_manager.save(e));before=snapshot(e)
        player,world,local,cache=e.player,e.world_map,e.local_map,e.save_manager.cache
        payloads={p.relative_to(e.save_manager.checkpoint_path()).as_posix():p.read_bytes()
                  for p in e.save_manager.checkpoint_path().rglob('*') if p.is_file() and p.name!='manifest.json'}
        name=next(k for k in payloads if k.endswith('.pkl'))
        scene=pickle.loads(payloads[name]);scene.entities[0]['local_target']['deadline']=True
        payloads[name]=pickle.dumps(scene)
        generation,_,_=e.save_manager.store.publish(payloads,None,e.save_manager.store.token())
        e.save_manager.generation=generation
        self.assertFalse(e.save_manager.load(e));self.assertIs(player,e.player)
        self.assertIs(world,e.world_map);self.assertIs(local,e.local_map);self.assertIs(cache,e.save_manager.cache)
        self.assertEqual(before,snapshot(e))

    def test_rng_independent_lazy_identity_and_dead_actor_loses_its_later_speed_step(self):
        e=self.e;a,b=self.pair(b=(13,12));before=e.rng.getstate()
        allocate(e,[a,b]);self.assertEqual(before,e.rng.getstate())
        # Disclosed HP and RNG boundary: one ordinary lethal strike before the
        # later scheduled actor's speed budget. No bonus attack/action is injected.
        a.perception.hostile_to=['stalker'];b.perception.hostile_to=['outlaw']
        b.fighter.hp=1;e.rng=random.Random(4)
        with patch.object(b.ai,'take_turn',wraps=b.ai.take_turn) as later:
            for _ in range(20):
                e.ai_system.process(e.entities,e.player,e.local_map,e.world_map,0,0,e.log,e.world_time,e.data,engine=e)
                if not b.is_alive:break
            calls=later.call_count
            self.assertFalse(b.is_alive)
            e.ai_system.process(e.entities,e.player,e.local_map,e.world_map,0,0,e.log,e.world_time,e.data,engine=e)
            self.assertEqual(calls,later.call_count)

    def test_nonadjacent_observed_rivals_close_and_attack_with_normal_credit(self):
        e=self.e;a,b=self.pair(b=(18,12));start=abs(a.x-b.x)
        self.decision(a);self.assertLess(abs(a.x-b.x),start)
        for _ in range(6):
            e._advance_turn()
            if not a.is_alive or not b.is_alive:break
        self.assertTrue(a.fighter.hp<16 or b.fighter.hp<16)
        self.assertEqual(0,e.player.level.exp)

    def test_second_authored_geometry_door_changes_burst_not_anonymous_sound(self):
        from engine.scene_generation import create_submap
        from engine.effect_lifecycle import zone_covers
        e=self.e
        raw=json.loads((Path(__file__).resolve().parents[1]/'fixtures/g20/corner_store.json').read_text())
        raw['id']='g21_corner_boundary';raw['special_tiles']=[
            dict(type='creature',x=6,y=4,creature_id='highland_bandit'),
            dict(type='creature',x=8,y=4,creature_id='heath_stalker')]
        e.data=copy.copy(e.data);e.data.layouts=dict(e.data.layouts);e.data.layouts[raw['id']]=raw
        sub=SubMap('g21-corner','cave','G21 corner fixture',29417,layout_id=raw['id'])
        result=create_submap(e.world_map,0,0,sub,e.data,e.item_factory,e.creature_factory,80,43)
        e.local_map=result.local_map;e.entities=[e.player]+result.actors;e.player.x,e.player.y=result.spawn
        a,b=result.actors;zone=dict(x=a.x,y=a.y,radius=3,turns_remaining=6)
        self.assertTrue(zone_covers(e.local_map,zone,a.x,a.y));self.assertFalse(zone_covers(e.local_map,zone,b.x,b.y))
        self.assertGreater(emit(e,a.x,a.y,'musk',maker=e.player),0)
        self.assertIsNone(getattr(b.ai,'local_target',None));self.assertIsNone(getattr(b,'_last_known_px',None))
        e.local_map.set_tile(a.x+1,a.y,'door_open',True,True)
        self.assertTrue(zone_covers(e.local_map,zone,b.x,b.y))

    def test_individual_survives_genuine_player_transfer_and_local_switch_once(self):
        e=self.e;e.world_map.width=2
        e.world_map.set(Chunk(1,0,RegionType.PLAINS,29418,visited=True))
        m=LocalMap();m.tiles[:]=make_tile('grass',True,True)
        rival=e.creature_factory.spawn('heath_stalker',4,12)
        e.save_manager.cache.store(1,0,m,[rival])
        a=self.actor('highland_bandit',77,12);e.player.x,e.player.y=79,12
        self.decision(a);allocate(e,[a]);identity=a._individual_id
        e._handle_key(pygame.K_RIGHT)
        self.assertTrue(any(lp[0] is a for lp in e._live_pursuers) or any(r['entity'] is a for r in e._pending_pursuer_arrivals) or a in e.entities)
        self.assertTrue(e.save_manager.save(e),e.save_manager.last_error)
        self.assertTrue(e.save_manager.load(e),e.save_manager.last_error)
        a=next(x for x in [r[0] for r in e._live_pursuers]+[r['entity'] for r in e._pending_pursuer_arrivals]+e.entities
               if getattr(x,'_individual_id',None)==identity)
        for _ in range(15):
            e._advance_turn()
            if getattr(a.ai,'local_target',None):break
        self.assertIn(a,e.entities);self.assertEqual(identity,a._individual_id)
        self.assertIsNotNone(a.ai.local_target);self.assertIsNone(a._last_known_px)
        self.assertFalse(any(lp[0] is a for lp in e._live_pursuers))
        self.assertFalse(any(r['entity'] is a for r in e._pending_pursuer_arrivals))
        self.assertEqual(1,sum(x is a for x in e.entities))
        self.assertTrue(e.save_manager.save(e),e.save_manager.last_error)
        self.assertTrue(e.save_manager.load(e),e.save_manager.last_error)
        self.assertEqual(1,sum(getattr(x,'_individual_id',None)==identity for x in e.entities))
