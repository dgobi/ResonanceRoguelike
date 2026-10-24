"""Pre-edit, genuine G8 checkpoint and portable-wiki defect reproduction."""
import contextlib
import gzip
import hashlib
import importlib.metadata
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest
import zipfile
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).resolve().parent
sys.path[:0]=[str(ROOT/'roguelike'),str(ROOT/'tools'),str(ROOT/'tools/critical_fix_regressions/tests'),str(ROOT/'Resonance_Wiki_Maintenance')]
os.environ.update(SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy',PYGAME_HIDE_SUPPORT_PROMPT='1')

def write(name,value):
    p=OUT/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')

def main():
    from verify_b3 import source_manifest
    from g7_evidence import reconciliation
    source=source_manifest();head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    assert head=='b94a0b0db3685f7484632701f0486f3b0b79101e'
    write('start.json',dict(head=head,branch=subprocess.check_output(['git','branch','--show-current'],cwd=ROOT,text=True).strip(),status=subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True),remotes=subprocess.check_output(['git','remote','-v'],cwd=ROOT,text=True),interpreter=sys.executable,python=sys.version,libraries={n:importlib.metadata.version(n) for n in ('pygame','tcod','numpy')},source=source,inputs=reconciliation(source,head,OUT)))
    package=OUT/'review-package';manifest=json.loads((package/'MANIFEST.json').read_text())
    for row in manifest['files']:
        raw=(package/row['path']).read_bytes();assert len(raw)==row['bytes'] and hashlib.sha256(raw).hexdigest()==row['sha256']
    with zipfile.ZipFile('C:/Users/dango/Downloads/Resonance_G8_Review_G9_Brief_20261024.zip') as z:assert z.testzip() is None
    write('package-verification.json',dict(passed=True,members=len(manifest['files']),manifest_sha256=hashlib.sha256((package/'MANIFEST.json').read_bytes()).hexdigest()))
    from test_wiki_inputs import WikiInputs
    from wiki_inputs import reviewed_inputs
    fixture=WikiInputs();fixture.setUp()
    try:
        guide=fixture.repo/'guide.md';original=guide.read_bytes();guide.write_bytes(original.replace(b'\r\n',b'\n').replace(b'\n',b'\r\n'))
        fixture.bind();guide.write_bytes(original.replace(b'\r\n',b'\n'))
        canonical=reviewed_inputs(fixture.repo,fixture.config)
        try:fixture.check();error=None
        except ValueError as exc:error=str(exc)
        assert error and 'stale source' in error
        deep=ROOT/'roguelike/data/languages/deep_tongue.json'
        if not deep.exists():deep=next((ROOT/'roguelike/data').rglob('deep_tongue.json'))
        raw=deep.read_bytes();payload=deep.read_text(encoding='utf-8-sig').encode('utf-8')
        write('wiki-original-defects.json',dict(canonical_source_accepted=True,drift_error=error,source_scope=canonical['scope'],raw_bytes=len(raw),download_bytes=len(payload),raw_sha256=hashlib.sha256(raw).hexdigest(),download_sha256=hashlib.sha256(payload).hexdigest(),missing_contract_input='test_wiki_inputs.py'))
    finally:fixture.doCleanups()
    from test_generation_g8_lifecycle import G8Lifecycle
    from generation.placement import digest
    from g1_support import fingerprint
    import pygame
    G8Lifecycle.setUpClass();case=G8Lifecycle();case.setUp()
    try:
        e=case.boot();e.debug=False;e.player_invincible=True;e.player.inventory.capacity=100
        plan=e.world_map.plan;assert plan['version']==6 and plan['generation_revision']=='wg8'
        town=next(s for s in plan['settlements'] if s['form']=='grid');common=next(c for c in plan['public_spaces'] if c['owner']==town['id'])
        visited=town['members'][0];pending=town['members'][-1];case.visit(e,visited)
        for _ in range(8):e._handle_key_local(pygame.K_z)
        with patch.object(type(e),'_advance_turn',lambda e:e.world_time.advance()):
            stone,prayer=[(a%80,b%43) for a,b in common['furnishing']];case.interact(e,stone);case.interact(e,prayer)
            assert stone in e.local_map.interacted_waystones
            assert any(getattr(i,'text_id',None)=='waystone_prayer_a' for i in e.player.inventory.items)
            e.local_map.set_tile(2,2,'mud',True,True)
            compound=next(s for s in plan['sites'] if s['kind']=='compound');case.visit(e,compound['chunk'])
            containers=list(e.local_map.container_state.items());assert len(containers)>=2
            original_second=repr(containers[1][1]);containers[0][1]['items'].clear();assert repr(containers[1][1])==original_second
            owners={tuple(xy) for s in plan['settlements'] for xy in s['members']}|{tuple(s['chunk']) for s in plan['sites']}
            roads=sorted({(p[0]//80,p[1]//43) for r in plan['routes'] if r['kind']=='country' for p in r['points']}-owners-{(e.world_map.start_wx,e.world_map.start_wy)})
            country_visited,country_pending=roads[0],roads[-1];case.visit(e,country_visited);e.local_map.set_tile(2,2,'mud',True,True)
            e._handle_key_local(pygame.K_F5);assert e.save_manager.last_error is None
        checkpoint=e.save_manager.checkpoint_path();dest=OUT/'witness';dest.mkdir(exist_ok=True)
        with zipfile.ZipFile(dest/'authentic-g8-checkpoint.zip','w',zipfile.ZIP_DEFLATED) as z:
            for p in sorted(checkpoint.rglob('*')):
                if p.is_file():z.write(p,p.relative_to(checkpoint).as_posix())
        scenes=[]
        for xy in [visited,compound['chunk'],country_visited]:
            m,actors=e._prepare_destination(*xy);scenes.append(dict(chunk=xy,fingerprint=fingerprint(m,actors),provenance=m.plan_provenance,creator=m.generation_revision))
        (dest/'g8-plan.json.gz').write_bytes(gzip.compress(json.dumps(plan,sort_keys=True,separators=(',',':')).encode(),mtime=0))
        write('witness/g8-witness.json',dict(head=head,plan_identity=digest(plan),scenes=scenes,pending=pending,country_pending=country_pending,common=common,mutations=dict(waystone=stone,prayer_taken=True,first_compound_container_emptied=containers[0][0],second_container_preserved=containers[1][0],terrain='mud at 2,2'),controls='Fixture teleports and interaction positioning; eight ordinary native updates then paused AI/survival; invincible player; production interaction/F5 handlers; direct terrain and first child container mutations explicitly labeled.',files={p.relative_to(checkpoint).as_posix():dict(bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in checkpoint.rglob('*') if p.is_file()}))
    finally:case.doCleanups()
    assert source==source_manifest()
    write('capture-result.json',dict(passed=True,source_stable=True,head=head))
    print('Genuine G8 witness and original wiki defects captured',flush=True)

if __name__=='__main__':main()
