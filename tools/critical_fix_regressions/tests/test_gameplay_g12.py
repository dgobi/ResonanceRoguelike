"""G12 production consumers: selected rewards, exact costs and readable knowledge."""
import copy
import hashlib
import json
import os
from pathlib import Path
import random
import subprocess
import sys
import tempfile
import unittest
import zipfile
from unittest.mock import patch

from test_effect_persistence import GAME_ROOT, load_data, make_engine
import pygame
from engine.crafting import plan_craft, commit_craft
from engine.item_transfers import exchange, take_floor, take_container, drop
from engine.save_components import serialize_item
from rendering.craft_screen import CraftScreen

FIXTURE = GAME_ROOT.parent/'tools/critical_fix_regressions/fixtures/g12'
SELECTED = ('revelation_lens', 'leather_satchel', 'herbalist_pouch', 'component_satchel')


def use(e, item):
    e.inventory_screen.open = True
    e.inventory_screen._flat = [(item, False, item.name)]
    e.inventory_screen.selected = 0
    e._handle_key(pygame.K_RETURN)
    e.inventory_screen.open = False


def load_witness(root):
    with zipfile.ZipFile(FIXTURE/'authentic-pre-g12-checkpoint.zip') as z:
        witness = json.loads((FIXTURE/'pre-g12-witness.json').read_text())
        for name, row in witness['files'].items():
            raw = z.read(name)
            assert len(raw) == row['bytes'] and hashlib.sha256(raw).hexdigest() == row['sha256']
        z.extractall(Path(root)/'slot_0')
    with patch('engine.save_manager.SAVE_DIR', Path(root)):
        e = make_engine(load_data())
        assert e.save_manager.load(e), e.save_manager.last_error
    return e, witness


def witness_state(e):
    return dict(items=[serialize_item(i) for i in e.player.inventory.items],
                hp=e.player.fighter.hp, hunger=e.player.needs.hunger,
                turn=e.world_time.turn, knowledge=e.creature_knowledge,
                recovered={str(k):v for k,v in e.player.language.recovered_text.items()},
                mutations=sorted(e.local_map.interacted_waystones),
                light_owned=e.player.light_source._item_ref is e.player.equipment.equipped_in('offhand'),
                load=e.player.inventory.current_weight)


class ExpeditionRewardsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = load_data()
        pygame.init()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='resonance-g12-test-')
        self.addCleanup(self.tmp.cleanup)
        p = patch('engine.save_manager.SAVE_DIR', Path(self.tmp.name)/'saves')
        p.start(); self.addCleanup(p.stop)
        self.e = make_engine(self.data)
        self.e.debug = None
        self.e.rng = random.Random(29417)

    def add(self, iid, weight=None):
        item = self.e.item_factory.create(iid)
        if weight is not None:
            item.weight = weight
        self.assertTrue(self.e.player.inventory.add(item))
        return item

    def test_all_selected_items_use_normal_equip_switch_and_unequip_commands(self):
        e = self.e
        for iid in SELECTED:
            item = self.add(iid)
            slot = self.data.items[iid]['slot']
            before = e.world_time.turn
            use(e, item)
            self.assertIs(e.player.equipment.equipped_in(slot), item)
            use(e, item)
            self.assertFalse(item.equipped)
            self.assertIsNone(e.player.equipment.equipped_in(slot))
            self.assertEqual(before+2, e.world_time.turn)
        use(e, e.player.inventory.get_by_id('revelation_lens'))
        blade = self.add('crude_blade')
        use(e, blade)
        self.assertFalse(e.player.inventory.get_by_id('revelation_lens').equipped)
        self.assertIs(e.player.equipment.equipped_in('weapon'), blade)

    def test_lens_reveal_true_strike_real_resolver_damage_and_cooldown(self):
        e = self.e
        lens = self.add('revelation_lens'); use(e, lens)
        target = e.creature_factory.spawn('hollow_knight', 13, 12)
        e.entities.append(target); e._update_fov()
        from engine.combat import resolve_attack
        with patch('engine.combat.resolve_attack', wraps=resolve_attack) as spy:
            e._handle_key(pygame.K_q)
            self.assertIn('hollow_knight', e.creature_knowledge)
            self.assertTrue(e.creature_knowledge['hollow_knight'])
            hp = target.fighter.hp
            e._handle_key(pygame.K_r)
            self.assertLess(target.fighter.hp, hp)
            calls = [c.kwargs for c in spy.call_args_list if c.kwargs['attacker_name']=='thou']
            args = calls[-1]
            self.assertEqual('1d4',e._get_equipped_weapon()['damage_dice'])
            self.assertIn(args['weapon']['damage_dice'],('1d1','2d1','3d1','4d1'))
            self.assertEqual(2,args['weapon']['damage_bonus'])
            self.assertEqual(0, args['defender_dodge_chance'])
            self.assertGreater(e.moveset_cooldowns.get('true_strike', 0), 0)
            turn = e.world_time.turn
            e._handle_key(pygame.K_r)
            self.assertEqual(turn, e.world_time.turn)
            self.assertEqual(2,len([c for c in spy.call_args_list if c.kwargs['attacker_name']=='thou']))

    def test_category_discounts_match_display_and_encumbrance_after_switching(self):
        from engine.inventory_screen import _effective_weight, _item_category, _get_satchel_reductions
        e = self.e; inv = e.player.inventory
        wood = self.add('wood_bundle', 5)
        food = self.add('crow_jerky', 4)
        tool = self.add('crude_blade', 3)
        bags = [self.add(i) for i in SELECTED[1:]]
        raw = [i.weight for i in inv.items]
        for bag in bags:
            use(e, bag)
            red = self.data.items[bag.item_id]['weight_reductions']
            expected = sum(i.weight*(1-red.get(_item_category(i,e),red.get('all',0))) for i in inv.items)
            self.assertAlmostEqual(expected, inv.current_weight)
            self.assertAlmostEqual(expected, sum(_effective_weight(i,_item_category(i,e),_get_satchel_reductions(e)) for i in inv.items))
            self.assertAlmostEqual(expected/inv.capacity, inv.encumbrance)
        self.assertEqual(raw, [i.weight for i in inv.items])

    def test_floor_container_exchange_and_overweight_bag_removal_are_nonlossy(self):
        e = self.e; inv = e.player.inventory
        bag = self.add('component_satchel'); use(e, bag)
        bulk = self.add('wood_bundle', 28)
        self.assertAlmostEqual(18.8, inv.current_weight)
        candidate = e.item_factory.create('wood_bundle')
        e.local_map.floor_objects[(12,12)] = [candidate]
        self.assertTrue(take_floor(e,candidate))
        other = e.item_factory.create('wood_bundle')
        e.local_map.container_state[(13,12)] = dict(state='open',items=[other])
        self.assertFalse(take_container(e,13,12,other))
        before = list(inv.items)
        output = e.item_factory.create('wood_bundle')
        self.assertFalse(exchange(e,[bag],[output]))  # The removed bag cannot discount its replacement.
        self.assertEqual(before, inv.items)
        self.assertTrue(drop(e,bag))
        self.assertEqual([bulk,candidate],inv.items)
        self.assertGreater(inv.current_weight,inv.capacity)
        self.assertFalse(inv.can_add(other))
        self.assertTrue(e.save_manager.save(e))
        self.assertTrue(e.save_manager.load(e), e.save_manager.last_error)
        self.assertEqual(2,len(e.player.inventory.items))
        self.assertGreater(e.player.inventory.current_weight,20)

    def test_materials_are_physical_tools_are_reused_and_choices_spend_equipped_light(self):
        e = self.e; inv = e.player.inventory
        torch = self.add('tallow_torch'); blade = self.add('crude_blade')
        use(e,torch); use(e,blade)
        recipe = self.data.recipes['campfire']
        ambient = CraftScreen._build_ambient_sources(e)
        self.assertTrue(plan_craft(recipe,inv,ambient_sources=ambient)[1])
        a,b = self.add('wood_bundle'),self.add('wood_bundle')
        plan,missing = plan_craft(recipe,inv,ambient_sources=ambient)
        self.assertFalse(missing)
        self.assertTrue(commit_craft(e,recipe,plan,ambient))
        self.assertEqual([torch,blade],inv.items)
        self.assertIs(e.player.equipment.equipped_in('weapon'),blade)
        # An explicitly selected reusable fuel is actually spent and detached.
        c = self.add('wood_bundle')
        plan,missing = plan_craft(recipe,inv,chosen_items={0:torch.item_id})
        self.assertFalse(missing)
        self.assertTrue(commit_craft(e,recipe,plan))
        self.assertEqual([blade],inv.items)
        self.assertIsNone(e.player.light_source)
        self.assertIsNone(e.player.equipment.equipped_in('offhand'))

    def test_floor_take_all_and_output_capacity_share_the_derived_load(self):
        e=self.e;inv=e.player.inventory
        bag=self.add('component_satchel');use(e,bag)
        bulk=self.add('wood_bundle',28)
        a=e.item_factory.create('wood_bundle')
        b=e.item_factory.create('wood_bundle')
        e.local_map.floor_objects[(12,12)]=[a,b]
        e._handle_key(pygame.K_COMMA)
        e._handle_key(pygame.K_DOWN);e._handle_key(pygame.K_DOWN)
        e._handle_key(pygame.K_RETURN)
        self.assertTrue(inv.contains(a))
        self.assertFalse(inv.contains(b))
        self.assertEqual([b],e.local_map.floor_objects[(12,12)])
        self.assertTrue(any('Too much to carry' in m.text for m in e.log.messages))
        # A small output is admitted under the same discount despite raw mass.
        output=e.item_factory.create('stalker_musk_gland')
        self.assertTrue(exchange(e,[],[output]))
        self.assertGreater(sum(i.weight for i in inv.items),inv.capacity)
        self.assertLess(inv.current_weight,inv.capacity)

    def test_heat_tracks_real_offhand_flame_but_passive_work_requires_station(self):
        e = self.e; torch = self.add('tallow_torch'); self.add('stalker_musk_gland')
        ambient = lambda: CraftScreen._build_ambient_sources(e)
        self.assertFalse(ambient())
        use(e,torch)
        self.assertIn(dict(tag='burning',tier=1),ambient())
        self.assertTrue(plan_craft(self.data.recipes['musk_pellet'],e.player.inventory,ambient_sources=ambient())[1])
        use(e,torch)
        self.assertFalse(ambient())
        use(e,torch)
        torch.turns_lit = torch.burn_turns
        self.assertFalse(ambient())
        torch.turns_lit = 0
        e.player.equipment.unequip('offhand')
        self.assertFalse(ambient())
        e.local_map.decor[(14,12)] = 'campfire_lit'
        self.assertFalse(plan_craft(self.data.recipes['musk_pellet'],e.player.inventory,ambient_sources=ambient())[1])
        e.local_map.decor[(14,12)] = 'campfire_unlit'
        self.assertFalse(ambient())

    def test_genuine_old_witness_preserves_mutable_state_owners_custom_handler_and_f9(self):
        e,w = load_witness(Path(self.tmp.name)/'witness')
        for row,item in zip(w['items'][:5],e.player.inventory.items[:5]):
            expected = dict(row['state'])
            if expected['on_use'] is None:
                expected['on_use'] = 'equip_toggle'
            self.assertEqual(expected,serialize_item(item))
        self.assertEqual('read',e.player.inventory.items[4].on_use)
        for owner,items in ((e.local_map,e.local_map.floor_objects[(13,12)]),
                            (e.local_map,e.local_map.container_state[(14,12)]['items']),
                            (e.save_manager.cache.load(1,0).local_map,e.save_manager.cache.load(1,0).local_map.floor_objects[(11,12)])):
            self.assertEqual('equip_toggle',items[0].on_use)
        initial = witness_state(e)
        e.debug = None
        for item in e.player.inventory.items[:4]:
            use(e,item)
            self.assertTrue(item.equipped)
        floor = e.local_map.floor_objects[(13,12)][0]
        self.assertTrue(take_floor(e,floor)); use(e,floor)
        stored = e.local_map.container_state[(14,12)]['items'][0]
        self.assertTrue(take_container(e,14,12,stored)); use(e,stored)
        e._handle_key(pygame.K_F9)
        self.assertEqual(initial,witness_state(e))
        result = subprocess.run([sys.executable,str(Path(__file__).resolve()),'--cold-witness'],
                                capture_output=True,text=True,timeout=40)
        self.assertEqual(0,result.returncode,result.stdout+result.stderr)
        self.assertEqual(json.loads(json.dumps(initial)),json.loads(result.stdout.strip().splitlines()[-1]))

    def reader(self,definition):
        e = self.e
        old=Path.cwd()
        try:
            os.chdir(GAME_ROOT); pygame.display.set_mode((480,320)); e.display.init()
        finally:
            os.chdir(old)
        e.text_reader.init(e.display)
        e.text_reader.open_text(definition)
        return e.text_reader

    def all_rows(self,reader,size=(480,320)):
        surface=pygame.Surface(size)
        reader.handle_key(pygame.K_HOME)
        reader.render(surface,self.e)
        seen=set(reader._visible_rows)
        for _ in range(300):
            if reader._scroll==reader._max_scroll:
                break
            self.e._handle_key(pygame.K_PAGEDOWN)
            reader.render(surface,self.e)
            seen.update(reader._visible_rows)
        self.assertEqual(set(range(len(reader._layout_rows))),seen)
        self.assertTrue(surface.get_rect().contains(reader._frame))
        self.assertTrue(reader._frame.contains(reader._viewport))
        self.assertTrue(all(sum(f['width'] for f in row)<=reader._viewport.width for row in reader._layout_rows))
        return reader._layout_rows

    def test_actual_warning_later_page_paragraphs_mixed_span_identity_and_no_turns(self):
        e=self.e
        definition=copy.deepcopy(self.data.texts['lab_label_sarcophagus'])
        definition['pages'].append(dict(text='Later paragraph.\n\n'+('Long words and clauses. '*80)+'[DAMAGED] then [REDACTED] end.'))
        r=self.reader(definition)
        e.player.language.recover_span(definition['id'],1,1,'RECOVERED ORIGINAL SPAN')
        before=(e.world_time.turn,e.rng.getstate(),copy.deepcopy(e.player.language.__dict__),e.player.needs.hunger)
        rows=self.all_rows(r)
        self.assertIn('do not ring the bells.',''.join(f['text'] for row in rows for f in row))
        e._handle_key(pygame.K_RIGHT)
        self.assertEqual(0,r._scroll)
        rows=self.all_rows(r)
        self.assertTrue(any(not row for row in rows))
        self.assertIn('RECOVERED ORIGINAL SPAN',''.join(f['text'] for row in rows for f in row))
        self.assertTrue(all(f['span']==1 for row in rows for f in row if 'RECOVERED' in f['text']))
        self.assertEqual(before,(e.world_time.turn,e.rng.getstate(),e.player.language.__dict__,e.player.needs.hunger))
        e._handle_key(pygame.K_KP_ENTER)
        self.assertFalse(r.open)

    def test_long_tokens_glyph_translations_and_complete_alphabet_are_bounded(self):
        e=self.e
        word=next(iter(self.data.deep_tongue))
        r=self.reader(dict(id='g12-glyph',deep_tongue=True,pages=[dict(text='W'*600+'\n'+((word+' ')*200))]))
        self.all_rows(r)
        e.player.language.known_deep_words.add(word)
        self.all_rows(r)
        r.open_text(dict(id='g12-inscription',pages=[dict(text=(word+'\n\n')*80)]),panel_style='ziggurat',text_align='center')
        self.all_rows(r)
        r.open_text(dict(id='g12-alphabet',render_mode='alphabet',pages=[dict(text='')]))
        rows=self.all_rows(r)
        from rendering.glyph_gen import get_all_phonemes
        self.assertTrue(get_all_phonemes())
        self.assertEqual([p for p,_ in get_all_phonemes()],[f['text'] for row in rows for f in row])


if __name__=='__main__':
    if '--cold-witness' in sys.argv:
        with tempfile.TemporaryDirectory(prefix='resonance-g12-cold-witness-') as root:
            e,_=load_witness(root)
            print(json.dumps(witness_state(e)))
    else:
        unittest.main()
