import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

def generate_pro_reference(sheet_path: str, tile_w: int = 16, tile_h: int = 16) -> None:
    path = Path(sheet_path)
    if not path.exists():
        print(f"Error: file not found: {sheet_path}")
        sys.exit(1)

    # 1. Load Original (Full Color & Alpha)
    img = Image.open(path).convert('RGBA')
    sheet_w, sheet_h = img.size
    cols, rows = sheet_w // tile_w, sheet_h // tile_h

    # 2. Schematic Geometry
    # We create a "Cell" that looks like a technical UI element
    padding = 8
    header_h = 16
    
    cell_w = tile_w + (padding * 2)
    cell_h = tile_h + header_h + (padding * 2)
    
    # Final image dimensions
    new_w = (cols * cell_w) + (cols + 1)
    new_h = (rows * cell_h) + (rows + 1)

    # 3. Color Palette
    BG_MAIN    = (18, 18, 22, 255)   # Rich Obsidian
    GRID_OUTER = (45, 45, 55, 255)   # Steel Blue-Grey
    GRID_INNER = (30, 30, 40, 255)   # Subtle Separator
    TEXT_GOLD  = (210, 180, 110, 255) # Muted Technical Gold
    
    out_img = Image.new('RGBA', (new_w, new_h), BG_MAIN)
    draw = ImageDraw.Draw(out_img)
    
    try:
        font = ImageFont.load_default() 
    except:
        font = None

    print(f"Drafting Professional Schematic for {path.name}...")

    # 4. Draw the Schematic Grid
    for c in range(cols + 1):
        x = c * (cell_w + 1)
        draw.line([(x, 0), (x, new_h)], fill=GRID_OUTER, width=1)
    for r in range(rows + 1):
        y = r * (cell_h + 1)
        draw.line([(0, y), (new_w, y)], fill=GRID_OUTER, width=1)

    # 5. Populate Technical Cells
    for r in range(rows):
        for c in range(cols):
            # Calculate Cell Bounds
            cell_left = (c * (cell_w + 1)) + 1
            cell_top  = (r * (cell_h + 1)) + 1
            
            # Draw Internal Header Separator
            sep_y = cell_top + header_h
            draw.line([(cell_left, sep_y), (cell_left + cell_w - 1, sep_y)], fill=GRID_INNER, width=1)

            # Draw Label (Centered in Header)
            label = f"{c} : {r}"
            bbox = draw.textbbox((0, 0), label, font=font)
            tw = bbox[2] - bbox[0]
            th = bbox[3] - bbox[1]
            
            lx = cell_left + (cell_w // 2) - (tw // 2)
            ly = cell_top + (header_h // 2) - (th // 2) - 1
            draw.text((lx, ly), label, fill=TEXT_GOLD, font=font)

            # Paste Sprite (Centered in Viewport)
            src_x, src_y = c * tile_w, r * tile_h
            dst_x = cell_left + padding
            dst_y = sep_y + padding
            
            tile = img.crop((src_x, src_y, src_x + tile_w, src_y + tile_h))
            out_img.paste(tile, (dst_x, dst_y), tile)

    # 6. Final Polish & Save
    out_name = f"{path.stem}_PRO_SCHEMATIC.png"
    out_img.save(out_name)
    print(f"Success! Reference saved to: {out_name}")

if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        print("Usage: python sprite_ref.py <image> [tile_w] [tile_h]")
    else:
        p = args[0]
        tw = int(args[1]) if len(args) > 1 else 16
        th = int(args[2]) if len(args) > 2 else tw
        generate_pro_reference(p, tw, th)