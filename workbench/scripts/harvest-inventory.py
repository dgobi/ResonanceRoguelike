"""Executable original-source harvest admission, not a creature ID allowlist."""
import contextlib,io,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'roguelike'))
from engine.data_loader import DataLoader
from engine.content_authoring import definition_sources
from engine import creature_authoring as a
with contextlib.redirect_stdout(io.StringIO()):data=DataLoader(str(ROOT/'roguelike/data'))
indexes=a.indexes_for(data.root);rows=[]
for identifier,sources in sorted(indexes['entities'].items()):
    for source in sources:
        if '/creatures/' not in source['path']:continue
        cap=a.capability(source['definition'],source['path'],source['pointer'])
        diagnostics,refs=a.validate_definition(source['definition'],data,source['path'],indexes)
        valid=not any(d['severity']=='error' for d in diagnostics)
        rows.append(dict(id=identifier,path=source['path'],pointer=source['pointer'],harvest_editable=valid and cap['harvest_editable'],
            operations=cap['operations'] if valid else [],reason=cap['harvest_reason'],special_binding=cap['special_binding'],
            profile_present='butcher_yield' in source['definition'],diagnostics=diagnostics,dependencies=refs))
result=dict(contract=a.CONTRACT,total=len(rows),harvest_admitted=sum(r['harvest_editable'] for r in rows),
    existing_tables=sum(r['harvest_editable'] and r['profile_present'] for r in rows),rules=a.RULES,rows=rows)
assert result['harvest_admitted']==11 and result['existing_tables']==9
out=Path(sys.argv[1]);out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes((json.dumps(result,indent=2,ensure_ascii=False)+'\n').encode())
print(json.dumps({k:v for k,v in result.items() if k not in ('rules','rows')}))
