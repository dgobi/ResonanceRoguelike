"""Compact genuine G16 preservation witness, including its pending BSP barrow."""
import argparse
from dataclasses import asdict
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT/'evidence/gameplay-g16/final-a/journey/cold-return/homeward/returned-pellet.zip'
SHA256 = '0867c43c7b39adf64ef13e26dadaccefa82730046021e62c7d1213682685287d'


def inspect():
    from test_effect_persistence import load_data, make_engine
    from g12_journey import install_checkpoint, snapshot
    from generation.placement import check_dependencies, digest
    from g1_support import fingerprint
    assert hashlib.sha256(ARCHIVE.read_bytes()).hexdigest() == SHA256
    with zipfile.ZipFile(ARCHIVE) as z:
        assert z.testzip() is None
    with tempfile.TemporaryDirectory(prefix='resonance-g17-historical-') as root, patch('engine.save_manager.SAVE_DIR', Path(root)):
        install_checkpoint(ARCHIVE, root)
        e = make_engine(load_data())
        assert e.save_manager.load(e), e.save_manager.last_error
        expected = json.loads(ARCHIVE.with_suffix('.json').read_text())
        assert snapshot(e) == expected
        plan = digest(e.world_map.plan)
        for p in e.world_map.plan['placements']:
            check_dependencies(p, e.world_map.plan, e.data)
        chunk = e.world_map.get(73, 97)
        sub = next(s for s in chunk.submaps if s.submap_id == 'submap_73_97_0')
        assert (sub.submap_type, sub.seed, sub.layout_id, sub.generated) == ('barrow', 107361, '', False)
        pending_metadata = asdict(sub)
        pending = e._ensure_submap_scene(73, 97, sub.submap_id)
        # Load the visited workshop through the saved ownership route, never regenerate it.
        with patch('engine.scene_generation.create_surface', side_effect=AssertionError('historical regeneration')):
            workshop = e._ensure_surface_scene(75, 100)
        after = snapshot(e)
        assert {k:v for k,v in after.items() if k != 'world'} == {k:v for k,v in expected.items() if k != 'world'}
        assert digest(e.world_map.plan) == plan
        return dict(archive=ARCHIVE.relative_to(ROOT).as_posix(), sha256=SHA256,
            restored_snapshot=expected, plan_identity=plan, dependency_checks=len(e.world_map.plan['placements']),
            pending_metadata=pending_metadata, pending_fingerprint=fingerprint(*pending),
            visited_workshop_fingerprint=fingerprint(*workshop), materialized_snapshot=after,
            blank_layout_retains_bsp=True, visited_scene_and_player_preserved=True)


def main():
    p=argparse.ArgumentParser(); p.add_argument('--output',type=Path,required=True); p.add_argument('--baseline',type=Path); a=p.parse_args()
    sys.path[:0]=[str(ROOT/'roguelike'), str(ROOT/'tools'), str(ROOT/'tools/critical_fix_regressions/tests')]
    os.environ.update(SDL_VIDEODRIVER='dummy', SDL_AUDIODRIVER='dummy', PYGAME_HIDE_SUPPORT_PROMPT='1', PYTHONHASHSEED='20261020')
    observed=inspect()
    if a.baseline: assert observed == json.loads(a.baseline.read_text())['observed']
    receipt=dict(passed=True,pid=os.getpid(),head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        observed=observed,comparison='exact genuine pre-edit receipt' if a.baseline else 'captured before G17 runtime edits')
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(passed=True,output=str(a.output))))


if __name__ == '__main__': main()
