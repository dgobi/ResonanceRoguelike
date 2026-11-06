"""Bind the genuine packaged authoring capture to final SYS-2 game inputs.

Reconstruct only the seven disclosed post-capture edits; reject any other changed
captured file. No game/source writes. Final native runtime separately repeats play.
"""
from pathlib import Path
import difflib,hashlib,json,subprocess,zipfile
ROOT=Path(__file__).resolve().parents[2]
def digest(b):return hashlib.sha256(b).hexdigest()
with zipfile.ZipFile(ROOT/'evidence/sys-2/preflight/authoring-receipts.zip') as z:
    receipt=json.loads(z.read('native-1793929237748/receipt.json'))
old=receipt['editedConsumer']['captured']['files'];results={}
def check(path,kind,reconstructed):
    actual=(ROOT/path).read_bytes()
    assert digest(reconstructed)==old[path],(path,'unexpected authoring delta')
    results[path]=dict(kind=kind,captured_sha256=old[path],final_sha256=digest(actual),exact_old_hash=True)
p='roguelike/engine/item_authoring.py';b=(ROOT/p).read_bytes()
needle=b'Owned lights retain captured mechanical reach, fuel and copied visuals after supported definition edits. Other owned items'
assert b.count(needle)==1
check(p,'publication guidance only',b.replace(needle,b'Owned items'))
for p in ('roguelike/engine/engine.py','roguelike/engine/item_factory.py','roguelike/engine/item_system.py'):
    before=subprocess.check_output(['git','show','884b9c7:'+p],cwd=ROOT).splitlines(keepends=True)
    now=(ROOT/p).read_bytes().splitlines(keepends=True)
    a=[x.rstrip(b'\r\n') for x in before];b=[x.rstrip(b'\r\n') for x in now];parts=[]
    for op,i,j,k,l in difflib.SequenceMatcher(a=a,b=b,autojunk=False).get_opcodes():
        parts.extend(before[i:j] if op=='equal' else [x+b'\r\n' for x in b[k:l]])
    check(p,'line endings of added lines only',b''.join(parts))
p='roguelike/engine/held_light.py';b=(ROOT/p).read_text(encoding='utf8')
b=b.replace('import math\n','import copy\nimport math\n',1)
block="""def restore(item, row, definition):
    if hasattr(item, 'held_light'):
        del item.held_light
    if 'held_light' in row:
        item.held_light = copy.deepcopy(row['held_light'])
    capture(item, definition)


"""
b=b.replace('def fuel_limit(item):',block+'def fuel_limit(item):',1)
candidate=next(x for x in (b.encode(),b.replace('\n','\r\n').encode()) if digest(x)==old[p])
check(p,'remove unused restore helper and import only',candidate)
p='roguelike/data/texts/world/notes/lamplit_store_note.json';b=(ROOT/p).read_bytes()
check(p,'clue avoids implying dropped-light emission',b.replace(b'Use the coals for light',b'Leave it by the coals'))
p='roguelike/data/loot_pools/tool_shed_c_lights.json';b=json.loads((ROOT/p).read_text())
b['items']=[r for r in b['items'] if r['item_id']!='watch_lantern']
candidate=(json.dumps(b,indent=2)+'\n').encode()
if digest(candidate)!=old[p]:candidate=candidate.replace(b'\n',b'\r\n')
check(p,'enroll published Watch Lantern in successor stock',candidate)
changed={p for p,h in old.items() if digest((ROOT/p).read_bytes())!=h}
assert changed==set(results),changed^set(results)
report=dict(passed=True,captured_files=len(old),unchanged=len(old)-len(changed),changes=results,
    captured_manifest_sha256=receipt['editedConsumer']['captured']['manifest_sha256'],
    authoring_receipts_sha256=digest((ROOT/'evidence/sys-2/preflight/authoring-receipts.zip').read_bytes()),
    limitation='This retains the executed authoring capture; rebuilt final native play and all worker tests are separate gates.')
(ROOT/'evidence/sys-2/authoring-retention.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print(json.dumps(dict(passed=True,captured_files=len(old),unchanged=report['unchanged'],disclosed_changes=len(changed))))
