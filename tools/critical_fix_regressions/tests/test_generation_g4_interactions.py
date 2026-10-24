"""Bounded production handlers and ordinary native turns; disposable saves only."""
import copy
import json
import os
from pathlib import Path
import random
import unittest
from unittest.mock import patch
import pygame
import test_generation_g4 as gameplay
import test_generation_g3_lifecycle as lifecycle
from test_effect_persistence import make_engine,GAME_ROOT
from engine.engine import GameMode
from engine.interaction_cursor import InteractionCursor
from engine.save_manager import _serialize_entity,_serialize_world
from generation.placement import digest
from generation.access import enterable,reachable
from g1_support import fingerprint


class G4Interactions(unittest.TestCase):
    setUpClass=classmethod(gameplay.G4Gameplay.setUpClass.__func__)
    setUp=gameplay.G4Gameplay.setUp
    boot=lifecycle.G3Lifecycle.boot

    def visit(self,e,xy):
        e.overmap_cursor_x,e.overmap_cursor_y=xy;e._teleport_to_overmap_cursor()
        self.assertEqual((e.world_x,e.world_y,e.current_submap_id),(*xy,None))

    def interact(self,e,xy):
        # Fixture positioning is explicit; visibility/reach and dispatch are real.
        occupied={(a.x,a.y) for a in e.entities[1:]}
        positions=[(xy[0]+dx,xy[1]+dy) for dx,dy in ((0,1),(1,0),(-1,0),(0,-1))
                   if enterable(e.local_map,(xy[0]+dx,xy[1]+dy),e.data) and (xy[0]+dx,xy[1]+dy) not in occupied]
        self.assertTrue(positions);e.player.x,e.player.y=positions[0];e._update_fov()
        self.assertTrue(InteractionCursor.can_reach(e,*xy))
        e.mode=GameMode.INTERACTION_CURSOR;e.interaction_cursor._cursor_x,e.interaction_cursor._cursor_y=xy
        e.interaction_cursor.candidates=[xy];e._handle_key(pygame.K_RETURN)
        e.text_reader.close();e.mode=GameMode.LOCAL

    def test_waystone_prayer_clay_real_interactions_and_restore(self):
        e=self.boot();e.debug=False;e.player_invincible=True;e.player.inventory.capacity=100
        start=(e.world_map.start_wx,e.world_map.start_wy);self.visit(e,start)
        stone=next(p for p,v in e.local_map.decor.items() if v=='waystone_plinth');self.interact(e,stone)
        self.assertIn(stone,e.local_map.interacted_waystones);inscription=e.local_map.waystone_inscriptions[stone]
        self.assertIn(inscription,e.data.texts)
        civic=next(s for s in e.world_map.plan['settlements'] if s['form']=='grid')
        member=next(m for m in civic['semantics']['members'] if m['waystone']);town=tuple(member['chunk']);self.visit(e,town)
        prayer_xy=next(xy for xy,rows in e.local_map.floor_objects.items() if any(getattr(v,'text_id','')=='waystone_prayer_a' for v in rows))
        self.interact(e,prayer_xy)
        self.assertTrue(any(getattr(v,'text_id','')=='waystone_prayer_a' for v in e.player.inventory.items))
        town_stone=next(p for p,v in e.local_map.decor.items() if v=='waystone_plinth');self.interact(e,town_stone)
        river=next(r for r in e.world_map.plan['routes'] if r['id']=='road-1')['points'][1];river=(river[0]//80,river[1]//43)
        self.visit(e,river);clay=next((x,y) for x in range(80) for y in range(43) if str(e.local_map.tiles[x,y]['terrain'])=='clay_deposit')
        definition=e.data.terrain['clay_deposit'];item_id=definition.get('gather_item',definition.get('harvest_item'))
        before=sum(i.item_id==item_id for i in e.player.inventory.items);e.rng=random.Random(1)
        # A declared bound handles the production gather probability; no terrain rewrite.
        attempts=0
        while attempts<12 and sum(i.item_id==item_id for i in e.player.inventory.items)==before:
            self.interact(e,clay);attempts+=1
        self.assertGreater(sum(i.item_id==item_id for i in e.player.inventory.items),before)
        saved_terrain=str(e.local_map.tiles[clay]['terrain']);self.assertEqual(saved_terrain,definition['depleted_tile'])
        e._handle_key_local(pygame.K_F5);self.assertIsNone(e.save_manager.last_error)
        e.local_map.set_tile(*clay,'mud',True,True);e.player.inventory.items.clear();e._handle_key_local(pygame.K_F9)
        self.assertEqual(str(e.local_map.tiles[clay]['terrain']),saved_terrain)
        self.assertTrue(any(i.item_id==item_id for i in e.player.inventory.items))
        self.visit(e,start);self.assertEqual(e.local_map.waystone_inscriptions[stone],inscription);self.assertIn(stone,e.local_map.interacted_waystones)
        self.visit(e,town);self.assertIn(town_stone,e.local_map.interacted_waystones)
        self.assertFalse(any(getattr(v,'text_id','')=='waystone_prayer_a' for rows in e.local_map.floor_objects.values() for v in rows))
        if os.environ.get('RESONANCE_TEST_EVIDENCE_DIR'):
            (Path(os.environ['RESONANCE_TEST_EVIDENCE_DIR'])/'g4-interactions.json').write_text(json.dumps(dict(start=start,waystone=stone,inscription=inscription,town=town,prayer_taken=True,clay=clay,river=river,gather_attempts=attempts,item=item_id,depleted_terrain=saved_terrain,restore=True,controls='fixture positioning; normal interaction cursor; native AI/survival enabled; player invincible'),indent=2)+'\n')

    def test_ordinary_native_turns_travel_cold_restore_f9_and_late_atomicity(self):
        e=self.boot();e.debug=False;e.player_invincible=True;e.rng=random.Random(20261023)
        xy=tuple(e.world_map.plan['settlements'][0]['members'][0]);self.visit(e,xy)
        natives=list(e.entities[1:]);self.assertGreaterEqual(len(natives),2)
        for i,a in enumerate(natives):a.name=f'G4 native {i}'
        before=[_serialize_entity(a) for a in natives];turn=e.world_time.turn
        for _ in range(8):e._handle_key_local(pygame.K_z)
        self.assertEqual(e.world_time.turn,turn+8);self.assertNotEqual([_serialize_entity(a) for a in natives],before)
        # Remove one native as an explicit saved mutation; no later respawn allowed.
        removed=natives[-1].name;e.entities.remove(natives[-1]);kept={a.name for a in natives[:-1]}
        e.local_map.set_tile(2,2,'mud',True,True)
        if os.environ.get('RESONANCE_TEST_EVIDENCE_DIR'):
            self.render(e,Path(os.environ['RESONANCE_TEST_EVIDENCE_DIR'])/'g4-native-production.png')
        head=e.save_manager.store.token()
        # Normal edge transition, positioned at the declared horizontal street.
        e.player.x,e.player.y=79,21;e._handle_key_local(pygame.K_RIGHT)
        self.assertEqual((e.world_x,e.world_y),(xy[0]+1,xy[1]));self.assertEqual(e.save_manager.store.token(),head)
        e._handle_key_local(pygame.K_F5);self.assertIsNone(e.save_manager.last_error)
        plan=digest(e.world_map.plan)
        reader=make_engine(self.data);self.assertTrue(reader.save_manager.load(reader),reader.save_manager.last_error)
        self.assertEqual(digest(reader.world_map.plan),plan)
        owned=reader._prepare_destination(*xy)
        self.assertEqual(str(owned[0].tiles[2,2]['terrain']),'mud')
        names=[a.name for a in owned[1]]+[a.name for a,*_ in reader._live_pursuers]
        for name in kept:self.assertEqual(names.count(name),1)
        self.assertNotIn(removed,names)
        expected=fingerprint(*owned);owned[0].set_tile(2,2,'grass',True,True)
        reader.debug=False;reader._handle_key_local(pygame.K_F9)
        self.assertEqual(fingerprint(*reader._prepare_destination(*xy)),expected)
        # Late failure after dressing and population: no owner/flag/cache/HEAD change.
        pending=tuple(e.world_map.plan['settlements'][1]['members'][0]);before=digest(_serialize_world(e.world_map));active=e.local_map;actors=list(e.entities);head=e.save_manager.store.token()
        with patch('generation.planned_scene.validate_access',side_effect=ValueError('late restored content failure')):
            self.assertIsNone(e._prepare_destination(*pending))
        self.assertIs(e.local_map,active);self.assertEqual(e.entities,actors);self.assertEqual(digest(_serialize_world(e.world_map)),before)
        self.assertIsNone(e.save_manager.cache.load(*pending));self.assertEqual(e.save_manager.store.token(),head)

    def render(self,e,path):
        from rendering.sprite_registry import SpriteRegistry
        from rendering.renderer import Renderer
        previous=Path.cwd()
        try:
            os.chdir(GAME_ROOT);pygame.init();screen=pygame.display.set_mode((1280,720));e.display.init()
            e.sprite_registry=SpriteRegistry();e.sprite_registry.load()
            renderer=Renderer(e.registry,e.display,e.sprite_registry);renderer._terrain_data=e.data.terrain;renderer._decor_defs=e.data.decoratives
            viewport=pygame.Rect(26,26,1228,668);e._update_fov();cx,cy=e._get_camera(viewport)
            renderer.render(screen,e.local_map,e.entities,cx,cy,viewport,player_x=e.player.x,player_y=e.player.y)
            pygame.image.save(screen,str(path))
        finally:os.chdir(previous)
