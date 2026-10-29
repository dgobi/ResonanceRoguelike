"""Production equipment consumers. Deterministic RNG is confined to these tests.

The ordinary engine attack caller and incoming AI caller invoke the real resolver;
spies only record its returned results. Native journey retains normal randomness.
"""
import copy
from pathlib import Path
import random
import tempfile
import unittest
from unittest.mock import patch
import pygame
from test_effect_persistence import load_data, make_engine
from engine.combat import resolve_attack
from engine.item_transfers import take_floor, drop, consume, exchange
from engine.item_system import _recompute_effective_av
from generation.floor_object_utils import place_floor_object
from components.ai import _monster_attack_entity


class BranchRng(random.Random):
    def __init__(self, roll=.9): super().__init__(17);self.roll=roll
    def random(self): return self.roll
    def randint(self,a,b): return b


class EquipmentConsumers(unittest.TestCase):
    @classmethod
    def setUpClass(cls): pygame.init();cls.base=load_data()
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='w5m-equipment-');self.addCleanup(self.tmp.cleanup)
        p=patch('engine.save_manager.SAVE_DIR',Path(self.tmp.name)/'saves');p.start();self.addCleanup(p.stop)
        self.data=copy.copy(self.base);self.data.items=copy.deepcopy(self.base.items)
        self.e=make_engine(self.data);self.e.debug=None;self.e.rng=BranchRng()
    def definition(self,source,id,**changes):
        self.data.items[id]=dict(self.data.items[source],id=id,on_use='equip_toggle',**changes)
        return self.data.items[id]
    def acquire(self,id):
        e=self.e;item=e.item_factory.create(id,e.player.x,e.player.y)
        self.assertTrue(place_floor_object(e.local_map,e.player.x,e.player.y,item));self.assertTrue(take_floor(e,item))
        self.assertFalse(take_floor(e,item));return item
    def use(self,item):
        e=self.e;screen=e.inventory_screen;screen.open=True;screen._flat=[(item,False,'')];screen.selected=0
        before=e.world_time.turn
        with patch.object(e,'_advance_turn',wraps=e._advance_turn) as advance:e._handle_key(pygame.K_RETURN)
        self.assertEqual(advance.call_count,1);self.assertEqual(e.world_time.turn,before+1)
        self.assertTrue(e.player.inventory.contains(item));screen.open=False
    def trace(self,action):
        observed=[]
        def record(**kwargs):
            result=resolve_attack(**kwargs);observed.append((kwargs,result));return result
        with patch('engine.combat.resolve_attack',side_effect=record):action()
        self.assertEqual(len(observed),1);return observed[0]

    def test_normal_attack_reads_equipped_definition_and_additional_crit_then_inherited_moveset(self):
        e=self.e;raw=self.definition('crude_blade','w5m_weapon',damage_dice='2d5',damage_bonus=2,crit_chance=.3)
        item=self.acquire(raw['id']);self.use(item)
        target=e.creature_factory.spawn('stone_lurker',13,12);e.entities.append(target)
        e.rng=BranchRng(.1)
        args,result=self.trace(lambda:e._player_attack(target))
        self.assertEqual(args['weapon']['id'],raw['id']);self.assertEqual(args['weapon']['damage_dice'],'2d5')
        self.assertEqual(result.damage_raw,12);self.assertTrue(result.is_crit)
        # Owned physical object stays the same; ordinary combat reads today's
        # loaded definition instead of an ITEM_STATE damage snapshot.
        self.data.items[item.item_id]['damage_dice']='1d2';self.data.items[item.item_id]['damage_bonus']=1
        target.fighter.hp=target.fighter.max_hp;target.is_alive=True
        self.assertEqual(self.trace(lambda:e._player_attack(target))[1].damage_raw,3)
        # Same inherited action ID, including cooldown identity across a new item.
        target.fighter.hp=target.fighter.max_hp;target.is_alive=True
        self.assertTrue(self.trace(lambda:e._try_moveset_action(e.display.MOVESET_KEY_1))[1].hit)
        self.assertEqual(e.moveset_cooldowns['hack'],4)
        self.definition('crude_blade','w5m_sibling_weapon',damage_dice='1d2')
        other=self.acquire('w5m_sibling_weapon');e.item_system.use(other,e)
        self.assertFalse(e._try_moveset_action(e.display.MOVESET_KEY_1));self.assertEqual(e.moveset_cooldowns['hack'],4)

    def test_incoming_route_supplies_shield_and_sum_av_ignores_coverage(self):
        e=self.e
        self.definition('faceted_ward','w5m_shield',block_chance=.8,block_value=3)
        self.definition('leather_jack','w5m_armour',armor_layers=[dict(name='shell',material='leather',armor_value=2,coverage=.1),dict(name='lining',material='cloth',armor_value=3)])
        shield=self.acquire('w5m_shield');armour=self.acquire('w5m_armour');self.use(shield);self.use(armour)
        self.assertEqual(e.player.fighter.effective_av,5)
        self.data.items['w5m_armour']['armor_layers'][0]['coverage']=1;_recompute_effective_av(e.player,self.data)
        self.assertEqual(e.player.fighter.effective_av,5)
        monster=e.creature_factory.spawn('stone_lurker',13,12);e.entities.append(monster)
        for roll,blocked in ((.1,True),(.9,False)):
            e.rng=BranchRng(roll);args,result=self.trace(lambda:_monster_attack_entity(monster,e.player,e))
            self.assertIs(args['shield_def'],self.data.items['w5m_shield']);self.assertEqual(result.blocked,blocked)
            self.assertEqual(result.block_reduction,3 if blocked else 0)
        self.use(armour);self.assertEqual(e.player.fighter.effective_av,0)

    def test_reduction_override_zero_fallback_owned_bag_and_capacity_admission(self):
        e=self.e;inv=e.player.inventory
        self.definition('leather_satchel','w5m_bag',weight_reductions={'all':.2,'Components':.75,'Tools':0})
        self.data.items['test_tool']=dict(id='test_tool',category='tool',weight=1)
        bag=self.acquire('w5m_bag');wood=self.acquire('wood_bundle');tool=self.acquire('test_tool')
        self.use(bag)
        from components.inventory import effective_weight,item_category
        expected=sum(effective_weight(i,item_category(i,self.data.items),{'all':.2,'Components':.75,'Tools':0}) for i in inv.items)
        self.assertAlmostEqual(inv.current_weight,expected);self.assertEqual(tool.weight,effective_weight(tool,'Tools',inv.reductions_for()))
        base=sum(i.weight for i in inv.items);weights=[i.weight for i in inv.items]
        inv.capacity=base+.1
        extra=e.item_factory.create('wood_bundle');self.assertTrue(inv.can_add(extra));self.use(bag);self.assertFalse(inv.can_add(extra))
        self.assertEqual(weights,[i.weight for i in inv.items]);self.use(bag)
        self.data.items[bag.item_id]['weight_reductions']={};self.assertEqual(inv.current_weight,base)
        self.data.items[bag.item_id]['weight_reductions']={'Components':.5};self.assertAlmostEqual(inv.current_weight,base-wood.weight*.5)
        inv.items.remove(bag);self.assertEqual(inv.reductions_for(),{});self.assertAlmostEqual(inv.current_weight,base-bag.weight)

    def test_exact_siblings_drop_replacement_stale_use_and_offhand_light(self):
        e=self.e;self.definition('leather_jack','w5m_armour')
        first=self.acquire('w5m_armour');second=self.acquire('w5m_armour');self.use(first);self.use(second)
        self.assertFalse(first.equipped);self.assertIs(e.player.equipment.equipped_in('armor_torso'),second)
        self.assertTrue(drop(e,first));self.assertIs(e.player.equipment.equipped_in('armor_torso'),second)
        self.assertFalse(e.item_system.use(first,e));self.assertIs(e.player.equipment.equipped_in('armor_torso'),second)
        self.assertTrue(consume(e,second));self.assertIsNone(e.player.equipment.equipped_in('armor_torso'));self.assertEqual(e.player.fighter.effective_av,0)
        torch=self.acquire('tallow_torch');self.use(torch);self.assertTrue(e.player.light_source.active)
        self.definition('faceted_ward','w5m_shield');shield=self.acquire('w5m_shield');burn=e.player.light_source._turns_used;self.use(shield)
        self.assertFalse(e.player.light_source.active);self.assertFalse(torch.equipped);self.assertTrue(e.player.inventory.contains(torch));self.assertGreaterEqual(torch.turns_lit,burn)
        self.assertIs(e.player.equipment.equipped_in('offhand'),shield)
        self.assertTrue(exchange(e,[shield]));self.assertIsNone(e.player.equipment.equipped_in('offhand'));self.assertTrue(e.player.inventory.contains(torch))

    def test_all_four_exact_legacy_repairs_retain_their_scope(self):
        e=self.e
        for id in ('revelation_lens','leather_satchel','herbalist_pouch','component_satchel'):
            item=self.acquire(id);self.assertIsNone(item.on_use);self.use(item);self.assertEqual(item.on_use,'equip_toggle')
            self.assertIs(e.player.equipment.equipped_in(self.data.items[id]['slot']),item)
        self.data.items['unbound']=dict(self.data.items['leather_satchel'],id='unbound')
        unbound=self.acquire('unbound');e.item_system.use(unbound,e);self.assertFalse(unbound.equipped)
        unbound.on_use='read';e.item_system.use(unbound,e);self.assertEqual(unbound.on_use,'read')

if __name__=='__main__':unittest.main(verbosity=2)
