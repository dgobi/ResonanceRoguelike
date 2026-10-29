"""Executable native pool capability inventory and optional frozen-seed comparison."""
import contextlib,hashlib,io,json,random,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'roguelike'))
from engine.data_loader import DataLoader
from engine.content_authoring import families
from engine.pool_authoring import authoring_context
from engine.item_factory import ItemFactory
from engine.loot_roller import roll_pool
with contextlib.redirect_stdout(io.StringIO()):data=DataLoader(str(ROOT/'roguelike/data'))
family=next(f for f in families() if f.id=='pool');rows=[]
for source in family.discover(ROOT):
    path=ROOT/source['path'];raw=json.loads(path.read_bytes());digest=hashlib.sha256(path.read_bytes()).hexdigest()
    context=authoring_context(raw,data,source['path'],data.root,{},digest)
    rows.append(dict(**source,working_sha256=digest,rows=len(raw.get('items',[])),count_representation=raw.get('roll_count','omitted'),
        capability=context['records'][0]['capability'],diagnostics=context['records'][0]['diagnostics']))
result=dict(contract='contextual-loot-1',production_route=family.route,total=len(rows),editable=sum(r['editable'] for r in rows),rows=rows)
assert result['total']==result['editable']==17
assert all(not any(d['severity']=='error' for d in r['diagnostics']) for r in rows)
if len(sys.argv)>2:
    before=json.loads(Path(sys.argv[2]).read_bytes())
    after={k:[[i.item_id for i in roll_pool(v,ItemFactory(data),random.Random(seed))] for seed in range(100)] for k,v in sorted(data.loot_pools.items())}
    assert before==after
    result['seeded_compatibility']=dict(pools=len(after),seeds_per_pool=100,samples=1700,identical=True,before_sha256=hashlib.sha256(Path(sys.argv[2]).read_bytes()).hexdigest(),
        scope='Actual shipped definitions/factory and random.Random(seed), requested-count and ordered item-ID outputs. Arithmetic-boundary controls are separate focused regressions.')
out=Path(sys.argv[1]);out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes((json.dumps(result,indent=2,ensure_ascii=False)+'\n').encode())
print(json.dumps({k:v for k,v in result.items() if k!='rows'}))
