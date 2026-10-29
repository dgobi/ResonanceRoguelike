"""Native furnishing admission, staged ownership, access, and visible crafting input."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import pygame
from test_effect_persistence import load_data, make_engine, GAME_ROOT
from engine.scene_generation import populate
from engine.crafting import plan_craft
from generation.authored_decor import admission
from generation.context import GenerationError
from generation.structure_contract import compile_structure
from generation.structure_preview import preview


class Furnishings(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = load_data()
        pygame.init()

    def room(self, *records):
        return dict(id='w5l_test', layers=['#######','#.....#','#.....#','#.....#','#..<..#','#######'],
                    legend={'#':'wall','.':'floor','<':'stairs_up'},
                    player_start=dict(x=1,y=1), special_tiles=list(records))

    def decor(self, x=3, y=2, identifier='campfire_unlit'):
        return dict(type='decor', x=x, y=y, decor_id=identifier)

    def test_registry_classes_identity_and_behavior_exclusions(self):
        for identifier in ('worn_mat','dried_herbs','street_lamp_working','decor_candle','campfire_unlit','campfire_lit'):
            self.assertTrue(admission(self.data,identifier)['supported'],identifier)
        for identifier, reason in [('crate','container'),('drying_herb','job'),('cooking_meat','job'),('corpse','identity'),
                ('vine_spore_vent','network'),('vine_growth','network'),('coldbell_flower','Harvesting'),
                ('waystone_plinth','interaction'),('stele','interaction'),('cracked_bell','interaction')]:
            self.assertIn(reason,admission(self.data,identifier)['reason'])
        for rows in ([dict(id='worn_mat')]*2,[dict(id='worn_mat'),dict(id='WORN_MAT')],[]):
            data=copy.copy(self.data);data.decorative_sources=rows
            self.assertFalse(admission(data,'worn_mat')['supported'])
        self.assertFalse(admission(self.data,'missing')['supported'])
        data=copy.copy(self.data);data.decoratives={**self.data.decoratives,'worn_mat':dict(id='worn_mat',callback='unsupported')}
        self.assertIn('callback',admission(data,'worn_mat')['reason'])
        for value in (True,-1,float('inf'),2**10000):
            data.decoratives={**self.data.decoratives,'worn_mat':dict(id='worn_mat',light_emit=value)}
            self.assertFalse(admission(data,'worn_mat')['supported'])
        self.assertEqual(admission(self.data,'decor_candle')['properties']['light_emit'],0)
        self.assertFalse(admission(self.data,'street_lamp_working')['properties']['stationary_fire'])

    def test_direct_route_types_bounds_and_typed_realized_receipt(self):
        raw=self.room(self.decor(),self.decor(2,2,'worn_mat'),self.decor(4,2,'street_lamp_working'))
        report,m,_=preview(raw,'authored_submap',self.data,derive_access=True)
        self.assertTrue(report['passed']);self.assertEqual(len(m.decor),3)
        receipt=report['population_receipts'][0]
        self.assertEqual(receipt['objects'],[]);self.assertEqual(receipt['actual_count'],1)
        self.assertEqual(receipt['source_xy'],[3,2]);self.assertEqual(receipt['xy'],[40,20])
        self.assertEqual(receipt['realized_decor']['id'],'campfire_unlit')
        cases=[self.room(dict(self.decor(),kind='item')),self.room(self.decor(True,2)),self.room(self.decor(7,2)),
               self.room(dict(type='weighted',x=3,y=2,spawn_table=[dict(type='decor',decor_id='worn_mat')]))]
        for raw in cases:
            with self.assertRaises(GenerationError):compile_structure(raw,'authored_submap',self.data)
        with self.assertRaises(GenerationError):compile_structure(self.room(self.decor()),'ordinary_building',self.data,category='storage')

    def test_final_conflicts_both_orders_and_no_partial_layers_or_receipts(self):
        e=make_engine(self.data)
        pairs=[(self.decor(14,12),self.decor(14,12,'worn_mat')),
               (self.decor(14,12),dict(type='container',x=14,y=12,decor_id='crate')),
               (self.decor(14,12),dict(type='creature',x=14,y=12,creature_id='hollow_revenant'))]
        for a,b in pairs:
            for records in ([a,b],[b,a]):
                receipts=[]
                with self.assertRaises(GenerationError):
                    populate(self.data,e.item_factory,e.creature_factory,e.local_map,
                             [dict(type='item',x=13,y=12,item_id='wood_bundle'),*records],authored_arrival=(12,12),receipts=receipts)
                self.assertFalse(e.local_map.decor);self.assertFalse(e.local_map.floor_objects)
                self.assertFalse(e.local_map.container_state);self.assertFalse(receipts)
        # A late factory failure also leaves the earlier decor/container plans unpublished.
        with patch.object(e.item_factory,'create',return_value=None), self.assertRaises(GenerationError):
            populate(self.data,e.item_factory,e.creature_factory,e.local_map,[self.decor(14,12),dict(type='item',x=13,y=12,item_id='wood_bundle')],authored_arrival=(12,12))
        self.assertFalse(e.local_map.decor)

    def test_arrival_return_required_content_access_and_harmless_overlap(self):
        for xy in ((1,1),(3,4)):
            with self.assertRaisesRegex(GenerationError,'special\\[0\\].*realized'):
                preview(self.room(self.decor(*xy)),'authored_submap',self.data,derive_access=True)
        # Final wall of blockers seals the item off; source ordering cannot grant access.
        records=[self.decor(3,y) for y in range(1,5)]+[dict(type='item',x=5,y=1,item_id='wood_bundle')]
        for rows in (records,list(reversed(records))):
            with self.assertRaises(GenerationError):preview(self.room(*rows),'authored_submap',self.data,derive_access=True)
        raw=self.room(self.decor(2,2,'worn_mat'),dict(type='item',x=2,y=2,item_id='wood_bundle'),dict(type='item',x=0,y=0,item_id='letter'))
        report,_,_=preview(raw,'authored_submap',self.data,derive_access=True)
        self.assertTrue(report['passed']);self.assertTrue(report['population_receipts'][-1]['relocated'])
        closed=self.room();closed['legend']['+']='door_closed';closed['layers'][1]='#+....#'
        before,_,_=preview(closed,'authored_submap',self.data,derive_access=True)
        self.assertNotEqual(before['spawn'],before['authored_start'])
        x,y=[a-b for a,b in zip(before['spawn'],before['origin'])]
        closed['special_tiles']=[self.decor(x,y)]
        with self.assertRaisesRegex(GenerationError,'actual arrival'):
            preview(closed,'authored_submap',self.data,derive_access=True)

    def test_legacy_grid_is_inactive_old_rooms_and_lab_unchanged(self):
        raw=self.room();baseline,m,_=preview(raw,'authored_submap',self.data,derive_access=True)
        raw['decor_layer']=[[None]*7 for _ in range(6)];raw['decor_layer'][2][3]='campfire_lit'
        report,other,_=preview(raw,'authored_submap',self.data,derive_access=True)
        self.assertEqual(report['terrain'],baseline['terrain']);self.assertEqual(report['spawn'],baseline['spawn'])
        self.assertEqual(other.decor,m.decor);self.assertFalse(other.decor)
        self.assertIn('INACTIVE_FIELD',[d['code'] for d in report['source_diagnostics']])
        lab=self.data.layouts['starting_lab'];_,labmap,_=preview(lab,'authored_submap',self.data)
        self.assertIn('decor_candle',labmap.decor.values())


class RecordingFont:
    def __init__(self, font, glyphs):self.font,self.glyphs=font,glyphs
    def render(self,text,*args):
        surface=self.font.render(text,*args);self.glyphs[id(surface)]=(surface,text);return surface
    def __getattr__(self,name):return getattr(self.font,name)


class CraftPresentation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.data=load_data();pygame.init()
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        p=patch('engine.save_manager.SAVE_DIR',Path(self.temp.name));p.start();self.addCleanup(p.stop)
        self.e=make_engine(copy.copy(self.data));self.e.debug=None
        self.recipe=dict(id='w5l',name='W5L',category='cooking',components=[dict(tag='edible')],result_item='cooked_meat')
        self.e.data.recipes={'w5l':self.recipe}
        self.meat=self.e.item_factory.create('raw_meat_common');self.e.player.inventory.add(self.meat)
        self.screen=self.e.craft_screen;self.screen.open=True;self.screen.selected=1
    def rendered(self):
        output=[];glyphs={}
        class DrawingSurface(pygame.Surface):
            def blit(self,source,dest,*args,**kwargs):
                rect=super().blit(source,dest,*args,**kwargs)
                # Only completely visible glyphs count as rendered evidence;
                # font calls clipped by the detail viewport do not count.
                if id(source) in glyphs and rect.size==source.get_size():output.append(glyphs[id(source)][1])
                return rect
        for name,size in (('_font_small',12),('_font_normal',14),('_font_title',16)):
            setattr(self.screen,name,RecordingFont(pygame.font.Font(None,size),glyphs))
        for size in ((1280,720),(800,600)):
            with patch('rendering.craft_screen.pygame.Surface',DrawingSurface):
                self.screen.render(DrawingSurface(size),self.e)
        return '\n'.join(output)
    def test_sole_protected_component_visible_choice_and_real_enter(self):
        self.meat.consumed_on_use=False
        text=self.rendered();self.assertIn('automatic: 0; choose: 1',text);self.assertIn('Choose materials',text)
        self.screen.handle_key(pygame.K_RETURN,self.e);self.assertTrue(self.screen._choosing)
        self.screen.handle_key(pygame.K_RETURN,self.e);self.assertFalse(self.e.player.inventory.contains(self.meat))
        self.assertTrue(any(i.item_id=='cooked_meat' for i in self.e.player.inventory.items))
    def test_protected_conjunction_visible_zero_and_real_handler_refuses(self):
        self.meat.consumed_on_use=False;self.recipe['components']=[]
        self.recipe['requires_single_item']=[dict(tag='edible'),dict(tag='vital')]
        text=self.rendered();self.assertIn('automatic: 0',text);self.assertNotIn('Choose materials',text)
        self.screen.handle_key(pygame.K_RETURN,self.e);self.assertFalse(self.screen._choosing)
        self.assertTrue(self.e.player.inventory.contains(self.meat));self.assertFalse(self.screen.open)
    def test_overlapping_rows_count_potential_and_combined_plan_refuses(self):
        self.recipe['components'].append(dict(tag='vital'))
        self.assertTrue(plan_craft(self.recipe,self.e.player.inventory)[1])
        text=self.rendered();self.assertGreaterEqual(text.count('automatic: 1; choose: 0'),2)
        self.assertIn('potential matches',text);self.assertIn('distinct item',text)
        self.assertNotIn('[ ENTER ] craft',text)
        turn=self.e.world_time.turn;self.screen.handle_key(pygame.K_RETURN,self.e)
        self.assertTrue(self.e.player.inventory.contains(self.meat));self.assertEqual(self.e.world_time.turn,turn)
