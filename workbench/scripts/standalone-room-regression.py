"""Headless ordinary main startup/default-save regression in a disposable fixture.

A verification-only wrapper passes Engine.run's frame observer; the production
loop, ordinary main construction and SaveManager defaults execute unchanged.
"""
import hashlib
import json
import os
from pathlib import Path
import sys

root=Path(sys.argv[1]).resolve()
output=Path(sys.argv[2]).resolve();output.mkdir(parents=True,exist_ok=True)
assert '.artifacts' in root.parts and 'w5h' in root.parts
game=root/'roguelike';saves=game/'saves'
assert not saves.exists(),'Use a fresh disposable fixture without an existing standalone save'
os.environ.update(SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy')
os.chdir(game);trace=[]
def audit(event,args):
    if event not in ('open','os.listdir','os.scandir','os.mkdir','os.rename','os.remove'):return
    for value in args[:2] if event=='os.rename' else args[:1]:
        if not isinstance(value,(str,bytes,os.PathLike)):continue
        p=Path(os.fsdecode(value)).absolute()
        if 'saves' in p.parts or '.sessions' in p.parts:
            assert p.is_relative_to(saves),(event,p)
            trace.append(dict(event=event,path=str(p)))
sys.addaudithook(audit)
sys.path.insert(0,str(game))
import pygame
import main
from engine.player_setup import STARTING_ITEMS
from engine.engine import Engine
original_run=Engine.run
result={}
def frame(e,screen):
    if result:return
    assert e.world_map.width==128 and e.world_map.height==128
    assert e.debug is not None  # The owner's ordinary debug default is preserved.
    assert e.save_manager.save_path==saves/'slot_0'
    assert [i.item_id for i in e.player.inventory.items]==list(STARTING_ITEMS)
    assert e.player.light_source.active
    before=[e.player.x,e.player.y,e.current_submap_id]
    assert e.current_submap_id and e.save_manager.save(e)
    assert e.save_manager.load(e)
    assert [e.player.x,e.player.y,e.current_submap_id]==before
    pygame.image.save(screen,str(output/'ordinary-startup.png'))
    result.update(passed=True,world=[128,128],scene=before,save_path=str(e.save_manager.save_path),seed=e.world_map.seed,
                  ordinary_debug_default=True,save_load=True,save_access_events=len(trace),main_sha256=hashlib.sha256((game/'main.py').read_bytes()).hexdigest())
    pygame.event.post(pygame.event.Event(pygame.QUIT))
def observed_run(e):return original_run(e,on_frame=frame)
Engine.run=observed_run
try:
    main.main()
except SystemExit as error:
    assert error.code in (None,0)
finally:
    Engine.run=original_run
    (output/'receipt.json').write_text(json.dumps(dict(result,save_access_trace=trace),indent=2),encoding='utf-8')
assert result.get('passed')
print(json.dumps(result))
