"""Explicit save ownership and ordinary controls without personal campaign access."""
import contextlib
import io
import os
from pathlib import Path
import sys
import tempfile
import unittest

from engine.data_loader import DataLoader
from engine.display_config import DisplayConfig
from engine.engine import Engine
from engine.item_factory import ItemFactory
from engine.player_setup import create_player
from engine.save_manager import SaveManager
from rendering.tile_registry import TileRegistry
from world.local_map import LocalMap,make_tile
from world.world_map import WorldMap,Chunk,RegionType

GAME=Path(__file__).resolve().parents[3]/'roguelike'


class RoomSessionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with contextlib.redirect_stdout(io.StringIO()):cls.data=DataLoader(str(GAME/'data'))

    def engine(self,manager):
        world=WorldMap(1,1);world.seed=20261027;world.start_wx=world.start_wy=0
        world.set(Chunk(0,0,RegionType.PLAINS,world.seed,visited=True))
        local=LocalMap();local.tiles[:]=make_tile('floor',True,True)
        player=create_player(self.data,ItemFactory(self.data),12,12)
        return Engine(player,local,[player],TileRegistry(str(GAME/'data/tiles.json')),world,0,0,self.data,DisplayConfig.from_config(),
                      save_manager=manager,debug_mode=False,bounded_room_test=True)

    def test_explicit_owner_before_startup_and_cache_has_no_other_save_access(self):
        with tempfile.TemporaryDirectory(prefix='w5h-isolation-') as directory:
            root=Path(directory);session=root/'test';session.mkdir();sentinel=root/'personal-sentinel'/'saves';sentinel.mkdir(parents=True)
            marker=sentinel/'do-not-touch';marker.write_bytes(b'owner sentinel')
            trace=[];active=[True]
            def audit(event,args):
                if not active[0] or event not in ('open','os.listdir','os.scandir','os.mkdir'):return
                if not args or not isinstance(args[0],(str,bytes,os.PathLike)):return
                p=Path(os.fsdecode(args[0])).absolute()
                if 'saves' in p.parts:
                    trace.append((event,str(p)))
                    if not p.is_relative_to(session):raise AssertionError(f'Foreign save access: {p}')
            sys.addaudithook(audit)
            try:
                manager=SaveManager(save_root=session/'saves');self.assertEqual(manager.startup_state(),('new',None))
                self.assertFalse(manager.cache.has(0,0));e=self.engine(manager)
                self.assertIs(e.save_manager,manager);self.assertIsNone(e.debug);self.assertFalse(e.player_invincible)
                self.assertTrue(manager.save(e));self.assertTrue(manager.load(e));self.assertTrue(trace)
            finally:active[0]=False
            self.assertEqual(marker.read_bytes(),b'owner sentinel')

    def test_standalone_default_still_uses_relative_saves_and_session_boundary_is_bounded(self):
        with tempfile.TemporaryDirectory(prefix='w5h-default-') as directory:
            previous=Path.cwd()
            try:
                os.chdir(directory);manager=SaveManager();self.assertEqual(manager.save_path,Path(directory)/'saves/slot_0')
                e=self.engine(manager);before=(e.world_x,e.world_y,e.player.x,e.player.y,len(e.world_map.chunks))
                e._transition_chunk(80,0);self.assertEqual(before,(e.world_x,e.world_y,e.player.x,e.player.y,len(e.world_map.chunks)))
            finally:os.chdir(previous)

    def test_normal_profile_has_equipped_light_and_real_needs(self):
        with tempfile.TemporaryDirectory(prefix='w5h-player-') as directory:
            e=self.engine(SaveManager(save_root=Path(directory)/'saves'))
            torch=next(i for i in e.player.inventory.items if i.item_id=='tallow_torch')
            e.item_system.use(torch,e)
            self.assertTrue(e.player.light_source.active)
            self.assertIs(e.player.equipment.equipped_in('offhand'),torch)
            self.assertIsNotNone(e.player.needs)
            self.assertIsNotNone(e.player.fighter)


if __name__=='__main__':unittest.main()
