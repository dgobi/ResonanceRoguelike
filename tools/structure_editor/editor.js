'use strict';
const {strictParse,DocumentModel,dimensions,gridKey}=StructureEditor;
const model=new DocumentModel(), catalog=window.STRUCTURE_CATALOG;
const $=id=>document.getElementById(id), cellSize=20;
let activeSpecial=0, resizing=null;
const option=(value,label=value)=>{const o=document.createElement('option');o.value=value;o.textContent=label;return o;};
function message(text,error=false) {$('message').textContent=text;$('message').className=error?'error':'';}
function act(action) {try {const result=action();render();message(result||'Draft updated. Export and run Python validation.');} catch(error){message(error.message,true);}}
function profile(doc) {
  if (Object.hasOwn(doc,'entrance_type')) return 'interior_entrance';
  if (Object.hasOwn(doc,'player_start') || doc.type==='submap') return 'authored_submap';
  if (doc.category==='plaza') return 'plaza';
  return $('route').value;
}
function importText(text) {
  const doc=strictParse(text), route=profile(doc);
  model.importText(text,route,route==='ordinary_building'?(doc.category||$('category').value):'');
  activeSpecial=0;return 'Imported intact. No runtime validation has been performed.';
}
function metadata() {
  const field=$('metadata-field').value, exists=model.doc && Object.hasOwn(model.doc,field);
  $('metadata').value=exists?JSON.stringify(model.doc[field],null,2):'';
  const inactive=catalog?.routes[model.route]?.inactive.includes(field);
  if(field==='placement'){ $('metadata-status').textContent=(exists?'Present':'Absent')+' · G3 placement profile; active only for explicit planned eligibility. Legacy fields remain inactive.'; return; }
  $('metadata-status').textContent=(exists?'Present':'Absent (no default will be exported)')+(inactive?' · retained but inactive on this route.':' · see route capability and Python check.');
}
function special() {
  const records=Array.isArray(model.doc?.special_tiles)?model.doc.special_tiles:[];
  $('special-index').replaceChildren(...records.map((s,n)=>option(String(n),`${n}: ${s?.type||s?.kind||'?'} (${s?.x},${s?.y})`)));
  if(activeSpecial>=records.length) $('special-index').append(option(String(records.length),'New record'));
  $('special-index').value=String(activeSpecial);
  $('special').value=records[activeSpecial]?JSON.stringify(records[activeSpecial],null,2):'{"type":"item","x":1,"y":1,"item_id":"flint_shard"}';
}
function references() {$('reference-id').replaceChildren(...(catalog?.ids[$('reference-kind').value]||[]).map(id=>option(id)));}
function render() {
  $('route').value=model.route; $('category').value=model.category||'residential';
  $('category').disabled=model.route!=='ordinary_building';
  const cap=catalog?.routes[model.route];
  $('capability').textContent=cap?`${cap.selection} Active: ${cap.active.join(', ')}. Transforms: ${cap.transforms.join(', ')}.`:'Catalog missing: run Python refresh command.';
  const doc=model.doc, {width,height}=dimensions(doc);
  $('asset-id').value=doc?.id??''; $('width').value=width; $('height').value=height;
  $('document-status').textContent=doc?`${doc.id??'(missing ID)'} · ${width}×${height} · draft, runtime unchecked`:'No document loaded';
  $('coordinate').textContent='Coordinate — move over the current grid';
  $('undo').disabled=!model.past.length; $('redo').disabled=!model.future.length; $('export').disabled=!doc;
  $('legend').value=doc?JSON.stringify(doc.legend??{},null,2):'';
  const brush=$('terrain-brush').value;
  $('terrain-brush').replaceChildren(...Object.entries(doc?.legend||{}).map(([ch,id])=>option(ch,`${ch===' '?'space':ch} → ${id??'untouched base'}`)));
  if(Object.hasOwn(doc?.legend||{},brush)) $('terrain-brush').value=brush;
  special(); metadata(); draw();
  const hints=[];
  if(doc) {
    if(!model.editable()) hints.push('Grid editing unavailable (malformed grid or exceeds 256×256). Document remains intact for export.');
    if(width>80||height>43) hints.push('Exceeds the current runtime map (80×43); Python will reject installation.');
    const rows=doc[gridKey(doc)];
    if(Array.isArray(rows)&&rows.some(r=>typeof r==='string'&&[...r].length!==width)) hints.push('Ragged legacy grid preserved. Explicit resize with null padding can normalize it.');
    for(const field of cap?.inactive||[]) if(Object.hasOwn(doc,field)) hints.push(`${field}: retained but inactive on ${model.route}.`);
    if(doc.special_tiles?.some?.(s=>['body','stele'].includes(s.type||s.kind))) hints.push('Body/stele physical behavior is deferred. Submap stele text metadata is retained.');
  }
  $('hints').textContent=hints.join('\n');
  const id=String(doc?.id||'draft').replace(/[^a-zA-Z0-9_-]/g,'_');
  $('command').textContent=`$ResonancePython = 'G:\\GameDev\\RoguelikeBaseline-20261020\\project\\.venv\\Scripts\\python.exe'\n& $ResonancePython -X utf8 tools/structure_authoring.py "authoring/${id}.json" --route ${model.route}${model.route==='ordinary_building'?` --category ${model.category||'residential'}`:''} --output "evidence/authoring/${id}.json"\n# Add --access authoring/access.json for intended targets; --register proves ordinary pool selection.\n& $ResonancePython -X utf8 tools/structure_authoring.py --check-editor-catalog`;
}
function draw() {
  const canvas=$('grid'),doc=model.doc,{width,height}=dimensions(doc);
  canvas.width=Math.min(width||36,256)*cellSize;canvas.height=Math.min(height||18,256)*cellSize;
  const ctx=canvas.getContext('2d');ctx.fillStyle='#12130f';ctx.fillRect(0,0,canvas.width,canvas.height);
  if(!doc||!model.editable()) return;
  ctx.font='14px monospace';ctx.textAlign='center';
  const rows=doc[gridKey(doc)];
  for(let y=0;y<height;y++) for(let x=0;x<width;x++) {
    const char=[...rows[y]][x],terrain=doc.legend?.[char];
    ctx.fillStyle=terrain===null?'#151813':/wall|rock/.test(terrain||'')?'#42413b':/water/.test(terrain||'')?'#243e51':'#29382b';
    ctx.fillRect(x*cellSize,y*cellSize,cellSize-1,cellSize-1);ctx.fillStyle='#dfd9c9';ctx.fillText(char??'×',x*cellSize+10,y*cellSize+15);
    const decor=Array.isArray(doc.decor_layer?.[y])?doc.decor_layer[y][x]:null;
    if($('show-decor').checked&&decor){ctx.fillStyle='#d5a3dc';ctx.fillRect(x*cellSize+13,y*cellSize+2,5,5);}
  }
  if($('show-specials').checked) for(const s of Array.isArray(doc.special_tiles)?doc.special_tiles:[]) {
    if(Number.isInteger(s?.x)&&Number.isInteger(s?.y)){ctx.strokeStyle='#edc76d';ctx.lineWidth=2;ctx.strokeRect(s.x*cellSize+2,s.y*cellSize+2,16,16);}
  }
}
$('route').replaceChildren(...Object.keys(catalog?.routes||{}).map(r=>option(r)));
$('category').replaceChildren(...Object.keys(catalog?.eligibility||{}).filter(c=>c!=='plaza').map(c=>option(c)));
$('decor-brush').replaceChildren(option('','Erase (null)'),...(catalog?.ids.decoratives||[]).map(id=>option(id)));
$('catalog-status').textContent=catalog?`Browser hints ${catalog.version}, data ${catalog.identity.slice(0,12)}. Freshness must be checked with --check-editor-catalog; this is never runtime approval.`:'Catalog unavailable. Preserve/export is still available.';
$('file').addEventListener('change',async event=>{
  const file=event.target.files[0];if(!file)return;
  try {const text=await file.text();act(()=>importText(text));} catch(error){message(error.message,true);} finally {event.target.value='';}
});
$('import-paste').onclick=()=>act(()=>importText($('paste').value));
$('route').onchange=()=>{model.past.push(model.state());model.future=[];model.route=$('route').value;render();};
$('category').onchange=()=>{model.past.push(model.state());model.future=[];model.category=$('category').value;render();};
$('new').onclick=()=>act(()=>{
  const route=model.route,doc={id:'new_structure',width:9,height:7,legend:{'#':'wall','.':route==='plaza'?'cobblestone':'floor','+':'door_closed',' ':null},layers:['#########','#.......#','#.......#','#.......#','#.......#','#.......#','####+####']};
  if(route==='ordinary_building')doc.category=model.category||'residential';
  if(route==='plaza')doc.category='plaza';
  if(route==='interior_entrance'){doc.entrance_type='sunken_ruin';doc.legend['>']='stairs_down';doc.layers[3]='#...>...#';}
  if(route==='authored_submap'){doc.player_start={x:4,y:3};doc.legend['<']='stairs_up';doc.layers[3]='#...<...#';}
  model.importText(JSON.stringify(doc),route,model.category);return 'New draft created with explicit defaults.';
});
$('apply-id').onclick=()=>act(()=>model.setField('id',$('asset-id').value));
$('apply-legend').onclick=()=>act(()=>model.setLegend(strictParse($('legend').value)));
$('special-index').onchange=()=>{activeSpecial=Number($('special-index').value);special();};
$('add-special').onclick=()=>{activeSpecial=Array.isArray(model.doc?.special_tiles)?model.doc.special_tiles.length:0;special();};
$('apply-special').onclick=()=>act(()=>model.setSpecial(activeSpecial,strictParse($('special').value)));
$('remove-special').onclick=()=>act(()=>{model.setSpecial(activeSpecial,null,true);activeSpecial=Math.max(0,activeSpecial-1);});
$('metadata-field').onchange=metadata;
$('apply-metadata').onclick=()=>act(()=>model.setField($('metadata-field').value,strictParse($('metadata').value)));
$('remove-metadata').onclick=()=>act(()=>model.setField($('metadata-field').value,null,true));
$('reference-kind').onchange=references;
$('insert-reference').onclick=()=>{try{const row=strictParse($('special').value),kind=$('reference-kind').value,id=$('reference-id').value;
  const fields={items:'item_id',texts:'text_id',scenes:'scene_id',decoratives:'decor_id',terrain:'tile'};
  if(kind==='loot_pools')row.loot_pools=[id];else row[fields[kind]]=id;
  $('special').value=JSON.stringify(row,null,2);message('Reference inserted into the record panel. Apply record to save the edit.');}catch(error){message(error.message,true);}};
$('resize').onclick=()=>{try{if(!model.doc)throw new Error('Import first.');resizing=model.resizeImpact(Number($('width').value),Number($('height').value));
  $('resize-impact').textContent=JSON.stringify(resizing,null,2)+'\nEnlargement uses null padding. Crops are refused. Existing content coordinates stay unchanged.';$('resize-review').hidden=false;
}catch(error){message(error.message,true);}};
$('resize-confirm').onclick=()=>act(()=>{if(!resizing)return;model.resize(resizing.width,resizing.height);$('resize-review').hidden=true;resizing=null;return 'Enlarged with null padding. Unknown coordinate metadata is unchanged; review it.';});
$('resize-cancel').onclick=()=>{$('resize-review').hidden=true;resizing=null;render();message('Resize cancelled; full document unchanged.');};
$('undo').onclick=()=>act(()=>model.undo());$('redo').onclick=()=>act(()=>model.redo());
$('show-decor').onchange=draw;$('show-specials').onchange=draw;
function coordinate(event){const r=$('grid').getBoundingClientRect();return [Math.floor((event.clientX-r.left)/cellSize),Math.floor((event.clientY-r.top)/cellSize)];}
$('grid').onmousemove=event=>{const [x,y]=coordinate(event),doc=model.doc,char=doc?.[gridKey(doc)]?.[y]?.[x];$('coordinate').textContent=`(${x},${y}) terrain: ${doc?.legend?.[char]??'untouched'} · decor: ${doc?.decor_layer?.[y]?.[x]??'none'}`;};
$('grid').onclick=event=>act(()=>{const [x,y]=coordinate(event),layer=$('layer').value;model.paint(x,y,layer,layer==='terrain'?$('terrain-brush').value:$('decor-brush').value||null);});
$('export').onclick=()=>{try{const text=model.exportText();$('export-text').value=text;const blob=new Blob([text],{type:'application/json'}),url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=String(model.doc.id||'draft').replace(/[^a-zA-Z0-9_-]/g,'_')+'.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);message('Draft exported intact. Runtime validation has not been performed on these bytes.');}catch(error){message(error.message,true);}};
references();render();
