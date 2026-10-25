"""Read-only G9 geography/base-terrain observations for next-arc selection.

No game source, save, world plan, or shipped content is written. Metadata worlds
use the ordinary production generator. Controlled base-only scenes characterize
the same base pass used by planned_surface; they do not claim populated gameplay.
"""
import argparse
from collections import Counter
import contextlib
import io
import json
import os
from pathlib import Path
import random
import subprocess
import sys

p=argparse.ArgumentParser()
p.add_argument('--repo',type=Path,required=True)
p.add_argument('--out',type=Path,required=True)
a=p.parse_args();repo=a.repo.resolve()
sys.path.insert(0,str(repo/'roguelike'))
os.environ.update(PYTHONDONTWRITEBYTECODE='1',SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy',PYGAME_HIDE_SUPPORT_PROMPT='1')
from engine.data_loader import DataLoader
from generation.context import GenerationContext
from generation.region_gen import generate_region
from generation.world_gen import generate_world
from world.world_map import Chunk,RegionType,WorldMap

rows=[];scene_rows=[]
with contextlib.redirect_stdout(io.StringIO()):
    data=DataLoader(str(repo/'roguelike/data'))
    for seed in (0,20261023,29417):
        w=WorldMap(128,128);w.seed=seed
        generate_world(w,data,random.Random(seed))
        counts=Counter(c.biome_id for c in w.chunks.values())
        pairs=[];wilderness_pairs=[]
        for (x,y),c in w.chunks.items():
            for delta in ((1,0),(0,1)):
                d=w.get(x+delta[0],y+delta[1])
                if not d:continue
                pairs.append(c.biome_id!=d.biome_id)
                if c.biome_id not in ('town','capital') and d.biome_id not in ('town','capital'):
                    wilderness_pairs.append(c.biome_id!=d.biome_id)
        rows.append(dict(seed=seed,biomes=dict(counts),all_cardinal_neighbor_pairs=len(pairs),different_biome_pairs=sum(pairs),
                         wilderness_cardinal_neighbor_pairs=len(wilderness_pairs),different_wilderness_biome_pairs=sum(wilderness_pairs),
                         scenes_materialized=0,scope='Adjacency of macro biome labels, not a direct measure of visual seam severity or gameplay quality.'))
    for biome in ('plains','forest','heath','swamp','drowned_wood','ash_wastes','mountain','deep_mountain'):
        for seed in (0,20261023,29417):
            c=Chunk(31,22,RegionType(biome),seed,biome_id=biome,world_seed=20261023)
            context=GenerationContext(20261023,seed,(31,22,None))
            m,spawn=generate_region(c,80,43,data.terrain,data=data,context=context,base_only=True)
            terrain=Counter(str(m.tiles[x,y]['terrain']) for x in range(80) for y in range(43))
            scene_rows.append(dict(biome=biome,scene_seed=seed,terrain=dict(terrain),decor=dict(Counter(m.decor.values())),
                                   walkable=int(m.walkable.sum()),tiles=3440,scope='Controlled base-only terrain before planned infrastructure, structures, entrances, functional dressing or population.'))
out=dict(source=subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip(),
         command=sys.argv,metadata_worlds=rows,base_scenes=scene_rows)
a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(dict(passed=True,worlds=len(rows),controlled_scenes=len(scene_rows),output=str(a.out))))
