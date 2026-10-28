"""Versioned opt-in assignment of saved ordinary rooms to new SubMap instances.

Read at new-world creation only. Never enroll or rewrite a restored world.
The selector owns no geography RNG and never constructs a local scene.
"""
from __future__ import annotations
from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
import random

CONTRACT = "authored-submap-selection-1"
IDENTITY = "authored_submap_selection"
PROFILE = "roguelike/data/generation/authored_submap_selection.json"
RELATIVE = "generation/authored_submap_selection.json"
TYPES = ("barrow", "cave", "vault")
DEFAULT = dict(id=IDENTITY, version=1, enabled=False, target_type="barrow", authored_chance=0.0, candidates=[])


class AssignmentError(ValueError):
    def __init__(self, diagnostics):
        from generation.structure_contract import Diagnostic
        self.diagnostics = [Diagnostic(**d) for d in diagnostics]
        super().__init__("; ".join(f"{d['field'] or PROFILE}: {d['message']}" for d in diagnostics if d['severity']=='error'))


def issue(field, message, severity="error", code="ASSIGNMENT_POLICY"):
    return dict(severity=severity, code=code, path=PROFILE, asset="", field=field, message=message,
                correction="Save eligible rooms and linked contents first; correct this profile field and validate again.")


def finite_number(value):
    if type(value) not in (int, float): return False
    try: return math.isfinite(value)
    except OverflowError: return False


@dataclass(frozen=True)
class Policy:
    enabled: bool = False
    target_type: str = "barrow"
    chance: float = 0.0
    candidates: tuple = ()

    def choose(self, world_seed, wx, wy, submap):
        if not self.enabled or not self.chance or submap.submap_type != self.target_type or submap.layout_id:
            return submap.layout_id
        # Identity and sorted candidate IDs make order/metadata/format immaterial.
        key = json.dumps([CONTRACT, world_seed, wx, wy, submap.submap_id, submap.seed], separators=(',', ':'))
        rng = random.Random(int.from_bytes(hashlib.sha256(key.encode()).digest(), 'big'))
        if rng.random() >= self.chance:
            return ""
        # Scale first: finite positive weights must never overflow their sum.
        maximum = max(weight for _, weight in self.candidates)
        weights = [weight / maximum for _, weight in self.candidates]
        threshold = rng.random() * math.fsum(weights)
        total = 0.0
        for (identifier, _), weight in zip(self.candidates, weights):
            total += weight
            if threshold < total:
                return identifier
        return self.candidates[-1][0]


def validate(raw, data):
    from generation.authored_rooms import source_index, locations, capability, authoring_validate, ROOT
    diagnostics=[]
    if not isinstance(raw, dict):
        return Policy(), [issue("", "Expected the fixed versioned assignment object.")]
    if raw.get('id') != IDENTITY: diagnostics.append(issue('id', f"Requires fixed identity {IDENTITY}."))
    if type(raw.get('version')) is not int or raw['version'] != 1: diagnostics.append(issue('version', 'Only integer version 1 is supported.'))
    if type(raw.get('enabled')) is not bool: diagnostics.append(issue('enabled', 'Expected explicit true or false.'))
    if raw.get('target_type') not in TYPES: diagnostics.append(issue('target_type', 'Choose barrow, cave or vault.'))
    chance=raw.get('authored_chance')
    if not finite_number(chance) or not 0 <= chance <= 1:
        diagnostics.append(issue('authored_chance', 'Expected a finite probability from 0 to 1.'))
    rows=raw.get('candidates'); candidates=[]; seen=set()
    # Inactive references are warnings; structural/type/weight errors stay errors.
    # This permits parking saved membership while disabled without concealing it.
    active=raw.get('enabled') is True and type(chance) in (int,float) and chance > 0
    severity='error' if active else 'warning'
    if not isinstance(rows,list): diagnostics.append(issue('candidates', 'Expected an ordered list of room/weight records.')); rows=[]
    if active and not rows: diagnostics.append(issue('candidates', 'Enabled nonzero assignment requires at least one eligible saved room.'))
    index=source_index(data.root) if rows else {}
    for n,row in enumerate(rows):
        field=f'candidates[{n}]'
        if not isinstance(row,dict): diagnostics.append(issue(field, 'Expected a layout_id and positive weight.')); continue
        identifier=row.get('layout_id'); weight=row.get('weight')
        if not isinstance(identifier,str) or not identifier:
            diagnostics.append(issue(field+'.layout_id', 'Choose an eligible saved ordinary room.')); continue
        if identifier.casefold() in seen: diagnostics.append(issue(field+'.layout_id', 'Duplicate room identity, including case aliases.'))
        seen.add(identifier.casefold())
        valid_weight=finite_number(weight) and weight > 0
        if not valid_weight: diagnostics.append(issue(field+'.weight', 'Expected a finite positive relative weight.'))
        sources=locations(index,identifier)
        if len(sources)!=1:
            diagnostics.append(issue(field+'.layout_id', 'Room is missing or ambiguous; choose one unique immediate layouts/ definition.',severity)); continue
        source=sources[0]; definition=source['definition']; path=source['path']
        cap=capability(definition,path)
        if not path.startswith(ROOT) or 'edit' not in cap['operations'] or identifier not in data.layouts:
            diagnostics.append(issue(field+'.layout_id', cap['reason'] or 'Publish the template as an ordinary room first; exact saved identity required.',severity)); continue
        entry=data.structure_catalog.by_route['authored_submap'].get(identifier)
        saved_path=(Path(data.root)/Path(path).relative_to('roguelike/data')).resolve()
        # Compare raw to raw, compiled to compiled, and the original source bytes.
        # Container defaults belong to the compiler, never to the saved source.
        if (entry is None or Path(entry.path).resolve()!=saved_path or entry.raw!=definition
                or entry.definition!=data.layouts[identifier]
                or data.structure_catalog.source_hashes.get(str(saved_path))!=hashlib.sha256(saved_path.read_bytes()).hexdigest()):
            diagnostics.append(issue(field+'.layout_id', 'Saved room differs from the loaded catalogue; reopen saved inputs before generation.',severity)); continue
        errors=authoring_validate(definition,data,path,data.root)
        for d in errors:
            diagnostics.append(issue(field+'.layout_id', f"{identifier} / {d['field']}: {d['message']}", severity if d['severity']=='error' else d['severity'], 'ASSIGNMENT_ROOM'))
        if valid_weight: candidates.append((identifier,float(weight)))
    return Policy(raw.get('enabled') is True, raw.get('target_type','barrow'), chance if type(chance) in (int,float) else 0,
                  tuple(sorted(candidates))), diagnostics


def resolve(data):
    path=Path(data.root)/RELATIVE
    if not path.exists(): return Policy()
    try: raw=json.loads(path.read_text(encoding='utf-8-sig'))
    except (OSError,ValueError) as error: raise AssignmentError([issue('',f'Cannot read explicit profile: {error}')]) from error
    policy,diagnostics=validate(raw,data)
    if any(d['severity']=='error' for d in diagnostics): raise AssignmentError(diagnostics)
    return policy
