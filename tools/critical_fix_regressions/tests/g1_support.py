"""Semantic generation evidence and small disposable-world fixtures."""
from __future__ import annotations
from dataclasses import asdict
import hashlib
import json
import copy
from engine.save_manager import _serialize_entity
from engine.save_components import serialize_item


def semantic_item_state(row, *, historical=False):
    """Generation semantics exclude random identity; save tests keep full state.

    Historical receipts may omit only the validated, approved empty clay addition.
    Other capability, water and item fields remain part of the comparison.
    """
    from engine.save_components import validate_item
    from engine.vessels import CLAY
    row=copy.deepcopy(row)
    if 'vessel' in row:
        validate_item(row,'semantic item')
        v=row['vessel']
        if historical and row['item_id']=='clay_pot' and v['config']==CLAY and v['water_ml']==0:
            row.pop('vessel')
        else:v.pop('id')
    if historical and 'vessel_absent_version' in row:
        validate_item(row,'historical item');row.pop('vessel_absent_version')
    return row


def semantic_item(item, *, historical=False):
    return semantic_item_state(serialize_item(item),historical=historical)


def fingerprint(m, actors, town=None, *, historical=False):
    def layer(name):
        return [[*xy, value] for xy, value in sorted(getattr(m, name, {}).items())]
    rows = {
        'terrain': m.tiles['terrain'].tolist(), 'walkable': m.walkable.tolist(),
        'transparent': m.transparent.tolist(), 'decor': layer('decor'),
        'items': [[*xy, [semantic_item(i,historical=historical) for i in values]] for xy, values in sorted(m.floor_objects.items())],
        'containers': [[*xy, dict(state=c['state'], decor_id=c['decor_id'],
                                 items=[semantic_item(i,historical=historical) for i in c['items']])]
                       for xy, c in sorted(m.container_state.items())],
        'actors': sorted([_serialize_entity(a) for a in actors], key=lambda r: json.dumps(r, sort_keys=True)),
        'links': layer('submap_links'), 'steles': layer('stele_text_ids'),
        'waystones': layer('waystone_inscriptions'), 'bells': layer('bell_inscriptions'),
        'revision': getattr(m, 'generation_revision', 'legacy-unversioned'),
        'town': asdict(town) if town else None,
        'plan_provenance': getattr(m, 'plan_provenance', None),
    }
    return hashlib.sha256(json.dumps(rows, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
