"""Actual roller and staged scene failures. RNG controls only at arithmetic edges."""
import copy, random, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
from engine.loot_roller import roll_pool, roll_pools
from engine.item_factory import ItemFactory
from engine.scene_generation import populate
from generation.context import GenerationError
from test_effect_persistence import load_data, make_engine


class BoundaryRng:
    def __init__(self,value): self.value=value; self.calls=[]
    def randint(self,a,b): self.calls.append(('count',a,b)); return b
    def random(self): self.calls.append(('entry',)); return self.value


class PoolConsumers(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.data=load_data()
    def setUp(self):
        temporary=tempfile.TemporaryDirectory(prefix='w5o-container-consumer-');self.addCleanup(temporary.cleanup)
        self.save_root=Path(temporary.name)/'saves'
        save=patch('engine.save_manager.SAVE_DIR',self.save_root);save.start();self.addCleanup(save.stop)
    def test_zero_positions_exact_boundaries_and_rounded_fallback(self):
        factory=ItemFactory(self.data)
        for weights in ([0,1],[1,0,1],[1,0],[0,1,0,1,0]):
            raw=dict(roll_count=[len(weights)],items=[dict(item_id='wood_bundle' if w else 'flint_shard',weight=w) for w in weights])
            for value in (0.0,.5,1.0):
                rng=BoundaryRng(value);items=roll_pool(raw,factory,rng)
                self.assertEqual([i.item_id for i in items],['wood_bundle']*weights.count(1))
                self.assertEqual(len({id(i) for i in items}),len(items))
                self.assertEqual(rng.calls,[('count',len(weights),len(weights))]+[('entry',)]*weights.count(1))
        # At an exact cumulative boundary the following positive row wins.
        rng=BoundaryRng(.5)
        raw=dict(roll_count=[1],items=[dict(item_id='flint_shard'),dict(item_id='tallow_torch',weight=0),dict(item_id='wood_bundle')])
        self.assertEqual(roll_pool(raw,factory,rng)[0].item_id,'wood_bundle')
    def test_count_defaults_zero_cap_repeats_and_ordered_pool_occurrences(self):
        factory=ItemFactory(self.data)
        a=dict(items=[dict(item_id='wood_bundle'),dict(item_id='wood_bundle'),dict(item_id='flint_shard',weight=0)],roll_count=[2**53-1])
        b=dict(items=[dict(item_id='tallow_torch')])
        rng=BoundaryRng(0)
        outputs=roll_pools(['a','b','a'],dict(a=a,b=b),factory,rng)
        self.assertEqual([i.item_id for i in outputs],['wood_bundle','wood_bundle','tallow_torch','wood_bundle','wood_bundle'])
        self.assertEqual(len({id(i) for i in outputs}),5)
        self.assertEqual(sum(c[0]=='entry' for c in rng.calls),5)
        for raw in ({},{'items':[]},{**a,'roll_count':[0]}):
            rng=BoundaryRng(0);self.assertEqual(roll_pool(raw,factory,rng),[]);self.assertEqual(len(rng.calls),1)
    def test_scene_rejects_missing_wrong_and_invalid_selected_factory_objects_before_publication(self):
        for failure in ('none','type','fields','exception'):
            data=copy.copy(self.data);data.loot_pools={'w5o':dict(roll_count=[1],items=[dict(item_id='wood_bundle')])}
            e=make_engine(data);m=e.local_map
            self.assertEqual(e.save_manager.save_path,self.save_root/'slot_0')
            self.assertIsNone(e.save_manager.cache.base_path)
            existing=e.item_factory.create('flint_shard');m.floor_objects[11,11]=[existing]
            before=(dict(m.floor_objects),dict(m.container_state),dict(m.decor))
            original=e.item_factory.create
            def create(identifier,*args,**kwargs):
                if failure=='exception': raise ValueError('factory fault')
                if failure=='none': return None
                if failure=='type': return object()
                value=original(identifier,*args,**kwargs);value.weight='heavy';return value
            with patch.object(e.item_factory,'create',side_effect=create):
                with self.assertRaises(GenerationError):
                    populate(data,e.item_factory,e.creature_factory,m,[dict(kind='container',x=14,y=14,decor_id='crate',loot_pools=['w5o'])])
            self.assertEqual((m.floor_objects,m.container_state,m.decor),before)
            self.assertIs(m.floor_objects[11,11][0],existing)
            populate(data,e.item_factory,e.creature_factory,m,[dict(kind='container',x=14,y=14,decor_id='crate',loot_pools=['w5o'])])
            self.assertEqual([i.item_id for i in m.container_state[14,14]['items']],['wood_bundle'])


if __name__=='__main__':unittest.main()
