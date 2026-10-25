"""Four ordinary G9 wilderness scenes through the unchanged production renderer."""
import argparse
from collections import Counter
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import random
import subprocess
import sys

p=argparse.ArgumentParser();p.add_argument('--repo',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
a=p.parse_args();repo=a.repo.resolve();out=a.out.resolve();out.mkdir(parents=True,exist_ok=True)
sys.path[:0]=[str(repo/'roguelike'),str(repo/'tools'),str(repo/'tools/critical_fix_regressions/tests')]
os.environ.update(SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy',PYGAME_HIDE_SUPPORT_PROMPT='1',PYTHONDONTWRITEBYTECODE='1')
from test_effect_persistence import load_data,make_engine
from generation.world_gen import generate_world
from generation.world_plan import slice_plan
from generation.placement import digest
from engine.scene_generation import create_surface
from engine.item_factory import ItemFactory
from engine.creature_factory import CreatureFactory
from world.world_map import WorldMap
from g7_visuals import render_compound
from g1_support import fingerprint
from PIL import Image,ImageDraw,ImageFont

rows=[]
with contextlib.redirect_stdout(io.StringIO()):
    data=load_data();w=WorldMap(128,128);w.seed=20261023;generate_world(w,data,random.Random(w.seed));e=make_engine(data)
    for biome in ('forest','drowned_wood','ash_wastes','mountain'):
        choices=sorted((c for c in w.chunks.values() if c.biome_id==biome and not c.submaps and not c.is_river),
                       key=lambda c:(abs(c.wx-w.start_wx)+abs(c.wy-w.start_wy),c.wx,c.wy))
        for c in choices:
            section=slice_plan(w.plan,c.wx,c.wy)
            if not any(section.get(k) for k in ('routes','waters','crossings','placements','sites','paths','public_spaces')):break
        else:raise ValueError('no ordinary unowned scene for '+biome)
        scene=create_surface(w,c,data,ItemFactory(data),CreatureFactory(data),80,43)
        e.local_map=scene.local_map;e.entities=[e.player,*scene.actors];e.player.x,e.player.y=scene.spawn;e.world_map=w;e.world_x,e.world_y=c.wx,c.wy
        name=f'{biome}-{c.wx}-{c.wy}.png'
        render_compound(e,dict(recipe=f'G9 {biome} seed20261023 ({c.wx},{c.wy})'),out/name)
        m=scene.local_map
        rows.append(dict(biome=biome,chunk=[c.wx,c.wy],scene_seed=c.seed,ordinary_unmodified_biome=True,production_renderer=True,
                         complete_native_scene=True,visibility='controlled full-scene reveal; not normal FOV',
                         image=name,sha256=hashlib.sha256((out/name).read_bytes()).hexdigest(),
                         terrain=dict(Counter(str(m.tiles[x,y]['terrain']) for x in range(80) for y in range(43))),
                         decor=dict(Counter(m.decor.values())),actors=len(scene.actors),fingerprint=fingerprint(m,scene.actors),
                         plan_provenance=m.plan_provenance,functional_generation=m.functional_generation))

fontpath='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
font=ImageFont.truetype(fontpath,23);small=ImageFont.truetype(fontpath,18)
cell_w,cell_h=960,564;sheet=Image.new('RGB',(cell_w*2,cell_h*2+104),(16,18,22));d=ImageDraw.Draw(sheet)
d.text((24,15),'Current G9 wilderness — ordinary seed 20261023',(245,245,245),font=font)
d.text((24,50),'Actual populated production scenes; complete reveal for comparison. No biome edits or proposed terrain.',(190,196,204),font=small)
for i,row in enumerate(rows):
    x=(i%2)*cell_w;y=104+(i//2)*cell_h
    d.text((x+12,y+6),f"{row['biome'].replace('_',' ').title()}  ({row['chunk'][0]}, {row['chunk'][1]})",(235,238,242),font=font)
    im=Image.open(out/row['image']).convert('RGB');im=im.crop((0,42,im.width,im.height));im.thumbnail((cell_w-16,cell_h-40),Image.Resampling.LANCZOS)
    sheet.paste(im,(x+8,y+38))
contact=out/'g9-wilderness-baseline.png';encoded=io.BytesIO();sheet.save(encoded,format='PNG');contact.write_bytes(encoded.getvalue())
Image.open(contact).verify()
report=dict(source=subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip(),seed=w.seed,plan_identity=digest(w.plan),start=[w.start_wx,w.start_wy],
            selection='Nearest to starting chunk by cardinal chunk distance, then coordinate, with requested ordinary biome; no submap, river, country/local route, placement, compound, public-space ownership.',
            views=rows,contact_sheet=dict(path=contact.name,sha256=hashlib.sha256(contact.read_bytes()).hexdigest()))
(out/'baseline-views.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(dict(passed=True,views=len(rows),contact_sheet=str(contact))))
