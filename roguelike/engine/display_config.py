# engine/display_config.py
from __future__ import annotations
from pathlib import Path
import pygame


class FontSheet:
    """
    A loaded character sheet — either a tcod-style glyph grid
    or eventually a sprite sheet.
    Provides get_glyph(char) → pygame.Surface.
    """

    def __init__(
        self,
        path:       str,
        columns:    int = 32,
        rows:       int = 8,
        sheet_type: str = "tcod",
    ) -> None:
        self.path       = path
        self.columns    = columns
        self.rows       = rows
        self.sheet_type = sheet_type
        self.name       = Path(path).stem

        self._sheet: pygame.Surface | None = None
        self._tile_w: int = 0
        self._tile_h: int = 0
        self._glyph_cache: dict[int, pygame.Surface] = {}

    def load(self) -> None:
        """Load the sheet image and compute tile dimensions."""
        raw = pygame.image.load(self.path).convert_alpha()
        self._sheet  = raw
        self._tile_w = raw.get_width()  // self.columns
        self._tile_h = raw.get_height() // self.rows

    @property
    def tile_width(self) -> int:
        return self._tile_w

    @property
    def tile_height(self) -> int:
        return self._tile_h

    def get_glyph(self, codepoint: int) -> pygame.Surface:
        """
        Return the glyph surface for a given codepoint.
        Uses the TCOD charmap layout: glyphs are arranged
        in a 32x8 grid matching the TCOD character map order.
        """
        if codepoint in self._glyph_cache:
            return self._glyph_cache[codepoint]

        # TCOD charmap: codepoint maps to grid position
        # The sheet is 32 columns x 8 rows = 256 glyphs
        # We use the raw index from the TCOD charmap
        idx = self._tcod_charmap_index(codepoint)
        if idx is None:
            # Return blank tile
            surf = pygame.Surface((self._tile_w, self._tile_h),
                                  pygame.SRCALPHA)
            return surf

        col = idx % self.columns
        row = idx // self.columns
        x   = col * self._tile_w
        y   = row * self._tile_h

        glyph = pygame.Surface((self._tile_w, self._tile_h),
                                pygame.SRCALPHA)
        glyph.blit(self._sheet, (0, 0),
                   pygame.Rect(x, y, self._tile_w, self._tile_h))

        self._glyph_cache[codepoint] = glyph
        return glyph

    def get_glyph_char(self, char: str) -> pygame.Surface:
        return self.get_glyph(ord(char))

    @staticmethod
    def _tcod_charmap_index(codepoint: int) -> int | None:
        """
        Map a Unicode codepoint to its index in the TCOD charmap grid.
        The TCOD charmap maps glyphs in a specific order defined by
        tcod.tileset.CHARMAP_TCOD. We replicate the key mappings here.
        """
        import tcod.tileset
        charmap = tcod.tileset.CHARMAP_TCOD
        try:
            return charmap.index(codepoint)
        except (ValueError, AttributeError):
            # Fall back to direct ASCII for printable characters
            if 32 <= codepoint <= 126:
                return codepoint
            return None

    @property
    def loaded(self) -> bool:
        return self._sheet is not None


class DisplayConfig:
    """
    Manages all display settings independently:
      - Font sheet selection (any file in fonts dir)
      - Zoom level (integer scale, always nearest-neighbour crisp)
      - Render mode (ascii / sprite)

    Font and zoom are fully decoupled.
    The options menu talks exclusively to this object.
    """

    def __init__(
        self,
        font_path:    str,
        font_columns: int  = 32,
        font_rows:    int  = 8,
        font_type:    str  = "tcod",
        zoom_level:   int  = 2,
        render_mode:  str  = "ascii",
        font_dir:     str  = "assets/Fonts",
    ) -> None:
        self.font_dir    = font_dir
        self.zoom_level  = max(1, zoom_level)
        self.render_mode = render_mode

        self._font_sheet = FontSheet(
            font_path, font_columns, font_rows, font_type
        )

        # UI fonts — None until init() is called after pygame.init()
        self.font_ui_large:      pygame.font.Font | None = None
        self.font_ui_normal:     pygame.font.Font | None = None
        self.font_ui_small:      pygame.font.Font | None = None
        self.font_ui_tiny:       pygame.font.Font | None = None
        self.font_ui_italic:     pygame.font.Font | None = None
        self.font_ui_bold:       pygame.font.Font | None = None
        self.font_ui_bold_large:    pygame.font.Font | None = None
        self.font_deep:             pygame.font.Font | None = None
        # Callout / floating text fonts — populated in init()
        self.font_callout_damage:   "pygame.font.Font | None" = None
        self.font_callout_status:   "pygame.font.Font | None" = None
        self.font_callout_creature: "pygame.font.Font | None" = None
        self.font_callout_crit:     "pygame.font.Font | None" = None
        self.CALLOUT_FONTS: dict = {}
        self.use_sprite_tint = False

        # Callout visibility toggles
        self.CALLOUT_DAMAGE_NUMBERS:  bool = True
        self.CALLOUT_CREATURE_SOUNDS: bool = True
        self.CALLOUT_STATUS_EFFECTS:  bool = True

        # Sprint constants
        self.SPRINT_KEY:          int   = pygame.K_w  # Shift+this key activates sprint
        self.SPRINT_DURATION:     int   = 8     # turns of sprint effect
        self.SPRINT_COOLDOWN:     int   = 30    # turns before sprint available again
        self.SPRINT_SPEED_MULT:   float = 2.0   # player moves twice per action
        self.SPRINT_HIT_PENALTY:  float = -0.25 # damage multiplier during sprint (additive)

        # Moveset keys
        self.MOVESET_KEY_1: int = pygame.K_q  # First moveset action
        self.MOVESET_KEY_2: int = pygame.K_r  # Second moveset action

    def init(self, *, project_root=None, typography_candidate=None) -> None:
        """Initialize fonts before consumers cache their objects and metrics."""
        from engine.typography import initialize
        root = Path(project_root) if project_root is not None else Path(__file__).resolve().parents[2]
        loaded = initialize(root, typography_candidate)
        self._font_sheet.load()
        for role, font in loaded["fonts"].items():
            setattr(self, role, font)
        self.font_coverage = loaded["coverage"]
        self.typography = {key: value for key, value in loaded.items() if key not in ("fonts", "coverage")}
        self.CALLOUT_FONTS = {
            "damage":   self.font_callout_damage,
            "status":   self.font_callout_status,
            "creature": self.font_callout_creature,
            "crit":     self.font_callout_crit,
            "levelup":  self.font_callout_levelup,
            "small":    self.font_callout_damage,    # alias
            "tiny":     self.font_callout_creature,  # alias
        }

    # ------------------------------------------------------------------ #
    #  Font discovery
    # ------------------------------------------------------------------ #

    def discover_fonts(self) -> list[FontSheet]:
        """
        Scan font_dir and return a FontSheet for every valid image.
        Not yet loaded — call sheet.load() before use.
        """
        d = Path(self.font_dir)
        if not d.exists():
            return []
        return [
            FontSheet(str(p))
            for p in sorted(d.iterdir())
            if p.suffix.lower() in {".png", ".bmp"}
        ]

    # ------------------------------------------------------------------ #
    #  Active font
    # ------------------------------------------------------------------ #

    @property
    def font_sheet(self) -> FontSheet:
        return self._font_sheet

    @property
    def tile_width(self) -> int:
        return self._font_sheet.tile_width * self.zoom_level

    @property
    def tile_height(self) -> int:
        return self._font_sheet.tile_height * self.zoom_level

    @property
    def current_font_name(self) -> str:
        return self._font_sheet.name

    # ------------------------------------------------------------------ #
    #  Runtime changes
    # ------------------------------------------------------------------ #

    def set_font(self, font_sheet: FontSheet) -> None:
        """Switch font. Zoom is preserved."""
        if not font_sheet.loaded:
            font_sheet.load()
        self._font_sheet = font_sheet

    def set_zoom(self, level: int) -> None:
        self.zoom_level = max(1, min(8, level))

    def zoom_in(self) -> None:
        self.set_zoom(self.zoom_level + 1)

    def zoom_out(self) -> None:
        self.set_zoom(self.zoom_level - 1)

    def set_render_mode(self, mode: str) -> None:
        self.render_mode = mode

    # ------------------------------------------------------------------ #
    #  Serialisation
    # ------------------------------------------------------------------ #

    def to_dict(self) -> dict:
        return {
            "font_path":    self._font_sheet.path,
            "font_columns": self._font_sheet.columns,
            "font_rows":    self._font_sheet.rows,
            "font_type":    self._font_sheet.sheet_type,
            "zoom_level":   self.zoom_level,
            "render_mode":  self.render_mode,
        }

    @classmethod
    def from_dict(cls, d: dict) -> DisplayConfig:
        return cls(**{
            "font_path":    d.get("font_path",
                                  "assets/Fonts/dejavu10x10_gs_tc.png"),
            "font_columns": d.get("font_columns", 32),
            "font_rows":    d.get("font_rows",    8),
            "font_type":    d.get("font_type",    "tcod"),
            "zoom_level":   d.get("zoom_level",   2),
            "render_mode":  d.get("render_mode",  "ascii"),
        })

    @classmethod
    def from_config(cls) -> DisplayConfig:
        from config import (
            FONT_PATH, FONT_COLUMNS, FONT_ROWS,
            FONT_TYPE, ZOOM_LEVEL, RENDER_MODE,
        )
        return cls(
            font_path    = FONT_PATH,
            font_columns = FONT_COLUMNS,
            font_rows    = FONT_ROWS,
            font_type    = FONT_TYPE,
            zoom_level   = ZOOM_LEVEL,
            render_mode  = RENDER_MODE,
        )
    
    @property
    def tile_width(self) -> int:
        return self.font_sheet.tile_width * self.zoom_level

    @property
    def tile_height(self) -> int:
        return self.font_sheet.tile_height * self.zoom_level

    def line_height(self, font_key: str = "normal") -> int:
        """Return line height for layout calculations."""
        fonts = {
            "large":      self.font_ui_large,
            "normal":     self.font_ui_normal,
            "small":      self.font_ui_small,
            "tiny":       self.font_ui_tiny,
            "bold":       self.font_ui_bold,
            "bold_large": self.font_ui_bold_large,
        }
        f = fonts.get(font_key, self.font_ui_normal)
        return f.get_linesize() if f else 18

    def status_bar_height(self) -> int:
        """Minimum height for the status bar based on current font."""
        from config import UI_PANEL_INSET
        lh = self.line_height("tiny")
        return max(120, lh * 3 + UI_PANEL_INSET * 2)

    def icon_size(self) -> int:
        """Sprite icon size at current zoom (matches 8px sprite × zoom)."""
        return self.zoom_level * 8

    def context_strip_height(self) -> int:
        """Context strip is eliminated. Returns 0."""
        return 0

    def effective_tile_size(
        self,
        sprite_registry: "SpriteRegistry | None" = None,
    ) -> tuple[int, int]:
        """
        Returns tile size in pixels accounting for zoom.
        Uses sprite sheet size in sprite mode, font size in ASCII mode.
        """
        if (self.render_mode == "sprite" and
                sprite_registry is not None and
                sprite_registry._loaded):
            tw, th = sprite_registry.tile_size()
            return tw * self.zoom_level, th * self.zoom_level
        return self.tile_width, self.tile_height