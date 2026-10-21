# engine/structure_placer.py
from __future__ import annotations
import random
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from world.local_map import LocalMap
    from engine.data_loader import DataLoader


class StructurePlacer:
    """
    Stamps structure blueprints onto a LocalMap.
    Reads layout grids from structure JSON and applies
    terrain, furniture, and loot references.
    """

    def __init__(self, data: DataLoader) -> None:
        self.data = data

    def place(
        self,
        local_map: LocalMap,
        structure_id: str,
        origin_x: int,
        origin_y: int,
        rng: random.Random | None = None,
        rotate: int = 0,
    ) -> bool:
        """
        Stamp a structure at (origin_x, origin_y).
        rotate: 0=none, 1=90°, 2=180°, 3=270°
        Returns True if placement succeeded, False if out of bounds.
        """
        rng = rng or random.Random()
        structure = self.data.structures.get(structure_id)
        if not structure:
            print(f"Warning: structure '{structure_id}' not found.")
            return False

        layers  = structure.get("layers") or structure.get("layout") or []
        legend  = structure["legend"]
        rows    = len(layers)
        cols    = max(len(row) for row in layers)

        # Apply rotation if requested and structure allows it
        if rotate and structure.get("rotatable", False):
            layers = self._rotate_layout(layers, rotate)
            rows   = len(layers)
            cols   = max(len(row) for row in layers)

        # Bounds check
        if (origin_x + cols > local_map.width or
                origin_y + rows > local_map.height):
            return False

        terrain_data = self.data.terrain

        for row_idx, row in enumerate(layers):
            for col_idx, char in enumerate(row):
                if char not in legend:
                    continue

                tx = origin_x + col_idx
                ty = origin_y + row_idx
                entry = legend[char]

                # Legend values may be plain strings ("wall") or dicts ({"terrain": "wall"})
                if entry is None:
                    continue
                if isinstance(entry, str):
                    terrain_key = entry
                    entry = {}
                else:
                    terrain_key = entry.get("terrain", "floor")
                t = terrain_data.get(terrain_key, terrain_data["floor"])
                local_map.set_tile(
                    tx, ty,
                    terrain_key,
                    t["walkable"],
                    t["transparent"],
                )

                # Store furniture and loot references on the map
                # (we'll use these when the item/furniture system is built)
                if "furniture" in entry or "loot" in entry:
                    if not hasattr(local_map, "furniture"):
                        local_map.furniture: dict = {}
                    local_map.furniture[(tx, ty)] = {
                        "furniture": entry.get("furniture"),
                        "loot":      entry.get("loot"),
                    }

        return True

    def _rotate_layout(
        self,
        layout: list[str],
        times: int,
    ) -> list[str]:
        """Rotate layout 90° clockwise `times` times."""
        rows = layout
        for _ in range(times % 4):
            cols  = max(len(r) for r in rows)
            padded = [r.ljust(cols) for r in rows]
            rows  = [
                "".join(padded[rows_idx][col_idx]
                        for rows_idx in range(len(padded) - 1, -1, -1))
                for col_idx in range(cols)
            ]
        return rows