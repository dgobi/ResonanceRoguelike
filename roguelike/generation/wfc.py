# generation/wfc.py
"""
Generic Wave Function Collapse solver.
Operates on a 2D grid, collapsing cells to tiles from a weighted set.
Tileset and adjacency rules loaded from JSON.
"""
from __future__ import annotations
import json
import random
from pathlib import Path


class WFCSolver:
    """
    Generic WFC solver. Usage:
        solver = WFCSolver.from_json("data/wfc/town_plaza.json", rng)
        result = solver.solve(width, height)
        # result: 2D list[list[str]] of tile names, or None on failure
    """

    MAX_ATTEMPTS = 10

    def __init__(
        self,
        tiles:     list[dict],
        adjacency: dict[str, dict[str, list[str]]],
        fallback:  str,
        rng:       random.Random,
    ) -> None:
        self._tiles     = tiles                      # [{"name": ..., "terrain": ..., "weight": ...}]
        self._adjacency = adjacency                  # tile_name → {N/E/S/W → [allowed_tile_names]}
        self._fallback  = fallback
        self._rng       = rng

        self._tile_names   = [t["name"] for t in tiles]
        self._tile_weights = {t["name"]: t.get("weight", 1) for t in tiles}
        self._all_tiles    = set(self._tile_names)

    @classmethod
    def from_json(cls, path: str, rng: random.Random) -> "WFCSolver":
        """Load tileset JSON and return a WFCSolver instance."""
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls(
            tiles     = data["tiles"],
            adjacency = data["adjacency"],
            fallback  = data.get("fallback", data["tiles"][0]["name"]),
            rng       = rng,
        )

    def solve(
        self,
        width:  int,
        height: int,
        fixed:  "dict[tuple[int,int], str] | None" = None,
    ) -> "list[list[str]] | None":
        """
        Solve for a width×height grid.
        fixed: optional dict of (x,y) → tile_name for pre-collapsed cells.
        Returns 2D list of tile names (x-major), or None if all attempts fail.
        """
        for attempt in range(self.MAX_ATTEMPTS):
            result = self._attempt(width, height, fixed)
            if result is not None and self.valid(result, width, height):
                return result
        return None

    def valid(self, grid, width, height) -> bool:
        """Check both directional constraints, including pre-collapsed singletons."""
        if len(grid) != width or any(len(col) != height for col in grid):
            return False
        for x in range(width):
            for y in range(height):
                tile = grid[x][y]
                if tile not in self._all_tiles:
                    return False
                for dx, dy, direction in ((0, -1, 'N'), (1, 0, 'E'), (0, 1, 'S'), (-1, 0, 'W')):
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < width and 0 <= ny < height:
                        if grid[nx][ny] not in self._adjacency.get(tile, {}).get(direction, []):
                            return False
        return True

    # ------------------------------------------------------------------ #

    def _attempt(
        self,
        width:  int,
        height: int,
        fixed:  "dict[tuple[int,int], str] | None",
    ) -> "list[list[str]] | None":
        # cells[x][y] = set of possible tile names
        cells: list[list[set[str]]] = [
            [set(self._tile_names) for _ in range(height)]
            for _ in range(width)
        ]

        # Apply fixed constraints
        if fixed:
            for (fx, fy), ftile in fixed.items():
                if 0 <= fx < width and 0 <= fy < height:
                    if ftile in self._all_tiles:
                        cells[fx][fy] = {ftile}
                    # Ignore unknown fixed tiles

        # Propagate fixed constraints
        queue: list[tuple[int, int]] = []
        if fixed:
            queue.extend(
                (fx, fy) for (fx, fy) in fixed
                if 0 <= fx < width and 0 <= fy < height
            )
        if queue:
            if not self._propagate(cells, queue, width, height):
                return None

        # Main WFC loop
        while True:
            # Find cell with lowest entropy > 1
            best_pos = None
            best_ent = len(self._tile_names) + 1
            for x in range(width):
                for y in range(height):
                    ent = len(cells[x][y])
                    if ent == 0:
                        return None   # contradiction
                    if 1 < ent < best_ent:
                        best_ent = ent
                        best_pos = (x, y)

            if best_pos is None:
                break   # all cells collapsed

            # Collapse: choose tile weighted by weights
            bx, by = best_pos
            possible = sorted(cells[bx][by])
            weights  = [self._tile_weights.get(t, 1) for t in possible]
            chosen   = self._rng.choices(possible, weights=weights, k=1)[0]
            cells[bx][by] = {chosen}

            # Propagate
            if not self._propagate(cells, [(bx, by)], width, height):
                return None

        # Extract result (take any element from each singleton set)
        return [
            [next(iter(cells[x][y])) if cells[x][y] else self._fallback
             for y in range(height)]
            for x in range(width)
        ]

    def _propagate(
        self,
        cells:  list[list[set[str]]],
        queue:  list[tuple[int, int]],
        width:  int,
        height: int,
    ) -> bool:
        """Constraint propagation. Returns False on contradiction."""
        DIRS = [
            (0, -1, "N", "S"),   # north neighbour uses N constraint; neighbour's S must allow us
            (1,  0, "E", "W"),
            (0,  1, "S", "N"),
            (-1, 0, "W", "E"),
        ]

        q = list(queue)
        while q:
            cx, cy = q.pop()
            cur_tiles = cells[cx][cy]

            for dx, dy, my_dir, their_dir in DIRS:
                nx, ny = cx + dx, cy + dy
                if not (0 <= nx < width and 0 <= ny < height):
                    continue

                # Compute allowed set: union of what cur_tiles allows in my_dir
                allowed: set[str] = set()
                for tile in cur_tiles:
                    allowed.update(
                        self._adjacency.get(tile, {}).get(my_dir, [])
                    )

                before = len(cells[nx][ny])
                cells[nx][ny] &= allowed
                after  = len(cells[nx][ny])

                if after == 0:
                    return False  # contradiction
                if after < before:
                    q.append((nx, ny))

        return True
