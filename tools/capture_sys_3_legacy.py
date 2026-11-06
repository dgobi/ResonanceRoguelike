"""One-time genuine pre-SYS-3 coating and vessel-job capture; no field stripping."""
import hashlib, json, os, pickle, subprocess, sys, tempfile, zipfile
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'roguelike'), str(ROOT/'tools/critical_fix_regressions/tests')]
os.environ.update(SDL_VIDEODRIVER='dummy', SDL_AUDIODRIVER='dummy', PYGAME_HIDE_SUPPORT_PROMPT='1')
import pygame
from unittest.mock import patch
from test_effect_persistence import load_data, make_engine
from engine.save_components import serialize_item
from engine.crafting import plan_craft
from engine import vessels
from rendering.craft_screen import CraftScreen
from generation.decor_utils import place_decor
from generation.floor_object_utils import place_floor_object


def main():
    revision = subprocess.check_output(['git','rev-parse','HEAD'], cwd=ROOT, text=True).strip()
    assert revision == '3a73956fa2e1e50be3c93cf22fed9e1ed1b581d8'
    assert not subprocess.check_output(['git','diff','--name-only','HEAD','--','roguelike'],cwd=ROOT,text=True).strip()
    out=ROOT/'evidence/sys-3';out.mkdir(parents=True,exist_ok=True)
    assert not (out/'legacy-baseline.json').exists()
    owner={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in subprocess.check_output(
        ['git','ls-files','--others','--exclude-standard'],cwd=ROOT,text=True).splitlines()
        if not p.startswith(('evidence/sys-3/','tools/capture_sys_3_legacy.py','docs/owner/SYS_3'))}
    (out/'owner-files.json').write_text(json.dumps(owner,indent=2)+'\n')
    pygame.init();os.chdir(ROOT/'roguelike')
    with tempfile.TemporaryDirectory(prefix='sys3-legacy-') as tmp:
        with patch('engine.save_manager.SAVE_DIR',Path(tmp)/'saves'): e=make_engine(load_data())
        e.debug=False
        for iid in ('briar_binding_oil','briar_binding_oil','bile_coating','hungering_oil','coldbell_cutting','coldbell_cutting','clay_pot','resonant_bone_fragment'):
            assert e.player.inventory.add(e.item_factory.create(iid)),iid
        pair=[i for i in e.player.inventory.items if i.item_id=='coldbell_cutting']
        pair[1].keywords=[dict(tag='binding',tier=2),dict(tag='binding',tier=1)]
        weapon=e.item_factory.create('binding_knife')
        assert e.player.inventory.add(weapon)
        e.player.equipment.equip(weapon,'weapon')
        oil=e.player.inventory.get_by_id('briar_binding_oil')
        assert e.item_system.use(oil,e)
        from engine.item_transfers import consume
        assert consume(e,oil)
        # The pre-existing contact consumer spends actual applied state.
        from engine.effect_lifecycle import coating_contact
        from types import SimpleNamespace
        coating_contact(e,weapon,SimpleNamespace(hit=True,dodged=False))
        coating_contact(e,weapon,SimpleNamespace(hit=True,dodged=False))
        floor=e.item_factory.create('bile_coating');assert place_floor_object(e.local_map,14,11,floor)
        e.local_map.container_state[(8,8)]=dict(items=[serialize_item(e.item_factory.create('hungering_oil'))],looted=True)
        pot=e.player.inventory.get_by_id('clay_pot');vessels.set_water(pot,250)
        place_decor(e.local_map,13,12,'campfire_lit')
        e._update_fov()
        recipe=e.data.recipes['resonant_bone_tincture']
        selected,missing=plan_craft(recipe,e.player.inventory,ambient_sources=CraftScreen._build_ambient_sources(e))
        assert not missing,missing
        e._start_processing_placement(recipe,selected);e._placement_cursor_x,e._placement_cursor_y=12,11
        e._handle_key(pygame.K_RETURN)
        assert e.local_map.processing_layer[(12,11)]['turns_remaining']==34
        (Path(tmp)/'dose.pkl').write_bytes(pickle.dumps(floor))
        e._handle_key(pygame.K_F5);assert e.save_manager.save_exists(),e.save_manager.last_error
        archive=out/'legacy-coatings-job.zip'
        with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
            for p in Path(tmp).rglob('*'):
                if p.is_file():z.write(p,p.relative_to(tmp))
        record=dict(source_revision=revision,producer=Path(__file__).name,archive=archive.name,
            sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),turn=e.world_time.turn,
            setup='Disposable real pre-change constructors, application/contact consumer, vessel commitment and F5. Same-ID keyword variant explicitly staged; no fields stripped.',
            inventory=[serialize_item(i) for i in e.player.inventory.items])
        (out/'legacy-baseline.json').write_text(json.dumps(record,indent=2)+'\n')
        print(json.dumps(dict(passed=True,source_revision=revision,archive=archive.name)))


if __name__=='__main__':main()
