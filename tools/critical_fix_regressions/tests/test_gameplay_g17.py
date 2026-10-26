"""Authored-only creature admission, complete initial occupancy and staged publication."""
import copy
import json
from pathlib import Path
import random
import tempfile
import unittest
from unittest.mock import patch

from test_effect_persistence import load_data, make_engine, GAME_ROOT
from engine.creature_factory import CreatureFactory
from engine.item_factory import ItemFactory
from engine.scene_generation import populate, create_submap
from engine.save_manager import _serialize_entity
from generation.context import GenerationError, GenerationContext
from generation.floor_object_utils import place_floor_object, place_container
from generation.placement import digest
from generation.spawn_specs import resolve_special
from generation.structure_contract import compile_structure, StructureError
from generation.structure_preview import preview
from world.local_map import LocalMap, make_tile
from world.world_map import SubMap
from g1_support import fingerprint

EXAMPLE = GAME_ROOT/'docs/examples/g17_authored_creature_room.json'
ACCESS = EXAMPLE.with_suffix('.access.json')


class AuthoredCreatures(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = load_data()

    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix='resonance-g17-test-'); self.addCleanup(tmp.cleanup)
        p = patch('engine.save_manager.SAVE_DIR', Path(tmp.name)); p.start(); self.addCleanup(p.stop)
        self.raw = json.loads(EXAMPLE.read_text())
        self.items, self.creatures = ItemFactory(self.data), CreatureFactory(self.data)

    def room(self):
        m = LocalMap(11, 7, generation_context=GenerationContext(17, 170, ('g17-test',)))
        m.tiles[:] = make_tile('floor', True, True)
        return m

    def population(self, m, rows, **kwargs):
        return populate(self.data, self.items, self.creatures, m, rows, authored_arrival=(2, 5), **kwargs)

    def bind(self, raw=None):
        data = copy.copy(self.data)
        raw = raw or self.raw
        data.layouts = dict(data.layouts, **{raw['id']: raw})
        return data

    def test_direct_factory_actor_translation_preview_and_mixed_ownership(self):
        made = []
        original = CreatureFactory.spawn
        def track(factory, *args, **kwargs):
            actor = original(factory, *args, **kwargs); made.append(actor); return actor
        with patch.object(CreatureFactory, 'spawn', track):
            report, m, actors = preview(self.raw, 'authored_submap', self.data, path=EXAMPLE,
                                        expectations=json.loads(ACCESS.read_text()))
        self.assertTrue(report['passed']); self.assertEqual(made, actors)
        actor, = actors
        self.assertEqual((42, 20, 'hollow_revenant', 14), (actor.x, actor.y, actor._creature_id, actor.fighter.hp))
        self.assertIsNotNone(actor.ai); self.assertIsNotNone(actor.perception)
        receipt = report['population_receipts'][0]
        self.assertEqual([7, 2], receipt['source_xy']); self.assertEqual([42, 20], receipt['xy'])
        self.assertEqual([_serialize_entity(actor)], receipt['actors']); self.assertEqual([], receipt['objects'])
        self.assertEqual(1, receipt['actual_count'])
        self.assertEqual(dict(id='hollow_revenant', sha256=digest(self.data.entities['hollow_revenant'])), receipt['creature_definition'])
        self.assertEqual(EXAMPLE.name, Path(receipt['source_path']).name)
        self.assertTrue(receipt['record_id'].endswith('special[0]'))
        self.assertEqual('wood_bundle', m.floor_objects[(42, 20)][0].item_id)
        self.assertEqual('crate', m.container_state[(43, 22)]['decor_id'])
        self.assertEqual(len(self.data.structure_catalog.entries), 67)
        self.assertNotIn(self.raw['id'], self.data.layouts)
        ordinary = copy.deepcopy(self.raw); ordinary['special_tiles'] = ordinary['special_tiles'][1:]
        self.assertTrue(preview(ordinary, 'authored_submap', self.data)[0]['passed'])
        with self.assertRaisesRegex(GenerationError, 'translation only'):
            preview(self.raw, 'authored_submap', self.data, flip_v=True)

    def test_schema_diagnostics_ids_coordinates_conflicts_routes_and_fields(self):
        mutations = [dict(creature_id=None), dict(creature_id='missing'), dict(creature_id='player'),
            dict(x=None), dict(x=True), dict(y=2.5), dict(x=-1), dict(y=7), dict(kind='item'),
            dict(count=2), dict(group='x'), dict(fighter={'hp': 999}), dict(population_route='internal')]
        for values in mutations:
            raw = copy.deepcopy(self.raw); raw['special_tiles'][0].update(values)
            with self.subTest(values=values), self.assertRaises(StructureError) as cm:
                compile_structure(raw, 'authored_submap', self.data, path='g17-bad.json')
            self.assertTrue(any(d.field.startswith('special_tiles[0]') for d in cm.exception.diagnostics))
            self.assertIn('g17-bad.json', str(cm.exception))
        for field in ('x', 'y', 'creature_id'):
            raw = copy.deepcopy(self.raw); del raw['special_tiles'][0][field]
            with self.subTest(missing=field), self.assertRaises(StructureError):
                compile_structure(raw, 'authored_submap', self.data)
        for route in ('ordinary_building', 'plaza', 'interior_entrance'):
            raw = dict(self.raw, entrance_type='cave')
            with self.subTest(route=route), self.assertRaisesRegex(StructureError, 'CREATURE_ROUTE'):
                compile_structure(raw, route, self.data, category='commercial' if route == 'ordinary_building' else None)
            with self.assertRaisesRegex(GenerationError, 'authored_submap'):
                resolve_special(self.raw['special_tiles'][0], random.Random(1), 'special[0]', route=route)
        weighted = dict(type='weighted', x=7, y=2, spawn_table=[dict(type='creature', creature_id='hollow_revenant')])
        with self.assertRaisesRegex(StructureError, 'CREATURE_ROUTE'):
            compile_structure(dict(self.raw, special_tiles=[weighted]), 'authored_submap', self.data)
        with self.assertRaisesRegex(GenerationError, 'unsupported type'):
            resolve_special(weighted, random.Random(1), 'special[0]', route='authored_submap')

    def test_initial_obstructions_arrival_stairs_duplicates_and_batch_order(self):
        creature = self.raw['special_tiles'][0]
        for obstruction in ('wall', 'decor', 'arrival', 'stairs_up', 'stairs_down', 'duplicate', 'container-first', 'actor-first'):
            m = self.room(); rows = [dict(creature)]
            if obstruction == 'wall': m.set_tile(7, 2, 'wall', False, False)
            if obstruction == 'decor': m.decor[(7, 2)] = 'crate'
            if obstruction == 'arrival': rows[0].update(x=2, y=5)
            if obstruction in ('stairs_up', 'stairs_down'): m.set_tile(7, 2, obstruction, True, True)
            if obstruction == 'duplicate': rows.append(dict(creature))
            if obstruction in ('container-first', 'actor-first'):
                container = dict(type='container', x=7, y=2, decor_id='crate', loot_pools=[])
                rows = [container, creature] if obstruction == 'container-first' else [creature, container]
            before = fingerprint(m, [])
            with self.subTest(obstruction=obstruction), self.assertRaises(GenerationError): self.population(m, rows)
            self.assertEqual(before, fingerprint(m, []))
        # A guarding actor in the only corridor is legal: access is geometric.
        raw = dict(id='corridor', layers=['#######', '#<....#', '#######'],
                   legend={'#':'wall', '<':'stairs_up', '.':'floor'}, player_start=dict(x=1,y=1),
                   special_tiles=[dict(type='creature', x=3, y=1, creature_id='hollow_revenant')])
        self.assertTrue(preview(raw, 'authored_submap', self.data)[0]['passed'])
        # The engine relocates a non-walkable closed-door start to (1,4).
        # Reserve that actual arrival, not merely the declared source start.
        raw = copy.deepcopy(self.raw); raw['legend']['D'] = 'door_closed'
        raw['layers'][5] = '#.D.......#'
        raw['special_tiles'][0].update(x=1, y=4)
        with self.assertRaisesRegex(GenerationError, 'player arrival'):
            preview(raw, 'authored_submap', self.data)
        raw['special_tiles'][0].update(x=7, y=2)
        report, _, _ = preview(raw, 'authored_submap', self.data)
        self.assertEqual([36,22],report['spawn'])

    def test_creature_specific_water_admission_does_not_override_wall_or_decor(self):
        water = next(k for k,v in self.data.terrain.items() if v.get('walkable') and v.get('creature_passable') is False)
        for iid, blocked in [('hollow_revenant', False), ('drowned_revenant', False), ('drowned_revenant', True)]:
            m = self.room(); m.set_tile(7, 2, water, True, True)
            if blocked: m.decor[(7, 2)] = 'crate'
            rows = [dict(type='creature', x=7, y=2, creature_id=iid)]
            if iid == 'drowned_revenant' and not blocked:
                self.assertEqual(1, len(self.population(m, rows)))
            else:
                with self.assertRaisesRegex(GenerationError, 'blocked'): self.population(m, rows)
        m = self.room(); m.set_tile(7, 2, water, False, True)
        with self.assertRaisesRegex(GenerationError, 'blocked'):
            self.population(m, [dict(type='creature',x=7,y=2,creature_id='drowned_revenant')])

    def test_late_failure_preserves_existing_object_identity_and_receipts(self):
        for failure in ('late-record', 'factory'):
            m = self.room(); kept = self.items.create('wood_bundle',1,1)
            place_floor_object(m,1,1,kept); place_container(m,1,2,'crate',[])
            before = fingerprint(m,[]); owner = m.container_state[(1,2)]; receipts = []
            rows = [dict(self.raw['special_tiles'][1]), dict(self.raw['special_tiles'][2]), self.raw['special_tiles'][0]]
            if failure == 'late-record': rows.append(dict(type='item',x=3,y=3,item_id='unknown'))
            with patch.object(self.creatures, 'spawn', return_value=None):
                with self.subTest(failure=failure), self.assertRaises(GenerationError): self.population(m,rows,receipts=receipts)
            self.assertEqual(before, fingerprint(m,[])); self.assertEqual([],receipts)
            self.assertIs(kept,m.floor_objects[(1,1)][0]); self.assertIs(owner,m.container_state[(1,2)])

    def test_real_entry_rejects_late_factory_failure_without_publishing_or_departing(self):
        for failure in ('invalid-record', 'late-factory', 'internal-declaration'):
            raw = copy.deepcopy(self.raw)
            raw['special_tiles'] = raw['special_tiles'][1:] + raw['special_tiles'][:1]
            if failure == 'invalid-record': raw['special_tiles'].append(dict(type='item',x=4,y=4,item_id='unknown'))
            if failure == 'internal-declaration': raw['special_tiles'][-1].update(x=2,y=5,population_route='internal')
            e = make_engine(self.bind(raw)); sub = SubMap('g17','cave','Fixture',17,layout_id=raw['id'],surface_x=12,surface_y=12)
            e.world_map.get(0,0).submaps.append(sub)
            e.local_map.set_tile(12,12,'stairs_down',True,True); e.local_map.submap_links[(12,12)] = sub.submap_id
            m, player, entities = e.local_map, e.player, list(e.entities)
            original_metadata = copy.deepcopy(vars(sub)); before = fingerprint(m,[])
            with patch.object(e.creature_factory, 'spawn', return_value=None), patch.object(e.save_manager.cache, 'store_submap') as store:
                e._try_descend(); store.assert_not_called()
            self.assertIs(m,e.local_map); self.assertIs(player,e.player); self.assertEqual(entities,e.entities)
            self.assertIsNone(e.current_submap_id); self.assertEqual(original_metadata,vars(sub))
            self.assertEqual(before,fingerprint(m,[])); self.assertIsNone(e.save_manager.cache.load_submap(sub.submap_id))

    def test_starting_lab_and_internal_population_keep_existing_contract(self):
        e = make_engine(self.data)
        result = create_submap(e.world_map,0,0,SubMap('lab','laboratory','Lab',17,layout_id='starting_lab'),
                               self.data,self.items,self.creatures,80,43)
        self.assertFalse(result.actors); self.assertTrue(result.local_map.generation_complete)
        m = self.room(); m.decor[(7,2)] = 'crate'
        actors = populate(self.data,self.items,self.creatures,m,[dict(kind='creature',x=7,y=2,creature_id='hollow_revenant')]*2)
        self.assertEqual(2,len(actors))  # Internal policy is deliberately preserved.

    def test_genuine_g16_pending_bsp_and_visited_state(self):
        from g17_historical import inspect, ROOT
        self.assertEqual(json.loads((ROOT/'evidence/gameplay-g17/pre-edit-historical.json').read_text())['observed'],inspect())
