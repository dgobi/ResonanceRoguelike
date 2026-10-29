import { useState } from "react";
import { ScalarControl } from "./ContractControls";
import type { ContentFamily } from "./content";
import type { RecipeRecord } from "./protocol";
import { recordRow } from "./orderedRecords";
import { recipeValue } from "./recipe";

export function ConjunctionEditor(p: {family:ContentFamily; value:unknown; record?:RecipeRecord; disabled:boolean; current:boolean; busy:boolean; onItem:(id:string,path?:string)=>void; onEdit:(edit:(text:string)=>string,label:string)=>void}) {
  const [tag,setTag]=useState("");
  const object = !!p.value && typeof p.value==="object" && !Array.isArray(p.value) ? p.value as Record<string,unknown> : null;
  const rows = Array.isArray(p.value) ? p.value : object?.tags;
  const valid=Array.isArray(rows)&&rows.every(r=>r&&typeof r==="object"&&!Array.isArray(r));
  const path:(string|number)[] = object ? ["requires_single_item","tags"] : ["requires_single_item"];
  const schema=p.family.descriptor.schema.properties!.components.items!.properties!;
  const matches=p.record?.candidates.find(r=>r.role==="requires_single_item")?.matches || [];
  return <section><h3>All tags on each material</h3><p>Automatic materials only. List form requires one physical item. Object form requires max_quantity items (default one). Each must satisfy every tag; none can also fill a component or retained-tool slot.</p>
    {p.value===undefined ? <div className="edit-actions">{["list","object"].map(shape=><button key={shape} disabled={p.disabled} onClick={()=>p.onEdit(s=>recipeValue(s,["requires_single_item"],shape==="list"?[]:{tags:[]}),"Add conjunction")}>Add {shape} conjunction</button>)}</div> : <>
      {object && <label>Required conjunction quantity<ScalarControl schema={{type:"integer",minimum:1,maximum:p.record?.capability.quantity_max || 32,default:1}} label="Required conjunction quantity" references={p.family.references} value={object.max_quantity} disabled={p.disabled} onChange={v=>p.onEdit(s=>recipeValue(s,["requires_single_item","max_quantity"],v),"Edit conjunction quantity")}/></label>}
      {valid ? rows.map((row,i)=><fieldset key={i} disabled={p.disabled}><legend>Conjunction tag {i+1}</legend>{["tag","min_tier"].map(key=><label key={key}>{schema[key].title}<ScalarControl schema={schema[key]} references={p.family.references} value={row[key]} label={`Conjunction ${key} ${i+1}`} onChange={v=>p.onEdit(s=>recipeValue(s,[...path,i,key],v),"Edit conjunction tag")}/></label>)}
        <div className="edit-actions">{(["up","down","remove"] as const).map(action=><button key={action} disabled={action==="up"&&i===0||action==="down"&&i===rows.length-1} aria-label={`${action} conjunction ${i+1}`} onClick={()=>p.onEdit(s=>recordRow(s,path,action,i),`${action} conjunction tag`)}>{action}</button>)}</div></fieldset>) : <p>Repair the conjunction shape in Source; the draft is retained.</p>}
      <label>New conjunction tag<select disabled={p.disabled||!valid} aria-label="New conjunction tag" value={tag} onChange={e=>setTag(e.target.value)}><option value="">Choose tag</option>{p.family.references.keywords?.map(r=><option key={r.id} value={r.id}>{r.label}</option>)}</select></label><button disabled={p.disabled||!valid||!tag} onClick={()=>p.onEdit(s=>recordRow(s,path,"add",-1,{tag}),"Add conjunction tag")}>Add conjunction tag</button>
      {p.current && <><p>Automatically eligible definitions: {matches.filter(m=>m.automatic_material).length}. {matches.length>0&&!matches.some(m=>m.automatic_material) && "No automatically eligible material is available; protected matches cannot be chosen for a conjunction."}</p>{matches.map(m=><div key={m.path+m.pointer}><button disabled={p.busy} onClick={()=>p.onItem(m.id,m.path)}>{m.id}</button><small>{m.automatic_material?"Automatic material match":"Tag match only · protected from automatic selection"}</small></div>)}<small>Potential matches establish neither availability nor complete allocation.</small></>}
    </>}
  </section>;
}
