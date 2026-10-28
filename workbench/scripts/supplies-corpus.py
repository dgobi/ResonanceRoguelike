"""Executable inventory of original-source item permissions; read-only."""
import contextlib, hashlib, io, json, sys
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'roguelike'))
from engine.data_loader import DataLoader
from engine.content_authoring import families
from engine import item_authoring
with contextlib.redirect_stdout(io.StringIO()):data=DataLoader(str(ROOT/'roguelike/data'))
family=next(f for f in families() if f.id=='item')
rows=[]
for row in family.discover(ROOT):
    raw=data.items.get(row['id'],{})
    cap=item_authoring.capability(raw,row['path'],row['pointer'])
    rows.append(dict(id=row['id'],path=row['path'],pointer=row['pointer'],category=row['category'],
        supply_class=cap['supply_class'],operations=['edit','variant'] if row['editable'] else [],reason=cap['reason'],
        sha256=hashlib.sha256((ROOT/row['path']).read_bytes()).hexdigest()))
result=dict(contract=item_authoring.CONTRACT,total=len(rows),admitted=sum(bool(r['operations']) for r in rows),
    classes=dict(Counter(r['supply_class'] for r in rows if r['operations'])),sources=rows)
target=Path(sys.argv[1]);target.parent.mkdir(parents=True,exist_ok=True);target.write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in result.items() if k!='sources'}))
