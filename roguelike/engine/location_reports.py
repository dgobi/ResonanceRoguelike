"""Two frozen, world-owned records. Reading learns reports, never terrain/reality.

The small owner token belongs only to this optional feature, not campaign identity.
Binding consumes completed metadata, no scene construction or gameplay RNG.
"""
from __future__ import annotations
import copy
import re
import uuid

ROLES = ("workshop", "ward_store")
PURPOSES = {
    "workshop": "A workshop once used for road preparations: fuel, musk work and a traveller's emergency wrap. Present stock and safety are unknown.",
    "ward_store": "A barrow store where a bronze ward was kept. Its present contents, inhabitants and safety are unknown.",
}
TOKEN = re.compile(r"[0-9a-f]{32}\Z")


def attachment(raw):
    rows = raw.get("location_reports", [])
    if (not isinstance(rows, list) or len(rows) > 2
            or any(not isinstance(r, dict) or set(r) != {"role"}
                   or not isinstance(r["role"], str) or r["role"] not in ROLES for r in rows)):
        raise ValueError("Location reports require at most two records containing only workshop or ward_store role.")
    roles = [r["role"] for r in rows]
    if len(set(roles)) != len(roles):
        raise ValueError("Duplicate location report role.")
    return roles


def candidates(world, role):
    if role == "workshop":
        from config import MAP_WIDTH, MAP_HEIGHT
        for p in (getattr(world, "plan", None) or {}).get("placements", []):
            if p["asset"] == "workshop_d":
                yield p["origin"][0] // MAP_WIDTH, p["origin"][1] // MAP_HEIGHT, p["id"], p["asset"]
    else:
        for (wx, wy), chunk in world.chunks.items():
            for sub in chunk.submaps:
                if sub.layout_id == "barrow_ward_store_a":
                    yield wx, wy, sub.submap_id, sub.layout_id


def bind(world, title):
    """Fresh world only. Absence is deliberately frozen too."""
    if getattr(world, "report_owner", None) is not None:
        raise ValueError("Reports already bound")
    origin = [world.start_wx, world.start_wy]
    lab = world.get(*origin).submaps[0]
    world.report_owner = uuid.uuid4().hex
    records = []
    for role in ROLES:
        eligible = [(abs(x-origin[0])+abs(y-origin[1]), x, y, identity, asset)
                    for x, y, identity, asset in candidates(world, role)
                    if abs(x-origin[0])+abs(y-origin[1]) <= 8]
        selected = min(eligible) if eligible else None
        records.append(dict(role=role, owner=world.report_owner, origin=origin[:], laboratory=lab.submap_id,
                            source=title, description=PURPOSES[role], target=(dict(x=selected[1], y=selected[2],
                            id=selected[3], asset=selected[4]) if selected else None)))
    world.location_reports = records
    world.learned_reports = []
    validate(world)


def _string(value, limit):
    return (isinstance(value, str) and 0 < len(value) <= limit
            and all(ord(c) >= 32 and ord(c) != 127 for c in value))


def validate(world):
    """Called on a staged restored world, before installation of any state."""
    owner = getattr(world, "report_owner", None)
    rows = getattr(world, "location_reports", [])
    learned = getattr(world, "learned_reports", [])
    if owner is None and rows == [] and learned == []:
        return
    if not isinstance(owner, str) or not TOKEN.fullmatch(owner):
        raise ValueError("Invalid report owner")
    if not isinstance(rows, list) or len(rows) != 2:
        raise ValueError("Invalid report record count")
    seen, ids = set(), set()
    for r in rows:
        if not isinstance(r, dict) or set(r) != {"role", "owner", "origin", "laboratory", "source", "description", "target"}:
            raise ValueError("Invalid report shape")
        role = r["role"]
        if not isinstance(role, str) or role not in ROLES or role in seen or r["owner"] != owner:
            raise ValueError("Invalid/duplicate/foreign report role")
        seen.add(role)
        origin = r["origin"]
        if (not isinstance(origin, list) or len(origin) != 2 or any(type(n) is not int for n in origin)
                or not world.in_bounds(*origin) or origin != [world.start_wx, world.start_wy]):
            raise ValueError("Invalid report reference point")
        chunk = world.get(*origin)
        if (not chunk or not _string(r["laboratory"], 160)
                or not any(s.submap_id == r["laboratory"] and s.layout_id == "starting_lab_b" for s in chunk.submaps)):
            raise ValueError("Foreign report laboratory")
        if not _string(r["source"], 160) or not _string(r["description"], 400):
            raise ValueError("Invalid report public text")
        t = r["target"]
        if t is None:
            continue
        if (not isinstance(t, dict) or set(t) != {"x", "y", "id", "asset"}
                or type(t["x"]) is not int or type(t["y"]) is not int
                or not world.in_bounds(t["x"], t["y"])
                or abs(t["x"]-origin[0])+abs(t["y"]-origin[1]) > 8
                or not _string(t["id"], 200) or not _string(t["asset"], 100)
                or t["id"] in ids
                or (t["x"], t["y"], t["id"], t["asset"]) not in set(candidates(world, role))):
            raise ValueError("Invalid/foreign report target")
        ids.add(t["id"])
    if (not isinstance(learned, list) or len(learned) > 2
            or any(not isinstance(r, str) or r not in seen for r in learned)
            or len(set(learned)) != len(learned)):
        raise ValueError("Invalid learned report roles")


def describe(r):
    t = r["target"]
    label = "Workshop" if r["role"] == "workshop" else "Ward store"
    if t is None:
        return f"{label}: incomplete record; no location recorded within eight coarse squares."
    dx, dy = t["x"]-r["origin"][0], t["y"]-r["origin"][1]
    bearing = ", ".join([f"{abs(n)} {positive if n > 0 else negative}" for n, positive, negative in
                         ((dx, "east", "west"), (dy, "south", "north")) if n]) or "at the reference square"
    return (f"{label} — square ({t['x']}, {t['y']}); {bearing} from the recorded laboratory "
            f"({r['origin'][0]}, {r['origin'][1]}). {abs(dx)+abs(dy)} coarse squares, not walking time.\n{r['description']}")


def reader_payload(raw, world=None, *, learn=False):
    roles = attachment(raw)
    if not roles:
        return raw
    result = copy.deepcopy(raw)
    rows = getattr(world, "location_reports", []) if world else []
    for role in roles:
        record = next((r for r in rows if r["role"] == role), None)
        text = describe(record) if record else f"{'Workshop' if role == 'workshop' else 'Ward store'}: location report unbound; this sheet has no owning fresh-world record."
        result["pages"].append(dict(text=text))
        if learn and record and role not in world.learned_reports:
            world.learned_reports.append(role)
    return result


def known(world, x=None, y=None):
    return [r for r in getattr(world, "location_reports", [])
            if r["role"] in getattr(world, "learned_reports", []) and r["target"] is not None
            and (x is None or (r["target"]["x"], r["target"]["y"]) == (x, y))]
