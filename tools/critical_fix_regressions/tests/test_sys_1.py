"""SYS-1 contracts; controlled geometry and disposable saves, production consumers."""
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest
import pygame
import test_ai_9 as ai9
from engine.save_manager import _serialize_entity
from engine.ai_profiles import validate_saved


class RegroupLifecycleTests(unittest.TestCase):
    setUpClass = classmethod(ai9.CompositionTests.setUpClass.__func__)
    setUp = ai9.CompositionTests.setUp

    def test_engine_exhausted_hold_concealment_restore_and_cold_continuation(self):
        e = self.e
        a = e.creature_factory.spawn('barrow_shy_listener',16,12)
        e.entities.append(a)
        a.ai.maneuver_config['modules'][0]['opportunity_budget'] = 2
        a.fighter.hp = 7
        b = e.creature_factory.spawn('hollow_revenant',17,13)
        e.entities.append(b)
        # Fixture-only stationary supporter, no policy or visibility overrides.
        e.data.entities['hollow_revenant']['speed'] = 0
        for _ in range(2): e._handle_key(pygame.K_PERIOD)
        c = a.ai.maneuvers['current']
        self.assertEqual((0,2),(c['left'],c['hold_left']))
        self.assertEqual(c['goal'],[a.x,a.y])
        validate_saved(_serialize_entity(a),e.local_map)
        e._handle_key(pygame.K_F5)
        self.assertTrue(e.save_manager.save_exists(),e.save_manager.last_error)
        # Uninterrupted holds remain legal and paid, including after F9.
        e._handle_key(pygame.K_F9); a=e.entities[1]
        for remaining in (1,0):
            before=e.world_time.turn;e._handle_key(pygame.K_PERIOD)
            self.assertEqual(before+1,e.world_time.turn)
            self.assertEqual('regroup_hold',a.ai.trace[-1]['reason'])
            self.assertEqual(remaining,(a.ai.maneuvers['current'] or {}).get('hold_left',0))
        self.assertTrue(a.ai.maneuvers['regroup_spent'])
        e._handle_key(pygame.K_F9); a=e.entities[1]
        # Expose the final-credit goal through actual normal vision. Player
        # position is disclosed fixture setup; all decisions/actions are real.
        e.player.x,e.player.y=16,12;e._update_fov()
        self.assertTrue(e.normal_player_vision()['visible'][a.x,a.y])
        old=(a.x,a.y);turn=e.world_time.turn;e._handle_key(pygame.K_PERIOD)
        self.assertEqual(turn+1,e.world_time.turn)
        self.assertNotEqual(old,(a.x,a.y))
        self.assertEqual('seek_concealment',a.ai.trace[-1]['reason'])
        self.assertEqual(1,len(a.ai.trace[-1]['steps']))
        self.assertFalse(a.ai.trace[-1]['bonus_consumed'])
        self.assertIsNone(a.ai.maneuvers['current'])
        self.assertTrue(a.ai.maneuvers['regroup_spent'])
        before=_serialize_entity(a);validate_saved(before,e.local_map)
        e._handle_key(pygame.K_F5);e._handle_key(pygame.K_F9)
        self.assertEqual(before,_serialize_entity(e.entities[1]))
        script = """
import json,pygame
from pathlib import Path
from unittest.mock import patch
from test_effect_persistence import make_engine,load_data
from engine.save_manager import _serialize_entity
from engine.ai_profiles import validate_saved
pygame.init()
with patch('engine.save_manager.SAVE_DIR',Path(__import__('sys').argv[1])): e=make_engine(load_data())
e.debug=False
assert e.save_manager.load(e),e.save_manager.last_error
a=e.entities[1];before=_serialize_entity(a)
assert not e.normal_player_vision()['visible'][a.x,a.y]
e._handle_key(pygame.K_PERIOD)
validate_saved(_serialize_entity(a),e.local_map)
assert a.ai.maneuvers['current'] is None and a.ai.maneuvers['regroup_spent']
print(json.dumps(before))
"""
        result=subprocess.run([sys.executable,'-X','utf8','-B','-c',script,str(self.root)],
                              capture_output=True,text=True)
        self.assertEqual(0,result.returncode,result.stderr)
        self.assertEqual(before,json.loads(result.stdout.splitlines()[-1]))

    def test_defensive_continuation_rejects_exhausted_off_goal_without_moving(self):
        from engine.enemy_maneuvers import _continue, REGROUP
        t=ai9.CompositionTests();t.e=self.e
        a=t.actor(moves=(REGROUP,),regroup_when_wounded=dict(opportunity_budget=2))
        t.actor(x=17,y=13,moves=None,alarms=None);a.fighter.hp=7
        t.decision(a);t.phase(a)
        a.x-=1;old=(a.x,a.y)
        with self.assertRaises(ValueError):validate_saved(_serialize_entity(a),self.e.local_map)
        self.assertIsNone(_continue(a.ai,self.e,a,[],1))
        self.assertEqual(old,(a.x,a.y));self.assertIsNone(a.ai.maneuvers['current'])
        self.assertTrue(a.ai.maneuvers['regroup_spent'])
