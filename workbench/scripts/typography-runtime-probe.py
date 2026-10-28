"""Fresh, isolated game display initialization and real consumers; no campaign."""
import hashlib
import json
import os
from pathlib import Path
import sys
import warnings

root=Path(sys.argv[1]).resolve()
sys.path.insert(0,str(root/"roguelike"))
os.chdir(root/"roguelike")
os.environ.update(SDL_VIDEODRIVER="dummy",SDL_AUDIODRIVER="dummy",PYGAME_HIDE_SUPPORT_PROMPT="1")
import pygame
from engine.display_config import DisplayConfig
from engine.text_reader import TextReader
from engine.ui import UI
from rendering.perk_screen import PerkScreen
from rendering.callouts import CalloutSystem
from engine.typography import PROFILE

before=(root/PROFILE).read_bytes()
pygame.init();pygame.display.set_mode((1,1))
with warnings.catch_warnings(record=True) as caught:
    display=DisplayConfig.from_config();display.init()
reader=TextReader();reader.init(display);hud=UI(display);hud.init();menu=PerkScreen();menu.init(display)
assert reader._font is display.font_ui_normal and hud._font_tiny is display.font_ui_tiny
assert menu._row_height==display.font_ui_normal.get_linesize()+4
calls=CalloutSystem();calls.add("37",1,1,(255,255,255));calls.draw(pygame.Surface((240,160)),display.CALLOUT_FONTS,24,24,0,0,0,0)
assert (root/PROFILE).read_bytes()==before
receipt=dict(pid=os.getpid(),python=sys.version,pygame=pygame.version.ver,typography=display.typography,
             warnings=[str(w.message) for w in caught],profile_sha256=hashlib.sha256(before).hexdigest(),
             corruption_alphabet=reader._corrupt_pool,small_alias=display.CALLOUT_FONTS["small"] is display.font_callout_damage,
             tiny_alias=display.CALLOUT_FONTS["tiny"] is display.font_callout_creature,
             scope="Fresh production DisplayConfig initialization plus reader/HUD/perk/callout consumers; no world or personal save")
pygame.quit()
print(json.dumps(receipt,ensure_ascii=False))
