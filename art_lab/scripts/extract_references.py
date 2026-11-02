"""Crop current registered game cells; never writes to the game's asset tree."""
import hashlib
import json
from pathlib import Path
import subprocess

from PIL import Image, ImageDraw

LAB = Path(__file__).resolve().parents[1]
ROOT = LAB.parent
IDS = ["player", "hollow_revenant", "heath_stalker", "amber_sting_beetle",
       "oil_lantern", "water_flask", "cracked_bell", "floor", "ancient_floor",
       "wall", "wall_1", "wall_2", "wall_3", "sprite_placeholder"]


def main():
    mapping_path = ROOT / "roguelike/data/sprites/sprite_map.json"
    mapping = json.loads(mapping_path.read_text())
    out = LAB / "references"
    (out / "crops").mkdir(parents=True, exist_ok=True)
    (out / "enlarged").mkdir(exist_ok=True)
    placeholder = mapping["tiles"]["sprite_placeholder"]
    records = []
    sheet = Image.new("RGB", (960, 4 * 148), "#20242b")
    draw = ImageDraw.Draw(sheet)
    for i, asset in enumerate(IDS):
        cell = mapping["tiles"][asset]
        spec = mapping["sheets"][cell["sheet"]]
        source = ROOT / "roguelike" / spec["file"]
        image = Image.open(source).convert("RGBA")
        w, h = spec["tile_w"], spec["tile_h"]
        x, y = cell["col"] * w, cell["row"] * h
        assert x + w <= image.width and y + h <= image.height, (asset, image.size)
        crop = image.crop((x, y, x + w, y + h))
        is_placeholder = cell == placeholder
        crop.save(out / "crops" / f"{asset}.png")
        enlarged = crop.resize((w * 4, h * 4), Image.Resampling.NEAREST)
        enlarged.save(out / "enlarged" / f"{asset}_4x.png")
        left, top = (i % 4) * 240 + 12, (i // 4) * 148 + 10
        draw.text((left, top), asset, fill="white")
        draw.text((left, top + 16), f"{cell['sheet']} [{cell['col']},{cell['row']}] {w}x{h}", fill="#c3c9d0")
        draw.text((left, top + 32), "PLACEHOLDER: not a design" if is_placeholder else "Source crop; native + exact 4x", fill="#ffbe6e" if is_placeholder else "#a7b5b9")
        sheet.paste(crop, (left, top + 60), crop)
        sheet.paste(enlarged, (left + 40, top + 54), enlarged)
        records.append({"id": asset, "mapping": cell, "source": source.relative_to(ROOT).as_posix(),
                        "sheet_size": list(image.size), "sheet_columns": image.width // w,
                        "crop_box": [x, y, x + w, y + h], "native_size": [w, h],
                        "placeholder": is_placeholder,
                        "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest()})
    sheet.save(out / "contact-sheet.png")
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    manifest = {"source_revision": revision, "mapping": mapping_path.relative_to(ROOT).as_posix(),
                "mapping_sha256": hashlib.sha256(mapping_path.read_bytes()).hexdigest(),
                "enlargement": "Exact nearest-neighbor 4x; these are existing 16px references, not new 32px art.",
                "entries": records}
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"Extracted {len(records)} references from {revision}; placeholders explicitly marked.")


if __name__ == "__main__":
    main()
