"""Genuine pre-SYS-5 fixture, generated once before modifying game sources."""
import copy, hashlib, json, os, subprocess, sys, tempfile, zipfile
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'roguelike'), str(ROOT/'tools/critical_fix_regressions/tests')]
os.environ.update(SDL_VIDEODRIVER='dummy', SDL_AUDIODRIVER='dummy', PYGAME_HIDE_SUPPORT_PROMPT='1')
import pygame
from unittest.mock import patch
from test_effect_persistence import load_data, make_engine
from engine.save_components import serialize_item
from engine.save_manager import _serialize_entity
from generation.floor_object_utils import place_floor_object, place_container


def main():
    revision = subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    assert revision == 'aea1d565097982a699230dcc7e4210b8106fbbe1'
    assert not subprocess.check_output(['git','diff','--name-only','HEAD','--','roguelike'],cwd=ROOT,text=True).strip()
    out=ROOT/'evidence/sys-5';out.mkdir(parents=True,exist_ok=True)
    assert not (out/'legacy-baseline.json').exists()
    owner={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in subprocess.check_output(
        ['git','ls-files','--others','--exclude-standard'],cwd=ROOT,text=True).splitlines()
        if not p.startswith(('evidence/sys-5/','tools/capture_sys_5_legacy.py','docs/owner/SYS_5'))}
    # Ignored owner authoring files are preserved too; no personal campaign loads.
    owner.update({p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
                  for p in (ROOT/'authoring').rglob('*') if p.is_file()})
    (out/'owner-files.json').write_text(json.dumps(owner,indent=2)+'\n')
    saves={p.relative_to(ROOT).as_posix():dict(sha256=hashlib.sha256(p.read_bytes()).hexdigest(),mtime_ns=p.stat().st_mtime_ns)
           for p in (ROOT/'roguelike/saves').rglob('*') if p.is_file()}
    (out/'personal-saves.json').write_text(json.dumps(saves,indent=2)+'\n')
    pygame.init();os.chdir(ROOT/'roguelike')
    with tempfile.TemporaryDirectory(prefix='sys5-legacy-') as tmp:
        with patch('engine.save_manager.SAVE_DIR',Path(tmp)/'saves'): e=make_engine(load_data())
        e.debug=False
        meat=e.item_factory.create('crow_meat');meat.count=3;e.player.inventory.add(meat)
        floor_meat=e.item_factory.create('stalker_meat');floor_meat.count=2
        assert place_floor_object(e.local_map,13,12,floor_meat)
        place_container(e.local_map,14,12,'crate',[e.item_factory.create('crow_meat')])
        for source,x in [('plague_crow',15),('heath_stalker',16)]:
            a=e.creature_factory.spawn(source,x,12);e.entities.append(a)
            e._on_entity_death(a,observed=False)
        for source,x in [('grave_skirmisher',18),('barrow_sentinel',22)]:
            e.entities.append(e.creature_factory.spawn(source,x,12))
        e.save_manager.cache.store_hot_only(1,0,copy.deepcopy(e.local_map),copy.deepcopy(e.entities[3:]))
        e.save_manager.cache.store_submap('sys5_legacy_room',copy.deepcopy(e.local_map),[])
        e.save_manager.cache.evict_distant(20,20)
        e._handle_key(pygame.K_F5)
        assert e.save_manager.save_exists(),e.save_manager.last_error
        archive=out/'legacy-resources.zip'
        with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
            for p in Path(tmp).rglob('*'):
                if p.is_file():z.write(p,p.relative_to(tmp))
        record=dict(source_revision=revision,producer=Path(__file__).name,archive=archive.name,
            sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),turn=e.world_time.turn,
            setup='Unmodified baseline constructors, real native death, floor/container/inventory owners, both future host recipes, surface/submap caches and real F5. No fields stripped.',
            inventory=[serialize_item(i) for i in e.player.inventory.items],
            floor={str(xy):[serialize_item(i) for i in rows] for xy,rows in e.local_map.floor_objects.items()},
            actors=[_serialize_entity(a) for a in e.entities if a is not e.player and a.is_alive])
        (out/'legacy-baseline.json').write_text(json.dumps(record,indent=2)+'\n')
        print(json.dumps(dict(passed=True,source_revision=revision,archive=archive.name,owner_files=len(owner),personal_saves=len(saves))))


if __name__=='__main__':main()
