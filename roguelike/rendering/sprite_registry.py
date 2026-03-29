# rendering/sprite_registry.py
from __future__ import annotations
import json
import pygame
from pathlib import Path


class SpriteSheet:
    """
    A loaded 1-bit sprite sheet.
    Sprites are white-on-transparent.
    Tinting is applied at draw time via BLEND_RGBA_MULT.
    """

    def __init__(self, path: str, tile_w: int = 8, tile_h: int = 8) -> None:
        self.path   = path
        self.tile_w = tile_w
        self.tile_h = tile_h
        self._sheet: pygame.Surface | None = None
        self._cache: dict[tuple[int,int], pygame.Surface] = {}

    def load(self) -> None:
        self._sheet = pygame.image.load(self.path).convert_alpha()

    @property
    def loaded(self) -> bool:
        return self._sheet is not None

    def get_tile(self, col: int, row: int) -> "pygame.Surface | None":
        key = (col, row)
        if key in self._cache:
            return self._cache[key]
        if not self._sheet:
            raise RuntimeError(f"Sheet not loaded: {self.path}")
        x    = col * self.tile_w
        y    = row * self.tile_h
        tile = pygame.Surface((self.tile_w, self.tile_h), pygame.SRCALPHA)
        tile.blit(self._sheet, (0, 0),
                pygame.Rect(x, y, self.tile_w, self.tile_h))
        # Detect completely transparent (blank) tiles — return None so the
        # registry can substitute the universal placeholder sprite.
        br = tile.get_bounding_rect()
        if br.width == 0 or br.height == 0:
            self._cache[key] = None
            return None
        self._cache[key] = tile
        return tile


class SpriteRegistry:
    """
    Loads sprite_map.json and serves tinted tile surfaces.

    1-bit coloring model:
      - Sprites are white pixels on transparent background
      - fg_color is multiplied onto the white pixels → any color
      - bg_color is drawn as a solid rect beneath the sprite
      - Lighting tint is applied on top of fg_color

    Adding new sheets:
      - Add sheet entry to sprite_map.json "sheets" section
      - Place PNG in assets/sprites/
      - Add tile entries referencing the new sheet id
      - No code changes needed
    """

    def __init__(
        self,
        sprite_map_path: str = "data/sprites/sprite_map.json",
    ) -> None:
        self._map:    dict                    = {}
        self._sheets: dict[str, SpriteSheet] = {}
        self._path    = sprite_map_path
        self._loaded  = False

    def load(self) -> None:
        """Load all sheets. Call after pygame display is initialized."""
        path = Path(self._path)
        if not path.exists():
            print(f"Warning: sprite map not found: {self._path}")
            return

        with open(path, encoding="utf-8") as f:
            data = json.load(f)

        for sheet_id, sheet_def in data.get("sheets", {}).items():
            sheet = SpriteSheet(
                path   = sheet_def["file"],
                tile_w = sheet_def.get("tile_w", 8),
                tile_h = sheet_def.get("tile_h", 8),
            )
            try:
                sheet.load()
                self._sheets[sheet_id] = sheet
                print(f"  Loaded sheet '{sheet_id}': {sheet_def['file']}")
            except Exception as e:
                print(f"  Warning: failed to load sheet '{sheet_id}': {e}")

        self._map    = data.get("tiles", {})
        self._loaded = True
        print(f"SpriteRegistry: {len(self._map)} tiles across "
              f"{len(self._sheets)} sheets")

    def _get_placeholder_raw(self) -> "pygame.Surface | None":
        """Return the universal placeholder sprite (? glyph at terrain col 1 row 7)."""
        ph = self._map.get("sprite_placeholder")
        if not ph:
            return None
        sheet = self._sheets.get(ph["sheet"])
        if not sheet:
            return None
        return sheet.get_tile(ph["col"], ph["row"])

    def has(self, tile_id: str) -> bool:
        return self._loaded and tile_id in self._map

    def get_tinted(
        self,
        tile_id:  str,
        fg_color: tuple[int, int, int],
        zoom:     int = 1,
    ) -> pygame.Surface | None:
        """
        Return a tinted sprite surface.
        fg_color is applied as a multiply tint over white pixels.
        zoom: integer scale, nearest-neighbour.
        """
        if not self._loaded or tile_id not in self._map:
            return None

        mapping  = self._map[tile_id]
        sheet_id = mapping["sheet"]
        sheet    = self._sheets.get(sheet_id)
        if not sheet:
            return None

        col = mapping["col"]
        row = mapping["row"]
        tw  = mapping.get("tile_w", sheet.tile_w)
        th  = mapping.get("tile_h", sheet.tile_h)

        # Get raw white-on-transparent tile (None = blank/invisible tile)
        raw = sheet.get_tile(col, row)
        if raw is None:
            raw = self._get_placeholder_raw()
            if raw is None:
                return None

        # Apply fg tint via multiply blend
        tinted = raw.copy()
        tint   = pygame.Surface((tw, th), pygame.SRCALPHA)
        tint.fill((*fg_color, 255))
        tinted.blit(tint, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)

        if zoom == 1:
            return tinted

        return pygame.transform.scale(
            tinted, (tw * zoom, th * zoom)
        )

    def tile_size(self, tile_id: str | None = None) -> tuple[int, int]:
        """Return (w, h) of a tile at native size."""
        if tile_id and tile_id in self._map:
            mapping  = self._map[tile_id]
            sheet_id = mapping["sheet"]
            sheet    = self._sheets.get(sheet_id)
            if sheet:
                return (
                    mapping.get("tile_w", sheet.tile_w),
                    mapping.get("tile_h", sheet.tile_h),
                )
        if self._sheets:
            s = next(iter(self._sheets.values()))
            return (s.tile_w, s.tile_h)
        return (8, 8)

    def remap(
        self,
        tile_id:  str,
        sheet_id: str,
        col:      int,
        row:      int,
    ) -> None:
        """
        Remap a tile at runtime.
        Used for live coordinate correction without restart.
        """
        if sheet_id not in self._sheets:
            print(f"Warning: sheet '{sheet_id}' not loaded")
            return
        self._map[tile_id] = {
            "sheet": sheet_id,
            "col":   col,
            "row":   row,
        }
        # Bust cache for that tile
        sheet = self._sheets[sheet_id]
        sheet._cache.pop((col, row), None)

    def save_map(self, path: str | None = None) -> None:
        """
        Save current tile mappings back to JSON.
        Useful after live remapping sessions.
        """
        out_path = Path(path or self._path)
        data = {
            "sheets": {
                sid: {
                    "file":   sheet.path,
                    "tile_w": sheet.tile_w,
                    "tile_h": sheet.tile_h,
                }
                for sid, sheet in self._sheets.items()
            },
            "tiles": self._map,
        }
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        print(f"Sprite map saved to {out_path}")

    def all_tile_ids(self) -> list[str]:
        return list(self._map.keys())
    
    def get(
        self,
        tile_id: str,
        zoom:    int = 1,
    ) -> pygame.Surface | None:
        """
        Return the raw sprite surface with no colour tinting applied.
        Used in full-colour mode (use_sprite_tint = False).
        zoom: integer scale, nearest-neighbour.
        """
        if not self._loaded or tile_id not in self._map:
            return None

        mapping  = self._map[tile_id]
        sheet_id = mapping["sheet"]
        sheet    = self._sheets.get(sheet_id)
        if not sheet:
            return None

        col = mapping["col"]
        row = mapping["row"]
        tw  = mapping.get("tile_w", sheet.tile_w)
        th  = mapping.get("tile_h", sheet.tile_h)

        raw = sheet.get_tile(col, row)
        if raw is None:
            raw = self._get_placeholder_raw()
            if raw is None:
                return None

        if zoom == 1:
            return raw

        return pygame.transform.scale(raw, (tw * zoom, th * zoom))

    def get_at_coords(
        self,
        sheet_id: str,
        col:      int,
        row:      int,
        zoom:     int = 1,
    ) -> pygame.Surface | None:
        """
        Return a raw sprite surface directly by sheet + col + row.
        Used for entities that store their own sprite coordinates
        (e.g. corpses) rather than a registry tile_id.
        """
        if not self._loaded:
            return None
        sheet = self._sheets.get(sheet_id)
        if not sheet:
            return None
        raw = sheet.get_tile(col, row)
        if raw is None:
            raw = self._get_placeholder_raw()
            if raw is None:
                return None
        if zoom == 1:
            return raw
        tw = sheet.tile_w
        th = sheet.tile_h
        return pygame.transform.scale(raw, (tw * zoom, th * zoom))