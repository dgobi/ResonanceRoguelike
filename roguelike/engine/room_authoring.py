"""Versioned, game-owned direct authored-room adapter. No gameplay imports here."""
from __future__ import annotations
import json
import hashlib
import re
from pathlib import Path, PurePosixPath
from generation.structure_contract import compile_structure, StructureError, read_document, Validator
from engine.content_authoring import definition_sources

CONTRACT = "authored-room-1"
TEMPLATE = "roguelike/docs/examples/g17_authored_creature_room.json"
ROOT = "roguelike/data/layouts/"
OBSERVE_INSPECTION = True
USES_SCENE_SEED = True
PRODUCTION_ROUTE = "authored_submap"
PUBLICATION_NOTE = ("Saved layout changes load at the next game/catalogue initialization and apply when a scene using that layout is first generated. "
    "This can include an unvisited submap in an existing campaign. Already generated scenes use their saved map/population and stored entry metadata; "
    "Workbench does not regenerate or migrate them. A new layout ID joins no world selector automatically.")
LIMITATIONS = "Initial geometry, population and static access only; no player FOV, combat balance, future path safety or natural selection proof. Resizing changes centering and may change position-derived loot even with the same seed."
VIEWS = ["room-spatial"]
SCHEMA = {"$schema":"https://json-schema.org/draft/2020-12/schema", "type":"object", "properties":{
    "id":{"type":"string","readOnly":True}, "description":{"type":"string","x-control":"multiline"}}, "additionalProperties":True}
FIELDS = {"id", "layers", "legend", "width", "height", "player_start", "exit_direction", "exit_x", "exit_y", "special_tiles"}
RECORD_FIELDS = {"creature":{"x","y","creature_id"}, "item":{"x","y","item_id","text_id"}, "container":{"x","y","decor_id","loot_pools"}}


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
    elif not isinstance(raw.get("special_tiles",[]),list) or any(not isinstance(s,dict) or s.get("type",s.get("kind")) not in RECORD_FIELDS for s in raw.get("special_tiles",[])): reason = "Only direct item, container and creature records are supported. Weighted, scene and deferred specials remain inspect-only."
    operations = [] if reason else ["variant"] if path==TEMPLATE else ["edit","variant"]
    return dict(editable=not reason, reason=reason, operations=operations, shape="direct room object")


def authoring_operations(context):
    return context["records"][0]["capability"]["operations"] if context and len(context["records"])==1 else []


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
    decor={k:dict(name=str(v.get("name",k)),container=v.get("container") is True,blocks_movement=bool(v.get("blocks_movement",False)),path="roguelike/data/decoratives.json",resolved=sum(1 for r in decor_rows if isinstance(r,dict) and str(r.get("id","")).casefold()==k.casefold())==1) for k,v in data.decoratives.items()}
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
    return diagnostics


def authorize_candidate(original,candidate,source,target,*,data=None):
    if not isinstance(candidate,dict) or not isinstance(original,dict): return [issue(source,"ROOM_FIELD","","Requires room objects.")]
    same=lambda a,b: json.dumps(a,sort_keys=True)==json.dumps(b,sort_keys=True)
    errors=[]
    if source==target and candidate.get("id")!=original.get("id"): errors.append(issue(target,"IDENTITY_CHANGE","id","Same-ID editing retains the exact original identity."))
    if source!=target and (candidate.get("id")!=Path(target).stem or str(candidate.get("id","")).casefold()==str(original.get("id","")).casefold()): errors.append(issue(target,"VARIANT_ID","id","A variant requires a distinct case-insensitively unique ID matching its new basename."))
    if str(candidate.get("id","")).casefold()=="starting_lab" or Path(target).name.casefold()=="starting_lab.json": errors.append(issue(target,"ROOM_PROTECTED","id","The starting laboratory identity and source are protected."))
    if not same({k:v for k,v in original.items() if k not in FIELDS},{k:v for k,v in candidate.items() if k not in FIELDS}): errors.append(issue(source,"ROOM_FIELD","","Inactive and unknown metadata must remain unchanged."))
    old,new=original.get("special_tiles",[]),candidate.get("special_tiles",[])
    if not isinstance(old,list) or not isinstance(new,list): return errors+[issue(source,"ROOM_FIELD","special_tiles","Requires ordered direct records.")]
    def kind(r): return r.get("type",r.get("kind")) if isinstance(r,dict) else None
    def immutable(r): return {k:v for k,v in r.items() if k not in RECORD_FIELDS.get(kind(r),set())}
    # Preserve source order and immutable per-record data while allowing direct
    # records to be deleted and public records to be added. No reserialization.
    states={0}
    for row in new:
        next_states=set()
        for pos in states:
            if kind(row) in RECORD_FIELDS and set(row)<=RECORD_FIELDS[kind(row)]|{"type","kind"}: next_states.add(pos)
            for index in range(pos,len(old)):
                if kind(old[index])==kind(row) and same(immutable(old[index]),immutable(row)): next_states.add(index+1)
        states=next_states
    if not states: errors.append(issue(source,"ROOM_FIELD","special_tiles","Preserve record order and untouched metadata; new records use direct public fields."))
    if data is not None:
        from engine.item_factory import ItemFactory
        factory=ItemFactory(data)
        for n,row in enumerate(new):
            if kind(row)!="item" or "text_id" not in row: continue
            historical=any(kind(r)=="item" and r.get("item_id")==row.get("item_id") and r.get("text_id")==row["text_id"] for r in old)
            if not historical and row.get("item_id") in data.items and getattr(factory.create(row["item_id"],0,0),"on_use",None)!="read":
                errors.append(issue(target,"FALSE_READABLE",f"special_tiles[{n}].text_id","Choose an existing readable carrier whose constructed on_use is read, or remove the text override."))
    return errors


def authoring_context(raw,data,path,data_root,identity,digest,observe=False,**kwargs):
    diagnostics=authoring_validate(raw,data,path,data_root)
    cap=capability(raw,path)
    if any(d["severity"]=="error" for d in diagnostics): cap=dict(cap,editable=False,operations=[],reason=cap["reason"] or "Compiler, identity or saved references need correction; inspect Problems.")
    generated=None
    if observe and not any(d["severity"]=="error" for d in diagnostics):
        from generation.structure_preview import preview
        from generation.context import GenerationError
        try:
            generated,_,_=preview(raw,PRODUCTION_ROUTE,data,seed=kwargs.get("seed",20261023),path=path,derive_access=True)
            generated.update(valid=generated["passed"],width=80,height=43,source=identity,source_path=path,source_sha256=digest,draft_sha256=digest,layout_contract=CONTRACT,scene_seed=str(generated["scene_seed"]),
                access_source=dict(kind="derived from exact direct population receipts and produced return stairs",coordinates="map"),
                candidate_sha256=generated["candidate_identity"],terrain_sha256=hashlib.sha256(json.dumps(generated["terrain"]).encode()).hexdigest(),
                legend={k:dict(walkable=bool(v.get("walkable",True)),transparent=bool(v.get("transparent",True))) for k,v in data.terrain.items()},elapsed_ms=0,
                context="Compiler → layout generation → create_submap → factories/population; exact receipt-owned objects and static access.",rendering=LIMITATIONS)
            if not generated["passed"]: diagnostics.append(issue(path,"ROOM_ACCESS","special_tiles","Initial production access failed; inspect realized receipt and access targets."))
        except GenerationError as error:
            diagnostic=issue(path,"PRODUCTION_PLACEMENT","special_tiles",str(error))
            match=re.search(r"special\[(\d+)\]",str(error))
            if match:
                n=int(match[1]); records=raw.get("special_tiles",[])
                if n<len(records): diagnostic.update(field=f"special_tiles[{n}]",source_xy=[records[n]["x"],records[n]["y"]],layer="specials")
            diagnostics.append(diagnostic)
    return dict(records=[dict(id=raw.get("id","") if isinstance(raw,dict) else "",definition=raw if isinstance(raw,dict) else {},capability=cap,diagnostics=diagnostics)],catalog=catalog(data,data_root),preview=generated)


def reference_options(context): return {}


def authoring_evidence(context):
    report=context.get("preview") if context else None
    verified=bool(report and report["passed"])
    return dict(semantic_verified=verified,placement_verified=verified,population_verified=verified,layout_contract=CONTRACT,preview=report)
