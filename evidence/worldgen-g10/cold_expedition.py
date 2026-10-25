"""Independent fresh-process startup of the actual explored expedition checkpoint."""
import argparse
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'roguelike'),str(ROOT/'tools'),str(ROOT/'tools/critical_fix_regressions/tests')]
os.environ.update(SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy',PYGAME_HIDE_SUPPORT_PROMPT='1')


def main():
    p=argparse.ArgumentParser();p.add_argument('--expedition',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    out=a.output.resolve();out.parent.mkdir(parents=True,exist_ok=True)
    report=json.loads((a.expedition/'expedition.json').read_text())
    archive=a.expedition/'explored-checkpoint.zip'
    assert report['passed'] and hashlib.sha256(archive.read_bytes()).hexdigest()==report['checkpoint_sha256']
    from verify_g10 import inputs
    source=inputs()
    import pygame
    import main as game
    from engine.engine import Engine
    from engine.save_manager import _serialize_player
    from generation.placement import digest
    from g1_support import fingerprint
    with tempfile.TemporaryDirectory(prefix='resonance-g10-actual-cold-') as tmp,patch('engine.save_manager.SAVE_DIR',Path(tmp)):
        slot=Path(tmp)/'slot_0'
        with zipfile.ZipFile(archive) as z:
            assert z.testzip() is None
            assert all(not Path(n).is_absolute() and '..' not in Path(n).parts for n in z.namelist())
            manifest=json.loads(z.read('manifest.json'))
            saved_player=json.loads(z.read('player.json'))
            z.extractall(slot/'generations'/manifest['generation'])
        (slot/'HEAD.json').write_text(json.dumps(dict(checkpoint_version=1,current=manifest['generation'],previous=None)))
        captured=[];old=Path.cwd()
        try:
            os.chdir(ROOT/'roguelike')
            with patch.object(Engine,'run',lambda e:captured.append(e)),patch.object(game,'generate_world',side_effect=AssertionError('cold startup replanned')):
                game.main()
        finally:os.chdir(old)
        e=captured[0];e.debug=False
        assert e.player.fighter.hp==report['final']['hp']
        assert e.player.needs.thirst==report['final']['thirst']
        assert [i.item_id for i in e.player.inventory.items]==report['final']['inventory']
        assert (e.world_x,e.world_y)==tuple(report['final']['chunk'])
        assert not e.player_invincible
        first=digest(_serialize_player(e));provenances=[]
        assert first==digest(saved_player), 'fresh startup must reproduce the complete saved player/transport/RNG state'
        for key,expected in report['visited'].items():
            import ast
            xy=ast.literal_eval(key);m,actors=e._prepare_destination(*xy)
            assert fingerprint(m,actors)==expected
            provenances.append(dict(chunk=xy,surface=m.surface_provenance))
        pending=report['pending'];assert fingerprint(*e._prepare_destination(*pending['chunk']))==pending['fingerprint']
        e._handle_key_local(pygame.K_F9)
        assert digest(_serialize_player(e))==first
        for key,expected in report['visited'].items():
            import ast
            assert fingerprint(*e._prepare_destination(*ast.literal_eval(key)))==expected
        assert fingerprint(*e._prepare_destination(*pending['chunk']))==pending['fingerprint']
    assert inputs()==source
    result=dict(passed=True,pid=os.getpid(),command=sys.argv,interpreter=sys.executable,python=sys.version,
        tested_input_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),source=source,
        archive_sha256=report['checkpoint_sha256'],normal_main_startup=True,replanning_forbidden=True,
        player_identity=first,complete_saved_player_transport_and_rng_equal=True,visited_terrain_mutations_actor_state_and_pending_equal=True,F9=True,
        provenances=provenances,source_stable=True)
    out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')


if __name__=='__main__':main()
