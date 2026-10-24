#!/usr/bin/env python3
"""Build the offline Resonance owner wiki from reviewed chapters and a pinned repo.

Dependency: mistune==3.4.0. Reading the generated HTML requires no dependencies.
The default build refuses a repository revision different from wiki-config.json.
"""
from __future__ import annotations
import argparse, ast, base64, hashlib, html, json, mimetypes, re, subprocess, sys
from collections import defaultdict
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parent
REPOSITORY = 'https://github.com/dgobi/ResonanceRoguelike'

def esc(x): return html.escape(str(x), quote=True)
def slug(text):
    text=re.sub(r'<[^>]+>', '', text).lower().strip()
    text=re.sub(r'[^\w\s-]', '', text)
    return re.sub(r'\s+', '-', text)
def short_id(path): return re.sub(r'[^a-z0-9]+','-',str(path).lower()).strip('-')
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def title_of(text, default):
    match=re.search(r'^#\s+(.+?)\s*#*\s*$',text,re.M)
    return match.group(1).replace('`','') if match else default
def git(repo,*args): return subprocess.check_output(['git','-C',str(repo),*args],text=True).strip()
def tracked(repo): return sorted(p for p in git(repo,'ls-files').splitlines() if (repo/p).is_file())

class Plain(HTMLParser):
    def __init__(self): super().__init__(); self.parts=[]
    def handle_data(self,s): self.parts.append(s)
    def handle_endtag(self,t):
        if t in ('p','div','li','h1','h2','h3','td','tr','pre'):self.parts.append(' ')
def plain(raw):
    p=Plain();p.feed(raw);return re.sub(r'\s+',' ',' '.join(p.parts)).strip()

ALLOWED={'p','h1','h2','h3','h4','h5','h6','a','em','strong','code','pre','blockquote','ul','ol','li','table','thead','tbody','tr','th','td','details','summary','br','hr','span','div','del','s','sup','sub','input'}
VOID={'br','hr','input'}
class CleanHTML(HTMLParser):
    """Retain document structure but never executable/imported HTML."""
    def __init__(self, repo, page, linkmap, commit, report):
        super().__init__(convert_charrefs=True); self.repo=repo;self.page=page;self.linkmap=linkmap;self.commit=commit;self.report=report;self.out=[];self.skip=0;self.hbuf=None;self.hattrs=None;self.used=defaultdict(int);self.linkstack=[]
    def append(self,s):
        if self.hbuf is not None:self.hbuf.append(s)
        else:self.out.append(s)
    def resolve(self,url):
        if not url:return None
        if url.startswith('#'):
            raw=unquote(url[1:]);target=raw if raw in self.linkmap.values() or '--' in raw else self.page['id']+'--'+raw
            return '#'+target
        parts=urlsplit(url)
        if parts.scheme:
            if parts.scheme not in ('http','https','mailto'):return None
            if url.startswith(REPOSITORY+'/blob/'):
                remain=url[len(REPOSITORY+'/blob/'):];parts2=remain.split('/',1)
                if len(parts2)==2:
                    source=unquote(parts2[1].split('#')[0]);fragment=parts.fragment
                    if source in self.linkmap:return '#'+self.linkmap[source]+('--'+fragment if fragment else '')
            return url
        if not self.page.get('source'):
            path=unquote(parts.path)
            if path in self.linkmap:return '#'+self.linkmap[path]+('--'+parts.fragment if parts.fragment else '')
            candidate=self.repo/path
        else:candidate=self.repo/self.page['source'].parent/unquote(parts.path)
        try:rel=candidate.resolve().relative_to(self.repo.resolve()).as_posix()
        except ValueError:return None
        if rel in self.linkmap:return '#'+self.linkmap[rel]+('--'+parts.fragment if parts.fragment else '')
        if not (self.repo/rel).exists():
            basename=Path(rel).name
            matches=[p for p in self.linkmap if Path(p).name==basename]
            if len(matches)==1:
                self.report['repaired_legacy_links'].append({'page':self.page['id'],'original':url,'resolved':matches[0]})
                return '#'+self.linkmap[matches[0]]+('--'+parts.fragment if parts.fragment else '')
            self.report['unavailable_legacy_links'].append({'page':self.page['id'],'target':url})
            return None
        return f'{REPOSITORY}/blob/{self.commit}/{rel}'+('#'+parts.fragment if parts.fragment else '')
    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs)
        if tag in ('script','style','iframe','object','embed'):self.skip+=1;return
        if self.skip:return
        if tag=='img':
            url=attrs.get('src','');alt=attrs.get('alt','Source figure');parts=urlsplit(url)
            if not parts.scheme and self.page.get('source'):
                file=(self.repo/self.page['source'].parent/unquote(parts.path)).resolve()
                if file.is_relative_to(self.repo.resolve()) and file.is_file() and file.suffix.lower() in ('.png','.jpg','.jpeg','.svg','.gif','.webp'):
                    mime=mimetypes.guess_type(file.name)[0] or 'image/png'
                    data=base64.b64encode(file.read_bytes()).decode()
                    self.append(f'<img loading="lazy" src="data:{mime};base64,{data}" alt="{esc(alt)}">');self.report['embedded_source_images'].append(str(file.relative_to(self.repo)));return
            link=self.resolve(url)
            self.append(f'<p class="small">Source figure: <a href="{esc(link)}">{esc(alt)}</a></p>' if link else f'<p class="small muted">Figure not present in this source snapshot: {esc(alt)}</p>');return
        if tag not in ALLOWED:return
        if re.fullmatch(r'h[1-6]',tag):self.hbuf=[];self.hattrs=tag;return
        if tag=='a':
            url=self.resolve(attrs.get('href',''));self.linkstack.append(bool(url))
            if url:self.append(f'<a href="{esc(url)}"'+(' rel="noopener noreferrer"' if url.startswith('http') else '')+'>')
            else:self.append(f'<span class="unavailable-link" title="Original link unavailable in this snapshot: {esc(attrs.get("href",""))}">')
            return
        safe={}
        if tag in ('code','ul','li','div','span') and attrs.get('class'):safe['class']=re.sub(r'[^a-zA-Z0-9_ -]','',attrs['class'])
        if tag=='ol' and attrs.get('start','').isdigit():safe['start']=attrs['start']
        if tag=='details' and 'open' in attrs:safe['open']=''
        if tag=='input':safe={'type':'checkbox','disabled':''};safe.update({'checked':''} if 'checked' in attrs else {})
        if tag in ('td','th'):
            for k in ('colspan','rowspan'):
                if attrs.get(k,'').isdigit():safe[k]=attrs[k]
        self.append('<'+tag+''.join(f' {k}="{esc(v)}"' for k,v in safe.items())+'>')
    def handle_endtag(self,tag):
        if tag in ('script','style','iframe','object','embed'):
            self.skip=max(0,self.skip-1);return
        if self.skip:return
        if re.fullmatch(r'h[1-6]',tag) and self.hbuf is not None:
            text=''.join(self.hbuf);self.hbuf=None
            s=slug(plain(text));n=self.used[s];self.used[s]+=1;s=s+('-'+str(n) if n else '')
            level=int(tag[1]);level=max(2,level) # Article title is provided once by the shell.
            self.out.append(f'<h{level} id="{self.page["id"]}--{esc(s)}">{text}</h{level}>');return
        if tag=='a':self.append('</a>' if self.linkstack.pop() else '</span>');return
        if tag in ALLOWED and tag not in VOID:self.append('</'+tag+'>')
    def handle_data(self,data):
        if not self.skip:self.append(esc(data))
    def handle_comment(self,data):pass

def classify(path):
    path=str(path)
    if path in ('CLAUDE.md','roguelike/CLAUDE.md') or 'WORLD_GENERATION_AUDIT_AND_PROPOSAL' in path or path.endswith('/ESSENCE.md'):
        return 'Design / mixed','design','Creative intent, historical implementation notes or a proposal. This text is retained in full; it is not proof that every described mechanic is implemented.'
    if path=='AGENTS.md':return 'Working convention','source','Repository collaboration rules at the audited revision. Apply them with the current owner instructions.'
    if path=='README.md':return 'Current entry point','source','Current G6 repository entry point. The wiki provides a consolidated owner workflow.'
    if path.endswith('WORLDGEN_G6.md'):return 'G6 delivery record','source','Current G6 delivery and verification scope. Recorded delivery tests are distinct from the focused checks run to create this wiki.'
    if path.endswith('TUNING_EXISTING_FEATURES.md'):
        return 'Current / caveats','archive','Useful current tuning guide with retained caveats. In particular, the claimed equipped-light crafting heat source does not work through normal offhand light equip in this revision; read the current crafting chapter.'
    if path.endswith('STRUCTURE_AUTHORING.md'):
        return 'Current + history','archive','This guide contains current G6 sections and a retained legacy G2 middle. Its old no-rotation and rural-POIs-deferred statements do not govern new G6 plans. Use the consolidated structure chapters for current steps.'
    if '/evidence/' in '/'+path or '_VERIFICATION' in path or re.search(r'WORLDGEN_G[1-5]\.md$',path):
        return 'Historical evidence','archive','A dated delivery/evidence record. Preserve its source identity and scope; do not read old passing counts or unresolved findings as a new test of current changes.'
    if '/owner/' in path:
        note='Earlier state, decisions or workflow with superseding and nested history. Use current wiki instructions for operation. The original wording is preserved for traceability.'
        if path.endswith('B3_STATE.md'):note+=' Its surface-boundary autosave statement was superseded by the later critical-fix pass: travel now preserves the last explicit checkpoint.'
        if path.endswith('STATUS.md'):note+=' Its top status is G5; the root README and WORLDGEN_G6 describe the newer G6 delivery.'
        if path.endswith('NEXT_ARC.md'):note+=' Its top next-arc recommendation is after G2 and is no longer the current implementation frontier.'
        return 'Historical / mixed','archive',note
    return 'Historical / mixed','archive','Original technical/design documentation retained in full. Several older schemas and runtime claims are superseded. Use the current guide layer for supported fields, units and workflows.'

def debug_table(repo):
    tree=ast.parse((repo/'roguelike/engine/debug.py').read_text(encoding='utf-8-sig'))
    rows=[]
    for node in tree.body:
        if isinstance(node,ast.AnnAssign) and getattr(node.target,'id','')=='CONSOLE_COMMANDS':
            for key,value in zip(node.value.keys,node.value.values):
                meta={ast.literal_eval(k):ast.literal_eval(v) for k,v in zip(value.keys,value.values) if isinstance(v,ast.Constant)}
                rows.append((meta.get('category',''),meta.get('usage',ast.literal_eval(key)),meta.get('desc','')))
    return '| Group | Exact command | Registry description |\n|---|---|---|\n'+'\n'.join('| '+a+' | `'+b.replace('|','\\|')+'` | '+c+' |' for a,b,c in rows)

def data_category(rel):
    bits=Path(rel).relative_to('roguelike/data').parts
    if len(bits)>1:
        return {'entities':'creatures','sprites':'terrain-and-sprites','bodies':'world-settings'}.get(bits[0],bits[0])
    return 'terrain-and-sprites' if bits[0] in ('terrain.json','decoratives.json','tiles.json') else 'world-settings'

def collect(repo,config):
    pages=[];links={};records=[];source_files=tracked(repo)
    for item in config['chapters']:
        path=ROOT/item['file'];text=path.read_text(encoding='utf-8')
        text=text.replace('<!-- DEBUG_COMMAND_TABLE -->',debug_table(repo))
        page={**item,'text':text,'title':item.get('title') or title_of(text,path.stem),'kind':'guide','source':None}
        pages.append(page)
    docs=[p for p in source_files if p.lower().endswith('.md')]
    for p in docs:
        text=(repo/p).read_text(encoding='utf-8-sig');status,cls,note=classify(p)
        page={'id':'source-'+short_id(p),'title':title_of(text,Path(p).name),'group':'Source library','kind':'source','source':Path(p),'text':text,'status':status,'class':cls,'note':note}
        pages.append(page);links[p]=page['id']
    groups=defaultdict(list)
    for rel in source_files:
        if rel.startswith('roguelike/data/') and rel.lower().endswith('.json'):
            cat=data_category(rel);groups[cat].append((repo/rel,rel,False))
        elif rel.startswith('roguelike/docs/examples/') and rel.lower().endswith('.json'):
            groups['examples'].append((repo/rel,rel,False))
    for path in sorted((ROOT/'examples').glob('*.json')):groups['examples'].append((path,'wiki/examples/'+path.name,True))
    for cat,files in groups.items():
        title={'terrain-and-sprites':'Terrain, decor & sprite registries','world-settings':'World, language & system settings','loot_pools':'Container loot pools','generation':'Generation policies','wfc':'WFC palettes','examples':'Complete authoring examples','creatures':'Creature definitions'}.get(cat,cat.replace('_',' ').title())
        pid='catalog-'+short_id(cat)
        entries=[]
        for file,rel,is_new in files:
            raw=file.read_text(encoding='utf-8-sig');obj=json.loads(raw)
            rid='data-'+short_id(rel);links[rel]=rid
            label=obj.get('id',file.stem) if isinstance(obj,dict) else file.stem
            entries.append({'id':rid,'path':rel,'title':str(label),'raw':raw,'bytes':file.stat().st_size,'sha256':sha(file),'new':is_new})
        page={'id':pid,'title':title,'group':'Content catalogues','kind':'data','source':None,'entries':entries,'text':''}
        pages.append(page);records+=entries
    for p in pages:links[p['id']]=p['id']
    return pages,links,records,docs

def read_audits():
    out={}
    for p in (ROOT/'audit').glob('*.json'):
        try:out[p.name]=json.loads(p.read_text(encoding='utf-8'))
        except ValueError:pass
    return out

def source_index(pages,repo,commit):
    sources=[p for p in pages if p['kind']=='source']
    out=['<p>Every tracked Markdown document in the audited repository is included below. The current guides reconcile operational instructions; these original texts preserve design intent, source context and delivery history.</p>',
    '<div class="callout"><strong>Read the status before following instructions.</strong> A recent file can contain older nested sections. “Current” in an original heading refers to that document’s own historical context, not automatically to G6.</div>',
    '<div class="filter-row"><label class="sr-only" for="source-filter">Filter original documents</label><input id="source-filter" type="search" placeholder="Filter by title, path or status…" data-filter="source-entries"><span class="small muted" data-filter-count="source-entries">'+str(len(sources))+' entries</span></div><p class="empty-filter">No matching sources.</p><div id="source-entries">']
    for p in sources:
        path=str(p['source']);out.append(f'<div class="index-entry" data-filter-text="{esc(p["title"]+" "+path+" "+p["status"])}"><a href="#{p["id"]}">{esc(p["title"])}</a> <span class="tag {p["class"]}">{esc(p["status"])}</span><span class="path-label">{esc(path)}</span><p>{esc(p["note"])}</p></div>')
    out.append('</div>');return ''.join(out)

def catalog_html(page,commit):
    entries=page['entries'];pid=page['id'];out=[f'<p>Exact source definitions from the audited revision. Search and expand any file, then copy its complete JSON or download it. There are <strong>{len(entries)} files</strong> in this catalogue.</p>',
    '<div class="callout"><strong>Declared fields are not automatically implemented features.</strong> These files preserve the exact data. Consult the current authoring chapter for active consumers, units, registration and saved-world behavior. Complete examples remain drafts until deliberately installed.</div>',
    f'<div class="filter-row"><label class="sr-only" for="{pid}-filter">Filter {esc(page["title"])}</label><input id="{pid}-filter" type="search" data-filter="{pid}-entries" placeholder="Filter by ID, filename or path…"><button data-expand="{pid}-entries" type="button">Expand entries</button><span class="small muted" data-filter-count="{pid}-entries">{len(entries)} entries</span></div><p class="empty-filter">No matching entries.</p><div id="{pid}-entries">']
    for r in entries:
        src=f'<a href="{REPOSITORY}/blob/{commit}/{esc(r["path"])}">Pinned source ↗</a>' if not r['new'] else '<span class="tag">New, checked wiki example</span>'
        out.append(f'<details class="data-record" id="{r["id"]}" data-filter-text="{esc(r["title"]+" "+r["path"])}"><summary><strong>{esc(r["title"])}</strong> <span class="path-label">{esc(Path(r["path"]).name)}</span></summary><p class="path-label">{esc(r["path"])}</p><div class="data-head">{src}<button type="button" class="quiet-button" data-download="{r["id"]}" data-filename="{esc(Path(r["path"]).name)}">Download JSON</button><span class="small muted">{r["bytes"]:,} bytes · SHA-256 {r["sha256"][:12]}…</span></div><pre data-language="json"><code class="language-json">{esc(r["raw"])}</code></pre></details>')
    out.append('</div>');return ''.join(out)

def catalogue_index(pages):
    shipped=sum(r['path'].startswith('roguelike/data/') for p in pages if p['kind']=='data' for r in p['entries'])
    out=[f'<p>Browse the game’s exact JSON, grouped by the work it supports. This edition embeds all <strong>{shipped} JSON files under <code>roguelike/data/</code></strong>, every repository authoring example, and the new checked cottage. No network request is needed to inspect or copy them.</p><p>Use global search for a field or content ID. The per-catalogue filter narrows filenames and IDs; expanding a file reveals the original complete definition.</p><div class="cards">']
    for p in pages:
        if p['kind']=='data':out.append(f'<a class="card" href="#{p["id"]}"><span class="card-no">{len(p["entries"])} FILES <span class="arrow">↗</span></span><h3>{esc(p["title"])}</h3><p>Complete definitions, pinned sources and copyable JSON.</p></a>')
    out.append('</div>');return ''.join(out)

def home_html(config,pages,docs,records):
    count=sum(p['kind']=='guide' for p in pages)
    shipped=sum(r['path'].startswith('roguelike/data/') for r in records)
    cards=[('01 / FIRST STEPS','Start working on the game','Set up the interpreter, run a disposable world and make one verifiable change.','getting-started'),('02 / WORLD AUTHORING','Build a place','Create a complete cottage, give it usable access and make it appear in new town plans.','first-building'),('03 / CONTENT','Add something worth finding','Items, creatures, recipes, readable texts, loot and progression—with the actual data routes.','content-workflow'),('04 / COMPOSITION','Shape the wider world','Town roles, roads, country-road sites, selection weights and the limits of existing plans.','world-generation'),('05 / PRESENTATION','Give it a visual identity','Sprite atlases, functional terrain and decor, palette, fonts and interface settings.','sprites-and-atlases'),('06 / REFERENCE','Find the exact definition','All shipped data and the original guide archive, organised for offline use.','catalogues')]
    art='<svg class="hero-art" viewBox="0 0 340 240" fill="none" aria-hidden="true"><g stroke="#83b79b" stroke-width="1"><path d="M25 225C-10 159 76 160 70 105S157 85 155 41 264 5 310 55 289 132 337 154"/><path d="M45 240C3 172 98 177 94 112S173 105 180 52 260 30 291 67 264 143 331 176"/><path d="M75 246C27 188 121 185 119 125S196 119 202 70 251 61 265 82 244 156 326 198"/><path d="M105 240C60 207 146 196 145 143S214 136 225 97 245 106 237 128 279 194 328 217"/><path d="M2 137C41 137 21 92 64 66S109 59 104 19M134 240C94 214 170 207 173 169S214 158 234 184 280 235 320 236"/><circle cx="224" cy="101" r="6" fill="#d0b485" stroke="none"/><path d="M224 79V89M224 113V123M202 101H212M236 101H246" stroke="#d0b485"/></g></svg>'
    out=[f'<div class="hero">{art}<div class="eyebrow">An owner’s field guide</div><h1>A world to shape.<br><span>A place to begin.</span></h1><p>The working handbook for Resonance. Find the right file, understand what the game actually reads, and check the result—from a small balance edit to a new place on a country road.</p><div class="edition">{esc(config["milestone"])} edition · {esc(config["date_label"])} · Offline & self-contained</div></div>',
    f'<div class="metrics"><div class="metric"><b>{count}</b><span>current guide chapters</span></div><div class="metric"><b>{len(docs)}</b><span>original source documents</span></div><div class="metric"><b>{shipped}</b><span>shipped JSON files</span></div></div>',
    '<div class="section-label">What would you like to work on?</div><div class="cards">']
    for no,title,desc,pid in cards:out.append(f'<a class="card" href="#{pid}"><span class="card-no">{no} <span class="arrow">↗</span></span><h3>{title}</h3><p>{desc}</p></a>')
    out+=['</div><div class="section-label">Keep close at hand</div><div class="quick-links"><a href="#controls">Controls</a><a href="#debug-tools">Debug console</a><a href="#saves-and-state">Save & load</a><a href="#verification">Verification</a><a href="#troubleshooting">Troubleshooting</a><a href="#glossary">Glossary</a></div>',
    '<h2 id="home--a-guide-you-can-trace">A guide you can trace</h2><p>The current chapters reconcile the loaders, factories, planners and runtime code at the revision shown below. Original documents are retained separately with visible status labels. Data catalogues preserve the actual files; the guides explain which fields the game uses.</p>',
    '<div class="callout"><strong>Two useful things to know first.</strong> The shipped debug mode makes F5 a teleport and F9 a state dump. Changed world-generation settings apply to new plans; an existing saved world does not automatically acquire them. See <a href="#saves-and-state">save and world behavior</a>.</div>',
    '<h2 id="home--using-the-handbook">Using the handbook</h2><p>Choose a chapter from the left, or press <kbd>/</kbd> or <kbd>Ctrl</kbd> + <kbd>K</kbd> to search everything. Search results identify current guides, data and original sources. Code blocks have copy buttons; the top bar adjusts reading size, copies the current link and prints the current chapter. The text remains available without JavaScript.</p>',
    f'<p class="small muted">Edition {esc(config["edition"])} · Source <a href="{REPOSITORY}/commit/{config["commit"]}"><code>{config["commit"]}</code></a><br>For the checks performed and limits of this edition, read <a href="#coverage">Coverage & audit</a>. For later feature pushes, follow <a href="#maintenance">Updating the handbook</a>.</p>']
    return ''.join(out)

def coverage_html(config,pages,docs,records,repo):
    guides=[p for p in pages if p['kind']=='guide'];words=sum(len(re.findall(r'\b\w+\b',p.get('text',''))) for p in guides)
    shipped=sum(r['path'].startswith('roguelike/data/') for r in records)
    examples=sum(r['path'].startswith('roguelike/docs/examples/') for r in records)
    text=f'''# Coverage and verification

This edition was audited on {config['date_label']} against `{config['commit']}` on `main`. The current guide layer contains **{len(guides)} authored chapters**, approximately **{words:,} words**, plus generated navigation, source coverage and catalogue pages.

## What is included

- All **{len(docs)} tracked repository Markdown documents**, including both documentation trees, the root guides, the perks README and evidence readmes. Original text is preserved with scope annotations.
- All **{shipped} JSON files under `roguelike/data/`**, organised into catalogues. These are exact snapshot definitions, not claims that every declared field is active.
- All **{examples} repository JSON authoring examples**, plus the complete new cottage created for this handbook.
- Current owner workflows for setup, controls, saving, items, combat, creatures, crafting, texts, loot, perks, survival, weather, world generation, structures, POIs, entrances, WFC, sprites, decor and the interface.
- A source manifest for subsequent revision checks. Code and definition links are pinned to this exact commit.

The uploaded `FullGame.zip` was checked for documentation coverage: all 42 Markdown documents in it also exist in the current checkout. Forty were identical after line-ending normalization; two had changed. The B–D review package and generation proposal were used as historical context. Neither supersedes the newer repository implementation. This is not a fresh forensic audit of every file in those older archives.

## Checks actually run for this wiki

| Check | Observed result | Scope |
|---|---|---|
| Current disposable launcher with seed 20261023 | Passed; shared-v1 plan, start [73,99], submap sub_73_99_0 | Actual headless initialization, not a complete playthrough. |
| Current structure catalogue | 64 assets, zero errors; 238 classified warnings | Shared authoring catalogue and supported constraints. |
| Existing G5 service house | Eight transforms and five selected grid previews passed | Candidate/complete scene checks at the stated seed. |
| Existing G6 wayhouse | Assigned east-frontage complete scene passed | Controlled site fit and materialization. |
| Authored starting laboratory | Direct preview passed | Current 60×16 layout route. |
| New wiki cottage | Eight transforms, three selected grid scenes, two selected roadside scenes passed | Complete example checked against current mixed policies at seed 20261023. |
| WFC example | 6×6 town_block solve and final adjacency check passed | Bounded solver example; fresh planned G6 towns use a different ground-fill route. |
| Content examples and consumers | 33 focused checks passed | Actual loaders/factories/crafting/loot/language/perk checks; includes reproduction of documented limits. |
| Asset loading probe | Six sheets, 263 mappings, 129 tile definitions inspected | Dummy-driver source/loading check; exposed the documented wall_pillar/Urizen geometry mismatch and ignored vine entries. |
| Generated editor catalogue freshness | **Failed on the untouched clone** | Raw identity differs although compared semantic sections and contract hash match. The cause is not established. |
| Handbook integrity | Passed; unique identifiers, internal links, search targets, source coverage and embedded JSON verified | Complete data definitions compare by value with the pinned checkout. Insertion fragments and historical abbreviated examples are reported separately. |
| Handbook browser review | Desktop, 390px and 768px layouts, navigation, search, filters and JSON download checked | Cloud Chrome HTTP preview; no physical Windows-keyboard or native file-URL browser certification. |

The focused runtime environment was Linux, CPython **3.12.14**, Pygame **2.6.1** and tcod **19.3.0**, with the exact declared dependency pins. It is distinct from the repository's recorded Windows / Python 3.11 acceptance environment.

This wiki does not claim a new full production/release gate, universal gameplay correctness, a physical Windows-keyboard check, or owner acceptance of a future feature. Recorded repository delivery evidence remains available with its original scope. The game source was not changed to make documentation probes pass.

## Corrections made in the current guide layer

The current chapters replace misleading operational advice about item field names, per-limb HP, loot schemas, torch crafting heat, perk prerequisite enforcement, creature spawn weights, modern structure selection/rotation, legacy WFC scope, old lab dimensions, debug teleports, travel autosaving, sprite defaults, palette identity and temporary sprite remapping.

Use [Troubleshooting](#troubleshooting) for the practical consequences. An unsupported field is labelled as such; the handbook does not silently implement it or redefine creative intent.

## The original source record

The [Source library](#source-library) is the exhaustive document inventory. Each entry identifies its repository path, status and any major caveat. Its rendered page includes a source SHA-256 and a pinned source link. The [Data catalogues](#catalogues) provide the equivalent source trace for JSON.

All reader content, styles, search data and included figures are embedded in the HTML. Only deliberately clicked external source links need an internet connection. See [Maintenance](#maintenance) for the rebuild and audit procedure.

The companion source package includes the reusable `validate_wiki.py` checker and recorded browser/audit results. It checks the document's integrity independently of the game probes. Structural offline checks confirm that the reader declares no external runtime assets and does not fetch its content from separate files.
'''
    return text

def render_document(repo,config,pages,linkmap,records,docs,md,report,output):
    extra=[{'id':'home','title':'The owner’s field guide','group':'Start here','kind':'guide','body':home_html(config,pages,docs,records)},
           {'id':'catalogues','title':'Browse the data','group':'Reference & upkeep','kind':'guide','body':catalogue_index(pages)},
           {'id':'source-library','title':'Original source library','group':'Reference & upkeep','kind':'guide','body':source_index(pages,repo,config['commit'])},
           {'id':'coverage','title':'Coverage & audit','group':'Reference & upkeep','kind':'guide','text':coverage_html(config,pages,docs,records,repo)}]
    for p in extra:linkmap[p['id']]=p['id']
    allpages=[extra[0]]+pages+extra[1:]
    # Establish every internal target before resolving relative links.
    pageids={p['id'] for p in allpages};linkmap.update({x:x for x in pageids})
    index=[];rendered=[]
    curated=[p for p in allpages if p['kind']=='guide']
    for page in allpages:
        pid=page['id'];kind=page['kind'];page.setdefault('source',None)
        if kind=='data':body=catalog_html(page,config['commit'])
        elif 'body' in page:body=page['body']
        else:
            text=re.sub(r'^#\s+[^\n]+\n','',page.get('text',''),count=1,flags=re.M)
            cleaner=CleanHTML(repo,page,linkmap,config['commit'],report);cleaner.feed(md(text));body=''.join(cleaner.out)
        body=re.sub(r'<table>',r'<div class="table-wrap"><table>',body).replace('</table>','</table></div>')
        if pid=='first-building' and (ROOT/'illustrations/owner-cottage.svg').exists():
            image=base64.b64encode((ROOT/'illustrations/owner-cottage.svg').read_bytes()).decode()
            illustration=f'<details><summary>View the verified cottage preview</summary><img src="data:image/svg+xml;base64,{image}" alt="Actual diagnostic map preview of the new cottage from the structure validator"><p class="small muted">Validator output at seed 20261023. This is a diagnostic map, not a game-renderer screenshot.</p></details><p><button class="quiet-button" type="button" data-download="data-wiki-examples-owner-cottage-a-json" data-filename="owner_cottage_a.json">Download the complete cottage JSON</button> <a href="#data-wiki-examples-owner-cottage-a-json" class="small">Inspect the complete example</a></p>'
            first=body.find('<h2');body=body[:first]+illustration+body[first:] if first>=0 else illustration+body
        if kind=='source':
            source=str(page['source']);meta=f'<span class="tag {page["class"]}">{esc(page["status"])}</span><span>{esc(source)}</span><span>SHA-256 {sha(repo/source)[:12]}…</span>'
            sourceurl=f'{REPOSITORY}/blob/{config["commit"]}/{source}'
            body=f'<div class="callout"><strong>Source scope.</strong> {esc(page["note"])} <a href="#source-library">Back to source inventory</a>.</div>'+body
        elif kind=='data':meta='<span class="tag data">Snapshot data</span><span>'+str(len(page['entries']))+' complete files</span>';sourceurl=None
        else:meta='<span class="tag">Current guide</span><span>Audited '+esc(config['date_label'])+'</span><span>'+esc(config['milestone'])+' · '+config['commit'][:12]+'</span>';sourceurl=None
        if sourceurl:meta+=f'<a href="{esc(sourceurl)}" rel="noopener noreferrer">Original at this commit ↗</a>'
        header='' if pid=='home' else f'<header class="article-header"><div class="eyebrow">{esc(page["group"])}</div><h1>{esc(page["title"])}</h1><div class="article-meta">{meta}</div></header>'
        footer=''
        if kind=='guide' and pid!='home':
            pos=curated.index(page);prev=curated[pos-1] if pos else None;nxt=curated[pos+1] if pos+1<len(curated) else None
            footer='<nav class="page-footer" aria-label="Chapter navigation">'+(f'<a href="#{prev["id"]}"><small>Previous</small>← {esc(prev["title"])}</a>' if prev else '<span></span>')+(f'<a class="next" href="#{nxt["id"]}"><small>Next</small>{esc(nxt["title"])} →</a>' if nxt else '')+'</nav>'
        rendered.append(f'<article class="article" id="{pid}" data-page="{pid}" data-title="{esc(page["title"])}" data-group="{esc(page["group"])}" data-kind="{kind}">{header}{body}{footer}</article>')
        if kind=='data':
            for r in page['entries']:index.append({'id':r['id'],'page':pid,'title':r['title']+' · '+Path(r['path']).name,'group':page['title'],'kind':'data','text':r['path']+' '+r['raw']})
        else:index.append({'id':pid,'page':pid,'title':page['title'],'group':page['group'],'kind':kind,'text':plain(body)})
    # Validate/correct fragments in historical documents after their headings exist.
    whole=''.join(rendered);ids=set(re.findall(r'\bid="([^"]+)"',whole));repairs=[]
    def fix_fragment(match):
        target=html.unescape(match.group(1))
        if target in ids:return match.group(0)
        owner=target.split('--')[0]
        if owner in pageids:
            repairs.append({'target':target,'fallback':owner});return 'href="#'+owner+'"'
        raise ValueError('Broken current internal link: '+target)
    whole=re.sub(r'href="#([^"]+)"',fix_fragment,whole)
    report['fragment_fallbacks']=repairs
    navgroups=defaultdict(list)
    for page in allpages:
        if page['kind']!='source':navgroups[page['group']].append(page)
    nav=[]
    for group in config['group_order']:
        group_pages=navgroups.get(group,[])
        if not group_pages:continue
        items=''.join(f'<a class="nav-link" href="#{p["id"]}">{esc(p.get("nav_title",p["title"]))}</a>' for p in group_pages)
        nav.append(f'<details class="nav-section"'+(' open' if group not in ('Content catalogues',) else '')+f'><summary>{esc(group)}</summary>{items}</details>')
    css=(ROOT/'theme.css').read_text(encoding='utf-8');js=(ROOT/'reader.js').read_text(encoding='utf-8');search_json=json.dumps(index,ensure_ascii=False).replace('<','\\u003c').replace('>','\\u003e').replace('&','\\u0026')
    logo='<svg class="brand-mark" width="34" height="43" viewBox="0 0 34 43" fill="none" aria-hidden="true"><path d="M17 2V41M5 11L17 4L29 11M5 31L17 38L29 31M7 14L25 29M27 14L9 29" stroke="currentColor" stroke-width="1.2"/><circle cx="17" cy="21" r="5" stroke="currentColor"/><circle cx="17" cy="4" r="2" fill="currentColor"/></svg>'
    shell=f'''<!doctype html>
<html lang="en" data-source-revision="{esc(config['commit'][:12])}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><meta name="color-scheme" content="dark"><meta name="description" content="The comprehensive offline owner handbook for Resonance Roguelike, audited against {esc(config['milestone'])}."><title>Resonance · Owner’s field guide</title><style>{css}</style></head><body>
<a class="skip" href="#main">Skip to content</a>
<aside class="sidebar" aria-label="Handbook navigation"><a href="#home" class="brand">{logo}<span><strong>RESONANCE</strong><small>The owner’s field guide</small></span></a><button class="nav-search" data-search-open type="button"><span aria-hidden="true">⌕</span> Search the handbook <kbd>/</kbd></button><nav class="nav-scroll">{''.join(nav)}</nav><div class="nav-foot"><span class="revision-dot"></span>{esc(config['milestone'])} · Edition {esc(config['edition'])}<br><a href="#coverage">{config['commit'][:12]} · {esc(config['date_label'])}</a><br><a href="#maintenance">Keep this handbook current ↗</a></div></aside>
<div class="mobile-shade" id="mobile-shade"></div>
<header class="topbar"><button class="menu-button" id="menu-toggle" type="button" aria-label="Toggle chapter navigation" aria-expanded="false">☰</button><div class="crumb"><span id="breadcrumb">Start here</span> <span aria-hidden="true"> / </span><span id="current-title">The owner’s field guide</span></div><div class="top-actions"><span class="top-chip">LOCAL EDITION</span><button type="button" class="quiet-button icon-button" data-font="-1" aria-label="Decrease reading size">A−</button><button type="button" class="quiet-button icon-button" data-font="1" aria-label="Increase reading size">A+</button><button type="button" class="quiet-button" id="copy-link" aria-label="Copy link to this page">Link</button><button type="button" class="quiet-button print-button" id="print-page">Print</button><button class="quiet-button" data-search-open type="button" aria-label="Search handbook">⌕</button></div></header>
<div id="reading-progress" class="reading-progress" aria-hidden="true"></div>
<noscript><div class="notice">JavaScript is disabled. All chapters remain readable below; use your browser’s Find command and the navigation links.</div></noscript>
<main class="main" id="main">{whole}</main>
<aside class="toc" aria-label="On this page"><div class="toc-title" id="toc-label">On this page</div><nav id="toc-links"></nav><div class="toc-footer" id="toc-note"></div></aside>
<dialog class="search-dialog" id="search-dialog" aria-label="Search the handbook"><div class="search-head"><label><span class="sr-only">Search query</span><input id="search-input" type="search" placeholder="What would you like to find?" autocomplete="off" spellcheck="false"></label><button id="search-close" type="button" aria-label="Close search">Esc</button></div><div class="search-options"><label for="search-scope">Look in</label><select id="search-scope"><option value="all">All content</option><option value="guide">Current guides</option><option value="data">Snapshot data</option><option value="source">Original sources</option></select><span class="search-count" id="search-count" aria-live="polite"></span></div><div class="search-results" id="search-results"></div><div class="search-foot">↑ ↓ to move · Enter to open · Esc to close · Everything is searched locally</div></dialog>
<div class="toast" id="toast" role="status" aria-live="polite"></div>
<script type="application/json" id="search-index">{search_json}</script><script>{js}</script></body></html>'''
    output=output.resolve();output.parent.mkdir(parents=True,exist_ok=True);output.write_text(shell,encoding='utf-8',newline='\n')
    report.update(article_count=len(allpages),guide_chapters=sum(p['kind']=='guide' for p in pages),search_records=len(index),output_bytes=output.stat().st_size,output_sha256=sha(output))
    (ROOT/'build-report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if not isinstance(v,list)},indent=2))

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo',required=True,type=Path);parser.add_argument('--output',type=Path,default=ROOT/'Resonance_Owner_Wiki.html');parser.add_argument('--check-drift',action='store_true');parser.add_argument('--write-manifest',action='store_true')
    args=parser.parse_args();repo=args.repo.resolve();config=json.loads((ROOT/'wiki-config.json').read_text(encoding='utf-8'));head=git(repo,'rev-parse','HEAD')
    files=tracked(repo);fingerprints={p:sha(repo/p) for p in files};baseline_path=ROOT/'source-manifest.json'
    if args.check_drift:
        base=json.loads(baseline_path.read_text(encoding='utf-8'));old=base['files'];drift={'audited_commit':base['commit'],'current_commit':head,'changed':[p for p in old if p in fingerprints and old[p]!=fingerprints[p]],'missing':[p for p in old if p not in fingerprints],'added':[p for p in fingerprints if p not in old]}
        drift['clean']=head==base['commit'] and not any(drift[k] for k in ('changed','missing','added'))
        print(json.dumps(drift,indent=2));return 0 if drift['clean'] else 2
    if head!=config['commit']:parser.error('Repository HEAD differs from the reviewed wiki revision. Audit affected chapters, then deliberately update wiki-config.json before building.')
    if git(repo,'status','--porcelain','--untracked-files=no'):parser.error('Tracked repository changes exist. Build from the reviewed clean revision so the SHA identifies the actual source.')
    if args.write_manifest or not baseline_path.exists():baseline_path.write_text(json.dumps({'repository':REPOSITORY,'commit':head,'audited':config['date'],'files':fingerprints},indent=2)+'\n',encoding='utf-8')
    import mistune
    md=mistune.create_markdown(escape=False,plugins=['table','strikethrough','url','task_lists'])
    pages,linkmap,records,docs=collect(repo,config)
    report={'commit':head,'repaired_legacy_links':[],'unavailable_legacy_links':[],'embedded_source_images':[],'article_count':0,'data_files':len(records),'source_documents':len(docs)}
    render_document(repo,config,pages,linkmap,records,docs,md,report,args.output)
    return 0

if __name__=='__main__':raise SystemExit(main())

