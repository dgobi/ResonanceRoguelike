"""Saved definition source identities, without choosing duplicate winners."""
import json

def definition_sources(data_root, family, excluded=()):
    """Mirror the loader's object/array convention without choosing an ID winner."""
    sources = {}
    for path in sorted((data_root / family).rglob("*.json")):
        if path.name.casefold() in excluded: continue
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            continue
        for index, row in enumerate(raw if isinstance(raw, list) else [raw]):
            if isinstance(row, dict) and isinstance(row.get("id"), str):
                sources.setdefault(row["id"], []).append(dict(
                    path="roguelike/data/" + path.relative_to(data_root).as_posix(),
                    pointer=f"/{index}" if isinstance(raw, list) else "", definition=row))
    return sources

