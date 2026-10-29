"""Executable source/authority coverage inventory; never opens campaign trees."""
import contextlib,hashlib,io,json,sys
from pathlib import Path
root=Path(__file__).resolve().parents[2];sys.path.insert(0,str(root/'roguelike'))
from engine.building_authoring import capability,source_problems,load_authoring_data
from generation.structure_contract import read_document
with contextlib.redirect_stdout(io.StringIO()):data=load_authoring_data(root/'roguelike/data')
rows=[]
for p in sorted((root/'roguelike/data/buildings').rglob('*.json')):
    raw=read_document(p);path=p.relative_to(root).as_posix();cap=capability(raw,path)
    problems=source_problems(raw,data,path,root/'roguelike/data') if cap['editable'] else []
    rows.append(dict(path=path,sha256=hashlib.sha256(p.read_bytes()).hexdigest(),id=raw.get('id') if isinstance(raw,dict) else None,
        category=p.parent.name,route='plaza' if p.parent.name=='plaza' else 'ordinary_building',editable=cap['editable'] and not problems,
        reason=cap['reason'],authority_diagnostics=problems,placement_present=isinstance(raw,dict) and 'placement' in raw,active_decor_layer=isinstance(raw,dict) and 'decor_layer' in raw))
ordinary=[r for r in rows if r['route']=='ordinary_building']
result=dict(scope='Current executable source coverage inventory, not an ID whitelist or all-source production-orientation verdict.',ordinary=len(ordinary),plazas=len(rows)-len(ordinary),
    placement_profiles=sum(r['placement_present'] for r in ordinary),active_decor_layers=sum(r['active_decor_layer'] for r in ordinary),sources=rows)
assert result['ordinary']==58 and result['plazas']==2 and all(r['editable'] for r in ordinary)
out=Path(sys.argv[1]) if len(sys.argv)>1 else root/'workbench/.artifacts/w5p/building-inventory.json';out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in result.items() if k!='sources'}))
