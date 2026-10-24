"""App-local populated production rendering; no desktop/window control."""
import os
from pathlib import Path
import pygame


def render_compound(e,site,path):
    from rendering.sprite_registry import SpriteRegistry
    from rendering.renderer import Renderer
    root=Path(__file__).resolve().parents[1]/'roguelike';old=Path.cwd()
    try:
        os.chdir(root);pygame.init();pygame.display.set_mode((1280,740));e.display.init()
        e.display.set_zoom(2);e.display.render_mode='sprite';e.sprite_registry=SpriteRegistry();e.sprite_registry.load()
        renderer=Renderer(e.registry,e.display,e.sprite_registry);renderer._terrain_data=e.data.terrain;renderer._decor_defs=e.data.decoratives
        tw,th=e.display.effective_tile_size(e.sprite_registry)
        screen=pygame.Surface((80*tw,43*th+42));viewport=pygame.Rect(0,42,80*tw,43*th)
        visible=e.local_map.tiles['visible'].copy();explored=e.local_map.tiles['explored'].copy()
        try:
            e.local_map.tiles['visible'][:]=True;e.local_map.tiles['explored'][:]=True
            renderer.render(screen,e.local_map,e.entities,0,0,viewport,player_x=e.player.x,player_y=e.player.y)
            label=e.display.font_ui_small.render('Production renderer / '+site['recipe']+' / controlled full-scene visibility / populated contents',True,(240,240,240))
            screen.blit(label,(12,10));pygame.image.save(screen,str(path))
        finally:e.local_map.tiles['visible'][:]=visible;e.local_map.tiles['explored'][:]=explored
    finally:os.chdir(old)
