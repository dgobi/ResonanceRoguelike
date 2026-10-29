import { useId, useState } from "react";
import { effectiveValue, recordDefaults, type FieldSchema, type ContentFamily, type References } from "./content";
import { recordRow } from "./orderedRecords";
import { itemValue, keyedNumber } from "./item";

export function ScalarControl(p: {schema: FieldSchema; value: unknown; references: References; label?: string; disabled?: boolean; nullable?: boolean; onChange: (value: string | number | boolean) => void}) {
  const s = p.schema, value = effectiveValue(s, p.value), label = p.label || s.title || "Value";
  const suggestionsId=useId();
  const common = {"aria-label":label, disabled:p.disabled || s.readOnly};
  const invalid = p.value !== undefined && !(p.nullable && p.value===null) && (s.type === "boolean" ? typeof p.value !== "boolean" : s.type === "string" ? typeof p.value !== "string" : typeof p.value !== "number" || !Number.isFinite(p.value));
  if (s.type === "boolean") return <><input {...common} type="checkbox" checked={value === true} aria-invalid={invalid} onChange={e=>p.onChange(e.target.checked)} />{invalid && <small>Invalid explicit value: {JSON.stringify(p.value)}. Repair or deliberately replace it.</small>}</>;
  if (s["x-reference"]) return <select {...common} value={typeof value === "string" ? value : ""} aria-invalid={invalid} onChange={e=>p.onChange(e.target.value)}>
    <option value={typeof value === "string" ? value : ""}>{typeof value === "string" ? value : p.value === undefined ? "Absent" : `Invalid: ${JSON.stringify(p.value)}`}</option>
    {(p.references[s["x-reference"]] || []).filter(r=>r.id!==value).map(r=><option key={r.id} value={r.id}>{r.label}</option>)}
  </select>;
  if (s.type === "string") return s["x-control"] === "multiline"
    ? <textarea {...common} value={typeof value === "string" ? value : ""} aria-invalid={invalid} onChange={e=>p.onChange(e.target.value)} />
    : <><input {...common} list={s["x-suggestions"] ? suggestionsId : undefined} value={typeof value === "string" ? value : ""} aria-invalid={invalid} onChange={e=>p.onChange(e.target.value)} />{s["x-suggestions"] && <datalist id={suggestionsId}>{s["x-suggestions"].map(v=><option key={v} value={v}/>)}</datalist>}</>;
  return <input {...common} type="number" min={s.minimum} max={s.maximum} step={s.type === "integer" ? 1 : "any"} value={typeof value === "number" ? value : ""} aria-invalid={invalid}
    onChange={e=>{if(e.target.value !== "" && Number.isFinite(Number(e.target.value))) p.onChange(Number(e.target.value));}} />;
}

export function OrderedRecords(p:{family:ContentFamily;values:Record<string,unknown>;disabled:boolean;allowEmpty?:boolean;view?:string;onEdit:(edit:(text:string)=>string,label:string)=>void}) {
  return <>{Object.entries(p.family.descriptor.schema.properties || {}).filter(([,s])=>s["x-control"]==="ordered-records" && s["x-view"]===p.view).map(([field,schema])=>{
    const rows=p.values[field];
    const valid=Array.isArray(rows) && rows.every(r=>r && typeof r==="object" && !Array.isArray(r));
    return <section key={field} className="ordered-records"><h3>{schema.title || field}</h3>
      {!valid ? <p className="notice warning">Repair {field} in Source; expected an ordered list of records.</p> : rows.map((row,i)=><fieldset key={i} disabled={p.disabled}><legend>{schema.title || field} {i+1}</legend>
        {Object.entries(schema.items?.properties || {}).map(([key,s])=><label key={key}>{s.title || key}<ScalarControl schema={s} value={row[key]} references={p.family.references} label={`${s.title || key} ${i+1}`} onChange={value=>p.onEdit(text=>itemValue(text,[field,i,key],value),`Edit ${field} ${i+1}`)}/>
          {row[key]===undefined && <small>Absent in source{s.default!==undefined ? ` · effective default: ${s.default}` : ""}</small>}{s.description && <small>{s.description}</small>}
        </label>)}
        <div className="edit-actions">{(["up","down","remove"] as const).map(action=><button key={action} aria-label={`${action} ${field} ${i+1}`} disabled={action==="up" && i===0 || action==="down" && i===rows.length-1 || action==="remove" && rows.length===1 && !p.allowEmpty} onClick={()=>p.onEdit(text=>recordRow(text,field,action,i),`${action} ${field}`)}>{action==="up" ? "Move up" : action==="down" ? "Move down" : "Remove"}</button>)}</div>
        {Object.keys(row).some(k=>!(k in (schema.items?.properties || {}))) && <details><summary>Preserved record metadata</summary><pre className="raw">{JSON.stringify(Object.fromEntries(Object.entries(row).filter(([k])=>!(k in (schema.items?.properties || {})))),null,2)}</pre></details>}
      </fieldset>)}
      <button disabled={p.disabled || !valid} onClick={()=>p.onEdit(text=>recordRow(text,field,"add",-1,recordDefaults(schema)),`Add ${field}`)}>Add {field} record</button>
    </section>;
  })}</>;
}

export function KeyedNumberMap(p:{family:ContentFamily;field:string;schema:FieldSchema;value:unknown;disabled:boolean;onEdit:(edit:(text:string)=>string,label:string)=>void}) {
  const [key,setKey]=useState("");
  const valid=p.value===undefined || !!p.value && typeof p.value==="object" && !Array.isArray(p.value);
  const rows=valid ? Object.entries((p.value || {}) as Record<string,unknown>) : [];
  const options=p.family.references[p.schema["x-reference"] || ""] || [];
  const numberSchema=typeof p.schema.additionalProperties==="object" ? p.schema.additionalProperties : {type:"number" as const};
  return <fieldset disabled={p.disabled}><legend>{p.schema.title}</legend><p>{p.schema.description}</p>
    {p.value===undefined && <small>Absent in source · effective empty map; no reduction.</small>}
    {!valid ? <p className="notice warning">Repair {p.field} in Source; expected a keyed JSON object.</p> : rows.map(([k,v])=><label key={k}>{k==="all" ? "all · fallback" : `${k} · category override`}
      <ScalarControl schema={numberSchema} value={v} references={{}} label={`Reduction ${k}`} onChange={value=>p.onEdit(text=>keyedNumber(text,p.field,k,Number(value)),`Change ${k} reduction`)}/>
      <button aria-label={`Remove reduction ${k}`} onClick={()=>p.onEdit(text=>keyedNumber(text,p.field,k),`Remove ${k} reduction`)}>Remove</button>
    </label>)}
    <label>New reduction category<select aria-label="New reduction category" value={key} onChange={e=>setKey(e.target.value)}><option value="">Choose category or fallback</option>{options.filter(o=>!rows.some(([k])=>k===o.id)).map(o=><option key={o.id} value={o.id}>{o.label}</option>)}</select></label>
    <button disabled={!valid || !key || rows.some(([k])=>k===key)} onClick={()=>{p.onEdit(text=>keyedNumber(text,p.field,key,0),`Add ${key} reduction`);setKey("");}}>Add reduction</button>
  </fieldset>;
}

export function ContractFields(p: {family: ContentFamily; values: Record<string,unknown>; view?: string; nullableFields?: string[]; disabledFields?:string[]; onChange: (path: (string|number)[], value: unknown)=>void}) {
  return <>{Object.entries(p.family.descriptor.schema.properties || {}).filter(([,s])=>!s.readOnly && !["array","object"].includes(s.type) && s["x-view"]===p.view).map(([key,s])=><label key={key}>
    {s.title || key}<ScalarControl schema={s} value={p.values[key]} disabled={p.disabledFields?.includes(key)} nullable={p.nullableFields?.includes(key)} references={p.family.references} onChange={value=>p.onChange([key],value)} />
    {p.values[key] === undefined && <small>{s.default === undefined ? "Absent in source" : `Absent in source · effective default: ${String(s.default)}`}</small>}
    {s.description && <small>{s.description}</small>}
    {p.values[key] === null && <small>Explicit null retained; validate for consumer behavior.</small>}
  </label>)}</>;
}
