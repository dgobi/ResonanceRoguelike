"""Preview access agrees with actual pickup/read, container and stair actions."""
import contextlib
import copy
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import pygame

from test_effect_persistence import load_data,make_engine,GAME_ROOT
from test_generation_ownership import action_path
from generation.structure_contract import read_document
from generation.structure_preview import preview,check_access,registration
from engine.engine import MOVE_KEYS,GameMode
from engine.interaction_cursor import InteractionCursor
from engine.scene_generation import populate
from world.world_map import Chunk,RegionType


class StructureAccessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.data=load_data()

    def setUp(self):
        temp=tempfile.TemporaryDirectory(prefix='g2-actions-');self.addCleanup(temp.cleanup)
        p=patch('engine.save_manager.SAVE_DIR',Path(temp.name));p.start();self.addCleanup(p.stop)
        capture=contextlib.redirect_stdout(io.StringIO());capture.__enter__();self.addCleanup(capture.__exit__,None,None,None)

    def walk(self,e,target):
        path=action_path(e,(e.player.x,e.player.y),target);self.assertIsNotNone(path)
        for xy in path[1:]:
            delta=xy[0]-e.player.x,xy[1]-e.player.y
            key=next(k for k,d in MOVE_KEYS.items() if d==delta)
            if str(e.local_map.tiles[xy]['terrain'])=='door_closed':e._handle_key_local(key)
            e._handle_key_local(key);self.assertEqual((e.player.x,e.player.y),xy)

    def test_cottage_access_matches_actual_note_and_container_actions_both_mirrors(self):
        doc=read_document(GAME_ROOT/'docs/examples/author_cottage_a.json')
        sidecar=read_document(GAME_ROOT/'docs/examples/author_cottage_access.json')
        for flip in (False,True):
            report,m,_=preview(doc,'ordinary_building',self.data,category='residential',flip_v=flip,expectations=sidecar)
            self.assertTrue(report['passed'],report['access'])
            e=make_engine(self.data);e.local_map=m
            e.player.x,e.player.y=report['access'][0]['xy'];e._update_fov()
            note=next(r for r in report['access'] if r.get('kind')=='readable')
            self.walk(e,tuple(note['xy']));e._handle_key_local(pygame.K_COMMA)
            item=next(i for i in e.player.inventory.items if i.text_id=='lab_label_equipment')
            e.item_system.use(item,e);self.assertTrue(e.text_reader.open);e.text_reader.open=False
            target=next(r for r in report['access'] if r.get('kind')=='container')
            self.walk(e,tuple(target['approaches'][0]));e._update_fov()
            self.assertTrue(InteractionCursor.can_reach(e,*target['xy']))
            e.mode=GameMode.INTERACTION_CURSOR;e.interaction_cursor._cursor_x,e.interaction_cursor._cursor_y=target['xy']
            e.interaction_cursor.candidates=[tuple(target['xy'])]
            e._handle_key(pygame.K_RETURN)
            self.assertIsNotNone(e.interaction_cursor._selection_prompt)
            container=m.container_state[tuple(target['xy'])];item=container['items'][0]
            e._handle_key(pygame.K_RETURN)
            self.assertIn(item,e.player.inventory.items);self.assertNotIn(item,container['items'])
        selected=registration(doc,self.data,'residential')
        self.assertTrue(selected['passed']);self.assertEqual(selected['preserved_installed_candidates'],58)
        self.assertTrue(all(len(p['objects'])==3 for p in selected['placements']))

    def test_submap_preview_entry_return_and_real_travel(self):
        doc=read_document(GAME_ROOT/'data/layouts/starting_lab.json')
        report,m,_=preview(doc,'authored_submap',self.data,expectations={'targets':[{'kind':'stairs_up',**doc['player_start']}]})
        self.assertTrue(report['passed'])
        e=make_engine(self.data);chunk=e.world_map.get(0,0)
        submap=chunk.add_submap('laboratory','Lab',123,layout_id='starting_lab')
        submap.surface_x,submap.surface_y=12,12
        e.local_map.set_tile(12,12,'stairs_down',True,True);e.local_map.submap_links[12,12]=submap.submap_id
        original=e.local_map
        e._descend_to_submap(submap.submap_id)
        self.assertEqual(e.current_submap_id,submap.submap_id)
        actual=check_access(e.local_map,self.data,{'coordinates':'map','entry':{'x':e.player.x,'y':e.player.y},
                            'targets':[{'kind':'stairs_up','x':e.player.x,'y':e.player.y}]},spawn=(e.player.x,e.player.y))
        self.assertTrue(all(r['passed'] for r in actual))
        e._ascend_from_submap();self.assertIsNone(e.current_submap_id)
        self.assertIs(e.local_map,original);self.assertEqual((e.player.x,e.player.y),(12,12))

    def test_content_blocking_required_stair_rejects_candidate_before_publication(self):
        e=make_engine(self.data);e.world_map.width=2
        chunk=Chunk(1,0,RegionType.TOWN,129,town_id=1,town_role='N')
        sm=chunk.add_submap('cave','Cave',123);e.world_map.set(chunk)
        original=e.local_map
        def blocked(data,item_factory,creature_factory,m,specs,**kwargs):
            actors=populate(data,item_factory,creature_factory,m,specs,**kwargs)
            for x,y in m.submap_links:
                for dx in (-1,0,1):
                    for dy in (-1,0,1):
                        if dx or dy:m.decor[x+dx,y+dy]='crate'
            return actors
        with patch('engine.scene_generation.populate',side_effect=blocked):
            self.assertIsNone(e._prepare_destination(1,0))
        self.assertIs(e.local_map,original);self.assertIsNone(e.save_manager.cache.load(1,0))
        self.assertIsNone(chunk.town_data);self.assertFalse(chunk.visited)

    def test_access_failure_names_target_and_interaction_corner_differs_from_movement(self):
        from world.local_map import LocalMap,make_tile
        from generation.floor_object_utils import place_container
        m=LocalMap(4,4);m.tiles[:]=make_tile('wall',False,False)
        m.set_tile(1,1,'floor',True,True);m.set_tile(2,2,'floor',True,True)
        place_container(m,2,2,'crate',[])
        check=check_access(m,self.data,{'coordinates':'map','entry':{'x':1,'y':1},'targets':[{'name':'sealed crate','kind':'container','x':2,'y':2}]})
        self.assertFalse(check[1]['passed']);self.assertEqual(check[1]['target'],'sealed crate')
        m.set_tile(2,1,'floor',True,True)
        check=check_access(m,self.data,{'coordinates':'map','entry':{'x':1,'y':1},'targets':[{'kind':'container','x':2,'y':2}]})
        self.assertTrue(check[1]['passed'])
