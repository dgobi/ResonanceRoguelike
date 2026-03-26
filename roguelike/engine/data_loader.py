# engine/data_loader.py
from __future__ import annotations
import json
from pathlib import Path


class DataLoader:
    """
    Loads and caches all JSON data files at startup.
    Single source of truth for all game data.
    Systems ask the loader; nothing reads files directly.
    """

    def __init__(self, data_root: str = "data") -> None:
        self.root = Path(data_root)

        self.tiles:      dict = self._load("tiles.json")
        self.terrain:    dict = self._load("terrain.json")
        self.qualities:  dict = self._load("qualities.json")
        self.zones:      dict = self._load_dir("zones")
        self.entities:   dict = self._load_dir("entities")
        self.items:      dict = self._load_dir("items")
        self.loot:       dict = self._load_dir("loot")
        self.recipes:    dict = self._load_dir("recipes")
        self.structures: dict = self._load_dir("buildings")
        self.biomes:     dict = self._load_dir("biomes")
        self.entrances:   dict = self._load_dir("entrances")
        self.texts:       dict = self._load_dir("texts")
        self.perks:       dict = self._load_dir("perks")
        self.bodies:      dict = self._load_dir("bodies")
        self.deep_tongue:       dict = self._load_deep_tongue()
        self.buildings:         dict = self._load_dir_nested("buildings")
        self.resonance_spawns:  list = self._load_list("resonance_spawns.json")
        self.weather_defs:      dict = self._load("weather.json")

    # ------------------------------------------------------------------ #

    def _load(self, relative_path: str) -> dict:
        path = self.root / relative_path
        if not path.exists():
            return {}
        with open(path, encoding="utf-8") as f:
            return json.load(f)

    def _load_dir(
        self,
        subdir: str,
        exclude: set[str] | None = None,
    ) -> dict:
        """
        Recursively load all JSON files under data/subdir/.
        Each file's contents are merged into a flat dict keyed by 'id'.
        Files without an 'id' field are skipped with a warning.
        """
        result: dict = {}
        exclude = exclude or set()
        base = self.root / subdir

        if not base.exists():
            return result

        for path in base.rglob("*.json"):
            if path.name in exclude:
                continue
            try:
                with open(path, encoding="utf-8") as f:
                    data = json.load(f)
                # Handle both single objects and arrays of objects
                entries = data if isinstance(data, list) else [data]
                for entry in entries:
                    if "id" not in entry:
                        print(f"Warning: {path} has no 'id' field, skipping.")
                        continue
                    result[entry["id"]] = entry
            except Exception as e:
                print(f"Warning: failed to load {path}: {e}")

        return result

    def _load_dir_nested(self, dirname: str) -> dict:
        """
        Load all JSON files from data/{dirname}/ grouped by subdirectory name.
        Returns dict[category_name, list[parsed_json]].
        Each list entry is the full parsed JSON dict for one file.
        """
        result: dict = {}
        base = self.root / dirname
        if not base.exists():
            return result
        for subdir in sorted(base.iterdir()):
            if not subdir.is_dir():
                continue
            cat = subdir.name
            result[cat] = []
            for f in sorted(subdir.glob("*.json")):
                try:
                    with open(f, encoding="utf-8") as fh:
                        result[cat].append(json.load(fh))
                except Exception as e:
                    print(f"Warning: failed to load {f}: {e}")
        return result

    def _load_list(self, relative_path: str) -> list:
        """Load a JSON file that contains a top-level list."""
        path = self.root / relative_path
        if not path.exists():
            return []
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []

    def _load_deep_tongue(self) -> dict:
        """Load deep_tongue.json and return a dict keyed by the 'deep' field."""
        raw = self._load("deep_tongue.json")
        return {w["deep"]: w for w in raw.get("words", [])}

    def structures_with_tags(self, tags: list[str]) -> list[dict]:
        """
        Return all structure definitions that have ALL of the given tags.
        """
        results = []
        for structure in self.structures.values():
            s_tags = set(structure.get("tags", []))
            if all(t in s_tags for t in tags):
                results.append(structure)
        return results

    def structures_with_any_tag(self, tags: list[str]) -> list[dict]:
        """
        Return all structure definitions that have ANY of the given tags.
        """
        results = []
        for structure in self.structures.values():
            s_tags = set(structure.get("tags", []))
            if any(t in s_tags for t in tags):
                results.append(structure)
        return results
    
    def zones_by_category(self, category: str) -> list[dict]:
        """Return all zones of a given category: settlement, wilderness, dungeon."""
        return [z for z in self.zones.values()
                if z.get("category") == category]

    def zone_structures(
        self,
        zone_id: str,
        rng: "random.Random | None" = None,
    ) -> list[dict]:
        """
        Return weighted-shuffled structure list for a zone.
        Each entry is the full structure definition.
        """
        import random
        rng = rng or random.Random()
        zone = self.zones.get(zone_id)
        if not zone:
            return []

        results = []
        for entry in zone.get("structures", []):
            struct = self.structures.get(entry["id"])
            if struct:
                results.append((struct, entry["weight"]))

        if not results:
            return []

        structs, weights = zip(*results)
        return list(rng.choices(structs, weights=weights, k=len(structs)))