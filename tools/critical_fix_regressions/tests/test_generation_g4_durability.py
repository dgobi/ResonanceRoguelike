"""Coherent checkpoint recovery and an explicit original-G3-plan adapter fixture."""
import copy
import gzip
import json
import pickle
import random
from pathlib import Path
import unittest
from unittest.mock import patch
import test_generation_g4 as gameplay
import test_generation_g3_lifecycle as lifecycle
from test_effect_persistence import make_engine
from generation.world_plan import validate_plan,address
from generation.placement import digest
from generation.context import GenerationError
from engine.save_manager import _serialize_world,_deserialize_world
from engine.checkpoints import record
from world.world_map import WorldMap
from g1_support import fingerprint


class G4Durability(unittest.TestCase):
    setUpClass=classmethod(gameplay.G4Gameplay.setUpClass.__func__)
    setUp=gameplay.G4Gameplay.setUp
    scene=gameplay.G4Gameplay.scene
    boot=lifecycle.G3Lifecycle.boot

    def old_world(self):
        w=copy.deepcopy(self.world)
        path=Path(__file__).resolve().parents[1]/'fixtures/g3_plan_20261023.json.gz'
        w.plan=json.loads(gzip.decompress(path.read_bytes())); w.generation_revision='wg3'
        for xy in w.town_chunks:
            c=w.get(*xy); c.town_role='planned'; c.name='historical '+str(xy)
            c.zones=[('heath',.6),('deepwood',.1)]; c.difficulty=.17; c.resonance=.21
        return w

    def test_original_g3_unseen_order_geometry_and_historical_metadata(self):
        w=self.old_world(); self.assertTrue(validate_plan(w.plan,128,128))
        before=digest(_serialize_world(w)); geometry=digest(w.plan)
        keys=[tuple(s['members'][0]) for s in w.plan['settlements'][:2]]
        first={xy:fingerprint((r:=self.scene(xy,w)).local_map,r.actors,r.metadata.town_data) for xy in keys}
        second={xy:fingerprint((r:=self.scene(xy,w)).local_map,r.actors,r.metadata.town_data) for xy in reversed(keys)}
        self.assertEqual(first,second); self.assertEqual(digest(w.plan),geometry); self.assertEqual(digest(_serialize_world(w)),before)
        r=self.scene(keys[0],w); self.assertEqual(r.local_map.generation_revision,'wg4')
        self.assertEqual(r.local_map.plan_provenance['adapter'],'g3-to-g4-v1'); self.assertEqual(r.local_map.plan_provenance['plan_revision'],'wg3')
        self.assertGreater(len(r.actors),0)
        # A real cold world reconstruction preserves old values rather than deriving new policy.
        cold=WorldMap(128,128);_deserialize_world(_serialize_world(w),cold)
        self.assertEqual(digest(_serialize_world(cold)),before)

    def test_old_visited_state_no_generation_and_adapter_checkpoint(self):
        e=self.boot(); old=self.old_world()
        start=(old.start_wx,old.start_wy)
        old.get(*start).submaps=copy.deepcopy(e.world_map.get(*start).submaps)
        e.world_map=old
        # Bootstrap start exists. Mark the disposable visited start as original G3,
        # with its historical missing interaction and saved mutations.
        xy=(old.start_wx,old.start_wy); cached=e.save_manager.cache.load(*xy); m=cached.local_map
        m.generation_revision='wg3'; m.decor={p:v for p,v in m.decor.items() if v!='waystone_plinth'}
        m.plan_provenance={k:v for k,v in m.plan_provenance.items() if k in ('mode','routes','crossings','placements')}
        from generation.world_plan import slice_plan
        section=slice_plan(old.plan,*xy)
        m.plan_provenance.update({k:[r['id'] for r in section[k]] for k in ('routes','crossings','placements')})
        m.set_tile(2,2,'mud',True,True); old.get(*xy).generation_revision='wg3'
        e.save_manager.cache.store(*xy,m,[])
        # First materialization from G3 geometry records the real G4 adapter.
        pending=tuple(old.plan['settlements'][0]['members'][0]); created=e._prepare_destination(*pending)
        self.assertIsNotNone(created); expected=fingerprint(*created)
        self.assertTrue(e.save_manager.save(e),e.save_manager.last_error)
        with patch('generation.world_plan.build_plan',side_effect=AssertionError('replanned')),patch('engine.scene_generation.populate',side_effect=AssertionError('repopulated')):
            self.assertTrue(e.save_manager.load(e),e.save_manager.last_error)
            self.assertEqual(fingerprint(*e._prepare_destination(*pending)),expected)
            visited=e._prepare_destination(*xy)[0]
            self.assertFalse(any(v=='waystone_plinth' for v in visited.decor.values()))
            self.assertEqual(str(visited.tiles[2,2]['terrain']),'mud')

    def test_malformed_records_and_world_reverse_ownership(self):
        mutations=[('settlement',lambda p:p['settlements'].pop()),
            ('rotation',lambda p:p['placements'][0].update(rotation=45)),
            ('mirror',lambda p:p['placements'][0].update(mirror=1)),
            ('boolean coordinate',lambda p:p['placements'][0]['origin'].__setitem__(0,True)),
            ('orphan',lambda p:p['plots'][0].update(owner='missing')),
            ('wrong road',lambda p:p['placements'][0].update(road='missing')),
            ('duplicate member',lambda p:p['settlements'][1]['members'].append(p['settlements'][0]['members'][0])),
            ('omitted reverse plot',lambda p:p['settlements'][0]['plots'].pop()),
            ('missing new semantics',lambda p:p['settlements'][0].pop('semantics')),
            ('new projection',lambda p:p.pop('dependency_projection')),
            ('reservation',lambda p:p['reservations'][-1]['rect'].__setitem__(0,True)),
            ('entrance',lambda p:p['placements'][0]['entrances'][0].update(width=False))]
        for label,mutate in mutations:
            p=copy.deepcopy(self.world.plan);mutate(p)
            with self.subTest(label=label),self.assertRaises(GenerationError):validate_plan(p,128,128)
        saved=_serialize_world(self.world); member=self.world.plan['settlements'][0]['members'][0]; key=','.join(map(str,member))
        for field,value in (('town_id',100),('town_role','missing'),('name','other'),('zones',[]),('difficulty',.123)):
            bad=copy.deepcopy(saved); bad['chunks'][key][field]=value
            with self.subTest(field=field),self.assertRaises(GenerationError):_deserialize_world(bad,WorldMap(128,128))
        w=self.old_world(); w.plan['settlements'].pop(); orphan=tuple(self.old_world().plan['settlements'][-1]['members'][0])
        with self.assertRaisesRegex(GenerationError,'settlement owner'):self.scene(orphan,w)

    def test_checksum_consistent_newest_corruption_coherent_recovery_and_failure(self):
        e=self.boot(); e.player.fighter.hp=41; self.assertTrue(e.save_manager.save(e)); earlier=e.save_manager.checkpoint_path()
        e.player.fighter.hp=37; self.assertTrue(e.save_manager.save(e)); newest=e.save_manager.checkpoint_path()
        original_world=(newest/'world.json').read_bytes(); original_manifest=(newest/'manifest.json').read_bytes()
        xy=(e.world_map.start_wx,e.world_map.start_wy); scene=newest/f'chunks/{xy[0]}_{xy[1]}.pkl'; original_scene=scene.read_bytes()
        for failure in ('missing-settlement','rotation','ownership','missing-map-marker','missing-provenance','missing-both','bad-identity','bad-revision'):
            (newest/'world.json').write_bytes(original_world);scene.write_bytes(original_scene)
            world=json.loads(original_world);saved=pickle.loads(original_scene);manifest=json.loads(original_manifest)
            if failure=='missing-settlement':world['plan']['settlements'].pop()
            elif failure=='rotation':world['plan']['placements'][0]['rotation']=45
            elif failure=='ownership':world['plan']['plots'][0]['owner']='missing'
            elif failure=='missing-map-marker':del saved.local_map.generation_revision
            elif failure=='missing-provenance':del saved.local_map.plan_provenance
            elif failure=='missing-both':del saved.local_map.generation_revision;del saved.local_map.plan_provenance
            elif failure=='bad-identity':saved.local_map.plan_provenance['plan_identity']='0'*64
            else:saved.local_map.generation_revision='wg99'
            (newest/'world.json').write_text(json.dumps(world));scene.write_bytes(pickle.dumps(saved,protocol=pickle.HIGHEST_PROTOCOL))
            manifest['files']['world.json']=record((newest/'world.json').read_bytes());manifest['files'][scene.relative_to(newest).as_posix()]=record(scene.read_bytes())
            (newest/'manifest.json').write_text(json.dumps(manifest))
            with self.subTest(failure=failure),self.assertRaises(ValueError):e.save_manager._prepare(e,newest)
            with patch('generation.world_plan.build_plan',side_effect=AssertionError('recovery replanned')),patch('engine.scene_generation.populate',side_effect=AssertionError('recovery populated')):
                self.assertTrue(e.save_manager.load(e),e.save_manager.last_error)
            self.assertEqual(e.player.fighter.hp,41)
        # Both supported candidates invalid: the currently active state survives.
        broken=json.loads((earlier/'world.json').read_bytes());broken['plan']['placements'][0]['rotation']=45
        (earlier/'world.json').write_text(json.dumps(broken));manifest=json.loads((earlier/'manifest.json').read_bytes())
        manifest['files']['world.json']=record((earlier/'world.json').read_bytes());(earlier/'manifest.json').write_text(json.dumps(manifest))
        active=e.local_map; before=digest(_serialize_world(e.world_map)); e.player.fighter.hp=33
        self.assertFalse(e.save_manager.load(e));self.assertIs(e.local_map,active);self.assertEqual(e.player.fighter.hp,33)
        self.assertEqual(digest(_serialize_world(e.world_map)),before)

    def test_legacy_world_new_scene_and_old_pending_dependency_edit(self):
        from generation.world_gen import generate_world
        from engine.scene_generation import create_surface
        e=self.boot(); w=WorldMap(128,128); w.seed=20261023
        generate_world(w,self.data,random.Random(0),plan_mode='legacy'); w.generation_revision='wg2'
        e.world_map=w
        # Separate legacy/no-plan positive uses its real no-plan generated scene.
        xy=(w.start_wx,w.start_wy);r=self.scene(xy,w);w.get(*xy).generation_revision='wg4'
        e.save_manager.cache.store(*xy,r.local_map,r.actors)
        self.assertFalse(hasattr(r.local_map,'plan_provenance'));self.assertTrue(e.save_manager.save(e));self.assertTrue(e.save_manager.load(e),e.save_manager.last_error)
        old=self.old_world();before=digest(old.plan);data=copy.copy(self.data);data.structures=copy.deepcopy(data.structures)
        data.structures['house_small_a']['legend']['w']='floor'; e.world_map=old;e.data=data
        house=next(p for p in old.plan['placements'] if p['asset']=='house_small_a');xy=address(*house['origin'])[:2]
        self.assertIsNone(e._prepare_destination(*xy)); self.assertEqual(digest(old.plan),before)
        landmark=next(p for p in old.plan['placements'] if p['context']=='landmark')
        self.assertIsNotNone(e._prepare_destination(*address(*landmark['origin'])[:2]))
