import {useState} from 'react';
import {legendMapping,resizeBuilding,entranceCells,matchingGoals,companionGoals,type Placement,type Entrance,type Goal} from './building';
import {valueEdit,appendValue,removeValue,deleteRecord,type Layout,type Catalog,type Special,type Cell} from './layout';
type Edit=(operation:(source:string)=>string,label:string)=>void;
export function BuildingGeometry({model:m,draft,catalog,disabled,onEdit}:{model:Layout;draft:string;catalog:Catalog;disabled:boolean;onEdit:Edit}){
 const [w,W]=useState(String(m.width)),[h,H]=useState(String(m.height)),[fill,F]=useState(Object.keys(m.legend)[0]);
 const [glyph,G]=useState(''),[terrain,T]=useState('__null__');
 const used=m.layers.reduce((n,r)=>n+Array.from(r).filter(g=>g===glyph).length,0);
 const raw=JSON.parse(draft.replace(/^\uFEFF/,''));
 return <details open className="room-geometry"><summary>Surface footprint, legend and active decor</summary>
 <fieldset disabled={disabled}><legend>Legend mapping</legend>
 <label>One character<input aria-label="Legend glyph" value={glyph} onChange={e=>G(e.target.value)}/></label>
 <label>Saved terrain<select aria-label="Legend terrain" value={terrain} onChange={e=>T(e.target.value)}><option value="__null__">null · preserve underlying scene terrain</option>{Object.keys(catalog.terrain).map(id=><option key={id}>{id}</option>)}</select></label>
 <p data-testid="mapping-impact">Setting this mapping affects all {used} source cells using {JSON.stringify(glyph)}. Null preserves the scene terrain underneath this surface building.</p>
 <button disabled={Array.from(glyph).length!==1} onClick={()=>onEdit(s=>legendMapping(s,glyph,terrain==='__null__'?null:terrain),'Set surface legend mapping')}>Set legend mapping</button>
 <button disabled={!(glyph in m.legend)} onClick={()=>onEdit(s=>legendMapping(s,glyph,null,true),'Remove unused legend mapping')}>Remove unused mapping</button>
 </fieldset>
 <fieldset disabled={disabled}><legend>Deliberate top-left resize · current {m.width} × {m.height}</legend>
 <label>Width<input aria-label="Building width" type="number" value={w} onChange={e=>W(e.target.value)}/></label><label>Height<input aria-label="Building height" type="number" value={h} onChange={e=>H(e.target.value)}/></label>
 <label>Extend using<select aria-label="Resize fill glyph" value={fill} onChange={e=>F(e.target.value)}>{Object.keys(m.legend).map(g=><option key={g} value={g}>{JSON.stringify(g)} → {m.legend[g]??'underlying terrain'}</option>)}</select></label>
 <p>Extend right/bottom or explicitly crop terrain. Retained records and coordinates stay fixed; active decor grows with null cells. Non-null decor, entrance spans, goals and supported coordinates cannot be cropped. South/east entrances can become invalid after growth: move and repaint them deliberately. Position-derived loot can change.</p>
 <button onClick={()=>onEdit(s=>resizeBuilding(s,Number(w),Number(h),fill),'Resize surface footprint')}>Apply resize (top-left anchor)</button>
 </fieldset>
 {m.decor_limitation&&<p role="note">{m.decor_limitation}</p>}
 <details><summary>Route-specific retained metadata</summary><p>decor_layer uses full saved IDs/null and is active. Omission stays absent until painting. legend_weights, player_start, facing and rotatable are inactive on ordinary surface construction. district_weights is consumed by the older district-selection route; it does not edit current shared-plan membership. Source may deliberately revise retained metadata.</p><pre className="raw">{JSON.stringify(Object.fromEntries(['legend_weights','player_start','facing','rotatable','district_weights'].map(k=>[k,k in raw?raw[k]:'(absent)'])),null,2)}</pre></details>
 </details>;
}

export function PlacementControls({draft,disabled,onEdit,onSelect,selected}:{draft:string;disabled:boolean;onEdit:Edit;onSelect:(cell:Cell,kind:string,index:number)=>void;selected?:string}){
 const raw=JSON.parse(draft.replace(/^\uFEFF/,'')),p=raw.placement as Placement|undefined;
 const edit=(key:string,v:unknown)=>onEdit(s=>valueEdit(s,['placement',key],v),'Edit placement '+key);
 if(p===undefined)return <fieldset disabled={disabled}><legend>Explicit placement profile</legend><p>No profile: legacy direct preview remains available; access/transforms are unverified. Door-looking terrain creates no declaration.</p><button onClick={()=>onEdit(s=>valueEdit(s,['placement'],{version:1,contexts:['grid','roadside'],weight:1,rotations:[0],mirror_x:false,buffer:1,approach:2,road_relation:'frontage',entrances:[],targets:[]}),'Create proposed placement profile')}>Create placement profile</button><small>These are authored scaffold proposals, not runtime defaults. Entrances and goals need deliberate completion.</small></fieldset>;
 const keys=['version','contexts','weight','rotations','mirror_x','buffer','approach','road_relation','entrances','targets'];
 if(!p||typeof p!=='object'||Array.isArray(p)||p.version!==1||Object.keys(p).some(k=>!keys.includes(k)))return <p className="notice warning">Unsupported placement version/fields retained exactly. Production rejects this profile; inspect Source to repair it deliberately.</p>;
 const number=(key:'weight'|'buffer'|'approach')=><label key={key}>{key}<input aria-label={'Placement '+key} type="number" value={p[key]??''} onChange={e=>edit(key,e.target.value===''?null:Number(e.target.value))}/><small>{key in p?'Authored':'Required, absent'}</small></label>;
 return <details open className="placement-controls"><summary>Placement version 1 · explicit authored values</summary><fieldset disabled={disabled}>
 <p>Contexts express eligibility. Selection membership lives in separate saved settlement/POI/compound policies. Most fields are required; controls never silently insert defaults. Lot fit and road connectivity require a real planned placement.</p>
 <div>Contexts {['grid','roadside','landmark','civic','compound'].map(c=><label key={c}><input aria-label={'Context '+c} type="checkbox" checked={Array.isArray(p.contexts)&&p.contexts.includes(c)} onChange={e=>edit('contexts',e.target.checked?[...(Array.isArray(p.contexts)?p.contexts:[]),c]:(p.contexts??[]).filter(v=>v!==c))}/>{c}</label>)}</div>
 {number('weight')}{number('buffer')}{number('approach')}
 <div>Permitted quarter turns {[0,90,180,270].map(r=><label key={r}><input aria-label={'Rotation '+r} type="checkbox" checked={Array.isArray(p.rotations)&&p.rotations.includes(r)} onChange={e=>edit('rotations',e.target.checked?[...(Array.isArray(p.rotations)?p.rotations:[]),r]:(p.rotations??[]).filter(v=>v!==r))}/>{r}°</label>)}</div>
 <label><input aria-label="Permit mirror X" type="checkbox" checked={p.mirror_x===true} onChange={e=>edit('mirror_x',e.target.checked)}/>Permit mirror X before rotation {p.mirror_x===undefined?'· required field absent':''}</label>
 <label>Road relation<select aria-label="Road relation" value={p.road_relation??''} onChange={e=>edit('road_relation',e.target.value)}><option value="">Required, absent</option>{['frontage','spur','remote'].map(v=><option key={v}>{v}</option>)}</select></label>
 <p>Remote profiles can have only optional entrances: construction/transforms still validate; access remains unverified without a required diagnostic entry.</p>
 {(Array.isArray(p.entrances)?p.entrances:[]).map((e,i)=>e&&typeof e==='object'?<EntranceFields key={i} row={e} index={i} selected={selected===`entrances:${i}`} onEdit={onEdit} onSelect={()=>onSelect([e.x,e.y],'entrances',i)}/>:<p key={i}>Malformed entrance {i} retained; repair Source.</p>)}
 <button onClick={()=>onEdit(s=>appendValue(s,['placement','entrances'],{id:'entrance_'+(p.entrances?.length??0),x:0,y:0,normal:'N',width:1,role:'main',required:true}),'Add entrance')}>Add entrance</button>
 {(Array.isArray(p.targets)?p.targets:[]).map((t,i)=>t&&typeof t==='object'?<GoalFields key={i} row={t} index={i} selected={selected===`targets:${i}`} onEdit={onEdit} onSelect={()=>onSelect([t.x,t.y],'targets',i)}/>:<p key={i}>Malformed target {i} retained; repair Source.</p>)}
 <button onClick={()=>onEdit(s=>appendValue(s,['placement','targets'],{x:1,y:1,kind:'floor',required:true}),'Add access target')}>Add access target</button>
 </fieldset></details>;
}
function EntranceFields({row:e,index:i,onEdit,onSelect,selected}:{row:Entrance;index:number;onEdit:Edit;onSelect:()=>void;selected:boolean}){
 const set=(key:string,value:unknown)=>onEdit(s=>valueEdit(s,['placement','entrances',i,key],value),'Edit entrance');
 return <fieldset data-overlay-selected={selected}><legend>Entrance {i} · {e.id}</legend><button onClick={onSelect}>Select entrance {i}</button>
 <label>ID<input aria-label={`Entrance ${i} id`} value={e.id??''} onChange={v=>set('id',v.target.value)}/></label>
 {(['x','y','width'] as const).map(k=><label key={k}>{k}<input type="number" aria-label={`Entrance ${i} ${k}`} value={e[k]??''} onChange={v=>set(k,v.target.value===''?null:Number(v.target.value))}/></label>)}
 <label>Normal<select aria-label={`Entrance ${i} normal`} value={e.normal??''} onChange={v=>set('normal',v.target.value)}><option value="">Required</option>{['N','E','S','W'].map(n=><option key={n}>{n}</option>)}</select></label>
 <label>Role<select aria-label={`Entrance ${i} role`} value={e.role??''} onChange={v=>set('role',v.target.value)}><option value="">Required</option><option>main</option><option>service</option></select></label>
 <label><input type="checkbox" aria-label={`Entrance ${i} required`} checked={e.required===true} onChange={v=>set('required',v.target.checked)}/>Required {e.required===undefined?'· absent':''}</label>
 <p>Every span cell: {entranceCells(e).map(c=>`(${c.join(',')})`).join(' ')}. N/S advances positive X; E/W positive Y. Terrain doors are edited separately.</p>
 <button onClick={()=>onEdit(s=>removeValue(s,['placement','entrances',i]),'Remove entrance')}>Remove entrance {i}</button></fieldset>;
}
function GoalFields({row:t,index:i,onEdit,onSelect,selected}:{row:Goal;index:number;onEdit:Edit;onSelect:()=>void;selected:boolean}){
 const set=(key:string,value:unknown)=>onEdit(s=>valueEdit(s,['placement','targets',i,key],value),'Edit access target');
 return <fieldset data-overlay-selected={selected}><legend>Access target {i}</legend><button onClick={onSelect}>Select access target {i}</button>
 {(['x','y'] as const).map(k=><label key={k}>{k}<input aria-label={`Target ${i} ${k}`} type="number" value={t[k]??''} onChange={v=>set(k,v.target.value===''?null:Number(v.target.value))}/></label>)}
 <label>Kind<select aria-label={`Target ${i} kind`} value={t.kind??''} onChange={v=>set('kind',v.target.value)}><option value="">Required</option>{['floor','item','readable','container','stairs_up','stairs_down'].map(k=><option key={k}>{k}</option>)}</select></label>
 <label><input aria-label={`Target ${i} required`} type="checkbox" checked={t.required===true} onChange={v=>set('required',v.target.checked)}/>Required {t.required===undefined?'· absent':''}</label>
 <button onClick={()=>onEdit(s=>removeValue(s,['placement','targets',i]),'Remove access target')}>Remove access target {i}</button></fieldset>;
}
export function DeleteSurfaceRecord({draft,record,index,disabled,onEdit,onDeleted}:{draft:string;record:Special;index:number;disabled:boolean;onEdit:Edit;onDeleted:()=>void}){
 const [remove,R]=useState(false),matches=matchingGoals(draft,record);
 return <fieldset disabled={disabled}><legend>Delete direct record</legend><p>Matching retained goals: {matches.length?matches.map(i=>`placement.targets[${i}]`).join(', '):'none'}. Other goals are retained.</p><label><input aria-label="Remove matching goals" type="checkbox" checked={remove} onChange={e=>R(e.target.checked)}/>Explicitly remove these matching goals with the record</label><button onClick={()=>{onEdit(s=>deleteRecord(remove?companionGoals(s,record,null):s,index),'Delete direct record and chosen goals');onDeleted();}}>Delete surface record</button></fieldset>;
}
