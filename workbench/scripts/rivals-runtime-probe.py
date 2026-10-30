"""Targeting from exact native-published/reopened definitions, controlled grass."""
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch

root=Path(sys.argv[1]);faction=sys.argv[2];hostile=json.loads(sys.argv[3])
sys.path[:0]=[str(root/'roguelike'),str(Path(__file__).resolve().parents[2]/'tools/critical_fix_regressions/tests')]
from test_effect_persistence import make_engine
from engine.data_loader import DataLoader
with tempfile.TemporaryDirectory(prefix='g21-published-rivals-') as saves,patch('engine.save_manager.SAVE_DIR',Path(saves)),contextlib.redirect_stdout(io.StringIO()):
    data=DataLoader(str(root/'roguelike/data'));e=make_engine(data)
    a=e.creature_factory.spawn('highland_bandit',12,12);b=e.creature_factory.spawn('heath_stalker',16,12)
    e.entities += [a,b];e.player.x,e.player.y=40,40;e.reality_bubble.update(0,0,e.world_map)
    assert (a.perception.faction,a.perception.hostile_to)==(faction,hostile)
    e._advance_turn()
    actual=[bool(getattr(x.ai,'local_target',None)) for x in (a,b)]
    expected=['stalker' in hostile,faction in b.perception.hostile_to]
    assert actual==expected,(actual,expected)
    assert all(getattr(x,'_last_known_px',None) is None for x in (a,b))
print(json.dumps(dict(faction=faction,hostile_to=hostile,selected_rival=actual,turn=e.world_time.turn,
                     positions=[[x.x,x.y] for x in (a,b)],scope='Native saved/reopened source -> real factory -> charged ordinary AI phase; controlled grass, not a natural encounter.')))
