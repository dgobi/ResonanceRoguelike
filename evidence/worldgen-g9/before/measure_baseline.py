"""Independent retained G8 measure, bound to the freshly captured full plans."""
from pathlib import Path
import hashlib
import json
import sys
ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).resolve().parent
sys.path[:0]=[str(OUT/'review-package/evidence/network'),str(ROOT/'roguelike')]
from measure_country_network import measure
from check_macro_corridors import physical,physical_distance
rows=[]
for seed in (0,20261023,29417):
    path=OUT/f'baseline/results/plan-{seed}.json';raw=path.read_bytes();plan=json.loads(raw)
    assert plan==json.loads((ROOT/f'evidence/worldgen-g8/final-b/diagnostic/results/plan-{seed}.json').read_text())
    row=measure(plan);cells=physical(plan)
    for pair in row['terminal_pairs']:pair['physical_steps']=physical_distance(cells,tuple(pair['a_xy']),tuple(pair['b_xy']))
    row.update(fresh_plan_sha256=hashlib.sha256(raw).hexdigest(),retained_final_b_plan_equal=True);rows.append(row)
(OUT/'network-baseline.json').write_text(json.dumps(dict(plans=rows,source='b94a0b0db3685f7484632701f0486f3b0b79101e',timing_scope='G8 diagnostic/journey executed unchanged in production checkout. Lightweight documentation tests/build/browser checks overlapped part of this pre-edit capture; exact timing comparisons require serial final measurement. Geometry and state identities were checked unchanged.'),indent=2)+'\n')
print('Three genuine G8 plans measured, all retained plans equal')
