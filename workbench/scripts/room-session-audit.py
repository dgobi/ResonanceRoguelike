"""Fresh-process supported --load bootstrap with save-path access auditing."""
import json
import os
from pathlib import Path
import sys

config_path=Path(sys.argv[1]).resolve()
config=json.loads(config_path.read_text(encoding='utf-8'))
state=Path(config['state_root']).resolve()
payload=Path(config['manifest']).parent/'payload'
observed=[]
def audit(event,args):
    if event not in ('open','os.listdir','os.scandir','os.mkdir','os.remove','os.rename','os.rmdir'):return
    for value in args[:2] if event=='os.rename' else args[:1]:
        if not isinstance(value,(str,bytes,os.PathLike)):continue
        path=Path(os.fsdecode(value)).absolute()
        if 'saves' in path.parts or '.sessions' in path.parts:
            observed.append(dict(event=event,path=str(path)))
            if not path.is_relative_to(state):
                raise AssertionError(f'Non-test save access: {event} {path}')
sys.addaudithook(audit)
sys.path.insert(0,str(payload/'roguelike'))
import room_test
sys.argv=['room_test','--session',str(config_path),'--load']
try:
    room_test.main()
finally:
    (state/'save-path-audit.json').write_text(json.dumps(dict(pid=os.getpid(),passed=True,events=observed),indent=2),encoding='utf-8')
