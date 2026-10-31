"""Published variant, real keys; disclosed staged authoring fixture, not journey."""
import contextlib
import io
import json
import os
from pathlib import Path
import random
import sys
import tempfile
from unittest.mock import patch

root,relative,out=Path(sys.argv[1]).resolve(),sys.argv[2],Path(sys.argv[3]).resolve()
repo=Path(__file__).resolve().parents[2]
assert root!=repo and (root.is_relative_to(repo/'workbench/.artifacts') or root.is_relative_to(repo/'.baseline'))
os.environ.update(SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy',PYGAME_HIDE_SUPPORT_PROMPT='1')
sys.path[:0]=[str(root/'roguelike'),str(repo/'tools/critical_fix_regressions/tests')]
import pygame
from engine.data_loader import DataLoader
from engine.location_reports import reader_payload
from generation.world_gen import generate_world
from world.world_map import WorldMap
from test_effect_persistence import make_engine
with contextlib.redirect_stdout(io.StringIO()):data=DataLoader(str(root/'roguelike/data'))
w=WorldMap(128,128);w.seed=20261023
with contextlib.redirect_stdout(io.StringIO()):generate_world(w,data,random.Random(w.seed))
raw=json.loads((root/relative).read_bytes());assert data.texts[raw['id']]==raw
with tempfile.TemporaryDirectory(prefix='g22-author-read-') as directory,patch('engine.save_manager.SAVE_DIR',Path(directory)):
    pygame.init();pygame.display.set_mode((1,1))
    e=make_engine(data);e.debug=None;e.world_map=w
    item=e.item_factory.create('letter');item.text_id=raw['id']
    # Disclosed test ownership fixture; ordinary full journey uses the native lab.
    e.local_map.floor_objects[(12,12)]=[item]
    before=e.world_time.turn;e._handle_key(pygame.K_COMMA)
    assert e.player.inventory.contains(item) and e.world_time.turn==before+1
    assert w.learned_reports==[]
    e._handle_key(pygame.K_i);e.inventory_screen._flat=[(item,False,'')]
    e.inventory_screen.selected=0;e._handle_key(pygame.K_RETURN)
    assert e.text_reader.open and e.world_time.turn==before+2
    assert w.learned_reports==['workshop','ward_store']
    assert e.text_reader._def==reader_payload(raw,w)
    assert e.player.inventory.contains(item)
    out.write_text(json.dumps(dict(passed=True,fixture='Published physical letter staged on ordinary fixture floor; native pickup/inventory/read keys. Fresh real world metadata supplies binding; no unaided acquisition/journey claim.',pages=e.text_reader._def['pages'],learned=w.learned_reports,read_cost=1,pickup_cost=1),indent=2)+'\n')
pygame.quit()
