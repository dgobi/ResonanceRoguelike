"""Bounded production Workbench room session; never enters campaign startup.

The native host supplies a frozen payload and an explicit mutable session root.
There is no default save destination in this entry point.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import random
import sys
import time

CONTRACT = "workbench-room-test-1"


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def write_json(path, value):
    path = Path(path)
    stage = path.with_suffix('.tmp')
    stage.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
    for attempt in range(10):
        try:
            stage.replace(path)
            break
        except PermissionError:
            if attempt==9:raise
            time.sleep(.003)


def confined(root, relative):
    from engine.typography import no_links
    p = PurePosixPath(relative)
    if p.is_absolute() or '..' in p.parts or '\\' in relative or ':' in relative:
        raise ValueError(f"External input reference refused: {relative}")
    target = no_links(root.joinpath(*p.parts))
    if not target.resolve().is_relative_to(root.resolve()):
        raise ValueError(f"Input escape: {relative}")
    return target


def verify_payload(config):
    root = Path(__file__).resolve().parent.parent
    manifest = read_json(config['manifest'])
    if manifest['contract'] != CONTRACT or manifest['snapshot_id'] != config['snapshot_id']:
        raise ValueError('Incompatible captured room-test contract')
    for relative, expected in manifest['files'].items():
        path = confined(root, relative)
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError(f'Captured input changed: {relative}')
    runtime = Path(sys.executable).resolve().parent
    for relative, expected in manifest['runtime_files'].items():
        if hashlib.sha256(confined(runtime,relative).read_bytes()).hexdigest()!=expected:
            raise ValueError(f'Captured runtime changed: {relative}')
    room = config['room_path']
    if PurePosixPath(room).parent.as_posix() != 'roguelike/data/layouts':
        raise ValueError('Save the template as an ordinary immediate layouts/ room first')
    if manifest['files'][room] != config['room_sha256']:
        raise ValueError('Room identity differs from captured manifest')
    return root


def validate(config):
    root = verify_payload(config)
    from engine.content_authoring import family_for
    from engine import room_authoring
    from engine.data_loader import DataLoader
    from generation.structure_preview import preview
    from engine.display_config import DisplayConfig
    from engine.player_setup import PROFILE
    from engine import typography
    import config as game_config
    import pygame
    import importlib.metadata
    expected = {'pygame':'2.6.1','tcod':'19.3.0','numpy':'2.4.6','cffi':'2.1.1','pycparser':'3.11','typing_extensions':'4.16.0'}
    if sys.version_info[:2] != (3,11) or any(importlib.metadata.version(k)!=v for k,v in expected.items()):
        raise ValueError('Room test requires the verified pinned Python 3.11 game runtime')
    family = family_for(config['room_path'])
    if family is None or family.id != 'room' or family.route != 'authored_submap' or room_authoring.CONTRACT != 'authored-room-2':
        raise ValueError('Selected project lacks the compatible registered room contract')
    from generation.structure_contract import read_document
    raw = read_document(root / config['room_path'])
    cap = room_authoring.capability(raw, config['room_path'])
    if 'edit' not in cap['operations']:
        raise ValueError(cap['reason'] or 'Save an ordinary room variant first')
    data = DataLoader('data')
    diagnostics = room_authoring.authoring_validate(raw, data, config['room_path'], root/'roguelike/data')
    from engine.item_factory import ItemFactory
    from engine.text_authoring import sources,validate_definition
    texts,_ = sources(root/'roguelike/data')
    factory=ItemFactory(data)
    for record in raw.get('special_tiles',[]):
        if record.get('type',record.get('kind'))!='item':continue
        item=factory.create(record.get('item_id'),0,0)
        if item is None or getattr(item,'on_use',None)!='read':continue
        identifier=record.get('text_id',getattr(item,'text_id',None))
        entries=texts.get(identifier,[])
        if identifier and len(entries)==1:
            entry=entries[0]
            # Reader shape/fields use the shared validator. Authoring eligibility
            # (e.g. alphabet prose or array storage) is not a gameplay ban, and
            # unrelated malformed records do not become a launch-cleanup gate.
            diagnostics += [d for d in validate_definition(entry['definition'],data,entry['path'],texts)
                            if d['code'] not in ('TEXT_CAPABILITY','DUPLICATE_TEXT')]
    if any(d['severity']=='error' for d in diagnostics):
        raise ValueError(json.dumps(diagnostics))
    report, _, _ = preview(raw, 'authored_submap', data, seed=config['seed'], path=config['room_path'], derive_access=True)
    if not report['passed']:
        raise ValueError('Captured production arrival/population/access validation failed')
    # Validate actual lazy rendering references, beyond the preview's Fonts/UI stamp.
    font = 'roguelike/' + game_config.FONT_PATH
    if not font.startswith(('roguelike/assets/Fonts/','roguelike/assets/sprites/')):
        raise ValueError('Glyph sheet must be a captured Fonts/sprites resource')
    pygame.image.load(str(confined(root,font)))
    if game_config.RENDER_MODE == 'sprite':
        sprite_map = read_json(root/'roguelike/data/sprites/sprite_map.json')
        if not sprite_map.get('sheets'):
            raise ValueError('Sprite renderer requires captured sprite sheets')
        for sheet in sprite_map['sheets'].values():
            relative = 'roguelike/' + sheet['file']
            if not relative.startswith('roguelike/assets/sprites/'):
                raise ValueError('Sprite reference must stay under captured assets/sprites')
            pygame.image.load(str(confined(root,relative)))
    # Preserve production typography fallback; return its diagnostics to the host.
    pygame.font.init()
    fonts = typography.initialize(root)
    diagnostics += fonts['diagnostics']
    ui=root/'roguelike/assets/ui'
    panels=sorted(ui.glob('*.png')) if ui.is_dir() else []
    if not panels:
        diagnostics.append(dict(severity='warning',code='UI_FALLBACK',field='assets/ui',message='No saved UI panel images; the game will use its ordinary plain-panel fallback.'))
    for panel in panels:
        try:pygame.image.load(str(panel))
        except (pygame.error,OSError) as error:
            diagnostics.append(dict(severity='warning',code='UI_FALLBACK',field='assets/ui/'+panel.name,message=f'Panel cannot load; the game will use its ordinary fallback: {error}'))
    return dict(contract=CONTRACT, room_id=raw['id'], room_contract=room_authoring.CONTRACT,
                descriptor_sha256=family.descriptor()[1], route=family.route,
                profile=PROFILE, diagnostics=diagnostics, spawn=report['spawn'], preview=report)


def build_engine(config, *, load=False):
    from config import MAP_WIDTH, MAP_HEIGHT
    from engine.save_manager import SaveManager
    from engine.data_loader import DataLoader
    from engine.display_config import DisplayConfig
    from rendering.tile_registry import TileRegistry
    from engine.engine import Engine
    from engine.item_factory import ItemFactory
    from engine.player_setup import create_player
    from engine.player_setup import PROFILE, STARTING_ITEMS
    from world.local_map import LocalMap
    from world.world_map import WorldMap, Chunk, RegionType, SubMap
    from engine.typography import no_links
    root = Path(config['state_root'])
    if not root.is_absolute():
        raise ValueError('An explicit absolute session root is required')
    no_links(root)
    if config.get('profile',PROFILE)!=PROFILE:
        raise ValueError('Captured player profile is incompatible with this bootstrap')
    if root.resolve().is_relative_to(Path(__file__).resolve().parent.parent):
        raise ValueError('Mutable state cannot live in the frozen payload')
    # Ownership is injected before ANY startup/checkpoint/cache inspection.
    saves = SaveManager(save_root=root/'saves')
    if load:
        startup, seed = saves.startup_state()
        if startup != 'load' or seed != config['seed']:
            raise ValueError('No matching room-test checkpoint to resume')
    data, display = DataLoader('data'), DisplayConfig.from_config()
    random.seed(config['seed'])
    world = WorldMap(1,1)
    world.seed = config['seed']
    world.start_wx = world.start_wy = 0
    chunk = Chunk(0,0,RegionType.PLAINS,config['seed'],visited=True,explored=True)
    world.chunks[(0,0)] = chunk
    foyer = LocalMap(MAP_WIDTH,MAP_HEIGHT)
    # Small physical foyer, surrounded by walls. No campaign generation.
    for x in range(9,18):
        for y in range(9,16):
            foyer.set_tile(x,y,'floor',True,True)
    instance = 'room-test-instance'
    raw = read_json(Path(__file__).resolve().parent.parent/config['room_path'])
    chunk.submaps.append(SubMap(instance,'cave','Disposable Workbench room',config['seed'],layout_id=raw['id'],surface_x=12,surface_y=12))
    foyer.set_tile(12,12,'stairs_down',True,True)
    foyer.submap_links[(12,12)] = instance
    player = create_player(data,ItemFactory(data),12,12)
    if [i.item_id for i in player.inventory.items]!=list(STARTING_ITEMS):
        raise ValueError('Saved definitions cannot construct all six ordinary starting items required by the disclosed profile')
    engine = Engine(player,foyer,[player],TileRegistry('data/tiles.json',mode=display.render_mode),world,0,0,data,display,
                    save_manager=saves, debug_mode=False, bounded_room_test=True,
                    session_label=f"Workbench disposable room test · {raw['id']} · {config['session_id'][:8]}")
    if load:
        if not saves.load(engine):
            raise ValueError(f'Room-test load refused: {saves.last_error}')
        if engine.world_map.width != 1 or engine.world_map.height != 1:
            raise ValueError('Checkpoint escaped the staged room world')
    else:
        torch = next(i for i in player.inventory.items if i.item_id=='tallow_torch')
        engine.item_system.use(torch,engine)
        if not getattr(player,'light_source',None) or not player.light_source.active:
            raise ValueError('Ordinary starting torch could not be equipped/lit')
        engine._try_descend()
        if engine.current_submap_id != instance:
            raise ValueError('Production room entry failed; inspect captured room dependencies')
    return engine


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--session',required=True)
    parser.add_argument('--validate',action='store_true')
    parser.add_argument('--load',action='store_true')
    args=parser.parse_args()
    config=read_json(args.session)
    os.chdir(Path(__file__).resolve().parent)
    report=validate(config)
    if args.validate:
        preflight=build_engine(config)
        report['bootstrap_arrival']=[preflight.player.x,preflight.player.y]
        report['bootstrap_instance']=preflight.current_submap_id
    write_json(config['validation_path'],report)
    if args.validate:
        return
    engine=build_engine(config,load=args.load)
    diagnostic=None
    if config.get('diagnostic_events') is True:
        from engine.room_test_diagnostics import DiagnosticEvents
        diagnostic=DiagnosticEvents(config['state_root'])
    ready=False
    def frame(e,screen):
        nonlocal ready
        if not ready:
            write_json(config['ready_path'],dict(contract=CONTRACT,session_id=config['session_id'],snapshot_id=config['snapshot_id'],pid=os.getpid(),arrival=[e.player.x,e.player.y],room_id=report['room_id']))
            ready=True
        if Path(config['stop_path']).exists():
            import pygame
            pygame.event.post(pygame.event.Event(pygame.QUIT))
        if diagnostic is not None:
            diagnostic.frame(e,screen)
    try:
        engine.run(on_frame=frame)
    except SystemExit as error:
        # Death/quit never enters main.py's campaign/restart loop. Reset remains
        # available in Workbench with this same captured version.
        if error.code not in (None,0,2):
            raise


if __name__=='__main__':
    main()
