"""Render retained plan diagrams with isolated headless Chromium; no desktop."""
import argparse
import json
import os
from pathlib import Path
import sys
from verify_structure_editor import DEV_ROOT


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--diagnostic',type=Path,required=True);a=p.parse_args()
    root=a.diagnostic.resolve();sys.path.insert(0,str(DEV_ROOT/'python'))
    os.environ['PLAYWRIGHT_BROWSERS_PATH']=str((DEV_ROOT/'browsers').resolve())
    from playwright.sync_api import sync_playwright
    report=json.loads((root/'run.json').read_text());paths=[root/'plan-20261023.svg'];axes=set()
    for run in report['runs']:
        for site in run['sites']['records']:
            axis='horizontal' if site['attachment']['normal'] in 'NS' else 'vertical'
            if axis not in axes:
                paths.append(root/f'{run["seed"]}-{site["id"]}-plan.svg');axes.add(axis)
    assert axes=={'horizontal','vertical'}
    results=[]
    with sync_playwright() as playwright:
        browser=playwright.chromium.launch(headless=True);page=browser.new_page(viewport={'width':1100,'height':720})
        for path in paths:
            page.goto(path.as_uri(),wait_until='load');page.locator('svg').screenshot(path=str(path.with_suffix('.png')))
            results.append(dict(source=str(path),rendered=str(path.with_suffix('.png')),kind='plan diagram, not gameplay rendering'))
        browser.close()
    (root/'visuals.json').write_text(json.dumps(results,indent=2)+'\n')
    print(json.dumps(dict(passed=True,images=len(results))))


if __name__=='__main__':raise SystemExit(main())
