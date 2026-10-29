"""Game-domain eligibility and compiler/reference checks for ordinary authored rooms.

No editor descriptors or UI imports. Construction remains lazy.
"""
import json
from pathlib import Path, PurePosixPath
from generation.structure_contract import compile_structure, StructureError, read_document, Validator
from engine.definition_sources import definition_sources

CONTRACT = "authored-room-2"
TEMPLATE = "roguelike/docs/examples/g17_authored_creature_room.json"
ROOT = "roguelike/data/layouts/"
PRODUCTION_ROUTE = "authored_submap"
RECORD_FIELDS = {'creature': {'x', 'creature_id', 'y'}, 'item': {'x', 'item_id', 'text_id', 'y'}, 'container': {'x', 'loot_pools', 'y', 'decor_id'}, 'decor': {'x', 'y', 'decor_id'}}

def matches(path):
    return path == TEMPLATE or (PurePosixPath(path).parent.as_posix() == ROOT.rstrip("/") and path.endswith(".json"))


def staging_path(asset):
    return "layouts/"+Path(asset).name


def discover_paths(root):
    paths=list((root/ROOT).glob("*.json"))
    if (root/TEMPLATE).is_file(): paths.append(root/TEMPLATE)
    return paths


def source_index(data_root):
    result = {}
    paths = list((data_root / "layouts").glob("*.json"))
    if (data_root.parent.parent / TEMPLATE).is_file(): paths.append(data_root.parent.parent / TEMPLATE)
    for path in sorted(paths):
        try: raw = read_document(path)
        except StructureError: continue
        if isinstance(raw, dict) and isinstance(raw.get("id"), str):
            result.setdefault(raw["id"], []).append(dict(path=TEMPLATE if path.name==Path(TEMPLATE).name and path.parent.name=="examples" else ROOT+path.name, pointer="", definition=raw))
    return result


def locations(index, identifier):
    return [row for key, rows in index.items() if isinstance(identifier,str) and key.casefold()==identifier.casefold() for row in rows]


def capability(raw, path, pointer=""):
    reason = ""
    if not matches(path) or pointer: reason = "Requires one object directly in layouts/ or the exact G17 template."
    elif not isinstance(raw,dict): reason = "Requires a single room object."
    elif str(raw.get("id", "")).casefold()=="starting_lab" or Path(path).name.casefold()=="starting_lab.json": reason = "The starting laboratory is protected by identity and source path."
    elif not isinstance(raw.get("layers"),list) or not raw["layers"] or any(not isinstance(r,str) for r in raw["layers"]): reason = "Requires rectangular terrain string layers."
    elif not isinstance(raw.get("player_start"),dict): reason = "Requires an explicit player_start."
    elif not isinstance(raw.get("special_tiles",[]),list) or any(not isinstance(s,dict) or s.get("type",s.get("kind")) not in RECORD_FIELDS for s in raw.get("special_tiles",[])): reason = "Only direct item, container, decor and creature records are supported. Weighted, scene and deferred specials remain inspect-only."
    operations = [] if reason else ["variant"] if path==TEMPLATE else ["edit","variant"]
    return dict(editable=not reason, reason=reason, operations=operations, shape="direct room object")


def issue(path, code, field, message, severity="error"):
    return dict(severity=severity,code=code,path=path,asset="",field=field,message=message,correction="Correct this source field or choose a unique saved dependency, then validate again.")


def catalog(data, data_root):
    indexes = {key:definition_sources(data_root, folder, ("text_item_map.json",) if key=="texts" else ()) for key,folder in (("items","items"),("texts","texts"),("creatures","entities"),("pools","loot_pools"))}
    choices = {}
    from engine.item_factory import ItemFactory
    factory = ItemFactory(data)
    for key,index in indexes.items():
        rows=[]
        for identifier, entries in sorted(index.items()):
            unique=len(locations(index,identifier))==1; entry=entries[0]
            supported=unique and identifier in getattr(data, {"creatures":"entities","pools":"loot_pools"}.get(key,key))
            readable=False
            if key=="creatures":
                v=Validator(data,"<catalogue>",identifier,PRODUCTION_ROUTE)
                v.special(dict(type="creature",x=0,y=0,creature_id=identifier),"special_tiles[0]",1,1)
                supported=supported and "/entities/creatures/" in entry["path"] and not any(d.severity=="error" for d in v.diagnostics)
            if key=="items" and supported:
                try: readable=getattr(factory.create(identifier,0,0),"on_use",None)=="read"
                except (ValueError,KeyError,TypeError): supported=False
            rows.append(dict(id=identifier,name=str(entry["definition"].get("name",entry["definition"].get("title",identifier))),path=entry["path"],paths=[e["path"] for e in entries],resolved=supported,readable=readable))
        choices[key]=rows
    # Decor is a list registry, not recursive object-file discovery.
    decor_rows=json.loads((data_root/"decoratives.json").read_text(encoding="utf-8"))
    from generation.authored_decor import admission
    decor={k:dict(name=str(v.get("name",k.replace('_',' '))),description=v.get('description',''),container=v.get("container") is True,blocks_movement=bool(v.get("blocks_movement",False)),path="roguelike/data/decoratives.json",resolved=sum(1 for r in decor_rows if isinstance(r,dict) and str(r.get("id","")).casefold()==k.casefold())==1,**admission(data,k)) for k,v in data.decoratives.items()}
    return dict(terrain={k:dict(walkable=bool(v.get("walkable",True)),transparent=bool(v.get("transparent",True))) for k,v in data.terrain.items()},decor=decor,
        loot_pools=[r["id"] for r in choices["pools"] if r["resolved"]], **choices)


def authoring_validate(raw,data,path,data_root):
    diagnostics=[]; cap=capability(raw,path)
    if not cap["editable"]: diagnostics.append(issue(path,"ROOM_SOURCE","",cap["reason"],"warning"))
    try: diagnostics += [d.json() for d in compile_structure(raw,PRODUCTION_ROUTE,data,path=path).diagnostics]
    except StructureError as error: diagnostics += [d.json() for d in error.diagnostics]
    if not isinstance(raw,dict): return diagnostics
    sources=locations(source_index(data_root),raw.get("id"))
    if len(sources)!=1 or sources[0]["path"] not in ([path, ROOT+Path(path).name] if path==TEMPLATE else [path]):
        diagnostics.append(issue(path,"DUPLICATE_ID","id","Room identity must resolve to this one immediate source, including case aliases."))
    options=catalog(data,data_root)
    for n,record in enumerate(raw.get("special_tiles",[]) if isinstance(raw.get("special_tiles",[]),list) else []):
        if not isinstance(record,dict): continue
        kind=record.get("type",record.get("kind")); f=f"special_tiles[{n}]"
        for field,key in (("creature_id","creatures"),("item_id","items"),("text_id","texts")):
            if field in record and not any(r["id"]==record[field] and r["resolved"] for r in options[key]): diagnostics.append(issue(path,"ROOM_REFERENCE",f+"."+field,f"Missing, ambiguous or unsupported saved {key} definition {record[field]!r}."))
        if kind=="container":
            if not options["decor"].get(record.get("decor_id","crate"),{}).get("resolved"): diagnostics.append(issue(path,"ROOM_REFERENCE",f+".decor_id","Container decor is ambiguous or missing in the saved list registry."))
            for p in record.get("loot_pools",[]) if isinstance(record.get("loot_pools",[]),list) else []:
                if p not in options["loot_pools"]: diagnostics.append(issue(path,"ROOM_REFERENCE",f+".loot_pools",f"Pool {p!r} is missing or ambiguous."))
                for row in data.loot_pools.get(p,{}).get("items",[]):
                    if not any(r["id"]==row.get("item_id") and r["resolved"] for r in options["items"]): diagnostics.append(issue(path,"ROOM_REFERENCE",f+".loot_pools",f"Pool {p!r} item dependency is missing or ambiguous."))
        if "text_id" in record and not any(r["id"]==record.get("item_id") and r["readable"] for r in options["items"]):
            diagnostics.append(issue(path,"INERT_TEXT_BINDING",f+".text_id","Historical text binding on an inert carrier does not establish readability.","warning"))
        if kind == 'item' and cap['editable']:
            from engine.item_factory import ItemFactory
            from engine.text_contract import validate_payload
            try:
                item=ItemFactory(data).create(record.get('item_id'),0,0)
                if item is None: raise ValueError('Factory returned no item')
                if getattr(item,'on_use',None)=='read':
                    identifier=record.get('text_id',getattr(item,'text_id',None))
                    if identifier:
                        entries=locations(definition_sources(data_root,'texts',('text_item_map.json',)),identifier)
                        if len(entries)!=1 or identifier not in data.texts:
                            diagnostics.append(issue(path,'ROOM_REFERENCE',f+'.text_id','Readable text is missing or ambiguous.'))
                        else:
                            for d in validate_payload(entries[0]['definition'],data,entries[0]['path']):
                                diagnostics.append(issue(path,d['code'],f+'.text_id',f"{identifier} / {d['field']}: {d['message']}"))
            except (ValueError,KeyError,TypeError,AttributeError) as error:
                diagnostics.append(issue(path,'ROOM_FACTORY',f+'.item_id',f'Saved item cannot be constructed: {error}'))
        if kind == 'creature' and cap['editable']:
            from engine.creature_factory import CreatureFactory
            import random
            try:
                if CreatureFactory(data).spawn(record.get('creature_id'),0,0,random.Random(0)) is None: raise ValueError('Factory returned no actor')
            except (ValueError,KeyError,TypeError,AttributeError) as error:
                diagnostics.append(issue(path,'ROOM_FACTORY',f+'.creature_id',f'Saved creature cannot be constructed: {error}'))
    if (not any(d['severity']=='error' for d in diagnostics)
            and any(isinstance(r,dict) and r.get('type',r.get('kind'))=='decor' for r in raw.get('special_tiles',[]))):
        # Admission for saved assignment candidates uses the same staged native
        # construction/access checks as the editor and lazy submap consumer.
        from generation.structure_preview import preview
        from generation.context import GenerationError
        try:
            preview(raw,PRODUCTION_ROUTE,data,path=path,derive_access=True)
        except GenerationError as error:
            import re
            diagnostic=issue(path,'PRODUCTION_PLACEMENT','special_tiles',str(error))
            match=re.search(r'special\[(\d+)\]',str(error))
            if match:
                n=int(match[1]);record=raw['special_tiles'][n]
                diagnostic.update(field=f'special_tiles[{n}]',source_xy=[record['x'],record['y']],layer='specials')
            diagnostics.append(diagnostic)
    return diagnostics

