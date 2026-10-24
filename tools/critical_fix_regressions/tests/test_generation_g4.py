"""G4 positive contracts derived from the independently reproduced G3 failures."""
import contextlib
import copy
import io
import json
import os
from pathlib import Path
import random
import tempfile
import unittest
from unittest.mock import patch
from test_effect_persistence import load_data, GAME_ROOT
from generation.context import GenerationError
from generation.world_gen import generate_world, BIOME_ZONES
from generation.world_plan import address, cells, settings, bands, Reservations, _plot
from generation.placement import digest, transform
from engine.scene_generation import create_surface
from engine.item_factory import ItemFactory
from engine.creature_factory import CreatureFactory
from world.world_map import WorldMap
from g1_support import fingerprint


class G4Gameplay(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data=load_data(); cls.world=WorldMap(128,128); cls.world.seed=20261023
        with contextlib.redirect_stdout(io.StringIO()): generate_world(cls.world,cls.data,random.Random(0))

    def setUp(self):
        tmp=tempfile.TemporaryDirectory(); self.addCleanup(tmp.cleanup); self.root=Path(tmp.name)
        p=patch('engine.save_manager.SAVE_DIR',self.root); p.start(); self.addCleanup(p.stop)
        cap=contextlib.redirect_stdout(io.StringIO()); cap.__enter__(); self.addCleanup(cap.__exit__,None,None,None)

    def scene(self,xy,world=None):
        w=world or self.world
        return create_surface(w,w.get(*xy),self.data,ItemFactory(self.data),CreatureFactory(self.data),80,43)

    def test_every_member_semantics_native_policy_and_determinism(self):
        observed=[]
        for s in self.world.plan['settlements']:
            for member in s['semantics']['members']:
                xy=member['chunk']; ch=self.world.get(*xy); r=self.scene(xy); native=r.local_map.native_generation_context
                self.assertEqual(ch.name,s['semantics']['name']); self.assertEqual(r.metadata.town_data.name,ch.name)
                self.assertEqual(ch.zones,BIOME_ZONES['town']); self.assertEqual(ch.town_role,member['role'])
                self.assertEqual(ch.difficulty,member['difficulty']); self.assertEqual(ch.resonance,member['resonance'])
                self.assertEqual(native['district'],member['district'])
                self.assertGreaterEqual(len(r.actors),2); self.assertLessEqual(len(r.actors),6)
                self.assertEqual(len(r.metadata.town_data.creature_spawns),len(r.actors))
                positions={(a.x,a.y) for a in r.actors}; self.assertEqual(len(positions),len(r.actors))
                self.assertFalse(positions & r.local_map.protected_cells)
                for a in r.actors:
                    self.assertTrue(r.local_map.walkable[a.x,a.y]); self.assertIsNotNone(a.ai)
                again=self.scene(xy)
                self.assertEqual(fingerprint(r.local_map,r.actors,r.metadata.town_data),fingerprint(again.local_map,again.actors,again.metadata.town_data))
                stones=[p for p,v in r.local_map.decor.items() if v=='waystone_plinth']
                prayers=[v for objects in r.local_map.floor_objects.values() for v in objects if getattr(v,'text_id','')=='waystone_prayer_a']
                self.assertEqual(len(stones),int(member['waystone'])); self.assertEqual(len(prayers),int(member['waystone']))
                observed.append(dict(form=s['form'],chunk=xy,role=member['role'],district=member['district'],actors=len(r.actors),waystones=len(stones)))
        self.assertEqual({r['form'] for r in observed},{'grid','roadside'})
        if os.environ.get('RESONANCE_TEST_EVIDENCE_DIR'):
            (Path(os.environ['RESONANCE_TEST_EVIDENCE_DIR'])/'g4-native-members.json').write_text(json.dumps(observed,indent=2)+'\n')

    def test_final_geometry_start_clay_and_late_failure(self):
        from generation.access import reachable
        start=(self.world.start_wx,self.world.start_wy); r=self.scene(start); m=r.local_map
        stones=[p for p,v in m.decor.items() if v=='waystone_plinth']; self.assertEqual(len(stones),1)
        reached=reachable(m,r.spawn,self.data)
        self.assertTrue(any((stones[0][0]+dx,stones[0][1]+dy) in reached for dx,dy in ((1,0),(-1,0),(0,1),(0,-1))))
        self.assertEqual(len(m.submap_links),1); self.assertTrue(set(m.submap_links)<=reached)
        crossing=next(r for r in self.world.plan['routes'] if r['id']=='road-1')['points'][1]
        r=self.scene(address(*crossing)[:2]); m=r.local_map
        clay={(x,y) for x in range(80) for y in range(43) if str(m.tiles[x,y]['terrain'])=='clay_deposit'}
        self.assertGreater(len(clay),0); self.assertFalse(clay&m.protected_cells)
        for x,y in clay:
            self.assertTrue(any(m.in_bounds(x+dx,y+dy) and str(m.tiles[x+dx,y+dy]['terrain']) in ('river_water','river_bank','river_stones') for dx in range(-3,4) for dy in range(-3,4)))
        before=digest(self.world.plan); ch=self.world.get(*start); old=copy.deepcopy(vars(ch))
        with patch('generation.planned_scene.validate_access',side_effect=GenerationError('late restored-pass failure')):
            with self.assertRaisesRegex(GenerationError,'late restored'): self.scene(start)
        self.assertEqual(vars(ch),old); self.assertEqual(digest(self.world.plan),before)
