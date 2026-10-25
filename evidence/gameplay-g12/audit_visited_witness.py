"""Supplement the focused witness regression with every visited mutable field.

Run with the established interpreter from the repository root. This bounded
audit imports the committed fixture helper; it never opens a personal save.
"""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'roguelike'),str(ROOT/'tools'),str(ROOT/'tools/critical_fix_regressions/tests')]
os.environ.update(SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy',PYGAME_HIDE_SUPPORT_PROMPT='1')
from test_gameplay_g12 import load_witness,use
from engine.save_components import serialize_item
from engine.item_transfers import take_floor,take_container
import pygame


def rows(e):
    inactive=e.save_manager.cache.load(1,0).local_map
    return [e.local_map.floor_objects[(13,12)][0],
            e.local_map.container_state[(14,12)]['items'][0],
            inactive.floor_objects[(11,12)][0]]


def main():
    pygame.init()
    report=dict(passed=False,head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        command=[sys.executable,'-X','utf8',str(Path(__file__).resolve())],
        script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        controls='Genuine pre-edit checkpoint; disposable extraction. Full serialize_item fields compared against the original witness, allowing only the commissioned null-handler correction. Native floor/container transfer and inventory use; native F9 restores source ownership. Inactive visited owner inspected without regeneration. No balance claim.')
    with tempfile.TemporaryDirectory(prefix='resonance-g12-visited-audit-') as root:
        e,w=load_witness(root);e.debug=None
        expected=[]
        for row,item in zip(w['items'][5:],rows(e)):
            state=dict(row['state'])
            assert serialize_item(item)==state
            assert (item.x,item.y)==tuple(map(int,row['owner'].split(':')[-1].split(',')))
            expected.append(dict(owner=row['owner'],state=state))
        floor,stored,inactive=rows(e)
        assert take_floor(e,floor);use(e,floor)
        assert floor.equipped and e.player.equipment.equipped_in('weapon') is floor
        assert take_container(e,14,12,stored);use(e,stored)
        assert stored.equipped and e.player.equipment.equipped_in('satchel') is stored
        for original,item in zip(expected[:2],(floor,stored)):
            state=serialize_item(item);state['on_use']=original['state']['on_use']
            assert state==original['state'] and item.on_use=='equip_toggle'
        assert e.player.inventory.contains(floor) and e.player.inventory.contains(stored)
        assert not any(i is floor for items in e.local_map.floor_objects.values() for i in items)
        assert not e.local_map.container_state[(14,12)]['items']
        assert e.player.inventory.items[4].on_use=='read'
        e._handle_key(pygame.K_F9)
        for row,item in zip(expected,rows(e)):
            assert serialize_item(item)==row['state']
            assert not e.player.inventory.contains(item) and not item.equipped
        report.update(passed=True,visited_items=expected,full_mutable_fields_match=True,
                      normal_acquire_and_equip=True,f9_restores_exact_source_owners=True,
                      custom_nonnull_handler_preserved=True,inactive_visited_scene_preserved=True)
    (Path(__file__).parent/'visited-witness.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(passed=True,visited_items=len(expected),full_mutable_fields_match=True)))


if __name__=='__main__':main()
