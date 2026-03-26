# rendering/tile_registry.py
from __future__ import annotations
import json
from pathlib import Path


class TileRegistry:
    """
    Loads tiles.json and serves visual data on request.
    The renderer never hardcodes colors or characters —
    it always asks the registry.

    Supports two modes (set in config.py):
      "ascii"     → returns character + colors
      "graphical" → returns sprite sheet coordinates (future)
    """

    def __init__(self, path: str = "data/tiles.json", mode: str = "ascii") -> None:
        self.mode = mode
        with open(Path(path), encoding="utf-8") as f:
            raw = json.load(f)
        # tiles.json wraps all entries under a "tiles" key alongside palette metadata
        self._data: dict = raw.get("tiles", raw)

    def get(self, tile_name: str) -> dict:
        """Return the full tile definition for a given tile name."""
        if tile_name not in self._data:
            raise KeyError(f"Tile '{tile_name}' not found in registry.")
        return self._data[tile_name]

    def char(self, tile_name: str) -> int:
        """Return the integer codepoint of the ASCII character for this tile.
        Handles both the rich format ("ascii": "<char>") and the compact
        format ("char": <codepoint int>) used by newer tile entries."""
        data = self._data.get(tile_name)
        if data is None:
            print(f"[tile_registry] unknown tile: {tile_name}")
            return ord("?")
        if "ascii" in data:
            return ord(data["ascii"])
        if "char" in data:
            return int(data["char"])
        print(f"[tile_registry] tile missing ascii/char: {tile_name}")
        return ord("?")

    def fg(self, tile_name: str, dark: bool = False) -> tuple[int, int, int]:
        """Return foreground RGB. dark=True for out-of-FOV version."""
        key = "color_fg_dark" if dark else "color_fg"
        return tuple(self._data[tile_name][key])

    def bg(self, tile_name: str, dark: bool = False) -> tuple[int, int, int]:
        """Return background RGB. dark=True for out-of-FOV version."""
        key = "color_bg_dark" if dark else "color_bg"
        return tuple(self._data[tile_name][key])

    def sprite(self, tile_name: str) -> tuple[int, int]:
        """Return [col, row] sprite sheet coordinates for graphical mode."""
        s = self._data[tile_name]["sprite"]
        return (s[0], s[1])

    def register(self, tile_name: str, definition: dict) -> None:
        """
        Programmatically register a new tile at runtime.
        Useful for procedurally generated or modded content.
        """
        self._data[tile_name] = definition

    def all_names(self) -> list[str]:
        return list(self._data.keys())