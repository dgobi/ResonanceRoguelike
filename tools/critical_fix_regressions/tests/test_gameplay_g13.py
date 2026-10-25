"""The installed stocked shed uses real content, access and fresh selection."""
import copy
import contextlib
import io
import json
from pathlib import Path
import random
import unittest
import zipfile

from test_effect_persistence import load_data
from historical_selection import historical_profiles
from generation.placement import transform, entrance_cells, NORMALS
from generation.structure_preview import preview
from generation.settlement_selection import validate
from generation.world_gen import generate_world
from engine.scene_generation import create_surface
from engine.item_factory import ItemFactory
from engine.creature_factory import CreatureFactory
from world.world_map import WorldMap


class G13Shed(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = load_data()

    def test_versioned_content_and_every_permitted_orientation(self):
        data = self.data
        old, new = data.structures['tool_shed_a'], data.structures['tool_shed_b']
        geometry = copy.deepcopy(old['placement'])
        geometry['contexts'] = ['grid', 'roadside']
        self.assertEqual(new['placement'], geometry)
        for key in ('width', 'height', 'facing'):
            self.assertEqual(new[key], old[key])
        # Interior furniture can change; the enclosing walls and doorway cannot.
        self.assertEqual([''.join('.' if c=='T' else c for c in row) for row in new['layers']], old['layers'])
        specials = [s for s in new['special_tiles'] if s['type']=='container']
        self.assertEqual([(s['x'], s['y'], s['decor_id']) for s in specials],
                         [(1,1,'crate'),(6,1,'crate'),(6,3,'barrel')])
        pools = [data.loot_pools[s['loot_pools'][0]] for s in specials]
        satchel = pools[1]
        self.assertEqual(satchel['roll_count'], [1, 1])
        self.assertEqual(satchel['items'], [dict(item_id='leather_satchel', weight=1)])
        self.assertFalse(any(row['item_id']=='leather_satchel' for pool in (pools[0], pools[2]) for row in pool['items']))
        for rotation in new['placement']['rotations']:
            with self.subTest(rotation=rotation):
                moved = transform(new, rotation, False)
                p = moved['placement']; door = p['entrances'][0]; dx, dy = NORMALS[door['normal']]
                report, m, actors = preview(moved, 'ordinary_building', data, category='storage', expectations={
                    'entry':dict(x=door['x']+dx,y=door['y']+dy),
                    'targets':p['targets']+[dict(x=x,y=y,kind='floor',required=True) for x,y in entrance_cells(door)]})
                self.assertTrue(report['passed'], report['access'])
                self.assertEqual(len(m.container_state), 3)
                self.assertEqual(sum(i.item_id=='leather_satchel' for c in m.container_state.values() for i in c['items']), 1)
                self.assertEqual(sum(d=='decor_candle' for d in m.decor.values()), 1)
                self.assertEqual(sum(str(t)=='table' for t in m.tiles['terrain'].flat), 1)

    def test_current_selection_and_production_materialization(self):
        data = self.data
        validate(data.settlement_profiles, data)
        expected = historical_profiles()
        for form in ('grid', 'roadside'):
            for row in expected['profiles'][form]['roles']['support']:
                if row['asset']=='tool_shed_a':
                    self.assertEqual(row, dict(asset='tool_shed_a',weight=1.0,max_per_settlement=3))
                    row['asset']='tool_shed_b'
            for row in expected['profiles'][form]['roles']['commercial']:
                if row['asset']=='apothecary_a':
                    self.assertEqual(row, dict(asset='apothecary_a',weight=1.0,max_per_settlement=5))
                    row['asset']='apothecary_b'
        self.assertEqual(data.settlement_profiles, expected)
        w = WorldMap(128,128); w.seed=20261023
        with contextlib.redirect_stdout(io.StringIO()):
            generate_world(w,data,random.Random(w.seed))
        selected = [p for p in w.plan['placements'] if p['asset']=='tool_shed_b']
        self.assertEqual(sorted((p['origin'][0]//80,p['origin'][1]//43) for p in selected), [(39,26),(75,99),(88,33)])
        checkpoint=Path(__file__).resolve().parents[3]/'evidence/gameplay-g12/final-b/journey/lab/lab-checkpoint.zip'
        with zipfile.ZipFile(checkpoint) as z:
            original=json.loads(z.read('world.json'))['plan']
        previous=[p for p in original['placements'] if p['asset']=='tool_shed_a' and p['context'] in ('grid','roadside')]
        keys=('id','origin','rotation','mirror','footprint','clearance','approach','entrances','targets','join','road')
        self.assertEqual([{k:p[k] for k in keys} for p in selected], [{k:p[k] for k in keys} for p in previous])
        self.assertFalse(any(p['asset']=='tool_shed_a' and p['context'] in ('grid','roadside') for p in w.plan['placements']))
        for p in selected:
            x,y=p['origin'][0]//80,p['origin'][1]//43
            scene=create_surface(w,w.get(x,y),data,ItemFactory(data),CreatureFactory(data),80,43)
            owned=[scene.local_map.container_state[t['x']-x*80,t['y']-y*43]
                   for t in p['targets'] if t['kind']=='container']
            self.assertEqual(len(owned),3)
            self.assertEqual(sum(i.item_id=='leather_satchel' for c in owned for i in c['items']),1)
            self.assertEqual([i.item_id for i in owned[1]['items']],['leather_satchel'])
