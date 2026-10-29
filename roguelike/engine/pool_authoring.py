"""Registered native contextual pools; source authority is independent of values.

No gameplay sampling lives here. Validator.pool, ItemFactory and ITEM_STATE own
the consumed rules and safe unowned construction respectively.
"""
from pathlib import PurePosixPath
import re
from engine.definition_sources import definition_sources
from generation.structure_contract import Validator

CONTRACT = "contextual-loot-1"
PRODUCTION_ROUTE = "contextual_loot_pool"
ROOT = "roguelike/data/loot_pools/"
MAX_ROWS = 64
PUBLICATION_NOTE = ("Saves definitions for the next catalogue and fresh construction. Pending planned surfaces retain selected semantic dependencies: changed consumed pools/items can reject construction until matching definitions are restored or a fresh world is started. "
    "Generated containers retain their saved physical contents and state; taking or consuming loot persists. Variants change no container reference. "
    "Reset uses the immutable capture; Test latest saved captures current saved dependencies.")
LIMITATIONS = ("Definition/source validation and unowned factory/persistence checks only; no sample, acquisition or gameplay-use proof. "
    "Container samples depend on scene inputs, realized position/decor and ordered pool occurrences. Saved dependencies alone supply validation and Test room.")
VIEWS = ["pool-entries"]
SCHEMA = {"$schema":"https://json-schema.org/draft/2020-12/schema", "type":"object", "properties":{
    "id":{"type":"string","readOnly":True}, "description":{"type":"string","x-control":"multiline"}}, "additionalProperties":True}


def matches(path):
    return path.startswith(ROOT) and path.endswith(".json")


def safe_id(value):
    return (isinstance(value,str) and re.fullmatch(r"[A-Za-z0-9_-]{1,100}",value) is not None
        and value.casefold() not in {"con","prn","aux","nul",*(f"{p}{n}" for p in ("com","lpt") for n in range(1,10))})


def locations(index, identifier):
    return [s for key, rows in index.items() if isinstance(identifier,str) and key.casefold()==identifier.casefold() for s in rows]


def issue(path, code, field, message, severity="error"):
    return dict(severity=severity,code=code,path=path,asset="",field=field,message=message,
        correction="Repair this draft field or choose a unique loader-accepted saved source, then validate again.")


def load_authoring_data(data_root):
    """Retain the real loader's already loaded pools/items if its later structure
    catalogue rejects a building that references the pool being repaired.

    This is only an authoring dependency snapshot, never a gameplay catalogue or
    a bypass of candidate pool validation. Runtime startup remains fail-closed.
    """
    from engine.data_loader import DataLoader
    from generation.structure_contract import StructureError
    data=DataLoader.__new__(DataLoader)
    try: DataLoader.__init__(data,str(data_root))
    except StructureError:
        if not hasattr(data,"loot_pools") or not hasattr(data,"items"): raise
    return data


def capability(raw, path, pointer=""):
    reason=""
    if PurePosixPath(path).parent.as_posix()!=ROOT.rstrip("/") or pointer or not isinstance(raw,dict):
        reason="Only one object in an immediate loot_pools/<safe-id>.json file is writable; nested/array formats remain inspect-only."
    elif not safe_id(raw.get("id")) or PurePosixPath(path).name!=raw["id"]+".json":
        reason="The original exact safe ID must match its immediate filename."
    return dict(editable=not reason,reason=reason,operations=[] if reason else ["edit","variant"],shape="native single pool object")


def source_problems(raw, data, path, data_root):
    identifier=raw.get("id") if isinstance(raw,dict) else None
    entries=locations(definition_sources(data_root,"loot_pools"),identifier)
    problems=[]
    if not isinstance(identifier,str) or not identifier:
        return [issue(path,"POOL_ID","id","Pool requires a nonempty string ID.")]
    if len(entries)!=1 or entries[0]["path"]!=path or entries[0]["pointer"]:
        problems.append(issue(path,"DUPLICATE_ID","id",f"Pool {identifier!r} must resolve to exactly {path}; sources: " +
            ", ".join(s["path"]+s["pointer"] for s in entries)))
    if data.loot_pools.get(identifier)!=raw:
        problems.append(issue(path,"LOADER_IDENTITY","id",f"Loader did not load the exact staged definition {identifier!r} from {path}; BOM/skipped or colliding sources cannot publish."))
    return problems


def validate_pool(raw, data, path, data_root, *, bounded=False):
    """All rows, including weight zero; never roll or overlay parked drafts."""
    from types import SimpleNamespace
    from engine.item_factory import ItemFactory
    from engine.harvesting import validate_output
    identifier=raw.get("id") if isinstance(raw,dict) else None
    v=Validator(SimpleNamespace(items=data.items,loot_pools={identifier:raw}) if isinstance(identifier,str) else data,path,str(identifier or "<pool>"),"ordinary_building")
    problems=source_problems(raw,data,path,data_root)
    if not isinstance(identifier,str) or not isinstance(raw,dict): return problems
    v.pool(identifier,"pool")
    problems += [d.json() for d in v.diagnostics]
    rows=raw.get("items",[])
    if bounded and isinstance(rows,list) and len(rows)>MAX_ROWS:
        problems.append(issue(path,"POOL_BOUND","items",f"Workbench publication permits at most {MAX_ROWS} ordered entries; reduce this draft deliberately."))
    index=definition_sources(data_root,"items"); factory=ItemFactory(data)
    for n,row in enumerate(rows if isinstance(rows,list) else []):
        item_id=row.get("item_id") if isinstance(row,dict) else None
        field=f"items[{n}].item_id"; entries=locations(index,item_id)
        paths=", ".join(s["path"]+s["pointer"] for s in entries)
        if not isinstance(item_id,str) or len(entries)!=1 or item_id not in data.items or entries[0]["definition"]!=data.items[item_id]:
            problems.append(issue(path,"ITEM_SOURCE",field,f"Item {item_id!r} is missing, skipped, ambiguous or case-aliased; sources: {paths}")); continue
        try:
            validate_output(factory.create(item_id),item_id)
        except Exception as error:
            problems.append(issue(path,"ITEM_FACTORY",field,f"Unowned factory/ITEM_STATE check failed for {item_id!r} ({paths}): {error}"))
    for key in raw.keys()-{"id","description","roll_count","items"}:
        problems.append(issue(path,"INACTIVE_POOL_FIELD",key,f"{key!r} is retained metadata; the roller does not consume it.","warning"))
    return problems


def container_dependencies(raw,data,path,data_root):
    problems=[]; index=definition_sources(data_root,"loot_pools")
    def containers(row,field):
        if not isinstance(row,dict): return
        kind=row.get("type",row.get("kind"))
        if kind=="container": yield row,field
        elif kind=="weighted" and isinstance(row.get("spawn_table"),list):
            for n,choice in enumerate(row["spawn_table"]):
                if isinstance(choice,dict) and choice.get("type",choice.get("kind"))=="container": yield choice,f"{field}.spawn_table[{n}]"
    rows=raw.get("special_tiles",[]) if isinstance(raw,dict) and isinstance(raw.get("special_tiles",[]),list) else []
    for row,location in (entry for n,row in enumerate(rows) for entry in containers(row,f"special_tiles[{n}]")):
        for p,identifier in enumerate(row.get("loot_pools",[]) if isinstance(row.get("loot_pools",[]),list) else []):
            field=f"{location}.loot_pools[{p}]"; entries=locations(index,identifier)
            if len(entries)!=1 or identifier not in data.loot_pools or entries[0]["definition"]!=data.loot_pools[identifier]:
                problems.append(issue(path,"POOL_SOURCE",field,f"Pool {identifier!r} is missing/skipped/case-ambiguous; sources: " + ", ".join(s["path"]+s["pointer"] for s in entries)));continue
            # Dependency consumption has no authoring row bound or editable-format
            # gate: unchanged larger/array/nested saved pools keep their native use.
            checks=validate_pool(data.loot_pools[identifier],data,entries[0]["path"],data_root)
            for d in checks:
                if d["code"]=="DUPLICATE_ID" and entries[0]["pointer"]: continue
                problems.append({**d,"path":path,"field":field+" -> "+entries[0]["path"]+entries[0]["pointer"]+" / "+d["field"]})
    return problems


def authoring_validate(raw,data,path,data_root):
    return validate_pool(raw,data,path,data_root,bounded=True)


def authorize_candidate(original,candidate,source,target,*,data=None):
    problems=[]; cap=capability(original,source)
    if not cap["editable"]: problems.append(issue(source,"SOURCE_ENTITLEMENT","",cap["reason"]))
    if not isinstance(original,dict): return problems
    if not isinstance(candidate,dict): return problems+[issue(target,"POOL_SHAPE","","Requires one native pool object.")]
    identifier=candidate.get("id")
    if target==source:
        if identifier!=original.get("id"): problems.append(issue(target,"IDENTITY_CHANGE","id","Same-ID editing retains exact identity and path."))
    elif (not safe_id(identifier) or identifier.casefold()==str(original.get("id","")).casefold()
          or PurePosixPath(target).name!=identifier+".json" or PurePosixPath(target).parent!=PurePosixPath(source).parent):
        problems.append(issue(target,"VARIANT_ID","id","Variants require a distinct safe ID matching a new filename beside the source."))
    # Unknown metadata remains deliberately Source-editable, per W3A.
    return problems


def authoring_context(raw,data,path,data_root,identity,digest,**kwargs):
    cap=capability(raw,path)
    identity_problems=source_problems(raw,data,path,data_root)
    if identity_problems: cap=dict(cap,editable=False,operations=[],reason="; ".join(d["message"] for d in identity_problems))
    items={}; index=definition_sources(data_root,"items")
    for identifier,entries in sorted(index.items()):
        all_entries=locations(index,identifier)
        items[identifier]=dict(id=identifier,name=str(entries[0]["definition"].get("name",identifier)),sources=all_entries,
            resolved=len(all_entries)==1 and identifier in data.items and entries[0]["definition"]==data.items[identifier])
    refs=[]
    from generation.structure_contract import ELIGIBILITY
    sources=[]
    for entries in definition_sources(data_root,"buildings").values():
        for e in entries:
            parts=PurePosixPath(e["path"]).parts
            if len(parts)==5 and parts[3] in ELIGIBILITY.keys()-{"plaza"} and not e["pointer"]:
                sources.append((e["definition"],e["path"],"ordinary_building"))
    from generation.authored_rooms import source_index, capability as room_capability
    for entries in source_index(data_root).values():
        for e in entries:
            if room_capability(e["definition"],e["path"])["editable"]: sources.append((e["definition"],e["path"],"authored_submap"))
    for definition,source,route in sources:
        records=definition.get("special_tiles",[])
        for n,row in enumerate(records if isinstance(records,list) else []):
            if not isinstance(row,dict) or row.get("type",row.get("kind"))!="container": continue
            pools=row.get("loot_pools",[])
            for p,identifier in enumerate(pools if isinstance(pools,list) else []):
                if isinstance(raw,dict) and identifier==raw.get("id"):
                    refs.append(dict(id=definition["id"],path=source,route=route,field=f"special_tiles[{n}].loot_pools[{p}]",x=row["x"],y=row["y"],decor_id=row.get("decor_id","crate")))
    return dict(records=[dict(id=raw.get("id","") if isinstance(raw,dict) else "",definition=raw if isinstance(raw,dict) else {},capability=cap,diagnostics=authoring_validate(raw,data,path,data_root))],
        items=items,references=sorted(refs,key=lambda r:(r["path"],r["field"])),consumer="engine/loot_roller.py:roll_pool → ItemFactory.create; engine/scene_generation.py:populate",
        validator="generation/structure_contract.py:Validator.pool + saved sources + ItemFactory + save_components.ITEM_STATE",
        rules="Weighted draws without replacement by entry; repeated IDs are separate physical items. Absent count is [1,1], [n] is fixed, [min,max] inclusive. Draws are capped to entries and stop at zero remaining weight. Absent weight is 1. Ordered/repeated pool occurrences roll independently with the caller RNG. Quantity/conditions/text overrides are inactive metadata.")


def reference_options(context): return {}


def authoring_evidence(context):
    return dict(semantic_verified=bool(context and not any(d["severity"]=="error" for r in context["records"] for d in r["diagnostics"])),placement_verified=False,population_verified=False)
