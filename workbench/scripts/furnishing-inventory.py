"""Executable disclosure of every saved decor record's direct-room admission."""
import contextlib,io,json,sys
from pathlib import Path
root=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(root/'roguelike'))
from engine.data_loader import DataLoader
from generation.authored_decor import admission
with contextlib.redirect_stdout(io.StringIO()):data=DataLoader(str(root/'roguelike/data'))
rows=[dict(index=n,id=r.get('id'),**admission(data,r.get('id'))) for n,r in enumerate(data.decorative_sources)]
result=dict(contract='authored-room-2',registry='roguelike/data/decoratives.json',total=len(rows),
            admitted=sum(r['supported'] for r in rows),records=rows,
            sources=['generation/authored_decor.py','engine/engine.py:_update_fov, _dispatch_interactable, _can_place_on_fire',
                     'engine/vine_system.py','rendering/renderer.py:_draw_decor_to'])
if len(sys.argv)>1:
    p=Path(sys.argv[1]);p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((json.dumps(result,indent=2)+'\n').encode())
else:print(json.dumps(result,indent=2))
