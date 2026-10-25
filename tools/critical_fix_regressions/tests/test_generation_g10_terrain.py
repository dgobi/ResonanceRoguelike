"""Behavioral wilderness fields, original owner gating and explicit contracts."""
import copy
import contextlib
import io
import json
import os
from pathlib import Path
import random
import subprocess
import sys
import unittest
import numpy as np
from test_effect_persistence import load_data
from generation.context import GenerationContext, GenerationError
from generation.wilderness import make_policy, validate_profiles, sample, materialize
from generation.world_gen import generate_world
from generation.placement import digest
from engine.scene_generation import create_surface
from engine.item_factory import ItemFactory
from engine.creature_factory import CreatureFactory
from world.world_map import WorldMap
from g1_support import fingerprint

ROOT=Path(__file__).resolve().parents[3]


class G10Terrain(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data=load_data();cls.world=WorldMap(128,128);cls.world.seed=20261023
        with contextlib.redirect_stdout(io.StringIO()):generate_world(cls.world,cls.data,random.Random(0))

    def test_world_coordinate_crop_equality_horizontal_vertical_corner_and_orders(self):
        w=self.world;p=w.surface_policy;x0,y0=73*80,99*43
        reference=sample(w,p,x0,y0,160,86)
        rows=[]
        for order in ([(0,0),(1,0),(0,1),(1,1)],[(1,1),(0,1),(1,0),(0,0)]):
            for dx,dy in order:
                independent=sample(w,p,x0+dx*80,y0+dy*43)
                self.assertEqual(independent['metadata_reads'],9)
                for key in ('terrain','biome','cover','patch','wet','moisture','elevation'):
                    np.testing.assert_array_equal(independent[key],reference[key][dx*80:(dx+1)*80,dy*43:(dy+1)*43])
                rows.append(dict(chunk=[73+dx,99+dy],base=digest(independent['terrain'].tolist())))
        self.assertEqual(rows[:4],list(reversed(rows[4:])))

    def test_fresh_hash_seeds_match_same_absolute_samples(self):
        command=[sys.executable,'-c',
            "import json; from test_effect_persistence import load_data; from world.world_map import WorldMap; "
            "from engine.save_manager import _deserialize_world; import gzip; "
            "from generation.wilderness import make_policy,sample; from generation.placement import digest; "
            f"w=WorldMap(128,128); _deserialize_world(json.loads(gzip.decompress(open({str(ROOT/'evidence/worldgen-g10/before/world-20261023.json.gz')!r},'rb').read())),w); "
            "d=load_data();p=make_policy(d.wilderness_profiles,d);s=sample(w,p,5917,4297,160,86); "
            "print(digest({k:v.tolist() for k,v in s.items() if k!='metadata_reads'}))"]
        outputs=[]
        for seed in ('1','987654'):
            env=dict(os.environ,PYTHONHASHSEED=seed)
            r=subprocess.run(command,env=env,text=True,capture_output=True,timeout=60)
            self.assertEqual(r.returncode,0,r.stderr);outputs.append(r.stdout.strip())
        self.assertEqual(outputs[0],outputs[1])

    def test_strict_profiles_and_atomic_new_world_creation(self):
        changes=[lambda p:p.update(version=True),lambda p:p.update(extra=1),
            lambda p:p['profiles']['forest'].update(unknown=1),
            lambda p:p['profiles']['forest'].update(cover=float('nan')),
            lambda p:p['profiles']['forest'].update(scale=100000),
            lambda p:p['profiles']['forest']['palette'].update(ground='grey_stone'),
            lambda p:p['profiles']['ash_wastes']['palette'].update(ground='varied_grass'),
            lambda p:p['profiles']['forest']['palette'].update(patch='varied_grass')]
        for change in changes:
            d=copy.copy(self.data);d.wilderness_profiles=copy.deepcopy(d.wilderness_profiles);change(d.wilderness_profiles)
            w=WorldMap(128,128);w.seed=44;before=copy.deepcopy(vars(w));rng=random.Random(42);state=rng.getstate()
            with self.assertRaises(GenerationError):generate_world(w,d,rng)
            self.assertEqual(vars(w),before);self.assertEqual(rng.getstate(),state)

    def test_barren_interior_and_complete_populated_owner_masks(self):
        from generation.access import enterable, reachable
        from generation.world_plan import address
        from rendering.decor import PLANT_DECOR_IDS
        w=self.world;items=ItemFactory(self.data);creatures=CreatureFactory(self.data)
        keys=[(72,103),(73,100),(79,106),(73,93),
              tuple(w.plan['settlements'][0]['members'][0]),tuple(w.plan['sites'][0]['chunk']),
              address(*next(r for r in w.plan['routes'] if r['id']=='road-1')['points'][1])[:2]]
        total=0
        with contextlib.redirect_stdout(io.StringIO()):
            for xy in keys:
                r=create_surface(w,w.get(*xy),self.data,items,creatures,80,43);m=r.local_map;total+=len(r.actors)
                self.assertTrue(all(enterable(m,p,self.data) for p in m.road_cells))
                self.assertFalse({(a.x,a.y) for a in r.actors}&m.protected_cells)
                if xy==(72,103):
                    interior={(x,y) for x in range(12,68) for y in range(12,31)}
                    self.assertTrue(all(str(m.tiles[xy]['terrain']) not in ('tree','grass','tall_grass') for xy in interior))
                    self.assertFalse({xy for xy,v in m.decor.items() if v in PLANT_DECOR_IDS}&interior)
                if xy==(73,100):
                    reached=reachable(m,r.spawn,self.data)
                    self.assertTrue(any(x in (0,79) or y in (0,42) for x,y in reached),
                                    'natural arrival must not select an isolated gap inside the tree mass')
                if w.get(*xy).biome_id=='town':
                    old=copy.copy(w);old.surface_schema=0;old.surface_policy=None
                    prior=create_surface(old,old.get(*xy),self.data,items,creatures,80,43)
                    self.assertEqual(fingerprint(m,r.actors),fingerprint(prior.local_map,prior.actors))
                    self.assertEqual(m.surface_provenance['owner'],'urban-g9')
        self.assertGreater(total,0)
        with contextlib.redirect_stdout(io.StringIO()):
            r=create_surface(w,w.get(w.start_wx,w.start_wy),self.data,items,creatures,80,43)
        stone=next(xy for xy,value in r.local_map.decor.items() if value=='waystone_plinth')
        td=self.data.terrain[str(r.local_map.tiles[stone]['terrain'])]
        self.assertFalse(any(td.get(k) for k in ('harvestable','gatherable','interactable')))

    def test_independent_completed_creation_orders_do_not_reseed_native_domains(self):
        w=self.world;items=ItemFactory(self.data);creatures=CreatureFactory(self.data);results={}
        for order in ([(73,99),(74,99)],[(74,99),(73,99)]):
            for xy in order:
                with contextlib.redirect_stdout(io.StringIO()):r=create_surface(w,w.get(*xy),self.data,items,creatures,80,43)
                actual=fingerprint(r.local_map,r.actors)
                if xy in results:self.assertEqual(results[xy],actual)
                results[xy]=actual
                self.assertEqual(r.local_map.generation_context,GenerationContext(w.seed,w.get(*xy).seed,(*xy,None)))
                self.assertEqual(r.local_map.generation_context.revision,'wg9')
                self.assertEqual(r.local_map.wilderness_generation['repairs'],[])
        self.assertFalse(any(c.visited for c in w.chunks.values()))
