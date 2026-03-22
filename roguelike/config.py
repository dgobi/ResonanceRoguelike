# config.py

# --- Display ---
TITLE = "Roguelike"

# --- Font ---
# Path to the font/tileset file.
# Can be any tcod-compatible tilesheet in assets/fonts/
# or eventually a spritesheet in assets/sprites/
FONT_PATH      = "assets/fonts/dejavu10x10_gs_tc.png"
FONT_COLUMNS   = 32   # glyphs across the sheet
FONT_ROWS      = 8    # glyphs down the sheet
FONT_TYPE      = "tcod"  # "tcod" | "cp437" | "sprite" (future)

# Tile size is READ from the font file automatically —
# we don't hardcode it. The engine queries it after load.

# --- Zoom ---
# Integer scale multiplier applied on top of the font's native size.
# 1 = native size, 2 = 2x, 3 = 3x, etc.
# At runtime this is changed via options menu and calls
# context.change_tileset() with a rescaled tileset.
ZOOM_LEVEL = 2

# --- Render mode ---
# "ascii"    → use ASCII characters from tiles.json
# "sprite"   → use sprite sheet coordinates (future)
RENDER_MODE = "ascii"

# --- Map ---
MAP_WIDTH  = 80
MAP_HEIGHT = 43

# --- FOV ---
FOV_RADIUS      = 8    # used as default when no light source data available
DARK_VISION_RADIUS = 1 # tiles visible with no light source

# --- FPS ---
FPS = 20

# --- Debug ---
DEBUG_MODE = True   # set False for release builds

RENDER_MODE = "sprite"
ZOOM_LEVEL  = 2    # 3× zoom → 24px tiles, comfortable on modern monitors
FONT_PATH   = "assets/fonts/dejavu10x10_gs_tc.png"  # keep for ASCII fallback

# --- UI Layout ---
MSG_PANEL_W       = 300   # width of right-side message panel in pixels
STATUS_BAR_H      = 120   # height of bottom status bar in pixels
UI_PANEL_INSET    = 24    # px from panel edge where content starts
OVERMAP_SIDEBAR_W = 320   # width of overmap info sidebar in pixels