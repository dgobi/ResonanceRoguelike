"""One-time genuine pre-SYS-2 held-light JSON/cache capture; no field stripping."""
import hashlib, json, os, pickle, subprocess, sys, tempfile, zipfile
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'roguelike'), str(ROOT/'tools/critical_fix_regressions/tests')]
os.environ.update(SDL_VIDEODRIVER='dummy', SDL_AUDIODRIVER='dummy', PYGAME_HIDE_SUPPORT_PROMPT='1')
import pygame
from unittest.mock import patch
from test_effect_persistence import load_data, make_engine
from engine.save_components import serialize_item
from generation.floor_object_utils import place_floor_object


def main():
    revision = subprocess.check_output(['git','rev-parse','HEAD'], cwd=ROOT, text=True).strip()
    assert revision == '884b9c7cd03ae3168702839a04b82ba55b1397da'
    assert not subprocess.check_output(['git','diff','--name-only','HEAD','--','roguelike'],cwd=ROOT,text=True).strip()
    out = ROOT/'evidence/sys-2'; out.mkdir(parents=True, exist_ok=True)
    assert not (out/'legacy-baseline.json').exists()
    pygame.init(); os.chdir(ROOT/'roguelike'); records=[]
    for active in (True, False):
        with tempfile.TemporaryDirectory(prefix='sys2-legacy-') as tmp:
            with patch('engine.save_manager.SAVE_DIR', Path(tmp)/'saves'):
                e=make_engine(load_data())
            e.debug=False
            for iid, used, fuel in [('tallow_torch',137,600),('tallow_torch',49,600),
                                    ('oil_lantern',321,1800),('tallow_torch',23,None),
                                    ('tallow_torch',600,0)]:
                item=e.item_factory.create(iid); item.turns_lit=used; item.burn_turns=fuel
                assert e.player.inventory.add(item)
            held=e.player.inventory.items[0]
            e.item_system.use(held,e)
            e._advance_turn()
            if not active:
                e.item_system.use(held,e); e._advance_turn()
            floor=e.item_factory.create('oil_lantern'); floor.turns_lit=777
            assert place_floor_object(e.local_map,13,12,floor)
            # Explicit pickle supplements the real save's cached map owner.
            (Path(tmp)/'partly-used-item.pkl').write_bytes(pickle.dumps(floor))
            e._handle_key(pygame.K_F5)
            assert e.save_manager.save_exists(),e.save_manager.last_error
            archive=out/('legacy-'+('active' if active else 'inactive')+'.zip')
            with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
                for p in Path(tmp).rglob('*'):
                    if p.is_file():z.write(p,p.relative_to(tmp))
            records.append(dict(active=active,source_revision=revision,archive=archive.name,
                sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),turn=e.world_time.turn,
                inventory=[serialize_item(i) for i in e.player.inventory.items],floor=serialize_item(floor)))
    (out/'legacy-baseline.json').write_text(json.dumps(dict(producer=Path(__file__).name,
        setup='Real baseline constructors, activation/charged phases and F5; disposable fixture; null/zero fuel legacy instances explicitly staged.',
        records=records),indent=2)+'\n',encoding='utf8')
    print(json.dumps(dict(passed=True,source_revision=revision,archives=len(records))))


if __name__=='__main__':main()
