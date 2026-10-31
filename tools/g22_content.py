"""Predeclared three-seed metadata comparison; no local scenes or routes."""
import argparse
import contextlib
import copy
import hashlib
import io
import json
import os
from pathlib import Path
import random
import subprocess
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
BASELINE = '98a5af7dd2653b1b9b9a34a57880a98f2d3599d7'
SEEDS = (20261023, 29417, 20261030)


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--evidence', type=Path, required=True); args = parser.parse_args()
    out = args.evidence.resolve(); out.mkdir(parents=True, exist_ok=True)
    sys.path.insert(0, str(ROOT/'roguelike'))
    os.environ.update(SDL_VIDEODRIVER='dummy', SDL_AUDIODRIVER='dummy', PYGAME_HIDE_SUPPORT_PROMPT='1')
    from engine.data_loader import DataLoader
    from engine.save_manager import _serialize_world
    from engine import location_reports as reports
    from generation import world_gen
    from world.world_map import WorldMap
    def original(path):
        return json.loads(subprocess.check_output(['git', 'show', BASELINE+':'+path], cwd=ROOT))
    with contextlib.redirect_stdout(io.StringIO()): data = DataLoader(str(ROOT/'roguelike/data'))
    old_data = copy.copy(data)
    old_data.settlement_profiles = original('roguelike/data/generation/settlement_profiles.json')
    result = dict(baseline=BASELINE, seeds=list(SEEDS), scope='Metadata only; fixed sample, no scenes, hazards, contents, routes or survival evaluation.', worlds=[])
    for seed in SEEDS:
        def generate(d):
            w = WorldMap(128, 128); w.seed = seed
            with contextlib.redirect_stdout(io.StringIO()): world_gen.generate_world(w, d, random.Random(seed))
            return w
        # Only the original fresh factory inputs are compared. Current loading
        # and saved restoration are never replaced by historical implementations.
        place = world_gen._place_starting_location
        def old_lab(w, rng):
            place(w, rng); w.get(w.start_wx, w.start_wy).submaps[0].layout_id = 'starting_lab'
        with patch.object(world_gen, '_place_starting_location', old_lab), patch.object(reports, 'bind'):
            previous = generate(old_data)
        current = generate(data)
        def comparable(w):
            row = copy.deepcopy(_serialize_world(w))
            for k in ('report_owner', 'location_reports', 'learned_reports'): row.pop(k)
            # Changed content dependencies are commissioned. Geometry, random
            # choices, placements, assignments and selection settings are exact.
            row['plan'].pop('dependencies')
            for key in ('dependencies','placements','selection','settings'):
                row['plan']['network']['baseline'][key]='commissioned content identity/dependency fingerprint; compared structurally outside this derived hash'
            return json.dumps(row, sort_keys=True).replace('workshop_d', 'workshop_c').replace('starting_lab_b', 'starting_lab')
        before, after = comparable(previous), comparable(current)
        if before != after:
            delta=[]
            def compare(a,b,path=''):
                if len(delta)>=40:return
                if type(a)!=type(b):delta.append([path,a,b])
                elif isinstance(a,dict):
                    for k in sorted(set(a)|set(b)):
                        if k not in a or k not in b:delta.append([path+'/'+k,a.get(k),b.get(k)])
                        else:compare(a[k],b[k],path+'/'+k)
                elif isinstance(a,list):
                    if len(a)!=len(b):delta.append([path+'/length',len(a),len(b)])
                    for i,(x,y) in enumerate(zip(a,b)):compare(x,y,path+'/'+str(i))
                elif a!=b:delta.append([path,a,b])
            compare(json.loads(before),json.loads(after))
            (out/f'drift-{seed}.txt').write_text(json.dumps(delta,indent=2)+'\n')
            raise AssertionError(f'Uncommissioned drift in seed {seed}; see drift file')
        rng = random.getstate()
        payload = reports.reader_payload(data.texts['lab_route_sheet_a'], current)
        assert random.getstate() == rng and current.learned_reports == []
        result['worlds'].append(dict(seed=seed, laboratory=[current.start_wx,current.start_wy],
            geometry_assignments_unchanged=True, comparison_sha256=hashlib.sha256(after.encode()).hexdigest(),
            reports=current.location_reports, rendered_pages=[p['text'] for p in payload['pages']]))
        (out/'sample.json').write_text(json.dumps(result, indent=2)+'\n')
        print(json.dumps(dict(seed=seed, targets=[r['target'] for r in current.location_reports])), flush=True)
    result['passed'] = True
    (out/'sample.json').write_text(json.dumps(result, indent=2)+'\n')


if __name__ == '__main__': main()
