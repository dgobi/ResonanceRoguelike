"""Run once on pre-SYS-1 source; real item construction, crafting and F5 archive."""
import hashlib, json, os, subprocess, sys, tempfile, zipfile
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'roguelike'), str(ROOT/'tools/critical_fix_regressions/tests')]
os.environ.update(SDL_VIDEODRIVER='dummy', SDL_AUDIODRIVER='dummy', PYGAME_HIDE_SUPPORT_PROMPT='1')
import pygame
from unittest.mock import patch
from test_effect_persistence import load_data, make_engine
from engine.crafting import plan_craft
from rendering.craft_screen import CraftScreen
from engine.save_components import serialize_item
from generation.decor_utils import place_decor


def main():
    revision = subprocess.check_output(['git','rev-parse','HEAD'], cwd=ROOT, text=True).strip()
    assert revision == '09cc1e5f560857cca4a54450839d69ca9119a658'
    out = ROOT/'evidence/sys-1'; archive = out/'legacy-items-job.zip'
    assert not archive.exists()
    pygame.init(); os.chdir(ROOT/'roguelike')
    with tempfile.TemporaryDirectory(prefix='sys1-legacy-') as tmp:
        with patch('engine.save_manager.SAVE_DIR', Path(tmp)/'saves'):
            e = make_engine(load_data())
        e.debug = False
        for iid in ('water_skin','empty_water_skin','clay_pot','resonant_bone_tincture',
                    'resonant_bone_fragment','resonant_bone_fragment'):
            assert e.player.inventory.add(e.item_factory.create(iid))
        place_decor(e.local_map, 13, 12, 'campfire_lit')
        recipe = e.data.recipes['resonant_bone_tincture']
        selected, missing = plan_craft(recipe, e.player.inventory,
            ambient_sources=CraftScreen._build_ambient_sources(e))
        assert not missing, missing
        e._start_processing_placement(recipe, selected)
        e._placement_cursor_x, e._placement_cursor_y = 12, 11
        e._handle_key(pygame.K_RETURN)
        assert e.local_map.processing_layer
        assert e.local_map.processing_layer[(12,11)]['turns_remaining'] == 34
        e._handle_key(pygame.K_F5)
        assert e.save_manager.save_exists(), e.save_manager.last_error
        with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as z:
            for p in (Path(tmp)/'saves').rglob('*'):
                if p.is_file(): z.write(p,p.relative_to(tmp))
        record = dict(source_revision=revision, producer=Path(__file__).name,
            archive=archive.name, sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),
            turn=e.world_time.turn, inventory=[serialize_item(i) for i in e.player.inventory.items],
            jobs=[dict(position=list(xy),record=r) for xy,r in e.local_map.processing_layer.items()])
        (out/'legacy-baseline.json').write_text(json.dumps(record,indent=2)+'\n')
        print(json.dumps(dict(passed=True,source_revision=revision,archive=archive.name)))


if __name__ == '__main__': main()
