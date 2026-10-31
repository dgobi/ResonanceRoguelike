"""G22 information ownership, narrow integration and fresh-only content."""
import copy
import json
import random
import unittest
from types import SimpleNamespace
from unittest.mock import patch
import pygame
import test_gameplay_g21 as g21
from test_effect_persistence import load_data, make_engine
from test_gameplay_g18 import equip
from engine import location_reports as reports
from engine.save_manager import _serialize_world, _deserialize_world
from world.world_map import WorldMap, Chunk, RegionType, SubMap


def world():
    w=WorldMap(10,10); w.seed=123; w.start_wx=w.start_wy=0
    w.set(Chunk(0,0,RegionType.FOREST,1))
    w.get(0,0).submaps=[SubMap('lab','laboratory','lab',1,layout_id='starting_lab_b')]
    w.set(Chunk(2,0,RegionType.FOREST,2))
    w.get(2,0).submaps=[SubMap('ward','barrow','secret name',2,layout_id='barrow_ward_store_a')]
    w.plan=dict(placements=[dict(id='b',asset='workshop_d',origin=[0,43]),dict(id='a',asset='workshop_d',origin=[80,0])])
    return w


class LocationReportsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.data=load_data()

    def test_bounded_ties_zero_absence_rng_and_no_scene_work(self):
        w=world(); before=random.getstate()
        reports.bind(w,'Old record')
        self.assertEqual(before,random.getstate())
        self.assertEqual((0,1,'b'),tuple(w.location_reports[0]['target'][k] for k in ('x','y','id')))
        self.assertEqual([0,0],w.location_reports[0]['origin'])
        self.assertFalse(any(c.generated if hasattr(c,'generated') else c.explored or c.visited for c in w.chunks.values()))
        with self.assertRaises(ValueError): reports.bind(w,'Again')
        w=world();w.plan['placements']=[];w.get(2,0).submaps=[];reports.bind(w,'Old record')
        self.assertTrue(all(r['target'] is None for r in w.location_reports))
        self.assertIn('incomplete record',reports.describe(w.location_reports[0]))
        w=world();w.plan['placements']=[dict(id='z',asset='workshop_d',origin=[80,0]),dict(id='a',asset='workshop_d',origin=[80,0])]
        reports.bind(w,'Tie');self.assertEqual('a',w.location_reports[0]['target']['id'])
        w=world();w.plan['placements']=[dict(id='far',asset='workshop_d',origin=[720,0])]
        reports.bind(w,'Bound');self.assertIsNone(w.location_reports[0]['target'])

    def test_snapshot_reread_preview_stale_drop_and_real_paid_read(self):
        import tempfile
        from engine.item_system import ItemSystem
        with tempfile.TemporaryDirectory() as root, patch('engine.save_manager.SAVE_DIR',root):
            e=make_engine(self.data);e.world_map=world();reports.bind(e.world_map,'Old record')
            sheet=e.item_factory.create('research_note');sheet.text_id='lab_route_sheet_a'
            raw=self.data.texts[sheet.text_id];before=copy.deepcopy(e.world_map.location_reports)
            item_system=ItemSystem()
            item_system._use_read(sheet,e)
            self.assertEqual([],e.world_map.learned_reports) # direct preview helper
            self.assertIn('unbound',e.text_reader._def['pages'][1]['text'])
            item_system.use(sheet,e);self.assertEqual([],e.world_map.learned_reports) # stale selection
            e.player.inventory.add(sheet)
            item_system.use(sheet,e);self.assertEqual(list(reports.ROLES),e.world_map.learned_reports)
            self.assertIn('square (0, 1)',e.text_reader._def['pages'][1]['text'])
            self.assertTrue(e.player.inventory.contains(sheet))
            e.player.inventory.remove(sheet)
            self.assertEqual(2,len(reports.known(e.world_map)))
            e.player.inventory.add(sheet);item_system.use(sheet,e)
            self.assertEqual(before,e.world_map.location_reports)
            self.assertEqual(2,len(e.world_map.learned_reports))
            self.assertIn('unbound',reports.reader_payload(raw)['pages'][1]['text'])
            self.assertEqual(raw,self.data.texts[sheet.text_id])

    def test_transactional_rejection_and_absent_legacy_defaults(self):
        w=world();reports.bind(w,'Old record');valid=copy.deepcopy(w.__dict__)
        cases=[]
        def case(fn):
            q=copy.deepcopy(w);fn(q);cases.append(q)
        case(lambda q:q.location_reports[0]['target'].update(x=True))
        case(lambda q:q.location_reports[0]['target'].update(y=10))
        case(lambda q:q.location_reports[0]['target'].update(id='foreign'))
        case(lambda q:q.location_reports[0].update(owner='0'*32))
        case(lambda q:q.location_reports[1].update(role='workshop'))
        case(lambda q:q.location_reports[0].update(origin=[False,0]))
        case(lambda q:q.location_reports[0].update(description='\x00'))
        case(lambda q:q.location_reports.append(q.location_reports[0]))
        case(lambda q:q.learned_reports.extend(['workshop','workshop']))
        case(lambda q:setattr(q,'learned_reports',None))
        for q in cases:
            with self.assertRaises(ValueError):reports.validate(q)
        self.assertEqual(valid,w.__dict__)
        reports.validate(WorldMap(1,1))
        # A foreign world's records cannot be installed just because seeds match.
        other=world();reports.bind(other,'Other record');other.location_reports=copy.deepcopy(w.location_reports)
        with self.assertRaises(ValueError):reports.validate(other)

    def test_attachment_exact_types_and_old_new_lab_protection(self):
        from generation.authored_rooms import capability
        from engine.room_authoring import authorize_candidate
        for raw in (None,{},['workshop'],[dict(role='other')],[dict(role='workshop',selector='exec')],
                    [dict(role='workshop'),dict(role='workshop')],True):
            with self.assertRaises(ValueError):reports.attachment(dict(location_reports=raw))
        self.assertEqual([],reports.attachment({}));self.assertEqual([],reports.attachment(dict(location_reports=[])))
        for identity in ('starting_lab','starting_lab_b'):
            raw=self.data.layouts[identity];p='roguelike/data/layouts/'+identity+'.json'
            self.assertFalse(capability(raw,p)['editable'])
            self.assertFalse(capability(dict(raw,id='disguised'),p)['editable'])
            self.assertTrue(any(d['code']=='ROOM_PROTECTED' for d in authorize_candidate(raw,raw,p,p,data=self.data)))

    def test_historical_content_and_narrow_supply_delta(self):
        import subprocess
        from pathlib import Path
        root=Path(__file__).resolve().parents[3]
        for p in ('layouts/starting_lab.json','buildings/commercial/workshop_c.json','buildings/commercial/workshop_b.json',
                  'buildings/commercial/apothecary_b.json','texts/world/notes/workshop_musk_notes_b.json','loot_pools/workshop_c_travel.json'):
            self.assertEqual(subprocess.check_output(['git','show','checkpoint/gameplay-g22-start-20261030-a:roguelike/data/'+p]).replace(b'\r\n',b'\n'),(root/'roguelike/data'/p).read_bytes().replace(b'\r\n',b'\n'))
        c=json.loads((root/'roguelike/data/buildings/commercial/workshop_c.json').read_bytes())
        d=json.loads((root/'roguelike/data/buildings/commercial/workshop_d.json').read_bytes())
        self.assertEqual(c['layers'],d['layers']);self.assertEqual(c['placement'],d['placement'])
        self.assertEqual(['workshop_c_travel','workshop_d_treatment'],d['special_tiles'][-1]['loot_pools'])
        self.assertEqual(dict(id='workshop_d_treatment',roll_count=[1,1],items=[dict(item_id='herbal_dressing',weight=1)]),self.data.loot_pools['workshop_d_treatment'])

    def test_overmap_unknown_reported_explored_visited_runtime_debug_and_free_controls(self):
        from rendering.renderer import Renderer
        from world.world_map import TownData
        from engine.engine import GameMode
        pygame.init()
        strings=[]
        class Font:
            def render(self,text,*args):strings.append(text);return pygame.Surface((max(1,len(text)*5),12))
            def get_linesize(self):return 14
            def get_height(self):return 12
            def size(self,text):return len(text)*5,12
        renderer=Renderer.__new__(Renderer);renderer.display=SimpleNamespace(font_ui_normal=Font(),font_ui_small=Font(),font_ui_large=Font())
        w=world();reports.bind(w,'Old record');c=w.get(2,0);c.name='SECRET PLACE';c.is_locus=True
        c.town_data=TownData('SECRET TOWN','large',['SECRET DISTRICT'],'cracked',False,None)
        surf=pygame.Surface((960,720));rect=pygame.Rect(640,0,320,720)
        def drawn(debug=False):
            strings.clear();renderer.render_overmap_sidebar(surf,rect,w,2,0,0,0,SimpleNamespace(debug=debug));return '\n'.join(strings)
        for visited in (False,True):
            c.visited=visited
            text=drawn();self.assertNotIn('SECRET',text);self.assertNotIn('LOCUS',text);self.assertNotIn('Bell:',text)
            self.assertNotIn('travel here',text);self.assertNotIn('teleport',text);self.assertIn('Cursor  (2, 0)',text)
        w.learned_reports=['ward_store'];text=drawn();self.assertIn('Old record',text);self.assertIn('Ward store',text);self.assertNotIn('SECRET',text)
        c.explored=True;text=drawn();self.assertIn('SECRET PLACE',text);self.assertIn('Bell: cracked',text);self.assertIn('SECRET DISTRICT',text)
        self.assertNotIn('submap_',text)
        text=drawn(True);self.assertIn('teleport',text);self.assertIn('layout: barrow_ward_store_a',text)
        import tempfile
        with tempfile.TemporaryDirectory() as root,patch('engine.save_manager.SAVE_DIR',root):
            e=make_engine(self.data);e.debug=None;e.world_map=w;e.mode=GameMode.OVERMAP
            e._free_move_pending=True;e._move_debt=.25
            before=(e.world_time.turn,e.player.x,e.player.y)
            for k in (pygame.K_RIGHT,pygame.K_LEFT,pygame.K_RETURN):e._handle_key(k)
            self.assertEqual(before,(e.world_time.turn,e.player.x,e.player.y));self.assertTrue(e._free_move_pending);self.assertEqual(.25,e._move_debt)

    def test_new_lab_keeps_candle_stairs_and_adds_only_sheet(self):
        from engine.scene_generation import create_submap
        from engine.item_factory import ItemFactory
        from engine.creature_factory import CreatureFactory
        w=world();c=w.get(0,0)
        for identity in ('starting_lab','starting_lab_b'):
            sub=SubMap('lab','laboratory','lab',1,layout_id=identity)
            result=create_submap(w,0,0,sub,self.data,ItemFactory(self.data),CreatureFactory(self.data),80,43)
            m=result.local_map
            self.assertEqual('stairs_up',str(m.tiles[result.spawn]['terrain']))
            self.assertEqual(1,sum(d=='decor_candle' for d in m.decor.values()))
            sheets=[(xy,i) for xy,rows in m.floor_objects.items() for i in rows if i.text_id=='lab_route_sheet_a']
            self.assertEqual(identity=='starting_lab_b',bool(sheets))
            if sheets:self.assertEqual((result.spawn[0]-1,result.spawn[1]),sheets[0][0])

    def test_f9_legacy_absence_clears_divergent_world_knowledge(self):
        import tempfile
        with tempfile.TemporaryDirectory() as root,patch('engine.save_manager.SAVE_DIR',root):
            e=make_engine(self.data);e.debug=None
            self.assertTrue({'report_owner','location_reports','learned_reports'}.isdisjoint(_serialize_world(e.world_map)))
            self.assertTrue(e.save_manager.save(e))
            divergent=world();reports.bind(divergent,'Divergent record');divergent.learned_reports=list(reports.ROLES)
            e.world_map=divergent
            e._handle_key(pygame.K_F9)
            self.assertIsNone(e.world_map.report_owner);self.assertEqual([],e.world_map.location_reports);self.assertEqual([],e.world_map.learned_reports)
            self.assertIsNot(e.world_map,divergent)


class NeutralGrassTests(unittest.TestCase):
    setUpClass=classmethod(g21.LocalRivalTests.setUpClass.__func__)
    setUp=g21.LocalRivalTests.setUp
    actor=g21.LocalRivalTests.actor
    decision=g21.LocalRivalTests.decision

    def test_actual_hostility_not_current_target_gates_automatic_entry(self):
        from engine.combat import CombatResult
        e=self.e;e.player.x=e.player.y=12;equip(e,'crude_blade')
        a=self.actor('highland_bandit',14,12);e.local_map.set_tile(13,12,'tall_grass',True,True)
        for hostility,expected in (([],0),(['stalker'],0),(['player','stalker'],1)):
            a.x=14;a.perception.hostile_to=hostility
            def step(**kw):a.x=13
            before=e.world_time.turn
            with patch.object(e.ai_system,'process',side_effect=step),patch('engine.combat.resolve_attack',return_value=CombatResult(hit=False)) as resolve:
                e._advance_turn()
            self.assertEqual(expected,resolve.call_count);self.assertEqual(before+1,e.world_time.turn)
        a.perception.hostile_to=[]
        with patch('engine.combat.resolve_attack',return_value=CombatResult(hit=False)) as resolve:
            self.assertTrue(e._player_attack(a))
        resolve.assert_called_once()

    def test_neutral_wandering_and_sound_remain_not_player_pursuit(self):
        from engine.sound import emit
        from components.ai import AIState
        a=self.actor('highland_bandit',12,12)
        for hostility in ([],['stalker']):
            a.perception.hostile_to=hostility;self.decision(a)
            self.assertNotEqual(a.ai.state,AIState.HUNTING)
            emit(self.e,14,12,'flint');self.decision(a)
            self.assertIsNone(getattr(a,'_last_known_px',None));self.assertIsNone(getattr(a.ai,'local_target',None))


if __name__=='__main__':unittest.main()
