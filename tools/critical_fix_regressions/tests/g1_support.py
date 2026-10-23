"""Semantic generation evidence and small disposable-world fixtures."""
from __future__ import annotations
from dataclasses import asdict
import hashlib
import json
from engine.save_manager import _serialize_entity
from engine.save_components import serialize_item


def fingerprint(m, actors, town=None):
    def layer(name):
        return [[*xy, value] for xy, value in sorted(getattr(m, name, {}).items())]
    rows = {
        'terrain': m.tiles['terrain'].tolist(), 'walkable': m.walkable.tolist(),
        'transparent': m.transparent.tolist(), 'decor': layer('decor'),
        'items': [[*xy, [serialize_item(i) for i in values]] for xy, values in sorted(m.floor_objects.items())],
        'containers': [[*xy, dict(state=c['state'], decor_id=c['decor_id'],
                                 items=[serialize_item(i) for i in c['items']])]
                       for xy, c in sorted(m.container_state.items())],
        'actors': sorted([_serialize_entity(a) for a in actors], key=lambda r: json.dumps(r, sort_keys=True)),
        'links': layer('submap_links'), 'steles': layer('stele_text_ids'),
        'waystones': layer('waystone_inscriptions'), 'bells': layer('bell_inscriptions'),
        'revision': getattr(m, 'generation_revision', 'legacy-unversioned'),
        'town': asdict(town) if town else None,
    }
    return hashlib.sha256(json.dumps(rows, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
