"""One revealed sprite sample through the existing production Pygame renderer.

No Engine, event loop, player, world persistence or game window is started.
This is a diagnostic reference, not normal player FOV.
"""
import hashlib
import json
import os
from pathlib import Path
import random
import sys
import time

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "workbench/.artifacts/reference"
OUTPUT.mkdir(parents=True, exist_ok=True)
os.environ.update(SDL_VIDEODRIVER="dummy", SDL_AUDIODRIVER="dummy", PYGAME_HIDE_SUPPORT_PROMPT="1")
sys.path.insert(0, str(ROOT / "roguelike"))
sys.path.insert(0, str(ROOT / "workbench/worker"))
from bridge import install_guard
install_guard(ROOT, OUTPUT)
os.chdir(ROOT / "roguelike")
import config
config.DEBUG_MODE = False
import pygame
import numpy as np
from engine.data_loader import DataLoader
from engine.display_config import DisplayConfig
from generation.structure_contract import read_document
from generation.structure_preview import preview
from rendering.renderer import Renderer
from rendering.tile_registry import TileRegistry
from rendering.sprite_registry import SpriteRegistry

random.seed(20261023); np.random.seed(20261023)
data = DataLoader(str(ROOT / "roguelike/data"))
asset = ROOT / "roguelike/data/layouts/starting_lab.json"
report, local_map, actors = preview(read_document(asset), "authored_submap", data, seed=20261023, path=str(asset))
terrain_hash = hashlib.sha256(json.dumps(report["terrain"], separators=(",", ":")).encode()).hexdigest()
assert terrain_hash == "c73cf0a453fd175538020adeaa6e588e609ba90852bd723479c5cd2771bd6b3d"
pygame.init(); pygame.display.set_mode((1, 1))
display = DisplayConfig(font_path=config.FONT_PATH, font_columns=config.FONT_COLUMNS,
                        font_rows=config.FONT_ROWS, font_type=config.FONT_TYPE, zoom_level=2, render_mode="sprite")
display.font_sheet.load()
sprites = SpriteRegistry(); sprites.load()
renderer = Renderer(TileRegistry(str(ROOT / "roguelike/data/tiles.json")), display, sprites)
renderer._terrain_data = data.terrain
local_map.visible[:] = True; local_map.explored[:] = True; local_map.light_map[:] = 1.0
tw, th = sprites.tile_size()
surface = pygame.Surface((80 * tw * display.zoom_level, 43 * th * display.zoom_level))
start = time.perf_counter()
renderer.render(surface, local_map, actors, 0, 0)
elapsed = round((time.perf_counter() - start) * 1000, 2)
pygame.image.save(surface, str(OUTPUT / "production-revealed.png"))
receipt = {"passed": True, "renderer": "rendering.renderer.Renderer.render", "mode": "Sprites, revealed, full uniform light; no player or FOV simulation",
           "terrain_sha256": terrain_hash, "size": list(surface.get_size()), "render_ms": elapsed,
           "comparison": "Identical production terrain grid to the worker; same centered room, stairs (15,20), open door (67,16). Different glyph/color presentation is intentional."}
(OUTPUT / "receipt.json").write_text(json.dumps(receipt, indent=2), encoding="utf-8")
pygame.quit()
print(json.dumps(receipt))
