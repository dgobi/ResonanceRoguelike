"""Executable read-only inventory of source-resolved recipe admission."""
import contextlib, hashlib, io, json, sys
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'roguelike'))
from engine.data_loader import DataLoader
from engine.content_authoring import families
from engine.recipe_authoring import authoring_context, CONTRACT
with contextlib.redirect_stdout(io.StringIO()): data=DataLoader(str(ROOT/'roguelike/data'))
family=next(f for f in families() if f.id=='recipe')
rows=[]
for source in family.discover(ROOT):
    path=ROOT/source['path']; raw=json.loads(path.read_bytes())
    context=authoring_context(raw,data,source['path'],ROOT/'roguelike/data',{},hashlib.sha256(path.read_bytes()).hexdigest())
    cap=context['records'][0]['capability']
    rows.append(dict(id=source['id'],path=source['path'],execution_class=cap['execution_class'],
        processing_source=raw.get('processing_source'),operations=family.operations_for(context),reason=cap['reason'],
        diagnostics=context['records'][0]['diagnostics'],sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
result=dict(contract=CONTRACT,total=len(rows),admitted=sum(bool(r['operations']) for r in rows),
    classes=dict(Counter(r['processing_source'] or 'immediate' for r in rows if r['operations'])),sources=rows)
assert result['total']==18 and result['admitted']==15,result
target=Path(sys.argv[1]);target.parent.mkdir(parents=True,exist_ok=True)
target.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
print(json.dumps({k:v for k,v in result.items() if k!='sources'}))
