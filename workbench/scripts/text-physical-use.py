"""Read a deliberately published disposable text via a physical letter and game keys.

Usage: bundled-python -B scripts/text-physical-use.py FIXTURE_ROOT RELATIVE_TEXT OUTPUT
The native journey invokes this after the host's publication/hash-checked reopen.
"""
import copy
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch

REPO = Path(__file__).resolve().parents[2]


def demonstrate(root, relative, output):
    root, output = Path(root).resolve(), Path(output).resolve()
    assert root.is_relative_to(REPO / "workbench/.artifacts"), "Only disposable workbench test inputs"
    assert root != REPO
    os.environ.update(SDL_VIDEODRIVER="dummy", SDL_AUDIODRIVER="dummy", PYGAME_HIDE_SUPPORT_PROMPT="1")
    sys.path[:0] = [str(root/"roguelike"), str(REPO/"tools/critical_fix_regressions/tests")]
    import config
    config.DEBUG_MODE = False
    import pygame
    from engine.data_loader import DataLoader
    from generation.structure_preview import preview
    from engine.scene_generation import populate
    from engine.text_reader import parse_page
    from rendering.ui_registry import UIRegistry
    from test_effect_persistence import make_engine
    import inspect
    assert inspect.signature(populate).parameters["map_text"].default is False
    raw_bytes = (root/relative).read_bytes(); definition = json.loads(raw_bytes)
    # Fresh production load AFTER deliberate host publication, no in-memory text injection.
    data = DataLoader(str(root/"roguelike/data"))
    assert data.texts[definition["id"]] == definition
    fixture = dict(id="w5b_letter_fixture", width=11, height=7,
                   layers=["###########", "#.........#", "#.........#", "#.........#", "#.........#", "#.<.......#", "###########"],
                   legend={"#":"wall", ".":"floor", "<":"stairs_up"}, player_start=dict(x=2,y=5),
                   special_tiles=[dict(type="item",item_id="letter",text_id=definition["id"],x=3,y=3)])
    output.mkdir(parents=True,exist_ok=True)
    (output/"physical-submap-fixture.json").write_text(json.dumps(fixture,indent=2),encoding="utf-8")
    # compile_structure -> create_submap -> generate_submap -> populate -> ItemFactory
    report, local_map, actors = preview(fixture,"authored_submap",data,path="fixture-only/w5b_letter_fixture.json")
    assert report["passed"] and not actors
    letters=[(xy,item) for xy,items in local_map.floor_objects.items() for item in items if item.item_id=="letter"]
    assert len(letters)==1
    xy, letter=letters[0];assert letter.text_id==definition["id"]
    with tempfile.TemporaryDirectory(prefix="w5b-game-saves-") as directory, patch("engine.save_manager.SAVE_DIR",Path(directory)/"saves"):
        pygame.init();pygame.display.set_mode((960,640))
        old=Path.cwd()
        try:
            os.chdir(root/"roguelike")
            engine=make_engine(data);engine.debug=None
            engine.local_map=local_map;engine.entities=[engine.player];engine.player.x,engine.player.y=report["spawn"]
            engine.display.init();engine.text_reader.init(engine.display);engine.inventory_screen.init(engine.display)
            engine.ui_registry=UIRegistry();engine.ui_registry.load();engine._update_fov()
            arrival_turn=engine.world_time.turn
            # This room has an unobstructed floor route from its real arrival.
            while (engine.player.x,engine.player.y)!=xy:
                old_xy=(engine.player.x,engine.player.y)
                engine._handle_key(pygame.K_RIGHT if engine.player.x<xy[0] else pygame.K_LEFT if engine.player.x>xy[0]
                                   else pygame.K_DOWN if engine.player.y<xy[1] else pygame.K_UP)
                assert (engine.player.x,engine.player.y)!=old_xy
            approach_turns=engine.world_time.turn-arrival_turn
            before=engine.world_time.turn
            engine._handle_key(pygame.K_COMMA)
            assert engine.player.inventory.contains(letter)
            assert letter not in local_map.floor_objects.get(xy,[])
            assert engine.world_time.turn==before+1
            engine._handle_key(pygame.K_i)
            assert engine.inventory_screen.open
            engine.inventory_screen.render(pygame.Surface((960,640)),engine)
            selected=next(i for i,row in enumerate(engine.inventory_screen._flat) if row[0] is letter)
            for _ in range(selected):engine._handle_key(pygame.K_DOWN)
            engine._handle_key(pygame.K_RETURN)
            reader=engine.text_reader
            assert reader.open and reader._def==definition and reader._def["title"]==definition["title"]
            assert engine.world_time.turn==before+2 and engine.player.inventory.contains(letter)
            invariant=(engine.world_time.turn,engine.rng.getstate(),copy.deepcopy(engine.player.language.__dict__),engine.player.needs.hunger)
            pages=[]
            for index,page in enumerate(definition["pages"]):
                assert reader._page==index
                surface=pygame.Surface((960,640));reader.render(surface,engine)
                assert parse_page(page["text"]) == parse_page(reader._def["pages"][index]["text"])
                seen=set(reader._visible_rows)
                for _ in range(10000):
                    if reader._scroll==reader._max_scroll:break
                    engine._handle_key(pygame.K_PAGEDOWN);reader.render(surface,engine);seen.update(reader._visible_rows)
                assert seen==set(range(len(reader._layout_rows)))
                rendered="".join(fragment["text"] for row in reader._layout_rows for fragment in row)
                for marker in ("[DAMAGED]","[REDACTED]"):
                    assert (marker in rendered)==(marker in page["text"])
                assert ("— [text ends here] —" in rendered)==bool(page.get("trailing"))
                assert surface.get_rect().contains(reader._frame) and reader._frame.contains(reader._viewport)
                assert all(sum(f["width"] for f in row)<=reader._viewport.width for row in reader._layout_rows)
                pygame.image.save(surface,str(output/f"physical-page-{index+1}-end.png"))
                pages.append(dict(index=index,body_sha256=hashlib.sha256(page["text"].encode()).hexdigest(),rows=len(reader._layout_rows),max_scroll=reader._max_scroll,all_rows_reached=True))
                if index<len(definition["pages"])-1:engine._handle_key(pygame.K_RIGHT);assert reader._scroll==0
            engine._handle_key(pygame.K_LEFT);engine._handle_key(pygame.K_HOME);engine._handle_key(pygame.K_END);engine._handle_key(pygame.K_ESCAPE)
            assert not reader.open and engine.player.inventory.contains(letter)
            assert invariant==(engine.world_time.turn,engine.rng.getstate(),engine.player.language.__dict__,engine.player.needs.hunger)
            assert not list(Path(directory).rglob("*")), "No saves should be created"
        finally:
            pygame.quit();os.chdir(old)
    receipt=dict(passed=True,definition_id=definition["id"],title=definition["title"],saved_sha256=hashlib.sha256(raw_bytes).hexdigest(),
                 reloaded_exact_definition=True,population_map_text_default=False,item_id=letter.item_id,text_id=letter.text_id,
                 source_xy=[3,3],physical_xy=list(xy),arrival=report["spawn"],approach_turns=approach_turns,pages=pages,pickup_turns=1,inventory_use_turns=1,reader_navigation_turns=0,
                 letter_retained=True,knowledge_rng_hunger_unchanged_during_reading=True,saves_written=False,
                 scope="Controlled disposable authored submap and existing letter. Production validation, construction, population, pickup, inventory selection/use and reader keys. No natural acquisition, world selection or campaign balance claim.")
    (output/"physical-use.json").write_text(json.dumps(receipt,indent=2),encoding="utf-8")
    print(json.dumps(receipt))
    return receipt


if __name__=="__main__":demonstrate(*sys.argv[1:])
