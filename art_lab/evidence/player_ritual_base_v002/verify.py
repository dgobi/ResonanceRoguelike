"""Independent read-only artwork checks; writes the validation receipt only."""
import hashlib
import json
from pathlib import Path
import struct
import zlib
from PIL import Image

HERE = Path(__file__).resolve().parent
LAB = HERE.parents[1]
STEM = 'player_ritual_base_v002'
LIVE = json.loads((HERE / 'live-state.json').read_text())
SOURCE = LAB / 'drafts/player_ritual_base' / (STEM + '.aseprite')
PNG = LAB / 'exports' / (STEM + '.png')

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def canonical(data):
    out = bytearray(data)
    for i in range(0, len(out), 4):
        if not out[i+3]:
            out[i:i+3] = b'\0\0\0'
    return bytes(out)

def decode_source(path):
    data = path.read_bytes()
    size, magic, frames, width, height, depth = struct.unpack_from('<I5H', data)
    assert size == len(data) and magic == 0xA5E0
    assert (frames, width, height, depth) == (1, 32, 32, 32)
    frame_size, frame_magic, old_count = struct.unpack_from('<IHH', data, 128)
    assert frame_magic == 0xF1FA and 128 + frame_size == len(data)
    count = struct.unpack_from('<I', data, 140)[0] or old_count
    at, layers, cels = 144, [], []
    for _ in range(count):
        n, kind = struct.unpack_from('<IH', data, at)
        assert n >= 6 and at+n <= len(data)
        payload = data[at+6:at+n]
        if kind == 0x2004:
            flags, layer_type = struct.unpack_from('<HH', payload)
            assert flags & 3 == 3 and layer_type == 0
            assert struct.unpack_from('<H', payload, 10)[0] == 0 and payload[12] == 255
            length = struct.unpack_from('<H', payload, 16)[0]
            layers.append(payload[18:18+length].decode())
        elif kind == 0x2005:
            layer, x, y, opacity, cel_type = struct.unpack_from('<HhhBH', payload)
            assert opacity == 255 and cel_type in (0, 2)
            w, h = struct.unpack_from('<HH', payload, 16)
            rgba = zlib.decompress(payload[20:]) if cel_type == 2 else payload[20:]
            assert len(rgba) == w*h*4
            cels.append((layer, x, y, w, h, rgba))
        at += n
    assert len(layers) == len(cels) == 12
    assert layers == [x['name'] for x in LIVE['info']['layers']]
    out, by_layer = bytearray(32*32*4), {}
    for layer, x0, y0, w, h, rgba in sorted(cels):
        coords = set()
        for y in range(h):
            for x in range(w):
                src = (y*w+x)*4
                assert rgba[src+3] in (0, 255)
                if rgba[src+3]:
                    xx, yy = x+x0, y+y0
                    assert 0 <= xx < 32 and 0 <= yy < 32
                    dst = (yy*32+xx)*4
                    out[dst:dst+4] = rgba[src:src+4]
                    coords.add((xx, yy))
        assert coords
        by_layer[layers[layer]] = coords
    return canonical(out), layers, by_layer

with Image.open(PNG) as file:
    assert file.format == 'PNG' and file.size == (32, 32)
    im = file.convert('RGBA')
pixels = canonical(im.tobytes())
source_pixels, layers, by_layer = decode_source(SOURCE)
assert pixels == source_pixels
live_pixels = bytearray()
for n in LIVE['pixels']['grid']:
    color = LIVE['pixels']['colors'][n].lstrip('#')
    live_pixels.extend(bytes.fromhex(color if len(color) == 8 else color+'ff'))
assert pixels == canonical(live_pixels)
assert LIVE['info']['modified'] is False and LIVE['info']['frameCount'] == 1
alpha = im.getchannel('A')
assert set(alpha.tobytes()) == {0, 255}
bbox = alpha.getbbox()
assert bbox == (8, 2, 26, 30), bbox
opaque = {(x,y) for y in range(32) for x in range(32) if alpha.getpixel((x,y))}
assert all(0 < x < 31 and 0 < y < 31 for x,y in opaque)
seen, pending = set(), [next(iter(opaque))]
while pending:
    p = pending.pop()
    if p in seen:
        continue
    seen.add(p)
    pending.extend((p[0]+dx,p[1]+dy) for dx in (-1,0,1) for dy in (-1,0,1)
                   if (p[0]+dx,p[1]+dy) in opaque-seen)
assert seen == opaque, 'Disconnected silhouette pixels'
# Actual transparent corridors, including the hanging hand at upper-thigh height.
for y in range(12,21):
    assert (11,y) not in opaque, ('rear arm/hand gap',y)
for y in range(20,29):
    assert (15,y) not in opaque, ('leg gap',y)
assert (16,29) not in opaque, 'Gap between right-pointing feet'
for point in ((18,13),(18,14),(18,15),(19,16),(22,13),(23,13)):
    assert point not in opaque, ('forward arm clearance',point)
assert {(9,18),(8,19),(9,19),(10,19),(9,20),(10,20)} <= by_layer['body-arm-hanging-left']
assert {(24,13),(24,14),(25,14),(24,15),(25,15)} <= by_layer['body-arm-reaching-right']
for layer in ('body-leg-rear','body-leg-forward'):
    assert max(y for x,y in by_layer[layer]) == 29
assert max(x for x,y in by_layer['body-leg-rear'] if y == 29) > max(x for x,y in by_layer['body-leg-rear'] if y == 27)
assert max(x for x,y in by_layer['body-leg-forward'] if y == 29) > max(x for x,y in by_layer['body-leg-forward'] if y == 27)
colors = sorted({'#'+bytes(im.getpixel(p)[:3]).hex() for p in opaque})
assert colors == sorted(c.lower() for c in LIVE['workingColors'].values())
previews = {}
for scale in (1,2,8):
    path = LAB / 'previews' / f'{STEM}_{scale}x.png'
    with Image.open(path) as p:
        assert p.size == (32*scale,32*scale)
        assert canonical(p.convert('RGBA').tobytes()) == canonical(im.resize(p.size,Image.Resampling.NEAREST).tobytes())
        previews[f'{scale}x'] = {'dimensions':list(p.size),'exact_nearest_neighbor':True,'sha256':digest(path)}
preservation_path = LAB / '.local/player-v002-owner-before.json'
if preservation_path.exists():
    baseline = json.loads(preservation_path.read_text())
    assert all(digest(LAB.parent / p) == h for p,h in baseline.items())
    preserved = len(baseline)
else:
    preserved = 'Local baseline absent; not rerun'
result = {
    'status':'passed', 'authoring':'Live Aseprite MCP, sprite #11; arbitrary Lua disabled',
    'dimensions':[32,32], 'frames':1, 'figure_bbox_exclusive':list(bbox),
    'figure_height':28, 'foot_baseline_y':29, 'editable_layers':layers,
    'opaque_pixels':len(opaque), 'transparent_pixels':1024-len(opaque),
    'alpha_values':[0,255], 'colors':colors, 'connected_components':1,
    'source_live_export_pixel_equality':True, 'negative_spaces':'passed',
    'empty_hand_bounds_inclusive':{'hanging_viewer_left':[8,18,10,20],'reaching_screen_right':[24,13,25,15]},
    'both_feet_point_right':True, 'pre_existing_owner_files_unchanged':preserved,
    'source_sha256':digest(SOURCE), 'png_sha256':digest(PNG), 'previews':previews,
    'mcp_validate':'Not exposed in this client; independent source/PNG checks used as documented in lab README.'
}
(HERE / 'validation.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
