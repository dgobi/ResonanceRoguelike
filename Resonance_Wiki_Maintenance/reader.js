/* Progressive enhancement: all document text is already in the HTML. */
(()=>{'use strict';
const $=(s,r=document)=>r.querySelector(s), $$=(s,r=document)=>Array.from(r.querySelectorAll(s));
const articles=$$('article[data-page]'), pages=new Map(articles.map(a=>[a.id,a]));
let active=null, toastTimer=null, scrollFrame=false, searchTimer=null;
const dialog=$('#search-dialog'), searchInput=$('#search-input'), results=$('#search-results');
const index=JSON.parse($('#search-index').textContent);
const escape=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const stateKey='resonance-owner-wiki-v1';
let preferences={font:16};
try{preferences={...preferences,...JSON.parse(localStorage.getItem(stateKey)||'{}')}}catch(e){}
preferences.font=Math.min(20,Math.max(14,Number(preferences.font)||16));
document.documentElement.style.setProperty('--reading',preferences.font+'px');
function notify(message){const t=$('#toast');t.textContent=message;t.classList.add('visible');clearTimeout(toastTimer);toastTimer=setTimeout(()=>t.classList.remove('visible'),2700)}
function savePreferences(){try{localStorage.setItem(stateKey,JSON.stringify(preferences))}catch(e){}}
function openAncestors(element){for(let n=element.parentElement;n;n=n.parentElement)if(n.tagName==='DETAILS')n.open=true;if(element.tagName==='DETAILS')element.open=true}
function revealFilteredTarget(target){
 const hidden=target.closest('.hidden-by-filter');if(!hidden)return;
 const input=$$('[data-filter]').find(input=>document.getElementById(input.dataset.filter)?.contains(hidden));
 if(input){input.value='';input.dispatchEvent(new Event('input',{bubbles:true}))}
}
function go(){
 let id;try{id=decodeURIComponent(location.hash.slice(1))}catch(e){id='home'}
 if(id==='main'){const main=$('#main');main.setAttribute('tabindex','-1');main.focus();return}
 let target=id?document.getElementById(id):null;
 let page=target?.closest('article[data-page]');
 if(!page){page=pages.get('home');target=page;if(id)notify('That section is not in this edition. Use search to find it.')}
 const changed=active!==page;
 if(changed){
  if(active)active.classList.remove('active');
  active=page;page.classList.add('active');
  document.title=page.dataset.title+' · Resonance Owner Wiki';
  $('#breadcrumb').textContent=page.dataset.group;
  $('#current-title').textContent=page.dataset.title;
  $$('.nav-link').forEach(a=>{const selected=a.hash==='#'+page.id;a.classList.toggle('active',selected);if(selected){a.setAttribute('aria-current','page');for(let p=a.parentElement;p;p=p.parentElement)if(p.tagName==='DETAILS')p.open=true}else a.removeAttribute('aria-current')});
  renderToc(page);
 }
 document.body.classList.remove('nav-open');$('#menu-toggle').setAttribute('aria-expanded','false');
 revealFilteredTarget(target);openAncestors(target);
 if(changed||target!==page){requestAnimationFrame(()=>{if(target===page)window.scrollTo({top:0,behavior:'instant'});else target.scrollIntoView({behavior:'instant',block:'start'});target.setAttribute('tabindex','-1');target.focus({preventScroll:true});progress()})}
}
function renderToc(page){const heads=$$('h2[id],h3[id]',page).filter(h=>!h.closest('.data-record'));$('#toc-links').innerHTML=heads.slice(0,45).map(h=>`<a href="#${escape(h.id)}" class="${h.tagName==='H3'?'toc-sub':''}">${escape(h.textContent)}</a>`).join('');$('#toc-label').textContent=heads.length?'On this page':'Your field guide';$('#toc-note').textContent=page.dataset.kind==='source'?'Original repository text. Read the status banner before using historical instructions.':'Source snapshot '+document.documentElement.dataset.sourceRevision+'. Use the source links to inspect the recorded implementation.'}
function progress(){if(!active)return;const height=Math.max(1,document.documentElement.scrollHeight-innerHeight);const ratio=Math.min(1,Math.max(0,scrollY/height));const left=parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--side'))||0;$('#reading-progress').style.width=((innerWidth-left)*ratio)+'px';const heads=$$('h2[id],h3[id]',active);let current='';for(const h of heads){if(h.getBoundingClientRect().top<150)current=h.id;else break}$$('#toc-links a').forEach(a=>a.classList.toggle('current',a.hash==='#'+current))}
window.addEventListener('scroll',()=>{if(!scrollFrame){scrollFrame=true;requestAnimationFrame(()=>{progress();scrollFrame=false})}},{passive:true});window.addEventListener('resize',progress);
window.addEventListener('hashchange',go);
$('#menu-toggle').addEventListener('click',()=>{const open=document.body.classList.toggle('nav-open');$('#menu-toggle').setAttribute('aria-expanded',String(open))});$('#mobile-shade').addEventListener('click',()=>{document.body.classList.remove('nav-open');$('#menu-toggle').setAttribute('aria-expanded','false')});
$$('[data-font]').forEach(b=>b.addEventListener('click',()=>{preferences.font=Math.max(14,Math.min(20,preferences.font+Number(b.dataset.font)));document.documentElement.style.setProperty('--reading',preferences.font+'px');savePreferences();notify('Reading size: '+preferences.font+' px')}));
async function copy(text,button){let success=false;try{if(navigator.clipboard&&window.isSecureContext){await navigator.clipboard.writeText(text);success=true}}catch(e){}
 if(!success){const t=document.createElement('textarea');t.value=text;t.style.cssText='position:fixed;left:0;top:0;opacity:0;width:1px;height:1px';document.body.append(t);t.select();try{success=document.execCommand('copy')}catch(e){}t.remove()}
 if(success){if(button){const old=button.textContent;button.textContent='Copied';setTimeout(()=>button.textContent=old,1800)}else notify('Link copied')}else{notify('Clipboard is unavailable here. The text has been selected for manual copy.');if(button){const code=button.parentElement.querySelector('code');if(code){const range=document.createRange();range.selectNodeContents(code);const selection=window.getSelection();selection.removeAllRanges();selection.addRange(range)}}}
}
$$('pre').forEach(pre=>{const code=$('code',pre);if(!code)return;pre.dataset.language=(code.className.match(/language-([^\s]+)/)||[])[1]||'Text';const b=document.createElement('button');b.className='code-copy';b.type='button';b.textContent='Copy';b.setAttribute('aria-label','Copy code block');b.addEventListener('click',()=>copy(code.textContent,b));pre.prepend(b)});
$('#copy-link').addEventListener('click',()=>copy(location.href.split('#')[0]+'#'+(location.hash.slice(1)||active.id)));
$('#print-page').addEventListener('click',()=>window.print());
document.addEventListener('click',e=>{const b=e.target.closest('[data-download]');if(!b)return;const record=document.getElementById(b.dataset.download);if(!record)return;const code=$('pre code',record);if(!code)return;const blob=new Blob([code.textContent],{type:'application/json;charset=utf-8'});const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download=b.dataset.filename||'example.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)});
$$('[data-filter]').forEach(input=>{input.addEventListener('input',()=>{const list=document.getElementById(input.dataset.filter),q=input.value.trim().toLowerCase();let shown=0;$$('[data-filter-text]',list).forEach(row=>{const match=!q||row.dataset.filterText.toLowerCase().includes(q);row.classList.toggle('hidden-by-filter',!match);if(match)shown++});const empty=$('.empty-filter',list.parentElement);if(empty)empty.style.display=shown?'none':'block';const count=document.querySelector(`[data-filter-count="${input.dataset.filter}"]`);if(count)count.textContent=shown+(shown===1?' entry':' entries')})});
$$('[data-expand]').forEach(button=>button.addEventListener('click',()=>{const group=document.getElementById(button.dataset.expand),records=$$('details.data-record',group).filter(r=>!r.classList.contains('hidden-by-filter'));const open=records.some(r=>!r.open);records.forEach(r=>r.open=open);button.textContent=open?'Collapse entries':'Expand entries'}));
function tokens(q){return q.toLowerCase().trim().split(/\s+/).filter(Boolean)}
function highlight(text,terms){if(!terms.length)return escape(text);const pattern=new RegExp('('+terms.slice().sort((a,b)=>b.length-a.length).map(t=>t.replace(/[.*+?^${}()|[\]\\]/g,'\\$&')).join('|')+')','ig');let out='',last=0;for(const m of text.matchAll(pattern)){out+=escape(text.slice(last,m.index))+'<mark>'+escape(m[0])+'</mark>';last=m.index+m[0].length}return out+escape(text.slice(last))}
const searchable=index.map(r=>({...r,hay:(r.title+' '+r.group+' '+r.text).toLowerCase(),titleLower:r.title.toLowerCase()}));
function search(){const q=searchInput.value.trim(),terms=tokens(q),scope=$('#search-scope').value;if(!terms.length){results.innerHTML='<div class="search-empty">Search the handbook, source documents and shipped JSON.<br>Try <strong>roadside</strong>, <strong>damage_bonus</strong>, <strong>save</strong>, or an exact content ID.</div>';$('#search-count').textContent='';return}
 const found=[];for(const row of searchable){if(scope==='guide'&&row.kind!=='guide')continue;if(scope==='data'&&row.kind!=='data')continue;if(scope==='source'&&row.kind!=='source')continue;if(!terms.every(t=>row.hay.includes(t)))continue;let score=row.kind==='guide'?30:row.kind==='data'?10:0;for(const t of terms){if(row.titleLower===t)score+=150;else if(row.titleLower.includes(t))score+=55;if(row.id.includes(t))score+=25}if(row.titleLower.includes(q.toLowerCase()))score+=60;found.push({...row,score})}
 found.sort((a,b)=>b.score-a.score||a.title.localeCompare(b.title));$('#search-count').textContent=found.length+(found.length===1?' match':' matches')+(found.length>60?' · showing 60':'');
 if(!found.length){results.innerHTML='<div class="search-empty">No matches in this scope. Try fewer words, an exact file or ID, or choose “All content”.</div>';return}
 results.innerHTML=found.slice(0,60).map(row=>{const lower=row.text.toLowerCase();let first=lower.indexOf(terms[0]);first=Math.max(0,first-70);let snippet=row.text.slice(first,first+235);if(first)snippet='…'+snippet;if(first+235<row.text.length)snippet+='…';const label=row.kind==='source'?'Original source · check status':row.kind==='data'?'Snapshot data':'Current guide';return `<a class="search-result" href="#${escape(row.id)}"><span class="result-kind">${escape(label+' / '+row.group)}</span><span class="result-title">${highlight(row.title,terms)}</span><span class="result-snippet">${highlight(snippet,terms)}</span></a>`}).join('');results.scrollTop=0;
}
function openSearch(){if(!dialog.open)dialog.showModal();searchInput.focus();searchInput.select();search()}
$$('[data-search-open]').forEach(b=>b.addEventListener('click',openSearch));$('#search-close').addEventListener('click',()=>dialog.close());dialog.addEventListener('click',e=>{if(e.target===dialog){const r=dialog.getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)dialog.close()}});
searchInput.addEventListener('input',()=>{clearTimeout(searchTimer);searchTimer=setTimeout(search,100)});$('#search-scope').addEventListener('change',search);
results.addEventListener('click',e=>{const link=e.target.closest('a');if(link){dialog.close();if(link.hash===location.hash)go()}});
searchInput.addEventListener('keydown',e=>{if(e.key==='ArrowDown'){e.preventDefault();$('.search-result',results)?.focus()}if(e.key==='Enter'){const first=$('.search-result',results);if(first){e.preventDefault();first.click()}}});
results.addEventListener('keydown',e=>{const links=$$('.search-result',results),at=links.indexOf(document.activeElement);if(e.key==='ArrowDown'){e.preventDefault();links[Math.min(links.length-1,at+1)]?.focus()}if(e.key==='ArrowUp'){e.preventDefault();if(at<=0)searchInput.focus();else links[at-1]?.focus()}});
document.addEventListener('keydown',e=>{const typing=/INPUT|TEXTAREA|SELECT/.test(e.target.tagName)||e.target.isContentEditable;if(((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='k')||(!typing&&e.key==='/')){e.preventDefault();openSearch()}if(e.key==='Escape'){document.body.classList.remove('nav-open');$('#menu-toggle').setAttribute('aria-expanded','false')}});
document.addEventListener('click',e=>{const a=e.target.closest('a[href^="#"]');if(a&&a.hash===location.hash&&!a.closest('.search-dialog'))go()});
go();
document.documentElement.classList.add('js');
})();
