"""Independent file checks for ART-1's retained MCP-authored trial.

Does not create creative pixels. Layer parsing follows the official format:
https://github.com/aseprite/aseprite/blob/main/docs/ase-file-specs.md
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct

from PIL import Image

LAB = Path(__file__).resolve().parents[1]


def source_info(path):
    data = path.read_bytes()
    size, magic, frames, width, height, depth = struct.unpack_from("<I5H", data)
    assert size == len(data) and magic == 0xA5E0, path
    assert (frames, width, height, depth) == (1, 32, 32, 32), path
    frame_size, frame_magic, old_count = struct.unpack_from("<IHH", data, 128)
    assert frame_magic == 0xF1FA and 128 + frame_size <= size, path
    count = struct.unpack_from("<I", data, 140)[0] or old_count
    cursor, layers, cels = 144, [], 0
    for _ in range(count):
        chunk_size, kind = struct.unpack_from("<IH", data, cursor)
        assert chunk_size >= 6 and cursor + chunk_size <= 128 + frame_size, path
        payload = cursor + 6
        if kind == 0x2004:
            flags, layer_type = struct.unpack_from("<HH", data, payload)
            length = struct.unpack_from("<H", data, payload + 16)[0]
            name = data[payload + 18:payload + 18 + length].decode("utf-8")
            layers.append({"name": name, "editable": bool(flags & 2), "type": layer_type})
        elif kind == 0x2005:
            cels += 1
        cursor += chunk_size
    assert len(layers) >= 2 and all(x["name"] and x["editable"] for x in layers), layers
    assert cels >= 2, path
    return {"dimensions": [width, height], "frames": frames, "depth": depth,
            "layers": layers, "cel_count": cels,
            "sha256": hashlib.sha256(data).hexdigest()}


def rgba(path):
    with Image.open(path) as image:
        assert image.format == "PNG", path
        return image.convert("RGBA")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--require-reopened", action="store_true",
                        help="Require the two .local PNGs re-exported by a live MCP reopen.")
    args = parser.parse_args()
    result = {"status": "passed", "assets": {}}
    files = sorted((LAB / "exports").glob("*.png"))
    assert files, "No exports to verify"
    for file in files:
        asset = file.stem.rsplit("_v", 1)[0]
        image = rgba(file)
        assert image.size == (32, 32), file
        alpha = image.getchannel("A")
        assert alpha.getextrema() == (0, 255) and alpha.getbbox(), file
        assert all(image.getpixel(p)[3] == 0 for p in [(0, 0), (31, 0), (0, 31), (31, 31)]), file
        source = LAB / "drafts" / asset / f"{file.stem}.aseprite"
        info = source_info(source)
        info.update({"transparent_pixels": alpha.tobytes().count(0),
                     "nontransparent_pixels": len(alpha.tobytes()) - alpha.tobytes().count(0),
                     "decoded_rgba_sha256": hashlib.sha256(image.tobytes()).hexdigest(),
                     "png_sha256": hashlib.sha256(file.read_bytes()).hexdigest()})
        preview = LAB / "previews" / f"{file.stem}_2x.png"
        if preview.exists():
            enlarged = rgba(preview)
            assert enlarged.size == (64, 64), preview
            assert enlarged.tobytes() == image.resize((64, 64), Image.Resampling.NEAREST).tobytes(), preview
            info["exact_2x_preview"] = True
        result["assets"][file.stem] = info
    before = rgba(LAB / "exports/diagnostic_v001.png")
    after = rgba(LAB / "exports/diagnostic_v002.png")
    changed = [(x, y) for y in range(32) for x in range(32) if before.getpixel((x, y)) != after.getpixel((x, y))]
    expected = [(15, 17), (16, 17), (15, 18), (16, 18)]
    assert changed == expected, changed
    for point in expected:
        assert before.getpixel(point) == (230, 80, 80, 255)
        assert after.getpixel(point) == (93, 228, 208, 255)
    result["diagnostic_correction"] = {"changed_pixels": changed, "before": "#e65050ff", "after": "#5de4d0ff", "other_pixels_preserved": True}
    beetles = sorted((LAB / "exports").glob("amber_sting_beetle_v*.png"))
    assert beetles, "No creative trial"
    if len(beetles) > 1:
        a, b = rgba(beetles[0]), rgba(beetles[-1])
        changed_count = sum(a.getpixel((x, y)) != b.getpixel((x, y)) for y in range(32) for x in range(32))
        assert changed_count > 0, "Revision did not change decoded pixels"
        result["beetle_revision_changed_pixels"] = changed_count
    result["live_reopen_comparisons"] = {}
    for name, original in [("diagnostic", LAB / "exports/diagnostic_v002.png"), ("beetle", beetles[-1])]:
        reopened = LAB / ".local" / f"{name}-reopened.png"
        if args.require_reopened:
            assert reopened.exists(), reopened
        if reopened.exists():
            a, b = rgba(original), rgba(reopened)
            assert a.size == b.size and a.tobytes() == b.tobytes(), reopened
            result["live_reopen_comparisons"][name] = "decoded RGBA equal"
        else:
            result["live_reopen_comparisons"][name] = "not rerun (local live-reopen export absent)"
    (LAB / "evidence").mkdir(exist_ok=True)
    (LAB / "evidence/file-validation.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"status": result["status"], "exports": len(files),
                      "correction_pixels": len(changed), "reopen": result["live_reopen_comparisons"]}))


if __name__ == "__main__":
    main()
