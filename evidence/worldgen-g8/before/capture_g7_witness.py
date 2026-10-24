"""One-time witness creator, run against unmodified reviewed G7 source."""
import contextlib
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import zipfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT/'roguelike'), str(ROOT/'tools'), str(ROOT/'tools/critical_fix_regressions/tests')]
os.environ.update(SDL_VIDEODRIVER='dummy', SDL_AUDIODRIVER='dummy', PYGAME_HIDE_SUPPORT_PROMPT='1')
import pygame
from test_generation_g7_compounds import G7Compounds
from generation.placement import digest
from g1_support import fingerprint
from engine.engine import GameMode
from verify_b3 import source_manifest

out = Path(__file__).parent/'witness'
out.mkdir(exist_ok=True)
source = source_manifest()
log = io.StringIO()
with contextlib.redirect_stdout(log):
    G7Compounds.setUpClass()
    case = G7Compounds()
    case.setUp()
    try:
        e = case.boot()
        assert e.world_map.plan['version'] == 5
        plan = e.world_map.plan
        town = next(s for s in plan['settlements'] if s['form']=='grid')
        visited = town['members'][0]
        pending = town['members'][1]
        compound = next(s for s in plan['sites'] if s['kind']=='compound')
        rural_pending = next(s for s in plan['sites'] if s != compound)
        e.debug = False
        e.player_invincible = True
        e.player.inventory.capacity = 100
        mutations = []
        with patch.object(type(e), '_advance_turn', lambda e:e.world_time.advance()):
            for xy in [visited, compound['chunk']]:
                case.visit(e, xy)
                children = [p for p in plan['placements'] if p.get('parent')==compound['id']] if xy==compound['chunk'] else [p for p in plan['placements'] if p['origin'][0]//80==xy[0] and p['origin'][1]//43==xy[1]]
                for child in children:
                    targets=[t for t in child['targets'] if t['kind']=='container']
                    if not targets:continue
                    target=targets[0];pos=(target['x']%80,target['y']%43)
                    state=e.local_map.container_state[pos]
                    if not state['items']:continue
                    before=len(state['items'])
                    case.interact(e,pos)
                    assert e.interaction_cursor._selection_prompt is not None
                    e.mode=GameMode.INTERACTION_CURSOR;e._handle_key(pygame.K_RETURN)
                    e.mode=GameMode.LOCAL;e.interaction_cursor._selection_prompt=None
                    assert len(state['items'])==before-1
                    mutations.append(dict(chunk=xy,placement=child['id'],target=pos,before=before,after=len(state['items']),action='production interaction handler; fixture positioning; stationary turns'))
                    if xy==visited:break
            e._handle_key_local(pygame.K_F5)
            assert e.save_manager.last_error is None
        checkpoint=e.save_manager.checkpoint_path()
        assert not (checkpoint/f'chunks/{pending[0]}_{pending[1]}.pkl').exists()
        assert not (checkpoint/f'chunks/{rural_pending["chunk"][0]}_{rural_pending["chunk"][1]}.pkl').exists()
        scenes=[]
        for xy in [visited,compound['chunk']]:
            m,actors=e._prepare_destination(*xy)
            scenes.append(dict(chunk=xy,fingerprint=fingerprint(m,actors),provenance=m.plan_provenance,creator=m.generation_revision))
        with zipfile.ZipFile(out/'authentic-g7-checkpoint.zip','w',zipfile.ZIP_DEFLATED) as archive:
            for path in sorted(checkpoint.rglob('*')):
                if path.is_file():archive.write(path,path.relative_to(checkpoint).as_posix())
        raw=json.dumps(plan,indent=2).encode()
        (out/'g7-plan.json.gz').write_bytes(gzip.compress(raw,mtime=0))
        inventory={p.relative_to(checkpoint).as_posix():dict(bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in checkpoint.rglob('*') if p.is_file()}
        record=dict(head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),source=source,source_stable=source==source_manifest(),python=sys.version,executable=sys.executable,plan_identity=digest(plan),visited=visited,pending=pending,compound=compound['chunk'],rural_pending=rural_pending['chunk'],scenes=scenes,mutations=mutations,checkpoint_inventory=inventory,controls='Fixture teleports/positioning, stationary AI/survival, invincible player; actual transfer and F5 handlers. No scene relabeling.')
        assert record['source_stable']
        (out/'g7-witness.json').write_text(json.dumps(record,indent=2)+'\n')
    finally:case.doCleanups()
(out/'output.txt').write_text(log.getvalue(),encoding='utf-8')
print(json.dumps(dict(passed=True,plan_identity=record['plan_identity'],mutations=len(mutations),scenes=len(inventory))))
