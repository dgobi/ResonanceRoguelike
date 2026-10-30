"""Versioned workshop content, native ownership, preparation and genuine old worlds."""
import contextlib
import io
import json
from pathlib import Path
import random
import tempfile
import unittest
from unittest.mock import patch

import pygame
from test_effect_persistence import load_data, make_engine, GAME_ROOT
from generation.placement import transform, entrance_cells, NORMALS
from generation.structure_preview import preview
from engine.item_transfers import take_container, take_floor
from engine.crafting import plan_craft
from rendering.craft_screen import CraftScreen
from g1_support import fingerprint


class WorkshopPreparation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data=load_data();pygame.init()

    def setUp(self):
        tmp=tempfile.TemporaryDirectory(prefix='resonance-g16-test-');self.addCleanup(tmp.cleanup)
        p=patch('engine.save_manager.SAVE_DIR',Path(tmp.name));p.start();self.addCleanup(p.stop)

    def room(self,rotation=0):
        raw=transform(self.data.structures['workshop_b'],rotation,False)
        p=raw['placement'];door=p['entrances'][0];dx,dy=NORMALS[door['normal']]
        report,m,actors=preview(raw,'ordinary_building',self.data,category='commercial',expectations={
            'entry':dict(x=door['x']+dx,y=door['y']+dy),
            'targets':p['targets']+[dict(x=x,y=y,kind='floor',required=True) for x,y in entrance_cells(door)]})
        self.assertTrue(report['passed'],report['access'])
        return raw,report,m,actors

    def test_all_rotations_real_content_and_clear_working_floor(self):
        old=self.data.structures['workshop_a'];new=self.data.structures['workshop_b']
        for field in ('width','height','facing'):
            self.assertEqual(old[field],new[field])
        for field in ('contexts','rotations','mirror_x','buffer','approach','road_relation','entrances'):
            self.assertEqual(old['placement'][field],new['placement'][field])
        self.assertNotIn('interior_loot_table',new)
        for pool,iid in (('workshop_b_musk','stalker_musk_gland'),('workshop_b_fuel','wood_bundle')):
            self.assertEqual(dict(id=pool,roll_count=[1,1],items=[dict(item_id=iid,weight=1)]),self.data.loot_pools[pool])
        for rotation in (0,90,180,270):
            with self.subTest(rotation=rotation):
                raw,report,m,actors=self.room(rotation)
                self.assertEqual(1,len(m.container_state))
                crate,=m.container_state.values()
                self.assertEqual('crate',crate['decor_id'])
                self.assertEqual(['stalker_musk_gland','wood_bundle'],sorted(i.item_id for i in crate['items']))
                notes=[i for rows in m.floor_objects.values() for i in rows if i.text_id=='workshop_musk_notes_b']
                self.assertEqual(1,len(notes))
                self.assertFalse(any(i.item_id=='musk_pellet' for rows in m.floor_objects.values() for i in rows))
                # The two new work-floor targets follow the original floor target.
                # Exercise the real validators at this exact rotated pair.
                e=make_engine(self.data);e.local_map=m
                floors=[tuple(r['xy']) for r in report['access'] if r.get('kind')=='floor']
                fire,dry=floors[1:3]
                self.assertTrue(e._is_valid_placement(*fire));self.assertTrue(e._is_valid_placement(*dry))
                m.decor[fire]='campfire_lit'
                self.assertTrue(e._is_valid_drying(*dry))

    def test_live_roles_preserve_membership_order_and_native_primary_selection(self):
        import copy
        from historical_selection import historical_profiles
        from generation.plan_preview import planned_preview
        from generation.world_gen import generate_world
        from world.world_map import WorldMap
        from engine.scene_generation import create_surface
        from engine.item_factory import ItemFactory
        from engine.creature_factory import CreatureFactory
        expected=historical_profiles()
        for form in ('grid','roadside'):
            for rows in expected['profiles'][form]['roles'].values():
                for row in rows:
                    if row['asset'] in ('tool_shed_a','apothecary_a','workshop_a'):
                        if row['asset']=='workshop_a':self.assertEqual(dict(asset='workshop_a',weight=1.0,max_per_settlement=5),row)
                        row['asset']='workshop_c' if row['asset']=='workshop_a' else row['asset'][:-1]+'b'
        self.assertEqual(expected,self.data.settlement_profiles)
        for form in ('grid','roadside'):
            selected=copy.deepcopy(self.data.settlement_profiles)
            selected['profiles'][form]['roles']['commercial']=[dict(asset='workshop_b',weight=1.0,max_per_settlement=128)]
            with contextlib.redirect_stdout(io.StringIO()):
                report=planned_preview(self.data,20261023,self.data.structures['workshop_b'],category='commercial',context=form,selection=selected)
            self.assertTrue(report['previews'])
            self.assertTrue(any(p['asset']=='workshop_b' and p['context']==form for p in report['plan']['placements']))
        w=WorldMap(128,128);w.seed=20261023
        with contextlib.redirect_stdout(io.StringIO()):generate_world(w,self.data,random.Random(w.seed))
        self.assertEqual((73,99),(w.start_wx,w.start_wy))
        p=next(p for p in w.plan['placements'] if p['id']=='settlement-0-cross-market-lot-1-44-S-0-building')
        self.assertEqual('workshop_c',p['asset']);self.assertEqual((75,100),(p['origin'][0]//80,p['origin'][1]//43))
        self.assertFalse(any(p['asset']=='workshop_a' and p['context'] in ('grid','roadside') for p in w.plan['placements']))
        scene=create_surface(w,w.get(75,100),self.data,ItemFactory(self.data),CreatureFactory(self.data),80,43)
        xy=next((t['x']%80,t['y']%43) for t in p['targets'] if t['kind']=='container')
        self.assertEqual(['stalker_musk_gland','wood_bundle'],sorted(i.item_id for i in scene.local_map.container_state[xy]['items']))

    def test_exact_native_gland_transfer_processing_and_depletion_survive_disk_revisit(self):
        from test_gameplay_g12 import use
        _,_,m,_=self.room()
        e=make_engine(self.data);e.debug=None;e.local_map=m;e.entities=[e.player]
        xy,=m.container_state;crate=m.container_state[xy];crate['state']='open'
        gland=next(i for i in crate['items'] if i.item_id=='stalker_musk_gland')
        wood=next(i for i in crate['items'] if i.item_id=='wood_bundle')
        for item in (gland,wood):self.assertTrue(take_container(e,*xy,item))
        self.assertFalse(take_container(e,*xy,gland));self.assertEqual([],crate['items'])
        blade=e.item_factory.create('crude_blade');self.assertTrue(e.player.inventory.add(blade));use(e,blade)
        # Test fixture establishes only heat/position; the committed material is
        # the exact authored container object, never an injected gland or pellet.
        clear=next((x,y) for x in range(2,m.width-2) for y in range(2,m.height-2)
                   if m.walkable[x,y] and m.walkable[x+1,y] and not m.decor.get((x,y)) and not m.decor.get((x+1,y)))
        e.player.x,e.player.y=clear;m.decor[clear[0]+1,clear[1]]='campfire_lit';e._update_fov()
        recipe=self.data.recipes['musk_pellet'];ambient=CraftScreen._build_ambient_sources(e)
        selected,missing=plan_craft(recipe,e.player.inventory,ambient_sources=ambient)
        self.assertFalse(missing);self.assertEqual([gland],selected.materials)
        before=e.world_time.turn;e._start_processing_placement(recipe,selected)
        spot=e._placement_cursor_x,e._placement_cursor_y
        e._handle_key(pygame.K_RETURN)
        self.assertFalse(e.player.inventory.contains(gland));self.assertEqual(9,m.processing_layer[spot]['turns_remaining'])
        for _ in range(9):e._handle_key(pygame.K_z)
        self.assertEqual(before+10,e.world_time.turn)
        pellet,=[i for i in m.floor_objects[spot] if i.item_id=='musk_pellet']
        self.assertTrue(take_floor(e,pellet));self.assertTrue(e.player.inventory.contains(wood))
        self.assertIs(blade,e.player.equipment.equipped_in('weapon'))
        self.assertTrue(e.save_manager.save(e),e.save_manager.last_error)
        reader=make_engine(self.data);self.assertTrue(reader.save_manager.load(reader),reader.save_manager.last_error)
        self.assertEqual([],reader.local_map.container_state[xy]['items'])
        self.assertEqual(1,sum(i.item_id=='musk_pellet' for i in reader.player.inventory.items))
        expected=fingerprint(reader.local_map,[])
        reader.save_manager.cache.store(0,0,reader.local_map,reader.entities)
        reader.save_manager.cache.evict_distant(10,10);reader.world_x=reader.world_y=10
        with patch('engine.scene_generation.create_surface',side_effect=AssertionError('must not regenerate')):
            restored,actors=reader._prepare_destination(0,0)
        self.assertEqual(expected,fingerprint(restored,actors));self.assertEqual([],restored.container_state[xy]['items'])

    def test_genuine_g15_visited_and_pending_old_workshop_match_preedit(self):
        from g16_historical import inspect
        self.assertEqual(json.loads((GAME_ROOT.parent/'evidence/gameplay-g16/pre-edit-historical.json').read_text())['observed'],inspect())


if __name__=='__main__':unittest.main()
