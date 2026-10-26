"""Exact comparison of the genuine G15 visited and pending old workshops."""
import argparse
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
ARCHIVE = ROOT/'evidence/gameplay-g15/final-a/journey/acquisition/acquired-unused.zip'
SHA256 = '503309d073b96139a84fc0769ad9eb89fe53b1f1b4c89230d0af318eb20037de'


def inspect():
    from test_effect_persistence import load_data, make_engine
    from g12_journey import install_checkpoint, snapshot
    from generation.placement import check_dependencies, digest
    from g1_support import fingerprint
    assert hashlib.sha256(ARCHIVE.read_bytes()).hexdigest() == SHA256
    with zipfile.ZipFile(ARCHIVE) as z:
        assert z.testzip() is None
    with tempfile.TemporaryDirectory(prefix='resonance-g16-historical-') as root, patch('engine.save_manager.SAVE_DIR', Path(root)):
        install_checkpoint(ARCHIVE, root)
        e = make_engine(load_data())
        assert e.save_manager.load(e), e.save_manager.last_error
        expected = json.loads(ARCHIVE.with_suffix('.json').read_text())
        assert snapshot(e) == expected
        plan = digest(e.world_map.plan)
        for p in e.world_map.plan['placements']:
            check_dependencies(p, e.world_map.plan, e.data)
        selected = [p for p in e.world_map.plan['placements'] if p['asset']=='workshop_a']
        assert len(selected)==4 and not any(p['asset']=='workshop_b' for p in e.world_map.plan['placements'])
        p = next(p for p in selected if p['id']=='settlement-0-cross-market-lot-81-3-S-0-building')
        chunk = e.world_map.get(76,99)
        assert not chunk.visited and not getattr(chunk,'generation_revision',None)
        pending = e._ensure_surface_scene(76,99)
        assert not any(i.item_id=='stalker_musk_gland' for c in pending[0].container_state.values() for i in c['items'])
        after = snapshot(e)
        assert {k:v for k,v in after.items() if k!='world'} == {k:v for k,v in expected.items() if k!='world'}
        assert digest(e.world_map.plan)==plan
        return dict(archive=ARCHIVE.relative_to(ROOT).as_posix(),sha256=SHA256,
            restored_snapshot=expected,plan_identity=plan,dependency_checks=len(e.world_map.plan['placements']),
            selected_old_workshops=len(selected),pending_placement=p,pending_fingerprint=fingerprint(*pending),
            materialized_snapshot=after,no_workshop_backfill=True,visited_scene_and_player_preserved=True)


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--baseline',type=Path);a=p.parse_args()
    sys.path[:0]=[str(ROOT/'roguelike'),str(ROOT/'tools'),str(ROOT/'tools/critical_fix_regressions/tests')]
    os.environ.update(SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy',PYGAME_HIDE_SUPPORT_PROMPT='1',PYTHONHASHSEED='20261020')
    observed=inspect()
    if a.baseline:
        assert observed==json.loads(a.baseline.read_text())['observed']
    receipt=dict(passed=True,pid=os.getpid(),head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        observed=observed,comparison='exact genuine pre-edit receipt' if a.baseline else 'captured before G16 content edits')
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(passed=True,output=str(a.output))))


if __name__=='__main__':main()
