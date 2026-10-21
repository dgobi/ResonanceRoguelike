#!/usr/bin/env python3
"""
sprite_ref.py — Sprite Coordinate Reference Sheet Generator

Generates visual reference sheets for any 1-bit spritesheet PNG,
showing every tile with its column index for use in sprite_map.json.

Usage:
    python sprite_ref.py <spritesheet.png> [tile_w] [tile_h]

Examples:
    python sprite_ref.py urizen_onebit_tileset__v2d0-Sheet.png
    python sprite_ref.py urizen_onebit_tileset__v2d0-Sheet.png 12 12
    python sprite_ref.py my_sheet.png 8 8

Arguments:
    spritesheet.png  — path to the PNG file (must be in same folder or provide path)
    tile_w           — tile width in pixels (default: 12)
    tile_h           — tile height in pixels (default: 12)

Output:
    One or more PNG reference sheets named:
        <sheet_name>_ref_0000_0499.png
        <sheet_name>_ref_0500_0999.png
        etc.

    Each sheet shows 50 tiles per row with the column index printed below.
    Tiles are displayed as white-on-dark regardless of source format
    (handles both white-on-transparent and black-on-white input).

Notes:
    - col index is the value to use in sprite_map.json "col" field
    - row is always 0 for single-row sheets
    - For multi-row sheets, col = x position, row = y position from top-left
"""

import sys
import os
from pathlib import Path

try:
    from PIL import Image, ImageDraw
except ImportError:
    print("Error: Pillow is required. Install with: pip install Pillow")
    sys.exit(1)


TILES_PER_ROW  = 50
TILE_DISPLAY   = 24    # display size per tile in reference sheet (pixels)
LABEL_H        = 11    # height reserved for index label below each tile
PADDING        = 2     # gap between tiles
TILES_PER_SHEET = 500  # how many tiles per output file

BG_COLOR       = (22, 22, 32)     # reference sheet background
TILE_BG_COLOR  = (38, 38, 52)     # individual tile background
SPRITE_COLOR   = (220, 220, 200)  # sprite pixel color in reference
LABEL_COLOR    = (150, 150, 120)  # index label color
HEADER_COLOR   = (200, 200, 180)  # header text color


def detect_tile_format(img: Image.Image, tile_w: int, tile_h: int) -> str:
    """
    Detect whether the sheet is:
    - 'white_on_transparent' (RGBA, sprite=white, bg=transparent)
    - 'black_on_white'       (RGB or RGBA, sprite=black, bg=white)
    - 'white_on_black'       (RGB or RGBA, sprite=white, bg=black)
    """
    if img.mode != 'RGBA':
        img = img.convert('RGBA')

    # Sample first tile
    sample_pixels = []
    for dx in range(min(tile_w, img.width)):
        for dy in range(min(tile_h, img.height)):
            sample_pixels.append(img.getpixel((dx, dy)))

    transparent = sum(1 for p in sample_pixels if p[3] < 128)
    white       = sum(1 for p in sample_pixels if p[3] >= 128 and p[0] > 200)
    black       = sum(1 for p in sample_pixels if p[3] >= 128 and p[0] < 50)

    if transparent > len(sample_pixels) * 0.3:
        return 'white_on_transparent'
    elif black > white:
        return 'black_on_white'
    else:
        return 'white_on_black'

def extract_tile_as_display(
    img:    Image.Image,
    col:    int,
    row:    int,
    tile_w: int,
    tile_h: int,
    fmt:    str, # Kept for signature compatibility, though unused
) -> Image.Image:
    """
    Extract a single tile and preserve original colors.
    """
    x = col * tile_w
    y = row * tile_h

    # Out of bounds — return blank tile
    if x + tile_w > img.width or y + tile_h > img.height:
        return Image.new('RGB', (TILE_DISPLAY, TILE_DISPLAY), TILE_BG_COLOR)

    # Crop the original tile
    tile = img.crop((x, y, x + tile_w, y + tile_h))
    
    # Create a display tile with the reference background color
    # This ensures transparent sprites remain visible on the dark UI
    display = Image.new('RGBA', (tile_w, tile_h), TILE_BG_COLOR)
    display.paste(tile, (0, 0), tile if tile.mode == 'RGBA' else None)
    
    # Convert to RGB (removes alpha) and scale to display size
    scaled = display.convert('RGB').resize((TILE_DISPLAY, TILE_DISPLAY), Image.NEAREST)
    return scaled
# def extract_tile_as_display(
#     img:    Image.Image,
#     col:    int,
#     row:    int,
#     tile_w: int,
#     tile_h: int,
#     fmt:    str,
# ) -> Image.Image:
#     """
#     Extract a single tile and convert to white-on-dark for display.
#     Handles all three source formats.
#     """
#     x = col * tile_w
#     y = row * tile_h

#     if x + tile_w > img.width or y + tile_h > img.height:
#         # Out of bounds — return blank tile
#         blank = Image.new('RGB', (TILE_DISPLAY, TILE_DISPLAY), TILE_BG_COLOR)
#         return blank

#     tile = img.crop((x, y, x + tile_w, y + tile_h))
#     if tile.mode != 'RGBA':
#         tile = tile.convert('RGBA')

#     # Convert to display format: white sprite pixels on TILE_BG_COLOR background
#     display = Image.new('RGB', (tile_w, tile_h), TILE_BG_COLOR)
#     pixels_in  = tile.load()
#     pixels_out = display.load()

#     for px in range(tile_w):
#         for py in range(tile_h):
#             r, g, b, a = pixels_in[px, py]

#             if fmt == 'white_on_transparent':
#                 # White pixels = sprite, transparent = background
#                 if a > 128 and r > 128:
#                     pixels_out[px, py] = SPRITE_COLOR
#                 # else: keep TILE_BG_COLOR

#             elif fmt == 'black_on_white':
#                 # Black pixels = sprite, white = background
#                 if r < 128:
#                     pixels_out[px, py] = SPRITE_COLOR
#                 # else: keep TILE_BG_COLOR

#             elif fmt == 'white_on_black':
#                 # White pixels = sprite, black = background
#                 if r > 128 and a > 128:
#                     pixels_out[px, py] = SPRITE_COLOR
#                 # else: keep TILE_BG_COLOR

#     # Scale to display size
#     scaled = display.resize((TILE_DISPLAY, TILE_DISPLAY), Image.NEAREST)
#     return scaled


def generate_reference_sheets(
    sheet_path: str,
    tile_w:     int = 12,
    tile_h:     int = 12,
) -> None:
    path = Path(sheet_path)
    if not path.exists():
        print(f"Error: file not found: {sheet_path}")
        sys.exit(1)

    print(f"Loading: {path.name}")
    img = Image.open(path)
    if img.mode != 'RGBA':
        img = img.convert('RGBA')

    sheet_w, sheet_h = img.size
    cols_in_sheet = sheet_w // tile_w
    rows_in_sheet = sheet_h // tile_h
    total_tiles   = cols_in_sheet * rows_in_sheet

    print(f"Sheet size:  {sheet_w}×{sheet_h}px")
    print(f"Tile size:   {tile_w}×{tile_h}px")
    print(f"Grid:        {cols_in_sheet} cols × {rows_in_sheet} rows")
    print(f"Total tiles: {total_tiles}")

    fmt = detect_tile_format(img, tile_w, tile_h)
    print(f"Format:      {fmt}")

    # For single-row sheets: linear index = col
    # For multi-row sheets:  linear index = row * cols_in_sheet + col
    # Reference labels show the linear index (= col for single-row sheets)

    stem       = path.stem
    output_dir = Path.cwd()  # always write to current working directory
    n_sheets   = (total_tiles + TILES_PER_SHEET - 1) // TILES_PER_SHEET

    print(f"Generating {n_sheets} reference sheet(s)...")

    for sheet_idx in range(n_sheets):
        start = sheet_idx * TILES_PER_SHEET
        end   = min(start + TILES_PER_SHEET, total_tiles)
        count = end - start

        n_rows   = (count + TILES_PER_ROW - 1) // TILES_PER_ROW
        out_w    = TILES_PER_ROW * (TILE_DISPLAY + PADDING) + PADDING
        out_h    = n_rows * (TILE_DISPLAY + LABEL_H + PADDING) + PADDING + 24

        out_img  = Image.new('RGB', (out_w, out_h), BG_COLOR)
        draw     = ImageDraw.Draw(out_img)

        # Header
        if rows_in_sheet == 1:
            header = (f"{path.name}  |  tiles {start}–{end-1}"
                      f"  |  col=index, row=0  |  tile {tile_w}×{tile_h}px")
        else:
            header = (f"{path.name}  |  tiles {start}–{end-1}"
                      f"  |  {cols_in_sheet} cols × {rows_in_sheet} rows"
                      f"  |  tile {tile_w}×{tile_h}px")
        draw.text((PADDING, PADDING), header, fill=HEADER_COLOR)

        for i in range(count):
            linear_idx = start + i

            # Convert linear index to col/row on the sheet
            if rows_in_sheet == 1:
                tile_col = linear_idx
                tile_row = 0
            else:
                tile_col = linear_idx % cols_in_sheet
                tile_row = linear_idx // cols_in_sheet

            # Position in output image
            grid_col = i % TILES_PER_ROW
            grid_row = i // TILES_PER_ROW
            px = PADDING + grid_col * (TILE_DISPLAY + PADDING)
            py = 24 + PADDING + grid_row * (TILE_DISPLAY + LABEL_H + PADDING)

            # Extract and draw tile
            tile_surf = extract_tile_as_display(
                img, tile_col, tile_row, tile_w, tile_h, fmt
            )
            out_img.paste(tile_surf, (px, py))

            # Draw index label
            label = str(linear_idx)
            draw.text((px, py + TILE_DISPLAY + 1), label, fill=LABEL_COLOR)

        # Save
        out_name = f"{stem}_ref_{start:04d}_{end-1:04d}.png"
        out_path = output_dir / out_name
        out_img.save(out_path)
        print(f"  Saved: {out_name}")

    print("Done.")
    if rows_in_sheet == 1:
        print(f"\nUsage in sprite_map.json:")
        print(f'  "my_tile": {{"sheet": "urizen", "col": INDEX, "row": 0}}')
    else:
        print(f"\nUsage in sprite_map.json:")
        print(f'  "my_tile": {{"sheet": "name", "col": COL, "row": ROW}}')
        print(f"  Where col = index % {cols_in_sheet}, row = index // {cols_in_sheet}")


def main():
    args = sys.argv[1:]

    if not args or args[0] in ('-h', '--help'):
        print(__doc__)
        sys.exit(0)

    sheet_path = args[0]

    # If no path separator and no extension check in current dir
    if not os.path.dirname(sheet_path) and not Path(sheet_path).exists():
        # Try same directory as script
        script_dir = Path(__file__).parent
        candidate  = script_dir / sheet_path
        if candidate.exists():
            sheet_path = str(candidate)

    tile_w = int(args[1]) if len(args) > 1 else 12
    tile_h = int(args[2]) if len(args) > 2 else tile_w  # square by default

    generate_reference_sheets(sheet_path, tile_w, tile_h)


if __name__ == "__main__":
    main()
