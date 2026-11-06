"""One-time genuine pre-SYS-4 containers and map caches; no field stripping."""
import copy, hashlib, json, os, pickle, subprocess, sys, tempfile, zipfile
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'roguelike'), str(ROOT/'tools/critical_fix_regressions/tests')]
os.environ.update(SDL_VIDEODRIVER='dummy', SDL_AUDIODRIVER='dummy', PYGAME_HIDE_SUPPORT_PROMPT='1')
import pygame
from unittest.mock import patch
from test_effect_persistence import load_data, make_engine
from engine.save_components import serialize_item
from generation.floor_object_utils import (place_container, open_container,
    get_container_items, take_from_container, dismantle_empty_crate)


def main():
    revision = subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    assert revision == '8c4cc267ef7c09837c1aac5fc5c22e8543d0d984'
    assert not subprocess.check_output(['git','diff','--name-only','HEAD','--','roguelike'],cwd=ROOT,text=True).strip()
    out=ROOT/'evidence/sys-4';out.mkdir(parents=True,exist_ok=True)
    assert not (out/'legacy-baseline.json').exists()
    owner={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in subprocess.check_output(
        ['git','ls-files','--others','--exclude-standard'],cwd=ROOT,text=True).splitlines()
        if not p.startswith(('evidence/sys-4/','tools/capture_sys_4_legacy.py','docs/owner/SYS_4'))}
    (out/'owner-files.json').write_text(json.dumps(owner,indent=2)+'\n')
    saves={p.relative_to(ROOT).as_posix():dict(sha256=hashlib.sha256(p.read_bytes()).hexdigest(),mtime_ns=p.stat().st_mtime_ns)
           for p in (ROOT/'roguelike/saves').rglob('*') if p.is_file()}
    (out/'personal-saves.json').write_text(json.dumps(saves,indent=2)+'\n')
    pygame.init();os.chdir(ROOT/'roguelike')
    with tempfile.TemporaryDirectory(prefix='sys4-legacy-') as tmp:
        with patch('engine.save_manager.SAVE_DIR',Path(tmp)/'saves'): e=make_engine(load_data())
        e.debug=False
        for x in (10,11,12):
            value=e.item_factory.create('bile_coating');value.count=1
            place_container(e.local_map,x,10,'crate',[value])
        open_container(e.local_map,11,10)
        open_container(e.local_map,12,10)
        taken=get_container_items(e.local_map,12,10,e.item_factory)[0]
        assert take_from_container(e.local_map,12,10,taken)
        assert e.player.inventory.add(taken)
        place_container(e.local_map,13,10,'crate',[])
        assert dismantle_empty_crate(e.local_map,13,10,e.local_map.container_state[(13,10)],e.item_factory.create('wood_bundle'))
        # Independent inactive surface and submap owners travel through real caches.
        e.save_manager.cache.store_hot_only(1,0,copy.deepcopy(e.local_map),[])
        e.save_manager.cache.store_submap('sys4_legacy_room',copy.deepcopy(e.local_map),[])
        e.save_manager.cache.evict_distant(20,20)
        e._handle_key(pygame.K_F5)
        assert e.save_manager.save_exists(),e.save_manager.last_error
        archive=out/'legacy-containers.zip'
        with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
            for p in Path(tmp).rglob('*'):
                if p.is_file():z.write(p,p.relative_to(tmp))
        record=dict(source_revision=revision,producer=Path(__file__).name,archive=archive.name,
            sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),turn=e.world_time.turn,
            setup='Unmodified baseline constructors and container APIs; closed/open/looted owners, dismantled crate, distinct surface and submap caches, real F5. Disposable fixture; no fields stripped.',
            inventory=[serialize_item(i) for i in e.player.inventory.items],
            containers={str(xy):dict(state=row['state'],items=[serialize_item(i) for i in row['items']]) for xy,row in e.local_map.container_state.items()})
        (out/'legacy-baseline.json').write_text(json.dumps(record,indent=2)+'\n')
        print(json.dumps(dict(passed=True,source_revision=revision,archive=archive.name)))


if __name__=='__main__':main()
