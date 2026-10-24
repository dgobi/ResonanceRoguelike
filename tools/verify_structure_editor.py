"""Bounded headless Chromium + Firefox local-file controls and downloaded bytes.

Install pinned dev tooling outside the game environment; see the authoring guide.
No existing browser/profile or personal save is opened.
"""
from __future__ import annotations
import argparse
import base64
import copy
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

ROOT=Path(__file__).resolve().parents[1]
DEV_ROOT=(Path(os.environ.get('LOCALAPPDATA',str(Path.home()/'.cache')))/'ResonanceAuthoring').resolve()


def worker(browser_name,evidence):
    sys.path.insert(0,str(DEV_ROOT/'python'))
    # Resolve packaged-Windows filesystem redirection before native DLL probing.
    # Firefox's side-by-side loader cannot follow the logical LocalAppData alias.
    os.environ['PLAYWRIGHT_BROWSERS_PATH']=str(Path(os.environ.get('PLAYWRIGHT_BROWSERS_PATH',DEV_ROOT/'browsers')).resolve())
    from playwright.sync_api import sync_playwright
    corpus=ROOT/'tools/critical_fix_regressions/fixtures/g2_original'
    manifest=json.loads((corpus/'manifest.json').read_text())
    docs=[(a['repository_path'],(corpus/a['repository_path']).read_text(encoding='utf-8')) for a in manifest['assets']]
    delivered=[(str(p.relative_to(ROOT)),p.read_text(encoding='utf-8')) for folder in ['buildings','entrances','layouts'] for p in sorted((ROOT/'roguelike/data'/folder).rglob('*.json'))]
    checks=[]; errors=[]
    def check(name,condition):
        checks.append({'name':name,'passed':bool(condition)})
        if not condition: raise AssertionError(name)
    check('frozen corpus matches all 65 pinned baseline blob hashes',all(
        hashlib.sha256((corpus/a['repository_path']).read_bytes().replace(b'\r\n',b'\n')).hexdigest()==a['sha256']
        for a in manifest['assets']))
    evidence.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='resonance-browser-downloads-') as temporary,sync_playwright() as playwright:
        browser=getattr(playwright,browser_name).launch(headless=True,downloads_path=temporary)
        context=browser.new_context(accept_downloads=True,viewport={'width':1640,'height':1050})
        page=context.new_page();page.set_default_timeout(10000)
        page.on('pageerror',lambda e:errors.append(str(e)))
        page.goto((ROOT/'layout_painter.html').as_uri(),wait_until='load')
        page.wait_for_function('typeof StructureEditor !== "undefined"')
        def export(name):
            with page.expect_download() as event: page.locator('#export').click()
            path=Path(temporary)/(name+'.json');event.value.save_as(path)
            return json.loads(path.read_text(encoding='utf-8')),path
        def load(path):
            expected=json.loads(path.read_text(encoding='utf-8'))
            page.locator('#file').set_input_files(str(path))
            page.wait_for_function('(id)=>document.querySelector("#asset-id").value===id',arg=expected['id'])
            return expected
        codec=page.evaluate('''rows => rows.map(([path,text]) => {
            const m=new StructureEditor.DocumentModel();m.importText(text);
            return [path,JSON.parse(m.exportText())];
        })''',docs+delivered)
        check(f'65 frozen originals plus {len(delivered)} delivered catalog documents round-trip',
              all(row[1]==json.loads(source[1]) for row,source in zip(codec,docs+delivered)) and len(docs)==65 and len(codec)==len(docs)+len(delivered))
        sentinels={'id':'sentinel','layers':['.'],'legend':{'.':'floor'},'unknown':{'list':[None,False,0,{'nested':[3,2,1]}]},'weight':0,'decor_layer':None}
        result=page.evaluate('''doc=>{const m=new StructureEditor.DocumentModel();m.importText(JSON.stringify(doc));return JSON.parse(m.exportText());}''',sentinels)
        check('unknown metadata, null/false/zero and ordered arrays preserved',result==sentinels and 'player_start' not in result)
        unsafe=['{"id":"a","id":"b"}','{"id":"a","x":9007199254740993}','{"id":"a","x":0.123456789012345678901}',
                '{"id":"a","x":1e-999}','{"id":"a","x":1e999}','{"id":"a","x":NaN}']
        rejected=page.evaluate('''rows=>rows.map(text=>{try{StructureEditor.strictParse(text);return false;}catch(e){return true;}})''',unsafe)
        check('duplicates and unrepresentable numbers rejected explicitly',all(rejected))
        geometry=page.evaluate('''()=>{
            const huge={id:'large',layers:['.'.repeat(257)],legend:{'.':'floor'},extra:{x:300}};
            const m=new StructureEditor.DocumentModel();m.importText(JSON.stringify(huge));
            const preserved=JSON.parse(m.exportText());let refused=false;
            try{m.paint(0,0,'terrain','.');}catch(e){refused=true;}
            const ragged={id:'ragged',layers:['..','.'],legend:{'.':'floor',' ':null},extra:{x:99}};
            m.importText(JSON.stringify(ragged));m.resize(2,2);const padded=JSON.parse(m.exportText());m.undo();
            return {preserved,refused,padded,restored:JSON.parse(m.exportText())};
        }''')
        check('oversized document preserved read-only and explicit ragged normalization reversible',
              geometry['refused'] and len(geometry['preserved']['layers'][0])==257 and
              geometry['padded']['layers']==['..','. '] and geometry['restored']['layers']==['..','.'] and geometry['padded']['extra']=={'x':99})
        original=load(ROOT/'roguelike/docs/examples/author_cottage_a.json')
        got,_=export('cottage-original');check('real file input and download preserve cottage',got==original)
        page.locator('#terrain-brush').select_option('.')
        page.locator('#grid').click(position={'x':10,'y':10})
        expected=copy.deepcopy(original);expected['layers'][0]='.'+expected['layers'][0][1:]
        got,_=export('terrain-edit');check('one terrain click changes only selected character',got==expected)
        page.locator('#layer').select_option('decor');page.locator('#decor-brush').select_option('decor_candle')
        page.locator('#grid').click(position={'x':90,'y':50})
        expected['decor_layer'][2][4]='decor_candle'
        got,_=export('decor-edit');check('full decor ID remains nested array',got==expected)
        page.locator('#decor-brush').select_option('');page.locator('#grid').click(position={'x':90,'y':50})
        expected['decor_layer'][2][4]=None
        got,_=export('decor-erase');check('decor erasing writes null only',got==expected)
        special=copy.deepcopy(expected['special_tiles'][0]);special['item_id']='research_note';special['text_id']='lab_label_equipment'
        page.locator('#special').fill(json.dumps(special));page.locator('#apply-special').click()
        expected['special_tiles'][0]=special
        got,path=export('browser-candidate');check('single record edit preserves unrelated data',got==expected)
        exported=evidence/(browser_name+'-exported-cottage.json');exported.write_bytes(path.read_bytes())
        page.locator('#undo').click();expected['special_tiles'][0]=original['special_tiles'][0]
        got,_=export('undo-record');check('undo restores entire prior document',got==expected)
        page.locator('#redo').click();expected['special_tiles'][0]=special
        got,_=export('redo-record');check('redo restores record and all layers',got==expected)
        page.locator('#paste').fill('{invalid') if page.locator('#paste').is_visible() else page.locator('summary').filter(has_text='Paste import').click()
        page.locator('#paste').fill('{invalid');page.locator('#import-paste').click()
        got,_=export('invalid-import');check('invalid import leaves complete current document intact',got==expected)
        page.locator('#file').set_input_files([])
        got,_=export('cancel-import');check('cancelled file selection leaves document intact',got==expected)
        entrance=load(ROOT/'roguelike/data/entrances/barrow_mound_a.json')
        got,_=export('entrance');check('building then entrance does not leak category/decor',got==entrance and 'decor_layer' not in got and 'category' not in got)
        lab=load(ROOT/'roguelike/data/layouts/starting_lab.json')
        got,_=export('lab-original');check('lab starts and specials survive real download',got==lab)
        page.locator('#width').fill('61');page.locator('#resize').click();page.locator('#resize-cancel').click()
        got,_=export('resize-cancel');check('resize cancellation preserves width60 lab',got==lab)
        page.locator('#width').fill('61');page.locator('#resize').click();page.locator('#resize-confirm').click()
        got,_=export('lab61');expected_lab=copy.deepcopy(lab);expected_lab['width']=61
        pad=next(k for k,v in lab['legend'].items() if v is None)
        expected_lab['layers']=[r+pad for r in lab['layers']]
        check('lab width60 to61 enlarges without truncation',got==expected_lab)
        page.locator('#width').fill('48');page.locator('#resize').click();page.locator('#resize-confirm').click()
        check('destructive crop reports refusal','Crop refused' in page.locator('#message').inner_text())
        got,_=export('crop-refused');check('refused crop preserves complete width61 document',got==expected_lab)
        page.locator('#resize-cancel').click();page.locator('#undo').click()
        got,_=export('undo-resize');check('undo enlargement restores original lab',got==lab)
        legend=copy.deepcopy(lab['legend']);del legend[next(ch for ch in lab['layers'][0] if ch in legend)]
        page.locator('#legend').fill(json.dumps(legend));page.locator('#apply-legend').click()
        check('used-legend deletion gives explicit error','Cannot delete used legend' in page.locator('#message').inner_text())
        got,_=export('legend-refused');check('failed legend edit is atomic',got==lab)
        page.locator('#metadata-field').select_option('player_start')
        start=copy.deepcopy(lab['player_start']);start['x']+=1
        page.locator('#metadata').fill(json.dumps(start));page.locator('#apply-metadata').click()
        expected_lab=copy.deepcopy(lab);expected_lab['player_start']=start
        got,_=export('edited-start');check('deliberate start edit changes one field',got==expected_lab)
        planned=load(ROOT/'roguelike/data/buildings/residential/house_small_a.json')
        page.locator('#asset-id').fill('browser_frontage_'+browser_name)
        page.locator('#apply-id').click()
        planned['id']='browser_frontage_'+browser_name
        page.locator('#layer').select_option('terrain');page.locator('#terrain-brush').select_option('.')
        page.locator('#grid').click(position={'x':150,'y':150})
        planned['layers'][7]=planned['layers'][7][:7]+'.'+planned['layers'][7][8:]
        page.locator('#metadata-field').select_option('placement')
        profile=copy.deepcopy(planned['placement']);profile['buffer']=2
        profile['entrances'].append(dict(id='separate-service',x=7,y=7,normal='S',width=1,role='service',required=True))
        page.locator('#metadata').fill(json.dumps(profile));page.locator('#apply-metadata').click()
        planned['placement']=profile
        weighted=dict(type='weighted',x=planned['special_tiles'][0]['x'],y=planned['special_tiles'][0]['y'],
                      spawn_table=[dict(planned['special_tiles'][0],weight=1)])
        page.locator('#special').fill(json.dumps(weighted));page.locator('#apply-special').click()
        planned['special_tiles'][0]=weighted
        got,path=export('planned-frontage')
        check('real placement panel edit/download preserves complete document',got==planned)
        check('explicit weighted child coordinates and allowed mirror survive real download',
              got['special_tiles'][0]['spawn_table'][0]['x']==got['special_tiles'][0]['x'] and got['placement']['mirror_x'] is True)
        planned_export=evidence/(browser_name+'-planned-frontage.json');planned_export.write_bytes(path.read_bytes())
        site=load(ROOT/'roguelike/docs/examples/g6_wayhouse.json')
        page.locator('#asset-id').fill('browser_site_'+browser_name);page.locator('#apply-id').click();site['id']='browser_site_'+browser_name
        page.locator('#metadata-field').select_option('placement')
        site['placement']['buffer']=2
        page.locator('#metadata').fill(json.dumps(site['placement']));page.locator('#apply-metadata').click()
        got,path=export('additional-site')
        check('G6 real downloaded site keeps separate required doors and populated contents',got==site)
        site_export=evidence/(browser_name+'-site.json');site_export.write_bytes(path.read_bytes())
        page.screenshot(path=str(evidence/(browser_name+'-site-editor.png')),full_page=True)
        child=load(ROOT/'roguelike/docs/examples/g7_wayhouse.json')
        page.locator('#asset-id').fill('browser_compound_'+browser_name);page.locator('#apply-id').click();child['id']='browser_compound_'+browser_name
        page.locator('#metadata-field').select_option('placement');child['placement']['weight']=1.75
        page.locator('#metadata').fill(json.dumps(child['placement']));page.locator('#apply-metadata').click()
        check('compound context exposed through shared metadata vocabulary','compound' in page.locator('#metadata-status').inner_text())
        got,path=export('compound-child');check('actual compound child download preserves contexts, doors, required goals and contents',got==child)
        compound_export=evidence/(browser_name+'-compound-child.json');compound_export.write_bytes(path.read_bytes())
        page.screenshot(path=str(evidence/(browser_name+'-compound-editor.png')),full_page=True)
        page.screenshot(path=str(evidence/(browser_name+'-lab.png')),full_page=True)
        check('no browser script errors',not errors)
        version=browser.version;context.close();browser.close()
    # The downloaded bytes cross the authoritative CLI and real pool consumer.
    command=[sys.executable,'-X','utf8',str(ROOT/'tools/structure_authoring.py'),str(exported),
             '--route','ordinary_building','--category','residential','--register',
             '--output',str(evidence/(browser_name+'-runtime.json'))]
    run=subprocess.run(command,cwd=ROOT,capture_output=True,text=True,timeout=60)
    check('downloaded JSON passes shared runtime preview and actual existing-pool selection',run.returncode==0)
    planned_command=[sys.executable,'-X','utf8',str(ROOT/'tools/structure_authoring.py'),str(planned_export),
                     '--planned','--category','residential','--context','grid','--seed','20261023',
                     '--output',str(evidence/(browser_name+'-planned-runtime.json'))]
    planned_run=subprocess.run(planned_command,cwd=ROOT,capture_output=True,text=True,timeout=90)
    check('downloaded placement metadata passes CLI and production planned placement',planned_run.returncode==0)
    orientation_command=[sys.executable,'-X','utf8',str(ROOT/'tools/structure_authoring.py'),str(planned_export),
                         '--route','ordinary_building','--category','residential','--orientations',
                         '--output',str(evidence/(browser_name+'-orientations.json'))]
    orientation_run=subprocess.run(orientation_command,cwd=ROOT,capture_output=True,text=True,timeout=60)
    check('downloaded explicit weighted coordinates pass all eight rotations/reflections',orientation_run.returncode==0)
    site_commands=[]
    for name,options in [('direct',['--route','ordinary_building','--orientations'])]+[(normal,['--assigned-site',normal]) for normal in 'NESW']:
        command_site=[sys.executable,'-X','utf8',str(ROOT/'tools/structure_authoring.py'),str(site_export),'--category','wilderness',*options,
                      '--output',str(evidence/(browser_name+'-site-'+name+'.json'))]
        result_site=subprocess.run(command_site,cwd=ROOT,capture_output=True,text=True,timeout=90)
        site_commands.append(dict(argv=command_site,cwd=str(ROOT),exit_code=result_site.returncode,expected_exit=0,stdout=result_site.stdout,stderr=result_site.stderr))
        check('actual downloaded G6 site passes production '+name,result_site.returncode==0)
    recipe=json.loads((ROOT/'roguelike/docs/examples/g7_travellers_court.json').read_text())
    recipe['slots'][1]['assets']=[dict(asset=child['id'],weight=1)]
    recipe_path=evidence/(browser_name+'-compound-recipe.json');recipe_path.write_text(json.dumps(recipe,indent=2)+'\n')
    compound_commands=[]
    for name,options in [('direct',[compound_export,'--route','ordinary_building','--category','wilderness','--orientations'])]+[(normal,['--compound',recipe_path,'--child',compound_export,'--assigned-compound',normal]) for normal in 'SE']:
        command_compound=[sys.executable,'-X','utf8',ROOT/'tools/structure_authoring.py',*options,'--output',evidence/(browser_name+'-compound-'+name+'.json')]
        result_compound=subprocess.run(list(map(str,command_compound)),cwd=ROOT,capture_output=True,text=True,timeout=90)
        compound_commands.append(dict(argv=list(map(str,command_compound)),cwd=str(ROOT),exit_code=result_compound.returncode,expected_exit=0,stdout=result_compound.stdout,stderr=result_compound.stderr))
        check('actual downloaded child passes compound '+name,result_compound.returncode==0)
    from g8_browser_consumer import consume
    g8_commands=consume(planned_export,evidence,browser_name)
    check('actual downloaded building occupies vertical frontage in both G8 layouts',bool(g8_commands))
    report={'browser':browser_name,'version':version,'passed':all(c['passed'] for c in checks),'checks':checks,'errors':errors,
            'command':command,'runtime_stdout':run.stdout,'runtime_stderr':run.stderr,'codec_documents':len(codec),
            'planned_command':planned_command,'planned_stdout':planned_run.stdout,'planned_stderr':planned_run.stderr,
            'command_records':[dict(argv=c,cwd=str(ROOT),exit_code=r.returncode,stdout=r.stdout,stderr=r.stderr) for c,r in
                               ((command,run),(planned_command,planned_run),(orientation_command,orientation_run))]+site_commands+compound_commands+g8_commands,
            'download_hashes':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (exported,planned_export,site_export,compound_export)}}
    (evidence/(browser_name+'.json')).write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'browser':browser_name,'passed':report['passed'],'checks':len(checks),'version':version}))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence',type=Path,default=ROOT/'evidence/worldgen-g2/browser')
    parser.add_argument('--worker',choices=['chromium','firefox'])
    args=parser.parse_args();evidence=args.evidence.resolve()
    distributions=list(importlib.metadata.distributions(path=[str(DEV_ROOT/'python')]))
    distribution=next((d for d in distributions if d.metadata['Name']=='playwright' and d.version=='1.64.1'),None)
    if distribution is None:parser.error('Install pinned Python Playwright 1.64.1 in the documented development directory.')
    version=distribution.version
    driver_path=DEV_ROOT/'python/playwright/driver/package/package.json'
    driver_version=json.loads(driver_path.read_text())['version']
    record=next(f for f in distribution.files if str(f)=='playwright/driver/package/package.json')
    actual=base64.urlsafe_b64encode(hashlib.sha256(driver_path.read_bytes()).digest()).decode().rstrip('=')
    if record.hash.value!=actual:parser.error('Driver files do not match the pinned Python package RECORD.')
    if args.worker: worker(args.worker,evidence);return 0
    sources=[ROOT/'layout_painter.html',ROOT/'roguelike/generation/structure_contract.py',ROOT/'tools/structure_authoring.py',Path(__file__).resolve(),*sorted((ROOT/'tools/structure_editor').glob('*'))]
    identities=lambda:{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources if p.is_file()}
    from verify_b3 import source_manifest
    runtime_source=source_manifest()
    before=identities();start=time.monotonic();results=[];evidence.mkdir(parents=True,exist_ok=True)
    for browser in ('chromium','firefox'):
        command=[sys.executable,'-X','utf8',str(Path(__file__).resolve()),'--worker',browser,'--evidence',str(evidence)]
        run=subprocess.run(command,cwd=ROOT,capture_output=True,text=True,timeout=240)
        (evidence/(browser+'-log.txt')).write_text(run.stdout+run.stderr,encoding='utf-8')
        print(run.stdout+run.stderr,end='');results.append({'browser':browser,'exit_code':run.returncode,'command':command})
    passed=all(r['exit_code']==0 for r in results) and before==identities() and runtime_source==source_manifest()
    (evidence/'summary.json').write_text(json.dumps({'passed':passed,'runs':results,'source':before,'source_stable':before==identities(),
                                                    'runtime_source':runtime_source,'runtime_source_stable':runtime_source==source_manifest(),
                                                    'seconds':round(time.monotonic()-start,2),'playwright':version,'driver':driver_version},indent=2)+'\n')
    return 0 if passed else 1


if __name__=='__main__':raise SystemExit(main())
