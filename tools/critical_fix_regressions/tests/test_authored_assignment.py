"""Real new-world assignment, isolated saved data, no personal campaigns."""
import contextlib, copy, hashlib, io, json, os, random, shutil, sys, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
from engine.data_loader import DataLoader
from engine.save_manager import _serialize_world, _deserialize_world
from generation.authored_submap_selection import DEFAULT, RELATIVE, AssignmentError, Policy, resolve, validate
from generation.world_gen import generate_world, _assign_submaps
from world.world_map import WorldMap, Chunk, RegionType
ROOT=Path(__file__).resolve().parents[3]
ROOM=dict(id='assignment_a',width=9,height=7,layers=['#########','#.......#','#.......#','#.......#','#.......#','#.<.....#','#########'],
          legend={'#':'wall','.':'floor','<':'stairs_up'},player_start={'x':3,'y':5},special_tiles=[dict(type='item',x=3,y=5,item_id='letter',text_id='lab_note_primary_b')])
# Complete serialized 32x32 legacy worlds from the W5I start checkpoint's
# unmodified production generator. Source inspection alone is not the oracle.
BASELINES={7:'bcb2f1cc4ca3084154a2993f07a2d41a0b852939468723fd48753a90570fd5ba',
           164:'b248892be224581dd31ed1b80c28d33fe83c80e3116935f9441342d08913a846',
           20261028:'1ce0e00a586f9455ec7d7cd6226c836c4f1b10b7f2aa6df3bcd1d7b840c28ffd'}


class AssignmentTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='assignment-');self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)/'data';shutil.copytree(ROOT/'roguelike/data',self.root)
        for identifier in ('assignment_a','assignment_b'):
            (self.root/f'layouts/{identifier}.json').write_text(json.dumps(dict(ROOM,id=identifier)),encoding='utf-8')
        self.profile=dict(DEFAULT,enabled=True,authored_chance=1,candidates=[dict(layout_id='assignment_a',weight=1),dict(layout_id='assignment_b',weight=3)])
        self.save(DEFAULT)
        with contextlib.redirect_stdout(io.StringIO()): self.data=DataLoader(str(self.root))
    def save(self,raw): (self.root/RELATIVE).write_text(json.dumps(raw),encoding='utf-8')
    def world(self,seed=7):
        w=WorldMap(32,32);w.seed=seed
        with contextlib.redirect_stdout(io.StringIO()): generate_world(w,self.data,random.Random(99),plan_mode='legacy')
        return w
    def test_disabled_missing_zero_preserve_complete_baseline_and_enabled_changes_only_layouts(self):
        for seed in (7,164,20261028):
            self.save(DEFAULT);baseline=_serialize_world(self.world(seed))
            self.assertEqual(hashlib.sha256(json.dumps(baseline,sort_keys=True).encode()).hexdigest(),BASELINES[seed])
            (self.root/RELATIVE).unlink();self.assertEqual(_serialize_world(self.world(seed)),baseline)
            self.save(dict(self.profile,authored_chance=0));self.assertEqual(_serialize_world(self.world(seed)),baseline)
            self.save(self.profile);assigned=_serialize_world(self.world(seed));changed=[]
            for key,chunk in assigned['chunks'].items():
                for sm,old in zip(chunk['submaps'],baseline['chunks'][key]['submaps']):
                    if sm['submap_type']=='barrow' and not old['layout_id']:
                        self.assertIn(sm['layout_id'],('assignment_a','assignment_b'));changed.append(sm['layout_id']);sm['layout_id']=''
            self.assertTrue(changed);self.assertEqual(assigned,baseline)
    def test_order_weights_chance_domain_and_presets(self):
        self.save(self.profile);first=_serialize_world(self.world())
        self.save(dict(self.profile,candidates=list(reversed(self.profile['candidates']))));self.assertEqual(_serialize_world(self.world()),first)
        self.save(dict(self.profile,candidates=[dict(r,weight=r['weight']*2) for r in self.profile['candidates']]));self.assertEqual(_serialize_world(self.world()),first)
        policy=resolve(self.data);observed=set();counts={}
        for seed in range(200):
            c=Chunk(0,0,RegionType.PLAINS,seed);sm=c.add_submap('barrow','fixed',seed)
            identifier=policy.choose(7,0,0,sm);observed.add(identifier);counts[identifier]=counts.get(identifier,0)+1
            self.assertEqual(Policy(True,'barrow',0,policy.candidates).choose(7,0,0,sm),'')
        self.assertEqual(observed,{'assignment_a','assignment_b'});self.assertGreater(counts['assignment_b'],counts['assignment_a'])
        mixed=Policy(True,'barrow',.5,policy.candidates)
        self.assertEqual({mixed.choose(n,0,0,sm) for n in range(80)},{'','assignment_a','assignment_b'})
        w=WorldMap(1,1);w.seed=7;c=Chunk(0,0,RegionType.PLAINS,3);w.set(c);sm=c.add_submap('barrow','manual',3,layout_id='starting_lab')
        _assign_submaps(w,random.Random(0),policy);self.assertEqual(c.submaps,[sm]);self.assertEqual(sm.layout_id,'starting_lab')
    def test_shared_plan_generation_preserves_all_unrelated_state_and_stays_lazy(self):
        def generate(raw):
            self.save(raw);w=WorldMap(128,128);w.seed=20261028
            with contextlib.redirect_stdout(io.StringIO()),patch('engine.scene_generation.create_submap',side_effect=AssertionError('eager room construction')):
                generate_world(w,self.data,random.Random(0))
            return _serialize_world(w)
        baseline=generate(DEFAULT);assigned=generate(dict(self.profile,authored_chance=.65));selected=procedural=0
        for key,chunk in assigned['chunks'].items():
            for sm,old in zip(chunk['submaps'],baseline['chunks'][key]['submaps']):
                if sm['submap_type']=='barrow':
                    if sm['layout_id']: selected+=1
                    else: procedural+=1
                    sm['layout_id']=old['layout_id']
        self.assertGreater(selected,0);self.assertGreater(procedural,0);self.assertEqual(assigned,baseline)
    def test_invalid_fields_active_references_and_atomic_world_publication(self):
        cases=[dict(self.profile,version=2),dict(self.profile,version=True),dict(self.profile,target_type='lab'),dict(self.profile,enabled=1),
               dict(self.profile,authored_chance=float('nan')),dict(self.profile,authored_chance=2),dict(self.profile,candidates=[])]
        cases += [dict(self.profile,candidates=[dict(layout_id='assignment_a',weight=w)]) for w in (0,-1,True,float('inf'),float('nan'))]
        cases += [dict(self.profile,candidates=[dict(layout_id=identifier,weight=1)]) for identifier in ('missing','starting_lab','g17_authored_creature_room')]
        cases.append(dict(self.profile,candidates=self.profile['candidates']+[dict(layout_id='ASSIGNMENT_A',weight=1)]))
        for raw in cases:
            self.save(raw);w=WorldMap(32,32);w.seed=7;before=copy.deepcopy(w.__dict__)
            with self.assertRaises(AssignmentError): generate_world(w,self.data,random.Random(7),plan_mode='legacy')
            self.assertEqual(w.__dict__,before)
        self.save(dict(self.profile,enabled=False,candidates=[dict(layout_id='missing',weight=1)]))
        policy,diagnostics=validate(json.loads((self.root/RELATIVE).read_bytes()),self.data)
        self.assertTrue(diagnostics);self.assertTrue(all(d['severity']=='warning' for d in diagnostics));resolve(self.data)
        (self.root/RELATIVE).write_text('{broken')
        with self.assertRaisesRegex(AssignmentError,'Cannot read explicit profile'): resolve(self.data)
    def test_saved_original_eligibility_compiler_and_dependency_semantics(self):
        from generation.authored_rooms import source_index
        for mutate in (lambda r:r.update(player_start=None),lambda r:r.update(special_tiles=[dict(type='weighted',x=1,y=1,spawn_table=[])]),lambda r:r['legend'].update({'.':'absent'})):
            raw=copy.deepcopy(ROOM);mutate(raw);(self.root/'layouts/assignment_a.json').write_text(json.dumps(raw))
            # Use the already loaded data to exercise source checks independently of catalogue initialization.
            self.assertTrue(any(d['severity']=='error' for d in validate(self.profile,self.data)[1]))
        (self.root/'layouts/assignment_a.json').write_text(json.dumps(ROOM))
        (self.root/'layouts/alias.json').write_text(json.dumps(dict(ROOM,id='ASSIGNMENT_A')))
        self.assertTrue(any('ambiguous' in d['message'] for d in validate(self.profile,self.data)[1]));(self.root/'layouts/alias.json').unlink()
        text=self.data.texts['lab_note_primary_b'];old=text['pages'];text['pages']=False
        text_path=self.root/'texts/lab/lab_note_primary_b.json';text_path.write_text(json.dumps(text))
        self.assertTrue(any('page' in d['message'] for d in validate(self.profile,self.data)[1]));text['pages']=old
    def test_recorded_world_restores_without_reading_changed_unused_policy(self):
        self.save(self.profile);world=self.world();recorded=_serialize_world(world)
        for content in ('{bad profile',None,json.dumps(dict(self.profile,enabled=False))):
            if content is None: (self.root/RELATIVE).unlink(missing_ok=True)
            else: (self.root/RELATIVE).write_text(content)
            with contextlib.redirect_stdout(io.StringIO()): data=DataLoader(str(self.root))
            loaded=WorldMap(recorded["width"],recorded["height"])
            with patch('generation.authored_submap_selection.resolve',side_effect=AssertionError('policy used during load')): _deserialize_world(recorded,loaded)
            self.assertEqual(_serialize_world(loaded),recorded)


if __name__=='__main__': unittest.main()
