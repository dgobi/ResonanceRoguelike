"""Multiple required doors, independent geometry and authentic G3 plan recovery."""
import copy
import gzip
import hashlib
import json
from pathlib import Path
import unittest
from unittest.mock import patch
import pygame
from test_effect_persistence import load_data
import test_generation_g4 as g4
import test_generation_g3_lifecycle as lifecycle
from generation.placement import dependencies, digest, entrance_cells, transform, frontage_entrance
from generation.structure_contract import compile_structure
from generation.structure_preview import preview
from generation.plan_preview import planned_preview
from generation.world_plan import _plot, address, validate_plan
from generation.planned_scene import validate_access
from generation.access import reachable
from generation.context import GenerationError
from engine.save_manager import _serialize_world, _deserialize_world
from world.world_map import WorldMap, RegionType
from g1_support import fingerprint

FIXTURES=Path(__file__).resolve().parents[1]/'fixtures/g5'


class G5Entrances(unittest.TestCase):
    setUpClass=classmethod(g4.G4Gameplay.setUpClass.__func__)
    setUp=g4.G4Gameplay.setUp
    scene=g4.G4Gameplay.scene
    boot=lifecycle.G3Lifecycle.boot
    fixture=g4.G4Placement.fixture

    def test_door_geometry_all_transforms_and_assigned_scenes(self):
        original=json.loads((FIXTURES/'two_entrance_house.json').read_text())
        for shape in ('opposite','separated','wide'):
            raw=copy.deepcopy(original)
            if shape=='separated':
                raw['layers'][0]='##########'
                raw['layers'][-1]='##.####.##'
                raw['placement']['entrances']=[dict(id=n,x=x,y=7,normal='S',width=1,role=r,required=True)
                    for n,x,r in [('main',2,'main'),('service',7,'service')]]
            if shape=='wide':
                raw['layers'][-1]='####...###'; raw['placement']['entrances'][0]['width']=3
            compile_structure(raw,'ordinary_building',self.data,category='residential')
            for rotation in raw['placement']['rotations']:
                for mirror in (False,True):
                    with self.subTest(shape=shape,rotation=rotation,mirror=mirror):
                        moved=transform(raw,rotation,mirror)
                        expected=[]
                        for e in raw['placement']['entrances']:
                            for x,y in entrance_cells(e):
                                if mirror:x=9-x
                                expected.append(((x,y),(7-y,x),(9-x,7-y),(y,9-x))[rotation//90])
                        self.assertEqual(set(expected),{xy for e in moved['placement']['entrances'] for xy in entrance_cells(e)})
                        e=moved['placement']['entrances'][0]
                        report,m,_=preview(moved,'ordinary_building',self.data,category='residential',expectations={
                            'coordinates':'source','entry':dict(x=e['x'],y=e['y']),
                            'targets':[dict(x=x,y=y,kind='floor',required=True) for x,y in expected]})
                        self.assertTrue(report['passed'],report['access'])
            bound=copy.copy(self.data);bound.structures=copy.deepcopy(self.data.structures);bound.structures[raw['id']]=raw
            # Real assigned preview retains the ordinary other assets and realizes complete scenes.
            report=planned_preview(bound,20261023,raw,category='residential')
            self.assertTrue(report['previews'])
            self.assertTrue(validate_plan(report['plan'],128,128))
            for p in report['plan']['placements']:
                if p['asset']!=raw['id']:continue
                primary=frontage_entrance(p)
                self.assertTrue(set(entrance_cells(primary)))
                if shape=='opposite':
                    self.assertTrue(any(not (p['approach'][0]<=x<p['approach'][2] and p['approach'][1]<=y<p['approach'][3])
                        for e in p['entrances'] for x,y in entrance_cells(e)))

    def test_inaccessible_required_service_door_rejects(self):
        raw=json.loads((FIXTURES/'two_entrance_house.json').read_text())
        # A blocking decor object covers the complete rear doorway; unlike a
        # rear room wall, this also prevents access through the exterior buffer.
        raw['decor_layer']=[[None]*10 for _ in range(8)]
        raw['decor_layer'][0][4]='crate'
        bound=copy.copy(self.data);bound.structures=dict(self.data.structures,house_small_a=raw)
        with self.assertRaisesRegex(GenerationError,'entrance span is inaccessible|approach is blocked'):
            planned_preview(bound,20261023,raw,category='residential')

    def test_authentic_g3_plan_synthetic_envelope_checkpoint_and_f9(self):
        raw_bytes=gzip.decompress((FIXTURES/'two_entrance_g3_plan.json.gz').read_bytes())
        binding=json.loads((FIXTURES/'two_entrance_fixture_binding.json').read_text())
        self.assertEqual(hashlib.sha256(raw_bytes).hexdigest(),binding['historical_plan_file_sha256'])
        plan=json.loads(raw_bytes); identity=digest(plan)
        self.assertEqual(identity,binding['historical_plan_identity'])
        raw=json.loads((FIXTURES/'two_entrance_house.json').read_text())
        self.assertEqual(dependencies(raw,self.data),plan['dependencies']['house_small_a'])
        e=self.boot(); w=copy.deepcopy(self.world);w.plan=plan;w.generation_revision='wg3'
        expected={tuple(xy):i for i,s in enumerate(plan['settlements']) for xy in s['members']}
        for xy in w.town_chunks-set(expected):
            c=w.get(*xy);c.region_type=RegionType.PLAINS;c.biome_id='heath';c.town_id=-1;c.town_role='';c.town_data=None
        w.town_chunks=set(expected);w.town_chunk_ids=expected;w.town_groups={i:[tuple(xy) for xy in s['members']] for i,s in enumerate(plan['settlements'])}
        for xy,i in expected.items():
            c=w.get(*xy);c.region_type=RegionType.TOWN;c.biome_id='town';c.town_id=i;c.town_role='planned';c.town_data=None
            c.name='historical '+str(xy);c.zones=[('heath',.6),('deepwood',.1)];c.difficulty=.17;c.resonance=.21
        start=(w.start_wx,w.start_wy);w.get(*start).submaps=copy.deepcopy(e.world_map.get(*start).submaps)
        e.world_map=w;e.data=copy.copy(self.data);e.data.structures=dict(self.data.structures,house_small_a=raw)
        # Genuine original plan; the surrounding world/checkpoint is explicitly synthetic.
        before=digest(_serialize_world(w));cold=WorldMap(128,128);_deserialize_world(_serialize_world(w),cold)
        self.assertEqual(before,digest(_serialize_world(cold)))
        # Adapt the existing disposable start's provenance to this original plan.
        from generation.world_plan import slice_plan
        cached=e.save_manager.cache.load(*start);m=cached.local_map;m.generation_revision='wg3'
        section=slice_plan(plan,*start);m.plan_provenance=dict(mode='shared-v1',**{k:[r['id'] for r in section[k]] for k in ('routes','crossings','placements')})
        m.set_tile(2,2,'mud',True,True);w.get(*start).generation_revision='wg3';e.save_manager.cache.store(*start,m,[])
        xy=address(*next(p for p in plan['placements'] if p['asset']=='house_small_a')['origin'])[:2]
        created=e._prepare_destination(*xy);self.assertIsNotNone(created)
        scene=fingerprint(*created);self.assertEqual(digest(e.world_map.plan),identity)
        self.assertTrue(e.save_manager.save(e),e.save_manager.last_error)
        e.save_manager._prepare(e,e.save_manager.checkpoint_path())
        created[0].set_tile(2,2,'rock',False,False);e.player.fighter.hp=3
        with patch('generation.world_plan.build_plan',side_effect=AssertionError('replanned')),patch('engine.scene_generation.populate',side_effect=AssertionError('repopulated')):
            self.assertTrue(e.save_manager.load(e),e.save_manager.last_error)
            e.debug=False;e._handle_key_local(pygame.K_F9)
            self.assertEqual(fingerprint(*e._prepare_destination(*xy)),scene)
            self.assertEqual(str(e._prepare_destination(*start)[0].tiles[2,2]['terrain']),'mud')
        self.assertEqual(digest(e.world_map.plan),identity)
