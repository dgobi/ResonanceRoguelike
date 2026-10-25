"""One-time genuine pre-G11 checkpoint capture; run before runtime edits."""
import contextlib
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
sys.path[:0] = [str(ROOT/'roguelike'), str(ROOT/'tools'), str(ROOT/'tools/critical_fix_regressions/tests')]
os.environ.update(SDL_VIDEODRIVER='dummy', SDL_AUDIODRIVER='dummy', PYGAME_HIDE_SUPPORT_PROMPT='1')


def main():
    from g10_play import boot, leave_lab, interact
    from g1_support import fingerprint
    from generation.placement import digest
    from engine.scene_generation import create_surface
    from engine.save_manager import _serialize_player
    out = ROOT/'tools/critical_fix_regressions/fixtures/g11'
    out.mkdir(parents=True, exist_ok=True)
    assert not (out/'authentic-g10-checkpoint.zip').exists()
    with tempfile.TemporaryDirectory(prefix='resonance-g11-capture-') as tmp, patch('engine.save_manager.SAVE_DIR', Path(tmp)):
        e = boot(tmp)
        assert e.world_map.surface_policy['version'] == 1
        inputs = []
        leave_lab(e, inputs)
        stone = next(xy for xy, value in e.local_map.decor.items() if value == 'waystone_plinth')
        interact(e, stone, inputs)
        assert stone in e.local_map.interacted_waystones
        assert e.save_manager.save(e), e.save_manager.last_error
        checkpoint = e.save_manager.checkpoint_path()
        files = {}
        with zipfile.ZipFile(out/'authentic-g10-checkpoint.zip', 'w', zipfile.ZIP_DEFLATED) as z:
            for p in sorted(checkpoint.rglob('*')):
                if p.is_file():
                    name = p.relative_to(checkpoint).as_posix()
                    raw = p.read_bytes()
                    files[name] = dict(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
                    z.writestr(name, raw)
        scenes = [dict(chunk=[e.world_x,e.world_y], fingerprint=fingerprint(e.local_map,e.entities[1:]))]
        pending = []
        for xy in ((44,8),(73,100),(72,103)):
            assert not e.world_map.get(*xy).visited
            r = create_surface(e.world_map,e.world_map.get(*xy),e.data,e.item_factory,e.creature_factory,80,43)
            pending.append(dict(chunk=xy,fingerprint=fingerprint(r.local_map,r.actors),
                                links=sorted((list(p),s) for p,s in r.local_map.submap_links.items())))
        binding = dict(head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
            files=files,scenes=scenes,pending=pending,mutation=dict(waystone=stone),
            player=digest(_serialize_player(e)),plan_identity=digest(e.world_map.plan),
            policy=e.world_map.surface_policy,controls='Normal start, real lab ascent and waystone interaction; no injected mutation.')
        (out/'g10-witness.json').write_text(json.dumps(binding,indent=2)+'\n',encoding='utf-8')


if __name__ == '__main__':
    with (ROOT/'evidence/worldgen-g11/before/capture-output.txt').open('w',encoding='utf-8') as log, contextlib.redirect_stdout(log):
        main()
