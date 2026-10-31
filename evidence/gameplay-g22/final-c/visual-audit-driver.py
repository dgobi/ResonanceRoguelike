"""Inspect the exact production reader frame hidden below the native viewport."""
import base64,contextlib,hashlib,io,json,os,shutil,sys
from pathlib import Path
root=Path(__file__).resolve().parents[1]
out=root/'evidence/gameplay-g22/final-c'
sys.path.insert(0,str(root/'roguelike'))
os.environ.update(SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy',PYGAME_HIDE_SUPPORT_PROMPT='1')
from engine.data_loader import DataLoader
from engine.text_authoring import render_reader
from engine.location_reports import reader_payload
source=root/'workbench/.artifacts/g22/final-reports-final-b/runtime-inputs/roguelike/data/texts/lab/g22_report_variant.json'
assert hashlib.sha256(source.read_bytes()).hexdigest()=='797d1e7f7e879f2b02092304940eb6c1ff5151842d5207588fd0f853af2c93c7'
raw=json.loads(source.read_bytes())
with contextlib.redirect_stdout(io.StringIO()):data=DataLoader(str(root/'roguelike/data'))
data.texts[raw['id']]=raw
assert 'unbound' in reader_payload(raw)['pages'][1]['text']
frame=render_reader(raw,data,root,dict(page=1,scroll=0))
png=base64.b64decode(frame.pop('image').split(',',1)[1]);assert hashlib.sha256(png).hexdigest()==frame['image_sha256']
(out/'unbound-reader-frame.png').write_bytes(png)
shutil.copy2(source,out/'published-report-variant.json')
shutil.copy2(__file__,out/'visual-audit-driver.py')
frame.update(passed=True,fixture='Exact final-b native-published variant in disposable reader context; no world or campaign, no learning. Native viewport screenshot truncates the frame; this standalone production frame permits visual inspection.',driver_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),tested_revision='22322cb98d0453a48e66625408e0772b03e80598',command=[sys.executable,'-X','utf8','-B',str(Path(__file__).resolve())])
(out/'visual-audit.json').write_text(json.dumps(frame,indent=2)+'\n')
