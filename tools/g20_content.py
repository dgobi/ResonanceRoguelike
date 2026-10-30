"""Predeclared three-seed feasibility sample and canonical authoring checks."""
import argparse
import contextlib
import copy
import hashlib
import io
import json
import os
from pathlib import Path
import random
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
ROOM='barrow_ward_store_a'


def main():
    p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,required=True);a=p.parse_args()
    out=a.evidence.resolve();out.mkdir(parents=True,exist_ok=True)
    assert not (out/'sample.json').exists(),'Use a fresh evidence directory'
    sys.path.insert(0,str(ROOT/'roguelike'))
    os.environ.update(SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy',PYGAME_HIDE_SUPPORT_PROMPT='1')
    from engine.data_loader import DataLoader
    from engine.room_authoring import authorize_candidate, authoring_validate
    from engine.item_factory import ItemFactory
    from engine.creature_factory import CreatureFactory
    from engine.scene_generation import create_submap, create_surface
    from generation.structure_preview import preview
    from generation.authored_submap_selection import resolve
    from generation.world_gen import generate_world
    from world.world_map import WorldMap
    from generation.placement import digest
    from engine import building_authoring,pool_authoring
    from generation.building_preview import orientations
    declaration=json.loads((ROOT/'evidence/gameplay-g20/seed-sample-declaration.json').read_text())
    assert declaration['seeds']==[20261023,29417,20261030]
    with contextlib.redirect_stdout(io.StringIO()):data=DataLoader(str(ROOT/'roguelike/data'))
    raw=data.layouts[ROOM];template=json.loads((ROOT/'roguelike/docs/examples/g17_authored_creature_room.json').read_text())
    path='roguelike/data/layouts/'+ROOM+'.json'
    diagnostics=authorize_candidate(template,raw,'roguelike/docs/examples/g17_authored_creature_room.json',path,data=data)
    diagnostics+=authoring_validate(raw,data,path,data.root)
    assert not any(d['severity']=='error' for d in diagnostics),diagnostics
    report,m,actors=preview(raw,'authored_submap',data,path=path,derive_access=True)
    assert report['passed'],report
    (out/'room-preview.json').write_text(json.dumps(report,indent=2)+'\n')
    policy=resolve(data);assert policy.enabled and policy.chance==.35
    workshop_path='roguelike/data/buildings/commercial/workshop_c.json'
    workshop_raw=json.loads((ROOT/workshop_path).read_text())
    predecessor=json.loads((ROOT/'roguelike/data/buildings/commercial/workshop_b.json').read_text())
    publication=building_authoring.authorize_candidate(predecessor,workshop_raw,'roguelike/data/buildings/commercial/workshop_b.json',workshop_path,data=data)
    publication+=building_authoring.authoring_validate(workshop_raw,data,workshop_path,data.root)
    pool_path='roguelike/data/loot_pools/workshop_c_travel.json'
    publication+=pool_authoring.authoring_validate(data.loot_pools['workshop_c_travel'],data,pool_path,data.root)
    assert not any(d['severity']=='error' for d in publication),publication
    built,problems=orientations(workshop_raw,data,path=workshop_path,category='commercial')
    assert built['passed'] and not problems,problems
    workshop_previews=[dict(rotation=r['rotation'],mirror=r['mirror'],passed=r['passed'],access_verified=r['access_verified'],candidate=r['candidate_identity']) for r in built['orientations']]
    assert len(workshop_previews)==4
    record=dict(declaration=declaration,policy=dict(enabled=policy.enabled,chance=policy.chance,candidates=policy.candidates),
                diagnostics=diagnostics,workshop_publication_diagnostics=publication,workshop_previews=workshop_previews,scope='Saved-policy ordinary worlds and native construction/access; revealed initial sample, no travel, FOV, acquisition or balance claim.',worlds=[],
                source={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in (path,'roguelike/data/texts/world/notes/barrow_ward_store_note_a.json','roguelike/data/generation/authored_submap_selection.json',workshop_path,pool_path,'roguelike/data/generation/settlement_profiles.json')})
    factory,creatures=ItemFactory(data),CreatureFactory(data)
    for seed in declaration['seeds']:
        started=time.perf_counter();w=WorldMap(128,128);w.seed=seed
        with contextlib.redirect_stdout(io.StringIO()):generate_world(w,data,random.Random(seed))
        barrows=[(c,s) for c in w.chunks.values() for s in c.submaps if s.submap_type=='barrow']
        chosen=[(c,s) for c,s in barrows if s.layout_id==ROOM]
        nearest=sorted(chosen,key=lambda cs:(abs(cs[0].wx-w.start_wx)+abs(cs[0].wy-w.start_wy),cs[0].wx,cs[0].wy,cs[1].submap_id))
        assert chosen and len(chosen)<len(barrows)
        c,s=nearest[0]
        # Construct the real exterior to resolve its ordinary physical entrance.
        surface=create_surface(w,c,data,factory,creatures,80,43)
        canonical=next(x for x in surface.metadata.submaps if x.submap_id==s.submap_id)
        result=create_submap(w,c.wx,c.wy,canonical,data,factory,creatures,80,43)
        assert len(result.actors)==1 and result.actors[0]._creature_id=='hollow_revenant'
        floor=[i.item_id for rows in result.local_map.floor_objects.values() for i in rows]
        assert floor.count('faceted_ward')==1 and floor.count('letter')==1
        row=dict(seed=seed,start=[w.start_wx,w.start_wy],plan_identity=digest(w.plan),barrows=len(barrows),authored=len(chosen),procedural=sum(not s.layout_id for _,s in barrows),
                 nearest=[dict(chunk=[c.wx,c.wy],submap=s.submap_id,seed=s.seed,layout=s.layout_id,distance=abs(c.wx-w.start_wx)+abs(c.wy-w.start_wy)) for c,s in nearest[:8]],
                 constructed=dict(chunk=[c.wx,c.wy],submap=s.submap_id,surface_entrance=[canonical.surface_x,canonical.surface_y],arrival=result.spawn,entry=result.authored_start,actors=[dict(id=a._creature_id,x=a.x,y=a.y) for a in result.actors],floor=floor),seconds=time.perf_counter()-started)
        record['worlds'].append(row);(out/'sample.json').write_text(json.dumps(record,indent=2)+'\n')
        print(json.dumps(row),flush=True)
    record['passed']=True;(out/'sample.json').write_text(json.dumps(record,indent=2)+'\n')


if __name__=='__main__':main()
