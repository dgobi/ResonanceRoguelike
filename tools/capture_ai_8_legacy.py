"""Capture a genuine v6 save by executing pinned pre-AI-8 Python in memory.

No checkout, source copy, schema downgrade or personal save is used. Current
unchanged AI-7 room/actor data is checked against Git before ordinary actions.
The archive is captured now under historical source, not claimed captured earlier.
"""
import argparse,hashlib,importlib.abc,importlib.util,json,os,random,shutil,subprocess,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
REV='272b0b1cb691df77057045631dd3788a1bae6315'


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--evidence',type=Path,required=True);args=ap.parse_args()
    out=args.evidence.resolve();out.mkdir(parents=True,exist_ok=True)
    def original(name):return subprocess.check_output(['git','show',REV+':'+name],cwd=ROOT)
    files=set(subprocess.check_output(['git','ls-tree','-r','--name-only',REV,'roguelike'],cwd=ROOT,text=True).splitlines())
    used={}
    class Loader(importlib.abc.SourceLoader):
        def __init__(self,name):self.name=name
        def get_filename(self,fullname):return str(ROOT/self.name)
        def get_data(self,path):
            raw=original(self.name);used[self.name]=hashlib.sha256(raw).hexdigest();return raw
        def get_code(self,fullname):return compile(self.get_data(None),self.get_filename(fullname),'exec')
    class Finder(importlib.abc.MetaPathFinder):
        def find_spec(self,fullname,path=None,target=None):
            base='roguelike/'+fullname.replace('.','/')
            for name in (base+'.py',base+'/__init__.py'):
                if name in files:
                    return importlib.util.spec_from_file_location(fullname,ROOT/name,loader=Loader(name))
    sys.meta_path.insert(0,Finder());sys.path.insert(0,str(ROOT/'roguelike'))
    os.environ.update(SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy',PYGAME_HIDE_SUPPORT_PROMPT='1')
    for name in ('roguelike/data/layouts/ai7_escort_lane.json','roguelike/data/entities/creatures/ash_escort.json'):
        assert json.loads(original(name))==json.loads((ROOT/name).read_bytes())
    import pygame
    from room_test import build_engine
    from engine.save_manager import _serialize_entity
    pygame.init();os.chdir(ROOT/'roguelike')
    with tempfile.TemporaryDirectory(prefix='resonance-ai8-historical-v6-') as temp:
        config=dict(state_root=temp,seed=20261027,room_path='roguelike/data/layouts/ai7_escort_lane.json',session_id='historical-ai7')
        e=build_engine(config);e.rng=random.Random(17);e.ai_system._rng=random.Random(19)
        e._handle_key(pygame.K_LEFT);a=e.entities[1]
        assert a.ai.escort['ward'] and a.ai.profile['version']==6
        assert e.save_manager.save(e),e.save_manager.last_error
        assert 'engine.enemy_responses' not in sys.modules
        record=dict(source_revision=REV,capture_kind=__doc__,config={k:v for k,v in config.items() if k!='state_root'},
            actor=_serialize_entity(a),turn=e.world_time.turn,python_sources=used)
        shutil.make_archive(str(out/'legacy-v6-save'),'zip',temp)
        record['archive_sha256']=hashlib.sha256((out/'legacy-v6-save.zip').read_bytes()).hexdigest()
        (out/'legacy-v6-snapshot.json').write_text(json.dumps(record,indent=2),encoding='utf8')
        print(json.dumps(dict(passed=True,source_revision=REV,modules=len(used),archive_sha256=record['archive_sha256'])))


if __name__=='__main__':main()
