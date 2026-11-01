import sys,os,json,random,tempfile,shutil,hashlib
from pathlib import Path
root=Path.cwd();sys.path[:0]=[str(root/'roguelike'),str(root/'tools')]
os.environ.update(SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy',PYGAME_HIDE_SUPPORT_PROMPT='1')
from room_test import build_engine
from engine.save_manager import _serialize_entity,_serialize_world
from engine import location_reports
from generation.world_gen import generate_world
from world.world_map import WorldMap
import pygame
pygame.init();os.chdir(root/'roguelike')
out=root/'.baseline/ai-6';temp=tempfile.mkdtemp(prefix='resonance-ai6-legacy-')
config=dict(state_root=temp,seed=20261027,room_path='roguelike/data/layouts/ai4_patient_opening.json',session_id='ai6-prechange')
e=build_engine(config);e.rng=random.Random(17);e.ai_system._rng=random.Random(19)
e._handle_key(pygame.K_COMMA);e._handle_key(pygame.K_RIGHT)
a=next(a for a in e.entities if getattr(a,'_creature_id','')=='patient_amber_hunter')
for n in range(30):
 e._handle_key(pygame.K_PERIOD)
 if a.ai.hunt:break
assert a.ai.hunt
w=WorldMap(64,64);w.seed=20261027;w=generate_world(w,e.data,random.Random(w.seed))
assert any(s.layout_id=='barrow_ward_store_a' for c in w.chunks.values() for s in c.submaps)
# Preserve a separately generated genuine fresh-world metadata/report snapshot.
(out/'legacy-world.json').write_text(json.dumps(_serialize_world(w),indent=2),encoding='utf-8')
assert e.save_manager.save(e),e.save_manager.last_error
snap=dict(actor=_serialize_entity(a),turn=e.world_time.turn,world=_serialize_world(e.world_map),config={k:v for k,v in config.items() if k!='state_root'})
(out/'legacy-snapshot.json').write_text(json.dumps(snap,indent=2),encoding='utf-8')
shutil.make_archive(str(out/'legacy-save'),'zip',temp)
print(json.dumps(dict(turn=e.world_time.turn,phase=a.ai.phase,archive_sha256=hashlib.sha256((out/'legacy-save.zip').read_bytes()).hexdigest(),world_seed=w.seed,reports=w.location_reports)))
shutil.rmtree(temp)
