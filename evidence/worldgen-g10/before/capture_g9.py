"""Run only on the genuine unmodified G9 runtime, before G10 terrain edits."""
from collections import Counter
import contextlib
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import random
import subprocess
import sys
import tempfile
import time
import zipfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
sys.path[:0] = [str(ROOT/'roguelike'), str(ROOT/'tools'), str(ROOT/'tools/critical_fix_regressions/tests')]
os.environ.update(SDL_VIDEODRIVER='dummy', SDL_AUDIODRIVER='dummy', PYGAME_HIDE_SUPPORT_PROMPT='1')


def write(path, value):
    p = OUT/path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(value, indent=2)+'\n', encoding='utf-8')


def main():
    from verify_b3 import source_manifest
    from generation.placement import digest
    from test_effect_persistence import load_data, make_engine
    from generation.world_gen import generate_world
    from generation.world_plan import slice_plan
    from engine.scene_generation import create_surface
    from engine.save_manager import _serialize_world
    from world.world_map import WorldMap
    from g1_support import fingerprint
    from g10_play import boot, status, leave_lab, walk, interact, render
    import pygame
    source = source_manifest()
    head = subprocess.check_output(['git','rev-parse','HEAD'], cwd=ROOT, text=True).strip()
    assert head == 'f9fe901417b360bc1fda84835e0a793eaac2f6df'
    write('start.json', dict(head=head, source=source, python=sys.version, interpreter=sys.executable,
        status=subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True),
        remote=subprocess.check_output(['git','remote','-v'],cwd=ROOT,text=True)))
    package = OUT/'review-package'
    manifest = json.loads((package/'MANIFEST.json').read_text())
    for row in manifest['members']:
        raw = (package/row['path']).read_bytes()
        assert len(raw) == row['bytes'] and hashlib.sha256(raw).hexdigest() == row['sha256']
    write('package-verification.json', dict(passed=True,members=len(manifest['members'])))
    data=load_data()
    with tempfile.TemporaryDirectory(prefix='resonance-g10-preflight-') as tmp, patch('engine.save_manager.SAVE_DIR', Path(tmp)):
        e=boot(tmp)
        preflight=dict(start=status(e), inputs=[])
        try:
            leave_lab(e, preflight['inputs'])
            stone=next(xy for xy,value in e.local_map.decor.items() if value=='waystone_plinth')
            interact(e, stone, preflight['inputs'])
            assert stone in e.local_map.interacted_waystones
            preflight.update(passed=True, final=status(e), waystone=stone)
        except Exception as exc:
            preflight.update(passed=False, final=status(e), error=repr(exc))
        render(e, OUT/'preflight-normal-fov.png', 'G9 normal-start preflight')
        preflight['controls']='Normal start, native AI, survival and FOV; invincibility off; known-seed BFS script avoids occupied cells; no injected supplies or positioning.'
        write('preflight.json',preflight)
        # The checkpoint witness has the real preflight waystone mutation. A second
        # wilderness scene is prepared separately as controlled compatibility data.
        xy=(e.world_map.start_wx+1,e.world_map.start_wy)
        pending=(xy[0],xy[1]+1)
        e._prepare_destination(*xy)
        e._handle_key_local(pygame.K_F5)
        assert e.save_manager.last_error is None
        checkpoint=e.save_manager.checkpoint_path()
        dest=ROOT/'tools/critical_fix_regressions/fixtures/g10'
        dest.mkdir(parents=True,exist_ok=True)
        with zipfile.ZipFile(dest/'authentic-g9-checkpoint.zip','w',zipfile.ZIP_DEFLATED) as z:
            for p in sorted(checkpoint.rglob('*')):
                if p.is_file():z.write(p,p.relative_to(checkpoint).as_posix())
        scenes=[]
        for key in [(e.world_map.start_wx,e.world_map.start_wy),xy]:
            m,actors=e._prepare_destination(*key)
            scenes.append(dict(chunk=key,fingerprint=fingerprint(m,actors),provenance=m.plan_provenance))
        pending_rows=[]
        for key in [pending,(72,103)]:
            assert not e.world_map.get(*key).visited
            r=create_surface(e.world_map,e.world_map.get(*key),data,e.item_factory,e.creature_factory,80,43)
            pending_rows.append(dict(chunk=key,fingerprint=fingerprint(r.local_map,r.actors),provenance=r.local_map.plan_provenance))
        binding=dict(head=head,source=source,plan_identity=digest(e.world_map.plan),scenes=scenes,pending=pending_rows,
            mutation=dict(waystone=preflight.get('waystone'),interacted=preflight.get('passed')),
            controls='Real normal-start preflight mutation; one additional prepared/cache-only scene. Pending reference scenes generated directly after checkpoint, without publishing metadata or visiting.',
            files={p.relative_to(checkpoint).as_posix():dict(bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in checkpoint.rglob('*') if p.is_file()})
        (dest/'g9-witness.json').write_text(json.dumps(binding,indent=2)+'\n')
    if '--witness-only' in sys.argv:
        assert preflight['passed'], preflight
        write('witness-capture.json',dict(passed=True,head=head,source_stable=all(source_manifest().get(k)==v for k,v in source.items() if '/fixtures/g10/' not in k)))
        return
    rows=[]
    for seed in (0,20261023,29417):
        w=WorldMap(128,128);w.seed=seed
        t=time.perf_counter();generate_world(w,data,random.Random(seed));elapsed=time.perf_counter()-t
        serialized=_serialize_world(w)
        (OUT/f'world-{seed}.json.gz').write_bytes(gzip.compress(json.dumps(serialized,sort_keys=True,separators=(',',':')).encode(),mtime=0))
        record=dict(seed=seed,plan_identity=digest(w.plan),world_identity=digest(serialized),planning_seconds=elapsed,scenes_at_plan_completion=0,scenes=[])
        assert not any(c.visited or c.generated if hasattr(c,'generated') else c.visited for c in w.chunks.values())
        if seed==20261023:
            e=make_engine(data);e.world_map=w
            for biome in ('forest','plains','heath','swamp','drowned_wood','ash_wastes','mountain','deep_mountain'):
                choices=sorted((c for c in w.chunks.values() if c.biome_id==biome and not c.submaps and not c.is_river),key=lambda c:(abs(c.wx-w.start_wx)+abs(c.wy-w.start_wy),c.wx,c.wy))
                c=next(c for c in choices if not any(slice_plan(w.plan,c.wx,c.wy).get(k) for k in ('routes','waters','crossings','placements','sites','paths','public_spaces')))
                t=time.perf_counter();r=create_surface(w,c,data,e.item_factory,e.creature_factory,80,43);seconds=time.perf_counter()-t
                e.local_map=r.local_map;e.entities=[e.player,*r.actors];e.player.x,e.player.y=r.spawn;e.world_x,e.world_y=c.wx,c.wy
                image=f'{biome}-{c.wx}-{c.wy}.png';render(e,OUT/image,f'G9 {biome} ({c.wx},{c.wy})',revealed=True)
                record['scenes'].append(dict(biome=biome,chunk=[c.wx,c.wy],seconds=seconds,fingerprint=fingerprint(r.local_map,r.actors),terrain=dict(Counter(r.local_map.tiles['terrain'].flat)),decor=dict(Counter(r.local_map.decor.values())),image=image))
        rows.append(record)
    after=source_manifest()
    assert all(after.get(k)==v for k,v in source.items() if '/fixtures/g10/' not in k)
    write('baseline.json',dict(passed=True,source_stable=True,head=head,runs=rows))
    print(json.dumps(dict(passed=True,preflight=preflight['passed'],baseline_seeds=len(rows))))


if __name__=='__main__':
    with (OUT/'capture-output.txt').open('w',encoding='utf-8') as log,contextlib.redirect_stdout(log):main()
