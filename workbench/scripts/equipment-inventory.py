"""Executable source/operation inventory for the one registered item family."""
import contextlib, io, json, sys
from collections import Counter
from pathlib import Path
root=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(root/'roguelike'))
from engine.data_loader import DataLoader
from engine.content_authoring import definition_sources
from engine import item_authoring as a
with contextlib.redirect_stdout(io.StringIO()):data=DataLoader(str(root/'roguelike/data'))
sources=definition_sources(data.root,'items');rows=[]
for identifier,locations in sorted(sources.items()):
    for row in locations:
        cap=a.capability(row['definition'],row['path'],row['pointer'])
        collisions=[s for k,ss in sources.items() if k.casefold()==identifier.casefold() for s in ss]
        eligible=cap['editable'] and len(collisions)==1
        rows.append(dict(id=identifier,path=row['path'],pointer=row['pointer'],equipment_class=cap.get('equipment_class'),supply_class=cap['supply_class'],
            operations=['edit','variant'] if eligible else [],reason=cap['reason'] if len(collisions)==1 else 'Ambiguous case-insensitive identity.',
            binding=a.use_binding(row['definition']),publication_diagnostics=a.validate_definition(row['definition'],data,row['path'],sources)))
result=dict(contract=a.CONTRACT,total=len(rows),admitted=sum(bool(r['operations']) for r in rows),classes=dict(Counter(r['supply_class'] for r in rows if r['operations'])),rows=rows)
out=Path(sys.argv[1]);out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes((json.dumps(result,indent=2,ensure_ascii=False)+'\n').encode())
print(json.dumps({k:v for k,v in result.items() if k!='rows'}))
