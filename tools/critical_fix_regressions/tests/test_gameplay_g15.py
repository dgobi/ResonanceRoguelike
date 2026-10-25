"""Finite native treatment: effect, ownership, action cost and historical worlds."""
import copy
import json
from pathlib import Path
import random
import tempfile
import unittest
from unittest.mock import patch

import pygame
from test_effect_persistence import load_data, make_engine, GAME_ROOT
from test_gameplay_g12 import use
from generation.placement import transform, entrance_cells, NORMALS
from generation.structure_preview import preview
from engine.engine import GameMode
from engine.save_components import serialize_item
from g1_support import fingerprint


class FiniteTreatment(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data=load_data()
        pygame.init()

    def setUp(self):
        temp=tempfile.TemporaryDirectory(prefix='resonance-g15-test-')
        self.addCleanup(temp.cleanup)
        p=patch('engine.save_manager.SAVE_DIR',Path(temp.name));p.start();self.addCleanup(p.stop)
        self.e=make_engine(self.data);self.e.debug=None;self.e.rng=random.Random(29417)

    def add(self,iid):
        item=self.e.item_factory.create(iid)
        self.assertTrue(self.e.player.inventory.add(item))
        return item

    def test_injured_and_near_full_exact_dose_effect_boundary_and_one_ordinary_turn(self):
        e=self.e;inv=e.player.inventory
        selected=self.add('herbal_dressing');other=self.add('herbal_dressing');blade=self.add('crude_blade')
        e.player.equipment.equip(blade,'weapon')
        self.assertFalse(selected.stackable);self.assertEqual(.1,selected.weight)
        for hp,amount in ((30,12),(58,2)):
            with self.subTest(hp=hp):
                if not inv.contains(selected):selected=self.add('herbal_dressing')
                e.player.fighter.hp=hp
                before=e.world_time.turn;possessions=list(inv.items)
                boundary=[];advance=e._advance_turn
                def observe():
                    boundary.append((e.player.fighter.hp,list(inv.items),e.world_time.turn))
                    advance()
                self.assertEqual(0,e._move_debt)
                with patch.object(e,'_advance_turn',side_effect=observe):use(e,selected)
                self.assertEqual([(hp+amount,[i for i in possessions if i is not selected],before)],boundary)
                self.assertEqual(hp+amount,e.player.fighter.hp)
                self.assertEqual(before+1,e.world_time.turn)
                self.assertTrue(inv.contains(other));self.assertIs(blade,e.player.equipment.equipped_in('weapon'))
                self.assertTrue(any(f'recover {amount} HP' in m.text for m in e.log.messages))
                self.assertFalse(inv.contains(selected))

    def test_full_stale_missing_and_dead_rejections_and_free_close_preserve_all_state(self):
        e=self.e;dose=self.add('herbal_dressing');inv=e.player.inventory
        for case in ('full','stale','missing','dead','zero-hp'):
            with self.subTest(case=case):
                fighter=e.player.fighter
                if not inv.contains(dose):inv.add(dose)
                fighter.hp=60 if case=='full' else 35;fighter._dead=case=='dead'
                if case=='zero-hp':fighter.hp=0
                if case=='stale':inv.remove(dose)
                if case=='missing':e.player.fighter=None
                e._move_debt=2.25
                owned=[serialize_item(i) for i in inv.items];before=e.world_time.turn;hp=fighter.hp
                with patch.object(e,'_advance_turn',side_effect=AssertionError('rejection must be free')):
                    use(e,dose)
                    e.inventory_screen.open=True;e._handle_key(pygame.K_ESCAPE)
                self.assertEqual(owned,[serialize_item(i) for i in inv.items])
                self.assertEqual(hp,fighter.hp);self.assertEqual(before,e.world_time.turn)
                self.assertEqual(2.25,e._move_debt)
                self.assertIn({'full':'already closed','stale':'no longer','missing':'living','dead':'living','zero-hp':'living'}[case],e.log.messages[-1].text)
                e.player.fighter=fighter;fighter._dead=False

    def test_reading_equipment_and_inventory_debt_semantics_remain_paid(self):
        e=self.e;blade=self.add('crude_blade')
        e._move_debt=2.25;before=e.world_time.turn
        use(e,blade)
        self.assertIs(blade,e.player.equipment.equipped_in('weapon'))
        self.assertEqual(before+1,e.world_time.turn);self.assertEqual(2.25,e._move_debt)
        doc=self.add('lab_note');doc.text_id='lab_label_sarcophagus'
        before=e.world_time.turn
        use(e,doc)
        self.assertTrue(e.text_reader.open);self.assertTrue(e.player.inventory.contains(doc))
        self.assertEqual(before+1,e.world_time.turn);self.assertEqual(2.25,e._move_debt)

    def test_versioned_chest_preserves_old_layout_and_pools_and_both_real_access_paths(self):
        old=self.data.structures['apothecary_a'];new=self.data.structures['apothecary_b']
        expected=copy.deepcopy(old);expected['id']='apothecary_b'
        expected['special_tiles'][0]['loot_pools'].append('apothecary_b_treatment')
        self.assertEqual(expected,new)
        pool=self.data.loot_pools['apothecary_b_treatment']
        self.assertEqual([1,1],pool['roll_count'])
        self.assertEqual([dict(item_id='herbal_dressing',weight=1)],pool['items'])
        for rotation in new['placement']['rotations']:
            with self.subTest(rotation=rotation):
                raw=transform(new,rotation,False);p=raw['placement'];door=p['entrances'][0];dx,dy=NORMALS[door['normal']]
                report,m,actors=preview(raw,'ordinary_building',self.data,category='commercial',expectations={
                    'entry':dict(x=door['x']+dx,y=door['y']+dy),
                    'targets':p['targets']+[dict(x=x,y=y,kind='floor',required=True) for x,y in entrance_cells(door)]})
                self.assertTrue(report['passed'],report['access'])
                self.assertEqual(3,len(m.container_state))
                doses=[i for c in m.container_state.values() for i in c['items'] if i.item_id=='herbal_dressing']
                self.assertEqual(1,len(doses))
                chest=next(c for c in m.container_state.values() if c['decor_id']=='medicine_chest')
                self.assertIn(doses[0],chest['items'])
                self.assertGreater(len(chest['items']),1)  # original reagent roll still occurs

    def test_native_current_selection_small_three_seed_recheck_and_production_materialization(self):
        import contextlib,io
        from generation.world_gen import generate_world
        from world.world_map import WorldMap
        from engine.scene_generation import create_surface
        from engine.item_factory import ItemFactory
        from engine.creature_factory import CreatureFactory
        for seed,start,target in ((20261023,(73,99),(75,100)),(0,(30,83),(32,84)),(29417,(106,46),(104,47))):
            with self.subTest(seed=seed):
                w=WorldMap(128,128);w.seed=seed
                with contextlib.redirect_stdout(io.StringIO()):generate_world(w,self.data,random.Random(seed))
                self.assertEqual(start,(w.start_wx,w.start_wy))
                selected=[p for p in w.plan['placements'] if p['asset']=='apothecary_b']
                self.assertTrue(any((p['origin'][0]//80,p['origin'][1]//43)==target for p in selected))
                self.assertFalse(any(p['asset']=='apothecary_a' and p['context'] in ('grid','roadside') for p in w.plan['placements']))
                scene=create_surface(w,w.get(*target),self.data,ItemFactory(self.data),CreatureFactory(self.data),80,43)
                for p in selected:
                    if (p['origin'][0]//80,p['origin'][1]//43)!=target:continue
                    chests=[scene.local_map.container_state[t['x']%80,t['y']%43] for t in p['targets'] if t['kind']=='container']
                    self.assertEqual(1,sum(i.item_id=='herbal_dressing' for c in chests for i in c['items']))

    def test_capacity_rejection_search_again_exact_transfer_consumption_and_disk_revisit(self):
        from generation.floor_object_utils import place_container
        e=self.e;inv=e.player.inventory;xy=(13,12)
        dose=e.item_factory.create('herbal_dressing')
        place_container(e.local_map,*xy,'medicine_chest',[dose])
        e._update_fov();before=e.world_time.turn
        inv.capacity=0
        def search():
            e.mode=GameMode.INTERACTION_CURSOR;e.interaction_cursor.enter([xy],12,12);e._handle_key(pygame.K_RETURN)
        for _ in range(2):
            search();e._handle_key(pygame.K_RETURN)
            self.assertEqual([dose],e.local_map.container_state[xy]['items'])
            self.assertFalse(inv.contains(dose));self.assertEqual(before,e.world_time.turn)
        inv.capacity=20
        search()
        e._handle_key(pygame.K_RETURN)
        self.assertTrue(inv.contains(dose));self.assertEqual([],e.local_map.container_state[xy]['items'])
        self.assertEqual(before+1,e.world_time.turn)
        e.mode=GameMode.LOCAL;e.player.fighter.hp=40
        use(e,dose);self.assertEqual(52,e.player.fighter.hp)
        self.assertTrue(e.save_manager.save(e),e.save_manager.last_error)
        reader=make_engine(self.data)
        self.assertTrue(reader.save_manager.load(reader),reader.save_manager.last_error)
        self.assertEqual(52,reader.player.fighter.hp);self.assertFalse(reader.player.inventory.has('herbal_dressing'))
        self.assertEqual([],reader.local_map.container_state[xy]['items'])
        expected=fingerprint(reader.local_map,[])
        reader.save_manager.cache.store(0,0,reader.local_map,reader.entities)
        reader.save_manager.cache.evict_distant(10,10);reader.world_x=reader.world_y=10
        with patch('engine.scene_generation.create_surface',side_effect=AssertionError('must not regenerate')):
            m,actors=reader._prepare_destination(0,0)
        self.assertEqual(expected,fingerprint(m,actors));self.assertEqual([],m.container_state[xy]['items'])

    def test_genuine_g14_checkpoint_pending_apothecary_and_depleted_visited_scene_match_preedit(self):
        from g15_historical import inspect
        baseline=GAME_ROOT.parent/'evidence/gameplay-g15/pre-edit-historical.json'
        self.assertEqual(json.loads(baseline.read_text())['observed'],inspect())


if __name__=='__main__':unittest.main()
