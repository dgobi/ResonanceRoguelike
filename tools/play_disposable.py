"""Run production code with a new, explicitly named disposable save root."""
import argparse
import json
import os
from pathlib import Path
import re
import sys
from unittest.mock import patch

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seed',type=int,default=20261023);parser.add_argument('--session',required=True)
    parser.add_argument('--headless-smoke',action='store_true')
    args=parser.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,64}',args.session):parser.error('session must use 1..64 letters, digits, underscores or hyphens')
    root=Path(__file__).resolve().parents[1];save=root/'.baseline'/('g3-play-'+args.session)
    if save.exists():parser.error('session already exists; choose a fresh name to preserve its state')
    (save/'slot_0').mkdir(parents=True);(save/'slot_0/world.json').write_text(json.dumps({'seed':args.seed}))
    sys.path.insert(0,str(root/'roguelike'));os.chdir(root/'roguelike')
    if args.headless_smoke:os.environ.update(SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy')
    import main as game
    with patch('engine.save_manager.SAVE_DIR',save):
        if args.headless_smoke:
            with patch.object(game.Engine,'run',lambda e:print(json.dumps({'seed':e.world_map.seed,'plan_mode':e.world_map.plan_mode,'start':[e.world_x,e.world_y],'submap':e.current_submap_id,'save_root':str(save)}))):game.main()
        else:game.main()
if __name__=='__main__':main()
