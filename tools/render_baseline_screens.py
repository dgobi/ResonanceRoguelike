"""Offscreen component renders, not game-window/input observations.

Use the real bootstrap/fonts/data/renderers at 1280x720 under SDL dummy video.
No dependency stand-ins or gameplay source edits. Not a resize certification.
"""
import argparse
import hashlib
import json
import os
import sys
from pathlib import Path
from baseline import ROOT, prepare


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--session", default="screen-components")
    a = p.parse_args()
    session, game = prepare(a.session, 20261020)
    os.chdir(game)
    sys.path.insert(0, str(game))
    os.environ["SDL_VIDEODRIVER"] = "dummy"
    os.environ["SDL_AUDIODRIVER"] = "dummy"
    import pygame
    from engine.engine import Engine
    from rendering.sprite_registry import SpriteRegistry
    from rendering.ui_registry import UIRegistry
    from rendering.renderer import Renderer
    from engine.palette import VOID_BLACK
    import main as game_main

    def run(e):
        pygame.init()
        screen = pygame.display.set_mode((1280, 720))
        e.display.init()
        e.sprite_registry = SpriteRegistry()
        e.sprite_registry.load()
        e.ui_registry = UIRegistry()
        e.ui_registry.load()
        for component in (e.craft_screen, e.text_reader, e.look_mode, e.inventory_screen):
            component.init(e.display)
        out = ROOT / "evidence/screens"
        out.mkdir(parents=True, exist_ok=True)
        renderer = Renderer(e.registry, e.display, e.sprite_registry)
        renderer._terrain_data = e.data.terrain
        renderer._decor_defs = e.data.decoratives
        e._viewport = pygame.Rect(26, 26, 928, 548)
        cx, cy = e._get_camera(e._viewport)
        def base():
            screen.fill(VOID_BLACK)
            renderer.render(screen, e.local_map, e.entities, cx, cy, e._viewport,
                            player_x=e.player.x, player_y=e.player.y)
        base()
        e.craft_screen.open = True
        e.craft_screen.selected = 1
        e.craft_screen.render(screen, e)
        pygame.image.save(screen, str(out / "craft-component.png"))
        e.craft_screen.open = False
        base()
        e.text_reader.open_text(e.data.texts["lab_label_sarcophagus"])
        e.text_reader.render(screen, e)
        pygame.image.save(screen, str(out / "text-component.png"))
        e.text_reader.close()
        base()
        e.look_mode.enter(15, 17)
        e.look_mode.render_cursor(screen, e, cx, cy)
        e.look_mode.render_hint_overlay(screen, e._viewport, e.display)
        e.look_mode.render_examine_popup(screen, e)
        pygame.image.save(screen, str(out / "look-component.png"))
        pygame.quit()
        record = {"evidence_class": "offscreen component renders; no OS input, no live event loop",
                  "dimensions": [1280,720], "seed": 20261020,
                  "source_hashes": {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                    for p in [ROOT/"tools/render_baseline_screens.py"] + [ROOT/"roguelike"/n for n in (
                        "rendering/craft_screen.py", "engine/text_reader.py", "engine/look_mode.py",
                        "rendering/renderer.py", "engine/display_config.py")]}}
        (ROOT/"evidence/screen-render-record.json").write_text(json.dumps(record,indent=2),encoding="utf-8")
    Engine.run = run
    game_main.main()


if __name__ == "__main__":
    main()
