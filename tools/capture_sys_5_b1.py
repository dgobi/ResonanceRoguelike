"""Source-bound B1 serializer compatibility, not an old-game integration run."""
import copy,hashlib,json,os,subprocess,sys,tempfile,types
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'roguelike'),str(ROOT/'tools/critical_fix_regressions/tests')]
os.environ.update(SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy',PYGAME_HIDE_SUPPORT_PROMPT='1')
REV='9bb0db884b989bb9a21f25387b5772e3246ba978'

def main():
 import pygame
 from test_effect_persistence import load_data,make_engine
 from engine.save_components import restore_item,serialize_item,validate_item
 from engine import flesh_resources as food
 pygame.init();sources={}
 def blob(path):
  raw=subprocess.check_output(['git','show',REV+':'+path],cwd=ROOT)
  sources[path]=hashlib.sha256(raw).hexdigest();return raw
 def module(path,name):
  m=types.ModuleType(name);m.__file__=REV+':'+path;sys.modules[name]=m
  exec(compile(blob(path),m.__file__,'exec'),m.__dict__);return m
 factory=module('roguelike/engine/item_factory.py','sys5_historical_item_factory')
 serializer=module('roguelike/engine/save_manager.py','sys5_historical_save_manager')
 with tempfile.TemporaryDirectory(prefix='sys5-b1-') as tmp,patch('engine.save_manager.SAVE_DIR',Path(tmp)):
  data=load_data();historical=copy.deepcopy(data)
  for key in ('crow_meat','stalker_meat'):
   historical.items[key]=json.loads(blob('roguelike/data/items/butchery/'+key+'.json'))
  e=make_engine(data);old_factory=factory.ItemFactory(historical)
  for key in ('crow_meat','stalker_meat'):e.player.inventory.add(old_factory.create(key))
  emitted=serializer._serialize_player(e)['inventory']['items'];after=[]
  for row in emitted:
   assert 'keywords' not in row and 'flesh_resource' not in row
   fresh=e.item_factory.create(row['item_id']);assert food.eligible(fresh)
   restore_item(fresh,row);assert not food.eligible(fresh)
   saved=serialize_item(fresh);validate_item(saved,'historical meat');after.append(saved)
  result=dict(passed=True,revision=REV,sources=sources,emitted_unchanged=emitted,restored=after,
   limits='Complete unmodified historical factory/serializer modules and historical meat definitions. Current dependency classes, palette and disposable harness engine; not a full historical-game run. No deleted modern fields.')
  output=ROOT/'evidence/sys-5/b1-serializer.json';output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf8');print(output)

if __name__=='__main__':main()
