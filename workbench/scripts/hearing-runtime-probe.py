"""Runtime threshold from the exact native-published creature, staged geometry."""
import contextlib
import io
import json
from pathlib import Path
import sys

root=Path(sys.argv[1]); expected=int(sys.argv[2])
sys.path[:0]=[str(root/'roguelike'),str(Path(__file__).resolve().parents[2]/'tools/critical_fix_regressions/tests')]
from test_effect_persistence import make_engine
from engine.data_loader import DataLoader
from engine.sound import emit
with contextlib.redirect_stdout(io.StringIO()):
    data=DataLoader(str(root/'roguelike/data')); e=make_engine(data)
a=e.creature_factory.spawn('hollow_revenant',12,12); e.entities.append(a)
e.player.x,e.player.y=40,40
assert a.perception.hearing_radius==expected
heard=emit(e,16,12,'flint')
assert heard==int(expected>=4), (heard,expected)
assert getattr(a,'_last_known_px',None) is None
print(json.dumps(dict(hearing=expected,cost=4,heard=heard,interest=a.ai.sound_interest,
                      source=str(root/'roguelike/data/entities/creatures/hollow_revenant.json'),
                      scope='Native saved/reopened definition, real factory and hearing; controlled open geometry.')))
