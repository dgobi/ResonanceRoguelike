"""Exercise the real standalone HTML in both installed headless browsers."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import subprocess


def main():
    p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,required=True);p.add_argument('--worker',choices=['chromium','firefox']);a=p.parse_args()
    root=Path(__file__).resolve().parent;html=root/'Resonance_Owner_Wiki.html'
    dev=(Path(os.environ['LOCALAPPDATA'])/'ResonanceAuthoring').resolve()
    # Match the established editor harness: resolve packaged-Windows path
    # redirection before Firefox's native side-by-side DLL loader starts.
    sys.path.insert(0,str(dev/'python'));os.environ['PLAYWRIGHT_BROWSERS_PATH']=str((dev/'browsers').resolve())
    if not a.worker:
        a.evidence.mkdir(parents=True,exist_ok=True);runs=[];commands=[]
        for name in ('chromium','firefox'):
            command=[sys.executable,'-X','utf8',str(Path(__file__).resolve()),'--worker',name,'--evidence',str(a.evidence.resolve())]
            r=subprocess.run(command,capture_output=True,text=True,encoding='utf-8',timeout=120)
            (a.evidence/(name+'-log.txt')).write_text(r.stdout+r.stderr,encoding='utf-8');assert r.returncode==0,r.stdout+r.stderr
            worker=json.loads((a.evidence/('reader-'+name+'.json')).read_text());runs.extend(worker['runs']);commands.append(dict(argv=command,exit_code=r.returncode))
        (a.evidence/'reader.json').write_text(json.dumps(dict(passed=True,html_sha256=hashlib.sha256(html.read_bytes()).hexdigest(),runs=runs,commands=commands,limits=worker['limits']),indent=2)+'\n',encoding='utf-8')
        return
    from playwright.sync_api import sync_playwright
    a.evidence.mkdir(parents=True,exist_ok=True);rows=[]
    with sync_playwright() as pw:
        for name in (a.worker,):
            browser=getattr(pw,name).launch(headless=True);page=browser.new_page(viewport=dict(width=1440,height=1000));errors=[]
            page.on('pageerror',lambda e:errors.append(str(e)))
            page.goto(html.as_uri());page.locator('article.active').wait_for()
            links=page.locator('a[href^="#"]').evaluate_all('(xs)=>xs.map(x=>x.getAttribute("href").slice(1)).filter(Boolean)')
            missing=page.evaluate('(ids)=>ids.filter(id=>!document.getElementById(decodeURIComponent(id)))',links)
            assert not missing,missing
            downloads=[]
            for filename in ('deep_tongue.json','owner_cottage_a.json','g7_travellers_court.json','g9_country_network.json'):
                record=page.locator('.data-record').filter(has=page.locator('button[data-filename="'+filename+'"]')).first
                record_id=record.get_attribute('id');page.goto(html.as_uri()+'#'+record_id)
                record.evaluate('(e)=>e.open=true')
                expected=dict(bytes=int(record.get_attribute('data-payload-bytes')),sha256=record.get_attribute('data-payload-sha256'))
                with page.expect_download() as event:record.locator('button[data-download]').click()
                download=event.value;target=a.evidence/(name+'-'+filename);download.save_as(str(target));raw=target.read_bytes()
                observed=dict(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest());assert observed==expected,(filename,expected,observed)
                downloads.append(dict(file=filename,advertised=expected,downloaded=observed,passed=True))
            page.locator('.nav-link[href="#settlement-layouts"]').click()
            page.locator('#settlement-layouts.active').wait_for()
            copy=page.locator('#settlement-layouts .code-copy').first;copy.click()
            # Clipboard permission differs by local-file engine. Both the success
            # label and the documented selected-text fallback are usable controls.
            page.wait_for_function('document.querySelector("#settlement-layouts .code-copy").textContent==="Copied" || String(window.getSelection()).length>20')
            copy_result=copy.inner_text();selection=page.evaluate('String(window.getSelection()).length')
            page.screenshot(path=str(a.evidence/(name+'-layout.png')),full_page=True,animations='disabled')
            page.locator('[data-search-open]').first.click();page.locator('#search-input').fill('compound')
            page.locator('#search-results .search-result').first.wait_for();count=page.locator('#search-results .search-result').count()
            page.locator('#search-results .search-result').first.click();page.locator('#search-dialog').wait_for(state='hidden')
            page.set_viewport_size(dict(width=390,height=844));page.locator('#menu-toggle').click()
            assert page.locator('#menu-toggle').get_attribute('aria-expanded')=='true'
            page.locator('.nav-link[href="#settlement-layouts"]').click();page.locator('#settlement-layouts.active').wait_for()
            assert page.locator('#menu-toggle').get_attribute('aria-expanded')=='false'
            page.screenshot(path=str(a.evidence/(name+'-mobile.png')),full_page=True,animations='disabled')
            page.screenshot(path=str(a.evidence/(name+'-mobile-viewport.png')),animations='disabled')
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'), 'mobile document overflows viewport'
            assert not errors,errors
            rows.append(dict(browser=name,version=browser.version,internal_links=len(links),missing=missing,search_results=count,copy_button=copy_result,selected_fallback_characters=selection,navigation=True,mobile_menu=True,script_errors=errors,downloads=downloads))
            browser.close()
    result=dict(passed=True,html_sha256=hashlib.sha256(html.read_bytes()).hexdigest(),runs=rows,limits='Headless local-file Chromium and Firefox, two viewport sizes; automated navigation/search/copy control checks and retained screenshots. No manual assistive-technology audit or OS clipboard readback.')
    (a.evidence/('reader-'+a.worker+'.json')).write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps(result,indent=2))


if __name__=='__main__':main()
