"""GUIDE-1 offline, relocated, keyboard, narrow, zoom and print reader checks."""
import json
from pathlib import Path
import shutil
import tempfile


def exercise(browser,page,html,out,name):
    out=Path(out);checks=[]
    page.set_viewport_size(dict(width=1440,height=1000))
    page.goto(html.as_uri()+'#home');page.locator('#home.active').wait_for()
    assert page.locator('#home .card').count()==4
    assert page.locator('#home .metrics').count()==0
    page.screenshot(path=str(out/(name+'-guide-home.png')),animations='disabled')
    page.locator('#home .card[href="#learning-path"]').click()
    page.locator('#learning-path.active').wait_for()
    queries=['add an ability','new town',"why isn't my item appearing",'save my new field']
    hits=[]
    for q in queries:
        page.keyboard.press('Control+k')
        page.locator('#search-input').fill(q)
        page.locator('#search-results .search-result').first.wait_for()
        page.wait_for_function('(q)=>document.querySelector("#search-results").dataset.query===q && document.querySelector("#search-results .search-result")?.textContent.includes("Current guide")',arg=q)
        first=page.locator('#search-results .search-result').first
        assert 'current guide' in first.inner_text().lower()
        hits.append(dict(query=q,href=first.get_attribute('href')))
        page.locator('#search-input').press('ArrowDown');page.keyboard.press('Enter')
        page.locator('#search-dialog').wait_for(state='hidden')
        assert page.locator('article.active').get_attribute('data-kind')=='guide'
    checks.append(dict(intent_searches=hits,keyboard_search_and_result=True))
    page.goto(html.as_uri()+'#practice-solutions')
    detail=page.locator('#practice-solutions details').first
    summary=detail.locator('summary').first;summary.focus();summary.press('Enter')
    assert detail.get_attribute('open') is not None
    assert 'def use_exchange' in detail.inner_text()
    page.goto(html.as_uri()+'#L01');page.locator('#L01.active').wait_for()
    page.screenshot(path=str(out/(name+'-lesson-desktop.png')),animations='disabled')
    before=page.locator('html').get_attribute('data-theme');page.locator('#theme-toggle').click()
    assert page.locator('html').get_attribute('data-theme')!=before
    page.screenshot(path=str(out/(name+'-lesson-dark.png')),animations='disabled')
    page.locator('#theme-toggle').click()
    for chapter in ('L01','L12','authoring-reference','practice-solutions'):
        page.set_viewport_size(dict(width=390,height=844));page.goto(html.as_uri()+'#'+chapter)
        page.locator('#'+chapter+'.active').wait_for()
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'),chapter
        if chapter in ('L01','L12'):
            page.screenshot(path=str(out/(name+'-'+chapter+'-narrow.png')),animations='disabled')
    checks.append(dict(narrow_width=390,chapters=['L01','L12','authoring-reference','practice-solutions'],document_overflow=False,theme_toggle=True,keyboard_reveal=True))
    # A 1440×1000 display at 200% browser zoom presents a 720×500 CSS viewport.
    # Match both reflow and device pixels without controlling browser chrome.
    zoom_context=browser.new_context(offline=True,viewport=dict(width=720,height=500),device_scale_factor=2)
    zoom=zoom_context.new_page();zoom.goto(html.as_uri()+'#L12');zoom.locator('#L12.active').wait_for()
    assert zoom.evaluate('document.documentElement.scrollWidth<=innerWidth')
    zoom.screenshot(path=str(out/(name+'-L12-200-percent.png')),animations='disabled')
    checks.append(dict(zoom='200% layout/device-pixel equivalent',css_viewport=[720,500],device_scale_factor=2,document_overflow=False))
    zoom_context.close()
    page.set_viewport_size(dict(width=1100,height=900));page.goto(html.as_uri()+'#L12')
    page.evaluate("dispatchEvent(new Event('beforeprint'))");page.emulate_media(media='print')
    assert page.locator('#L12 details:not([open])').count()==0
    assert page.locator('#L12 pre').first.evaluate('(e)=>getComputedStyle(e).maxHeight')=='none'
    page.screenshot(path=str(out/(name+'-L12-print.png')),full_page=True,animations='disabled')
    if name=='chromium':page.pdf(path=str(out/'L12-print.pdf'),format='A4',print_background=False)
    page.emulate_media(media='screen');page.evaluate("dispatchEvent(new Event('afterprint'))")
    checks.append(dict(print='active chapter, answers expanded, code wraps without height clipping'))
    with tempfile.TemporaryDirectory(prefix='guide moved ') as moved:
        copied=Path(moved)/'Resonance Handbook.html';shutil.copy2(html,copied)
        blocked=browser.new_context(offline=True,viewport=dict(width=1100,height=900))
        blocked.add_init_script("Storage.prototype.getItem=function(){throw new Error('storage blocked')};Storage.prototype.setItem=function(){throw new Error('storage blocked')};")
        p=blocked.new_page();errors=[];p.on('pageerror',lambda e:errors.append(str(e)))
        p.goto(copied.as_uri()+'#L10');p.locator('#L10.active').wait_for()
        p.locator('#theme-toggle').click();p.keyboard.press('/');p.locator('#search-input').fill('persistent subsystem');p.locator('.search-result').first.wait_for()
        assert not errors,errors
        blocked.close()
        nojs=browser.new_context(offline=True,java_script_enabled=False)
        p=nojs.new_page();p.goto(copied.as_uri()+'#L10');assert p.locator('#L10').is_visible();assert 'new ability primitive' in p.locator('#L10').inner_text().lower();nojs.close()
    checks.append(dict(relocated=True,network_disabled=True,storage_denied_reading_search_theme=True,no_javascript_readable=True,course_progress='plain external notes; no browser-only storage'))
    return checks
