"""Bounded real-input helpers shared by the G10 preflight and expedition.

Only boot intercepts Engine.run; all travel, doors and interactions use handlers.
Save roots must be supplied by a caller's SAVE_DIR patch.
"""
from collections import deque
import os
from pathlib import Path
from unittest.mock import patch
import pygame

ROOT = Path(__file__).resolve().parents[1]
KEYS = {(1, 0): pygame.K_RIGHT, (-1, 0): pygame.K_LEFT,
        (0, 1): pygame.K_DOWN, (0, -1): pygame.K_UP}


def boot(save_root, seed=20261023):
    import main
    from engine.engine import Engine
    slot = Path(save_root) / 'slot_0'
    slot.mkdir(parents=True, exist_ok=True)
    (slot / 'world.json').write_text('{"seed": %d}' % seed)
    captured = []
    old = Path.cwd()
    try:
        os.chdir(ROOT / 'roguelike')
        with patch.object(Engine, 'run', lambda e: captured.append(e)):
            main.main()
    finally:
        os.chdir(old)
    e = captured[0]
    e.debug = False
    assert not e.player_invincible
    return e


def status(e):
    return dict(chunk=[e.world_x, e.world_y], submap=e.current_submap_id,
                position=[e.player.x, e.player.y], turn=e.world_time.turn,
                hp=e.player.fighter.hp, hunger=e.player.needs.hunger,
                thirst=e.player.needs.thirst,
                inventory=[i.item_id for i in e.player.inventory.items],
                actors=[dict(id=getattr(a, '_creature_id', ''), name=a.name,
                             x=a.x, y=a.y, hp=a.fighter.hp if a.fighter else None)
                        for a in e.entities if a is not e.player])


def path(e, goals):
    from generation.access import enterable
    start = (e.player.x, e.player.y)
    occupied = {(a.x, a.y) for a in e.entities if a is not e.player and a.blocks_movement}
    parents = {start: None}
    todo = deque([start])
    goals = set(goals)
    while todo:
        p = todo.popleft()
        if p in goals:
            result = [p]
            while parents[result[-1]] is not None:
                result.append(parents[result[-1]])
            return result[::-1]
        for dx, dy in KEYS:
            q = p[0] + dx, p[1] + dy
            if q not in parents and q not in occupied and e.local_map.in_bounds(*q) and enterable(e.local_map, q, e.data):
                parents[q] = p
                todo.append(q)
    raise AssertionError('No real-input path to goals')


def walk(e, goals, report, limit=500):
    goals = set(goals)
    for _ in range(limit):
        if (e.player.x, e.player.y) in goals:
            return
        route = path(e, goals)
        assert len(route) > 1
        a, b = route[:2]
        terrain = str(e.local_map.tiles[b]['terrain'])
        before = status(e)
        e._handle_key_local(KEYS[b[0] - a[0], b[1] - a[1]])
        report.append(dict(key=pygame.key.name(KEYS[b[0] - a[0], b[1] - a[1]]),
                           terrain=terrain, start=before['position'], end=[e.player.x, e.player.y],
                           chunk=[e.world_x, e.world_y], turn=e.world_time.turn,
                           hp=e.player.fighter.hp, thirst=e.player.needs.thirst))
        assert e.player.fighter.hp > 0, 'Expedition died'
    raise AssertionError('Real-input route exceeded finite movement budget')


def leave_lab(e, report):
    stairs = [(x, y) for x in range(e.local_map.width) for y in range(e.local_map.height)
              if str(e.local_map.tiles[x, y]['terrain']) == 'stairs_up']
    walk(e, stairs, report)
    e._handle_key(pygame.K_LESS, '<')
    assert e.current_submap_id is None, 'Normal ascent failed'


def interact(e, xy, report):
    from engine.engine import GameMode
    from engine.interaction_cursor import InteractionCursor
    walk(e, {(xy[0]+dx, xy[1]+dy) for dx,dy in KEYS}, report)
    e._update_fov()
    assert InteractionCursor.can_reach(e, *xy)
    e._handle_key(pygame.K_e)
    assert e.mode == GameMode.INTERACTION_CURSOR
    e.interaction_cursor._cursor_x, e.interaction_cursor._cursor_y = xy
    e.interaction_cursor.candidates = [xy]
    e._handle_key(pygame.K_RETURN)


def render(e, path, label, *, revealed=False):
    from rendering.sprite_registry import SpriteRegistry
    from rendering.renderer import Renderer
    old = Path.cwd()
    try:
        os.chdir(ROOT / 'roguelike')
        pygame.init()
        pygame.display.set_mode((1280, 740))
        e.display.init()
        e.display.set_zoom(2)
        e.display.render_mode = 'sprite'
        registry = SpriteRegistry()
        registry.load()
        renderer = Renderer(e.registry, e.display, registry)
        renderer._terrain_data = e.data.terrain
        renderer._decor_defs = e.data.decoratives
        tw, th = e.display.effective_tile_size(registry)
        screen = pygame.Surface((80*tw, 43*th+42))
        visible = e.local_map.visible.copy()
        explored = e.local_map.explored.copy()
        try:
            if revealed:
                e.local_map.visible[:] = True
                e.local_map.explored[:] = True
            renderer.render(screen, e.local_map, e.entities, 0, 0, pygame.Rect(0,42,80*tw,43*th),
                            player_x=e.player.x, player_y=e.player.y)
            text = ('REVEALED comparison / ' if revealed else 'NORMAL FOV / ') + label
            screen.blit(e.display.font_ui_small.render(text, True, (240,240,240)), (10,10))
            pygame.image.save(screen, str(path))
        finally:
            e.local_map.visible[:] = visible
            e.local_map.explored[:] = explored
    finally:
        os.chdir(old)
