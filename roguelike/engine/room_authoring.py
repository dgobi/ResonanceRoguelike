"""Versioned, game-owned direct authored-room adapter. No gameplay imports here."""
from __future__ import annotations
import json
import hashlib
import re
from pathlib import Path, PurePosixPath
from generation.structure_contract import compile_structure, StructureError, read_document, Validator

CONTRACT = "authored-room-2"
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
RECORD_FIELDS = {"creature":{"x","y","creature_id"}, "item":{"x","y","item_id","text_id"}, "container":{"x","y","decor_id","loot_pools"}, "decor":{"x","y","decor_id"}}


from generation.authored_rooms import (matches, staging_path, discover_paths, source_index, locations, capability, issue, catalog, authoring_validate)


def authoring_operations(context):
    return context["records"][0]["capability"]["operations"] if context and len(context["records"])==1 else []




def authorize_candidate(original,candidate,source,target,*,data=None):
    if not isinstance(candidate,dict) or not isinstance(original,dict): return [issue(source,"ROOM_FIELD","","Requires room objects.")]
    same=lambda a,b: json.dumps(a,sort_keys=True)==json.dumps(b,sort_keys=True)
    errors=[]
    if source==target and candidate.get("id")!=original.get("id"): errors.append(issue(target,"IDENTITY_CHANGE","id","Same-ID editing retains the exact original identity."))
    if source!=target and (candidate.get("id")!=Path(target).stem or str(candidate.get("id","")).casefold()==str(original.get("id","")).casefold()): errors.append(issue(target,"VARIANT_ID","id","A variant requires a distinct case-insensitively unique ID matching its new basename."))
    if str(candidate.get("id","")).casefold() in ("starting_lab", "starting_lab_b") or Path(target).name.casefold() in ("starting_lab.json", "starting_lab_b.json"): errors.append(issue(target,"ROOM_PROTECTED","id","The starting laboratory identity and source are protected."))
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
