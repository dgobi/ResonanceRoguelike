"""W5J source rules and ordinary use: no live data or personal saves."""
import contextlib, copy, io, json, os, shutil, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
from collections import Counter
os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
import pygame
from test_effect_persistence import GAME_ROOT, load_data, make_engine
from engine.data_loader import DataLoader
from engine import item_authoring as a
from engine.content_authoring import families
from engine.definition_sources import definition_sources
from engine.item_transfers import consume


class SuppliesContract(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='w5j-contract-');self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)/'data';shutil.copytree(GAME_ROOT/'data',self.root)
        self.reload()
    def reload(self):
        with contextlib.redirect_stdout(io.StringIO()):self.data=DataLoader(str(self.root))
        self.sources=definition_sources(self.root,'items')
    def row(self,iid):return self.sources[iid][0]
    def valid(self,iid,**changes):
        row=self.row(iid);candidate=copy.deepcopy(row['definition']);candidate.update(changes)
        self.data.items[iid]=candidate
        sources=copy.deepcopy(self.sources);sources[iid][0]['definition']=candidate
        return a.authorize_candidate(row['definition'],candidate,row['path'],row['path'])+a.validate_definition(candidate,self.data,row['path'],sources,writable=True)
    def test_executable_corpus_and_classes(self):
        rows=[(iid,a.capability(row['definition'],row['path'])) for iid,ss in self.sources.items() for row in ss if len(ss)==1]
        admitted=[(iid,c) for iid,c in rows if c['editable']]
        self.assertEqual(Counter(c['supply_class'] for _,c in admitted),dict(material=30,food=9,drink=2,treatment=1,weapon=6,armour=2,shield=1,satchel=3))
        for iid,c in admitted:
            self.assertFalse(self.valid(iid),iid)
        for iid in ('empty_water_skin','resonant_tincture','debug_blade','corpse','tallow_torch','lab_note'):
            if iid in self.sources:self.assertFalse(a.capability(self.row(iid)['definition'],self.row(iid)['path'])['editable'],iid)
    def test_fields_defaults_nulls_and_original_identity(self):
        for iid,changes in [('wood_bundle',dict(weight=.25)),('animal_bone',dict(name='Bone')),
                            ('bitter_herb',dict(nutrition=.35,eat_message=None)),('cooked_meat',dict(nutrition=300)),
                            ('water_flask',dict(hydration=0,empty_form=None)),('herbal_dressing',dict(heal_amount=None))]:
            self.assertFalse(self.valid(iid,**changes),(iid,changes))
        for field,values in dict(weight=[True,-1,'1',float('nan'),float('inf'),10**400],nutrition=[True,-1,'300',float('nan'),float('inf'),2**53],heal_amount=[0,1.5,False,-1,2**53]).items():
            iid='bitter_herb' if field=='nutrition' else 'herbal_dressing' if field=='heal_amount' else 'wood_bundle'
            for value in values:self.assertTrue(self.valid(iid,**{field:value}),(field,value))
        for changes in (dict(category='butchery'),dict(on_use='drink'),dict(tile='missing'),dict(keywords=[dict(tag='fuel',tier=True)]),dict(keywords=[dict(tag='fuel',tier=2**53)])):
            self.assertTrue(self.valid('wood_bundle',**changes),changes)
        for value in ('eat','drink','heal_minor','',False,[]):self.assertTrue(self.valid('wood_bundle',on_use=value))
        for field in ('on_use_effects','slot','light','movesets'):
            self.assertTrue(self.valid('wood_bundle',**{field:None}))
    def test_effective_boundary_saved_maxima_and_factory_copied_defaults(self):
        for handler,field,maximum,default in [('eat','nutrition',1000,300),('drink','hydration',800,400)]:
            for value,expected in [(None,default/maximum),(0,0),(.35,.35),(1,1),(1.01,1.01/maximum),(300,300/maximum)]:
                raw=dict(id='probe',on_use=handler,**{field:value});eff=a.effective_use(raw,self.data)
                self.assertEqual(eff['fraction'],expected);self.assertIn('Whole item',eff['explanation'])
            self.data.survival['hunger' if handler=='eat' else 'thirst']['max']=maximum*2
            self.assertEqual(a.effective_use(dict(id='probe',on_use=handler,**{field:300}),self.data)['fraction'],300/(maximum*2))
        raw=dict(id='factory_defaults',category='consumable',on_use='eat',nutrition=None,eat_message=None)
        self.data.items[raw['id']]=raw;f=a.factory_preview(raw,self.data)
        self.assertTrue(all(r['equal'] for r in f['comparisons']));self.assertEqual(f['instance']['weight'],.1)
        self.assertIsNone(f['instance']['nutrition']);self.assertEqual(a.effective_use(dict(on_use='heal_minor',heal_amount=0),self.data)['amount'],3)
    def test_return_admission_identity_and_configuration_stamps(self):
        for iid in ('empty_water_skin','clay_pot','animal_bone','salt_pouch'):
            row,error=a.return_definition(iid,self.data,self.sources,owner='water_flask');self.assertIsNone(error);self.assertEqual(row['id'],iid)
        for iid in ('water_flask','missing','bitter_herb','tallow_torch','leather_satchel','resonant_tincture'):
            self.assertIsNotNone(a.return_definition(iid,self.data,self.sources,owner='water_flask')[1],iid)
        for value in (False,[],123):self.assertTrue(self.valid('water_flask',empty_form=value))
        before=a.return_definition('clay_pot',self.data,self.sources)[0]['sha256']
        p=self.root/'items/components/clay_pot.json';p.write_bytes(p.read_bytes()+b'\n')
        self.assertNotEqual(before,a.return_definition('clay_pot',self.data,self.sources)[0]['sha256'])
        before=a.effective_use(self.row('water_skin')['definition'],self.data)['configuration_sha256']
        p=self.root/'survival.json';p.write_bytes(p.read_bytes()+b'\n')
        self.assertNotEqual(before,a.effective_use(self.row('water_skin')['definition'],self.data)['configuration_sha256'])
        self.sources['CLAY_POT']=copy.deepcopy(self.sources['clay_pot'])
        self.assertIsNotNone(a.return_definition('clay_pot',self.data,self.sources)[1])


class SuppliesUse(unittest.TestCase):
    @classmethod
    def setUpClass(cls):pygame.init();cls.data=load_data()
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='w5j-owned-');self.addCleanup(self.tmp.cleanup)
        p=patch('engine.save_manager.SAVE_DIR',Path(self.tmp.name));p.start();self.addCleanup(p.stop)
        self.e=make_engine(self.data);self.e.debug=None
    def add(self,iid):
        item=self.e.item_factory.create(iid);self.assertTrue(self.e.player.inventory.add(item));return item
    def draw(self):
        s=self.e.inventory_screen
        for field in ('_font_title','_font_small','_font_normal'):setattr(s,field,pygame.font.Font(None,18))
        s._row_height=24
        s._draw_carried_panel(pygame.Surface((600,900)),self.e,0,0,600,900,20)
    def test_real_exchange_redraw_removes_stale_selected_object_with_screen_open(self):
        e=self.e;s=e.inventory_screen;item=self.add('water_flask');other=self.add('water_flask')
        e.player.needs.thirst=.8;s.open=True;self.draw();s.selected=next(i for i,r in enumerate(s._flat) if r[0] is item)
        before=e.world_time.turn
        with patch.object(e,'_advance_turn',wraps=e._advance_turn) as advance:
            e._handle_key(pygame.K_RETURN);self.draw()
            self.assertTrue(s.open);self.assertNotIn(item,[r[0] for r in s._flat]);self.assertTrue(e.player.inventory.contains(other))
            self.assertTrue(any(getattr(r[0],'item_id',None)=='empty_water_skin' for r in s._flat));self.assertIsNot(s._selected_item(),item)
            self.assertEqual(advance.call_count,1);self.assertEqual(e.world_time.turn,before+1)
            self.assertLess(e.player.needs.thirst,.4)
    def test_exchange_failure_is_atomic_and_no_return_drink_consumes_selected_only(self):
        e=self.e;item=self.add('water_flask');e.player.needs.thirst=.8;inv=e.player.inventory;before=list(inv.items)
        with patch.object(e.item_factory,'create',return_value=None):self.assertFalse(e.item_system.use(item,e))
        self.assertEqual(inv.items,before);self.assertEqual(e.player.needs.thirst,.8)
        heavy=e.item_factory.create('clay_pot');heavy.weight=inv.capacity+1
        with patch.object(e.item_factory,'create',return_value=heavy):self.assertFalse(e.item_system.use(item,e))
        self.assertEqual(inv.items,before);self.assertEqual(e.player.needs.thirst,.8)
        with patch.dict(e.data.items,{'water_flask':dict(e.data.items['water_flask'],empty_form=None)}):
            self.assertTrue(e.item_system.use(item,e));self.assertTrue(consume(e,item))
        self.assertFalse(inv.contains(item));self.assertLess(e.player.needs.thirst,.4)


if __name__=='__main__':unittest.main()
