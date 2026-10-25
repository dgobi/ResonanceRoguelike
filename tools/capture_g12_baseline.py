"""One-time selected-item witness, captured with the genuine pre-G12 executable."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'roguelike'), str(ROOT/'tools'),
               str(ROOT/'tools/critical_fix_regressions/tests')]
os.environ.update(SDL_VIDEODRIVER='dummy', SDL_AUDIODRIVER='dummy', PYGAME_HIDE_SUPPORT_PROMPT='1')


def main():
    from test_effect_persistence import load_data, make_engine
    from engine.save_components import serialize_item
    from verify_b3 import source_manifest
    from world.local_map import LocalMap, make_tile
    from world.world_map import Chunk, RegionType
    import pygame
    pygame.init()
    out = ROOT/'tools/critical_fix_regressions/fixtures/g12'
    out.mkdir(parents=True, exist_ok=True)
    assert not (out/'authentic-pre-g12-checkpoint.zip').exists()
    with tempfile.TemporaryDirectory(prefix='resonance-g12-capture-') as tmp, patch('engine.save_manager.SAVE_DIR', Path(tmp)):
        e = make_engine(load_data())
        rows = []
        for iid in ('revelation_lens', 'leather_satchel', 'herbalist_pouch', 'component_satchel'):
            i = e.item_factory.create(iid)
            assert i.on_use is None
            i.description = 'Witness: owner-altered '+iid
            i.weight += .137
            i.temporary_essence = [dict(essence='binding', strength=.7, hits_remaining=3)]
            assert e.player.inventory.add(i)
            rows.append(dict(owner='inventory', state=serialize_item(i)))
        custom = e.item_factory.create('revelation_lens')
        custom.on_use = 'read'
        custom.description = 'Explicit custom handler must remain'
        assert e.player.inventory.add(custom)
        rows.append(dict(owner='inventory', state=serialize_item(custom)))
        torch = e.item_factory.create('tallow_torch')
        assert e.player.inventory.add(torch)
        e.inventory_screen.open = True
        e.inventory_screen._flat = [(torch, False, torch.name)]
        e.inventory_screen.selected = 0
        e._handle_key(pygame.K_RETURN)
        e.inventory_screen.open = False
        # Two genuine visited scene owners, including an inactive cached scene.
        floor = e.item_factory.create('revelation_lens', 13, 12)
        floor.description = 'Visited floor witness'
        floor.weight = .713
        e.local_map.floor_objects[(13, 12)] = [floor]
        rows.append(dict(owner='floor:0,0:13,12', state=serialize_item(floor)))
        stored = e.item_factory.create('component_satchel', 14, 12)
        stored.description = 'Visited container witness'
        stored.weight = .819
        e.local_map.container_state[(14, 12)] = dict(state='open', items=[stored])
        rows.append(dict(owner='container:0,0:14,12', state=serialize_item(stored)))
        e.world_map.width = 2
        e.world_map.set(Chunk(1, 0, RegionType.PLAINS, 29418, visited=True))
        inactive = LocalMap()
        inactive.tiles[:] = make_tile('grass', True, True)
        old = e.item_factory.create('herbalist_pouch', 11, 12)
        old.description = 'Inactive visited scene witness'
        inactive.floor_objects[(11, 12)] = [old]
        e.save_manager.cache.store(1, 0, inactive, [])
        rows.append(dict(owner='floor:1,0:11,12', state=serialize_item(old)))
        e.player.fighter.hp = 47
        e.player.needs.hunger = 12.5
        e.player.language.known_deep_words.add('stone')
        e.player.language.recovered_text[('witness', 0, 0)] = 'remembered'
        e.creature_knowledge['heath_stalker'] = dict(revealed=True)
        e.local_map.interacted_waystones.add((16, 12))
        assert e.save_manager.save(e), e.save_manager.last_error
        checkpoint = e.save_manager.checkpoint_path()
        files = {}
        with zipfile.ZipFile(out/'authentic-pre-g12-checkpoint.zip', 'w', zipfile.ZIP_DEFLATED) as z:
            for p in sorted(checkpoint.rglob('*')):
                if p.is_file():
                    raw = p.read_bytes(); name = p.relative_to(checkpoint).as_posix()
                    files[name] = dict(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
                    z.writestr(name, raw)
        result = dict(head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
            source=source_manifest(), files=files, items=rows, turn=e.world_time.turn,
            controls='Controlled grass-map setup using current real Engine/factories/save writer. Four carried null-handler items; active floor/container and inactive visited floor owners; one explicit custom read handler; normal torch lighting; mutable HP, needs, coatings, descriptions, weights, knowledge and world mutation. No personal campaigns.')
        (out/'pre-g12-witness.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
        print(json.dumps(dict(head=result['head'], items=len(rows), files=len(files), saved=True)))


if __name__ == '__main__':
    main()
