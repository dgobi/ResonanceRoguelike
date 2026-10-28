import {useMemo,useState} from "react";
import {ContractFields} from "./ContractControls";
import {itemModel,itemValue} from "./item";
import type {ContentProps} from "./ContentEditor";
import {previewProblem} from "./familyData";

export function TypographyEditor(p:ContentProps){
  const [view,setView]=useState("typography-roles"),parsed=useMemo(()=>itemModel(p.draft),[p.draft]);
  if(p.family.id!=="typography")return null;
  const record=p.family.context?.records[0],values=parsed.model || record?.definition || {};
  const reason=p.disabled || (parsed.reason ? "Repair JSON in Source to resume font controls." : "") || (!record?.capability.editable ? record?.capability.reason || "Capability unavailable." : "");
  const frame=p.preview?.kind==="typography-preview" ? p.preview : null,problem=frame ? previewProblem(frame):"";
  return <section className="item-editor typography-editor" data-testid="typography-editor">
    <div className="pane-heading"><div><h2>Game typography</h2><code>{p.path}</code></div>{p.busy && <button disabled={p.disabled==="Publication in progress."} onClick={p.onCancel}>Cancel authoring request</button>}</div>
    <p className="notice">{p.family.descriptor.publication_note}</p>
    <div className="tabs"><button onClick={()=>setView("typography-roles")}>Font roles</button><button onClick={()=>setView("typography-preview")}>Game preview</button><button onClick={p.onSource}>Show source</button></div>
    {reason && <p className="notice warning">{reason}</p>}
    {view==="typography-roles" && <>
      <div className="edit-actions"><button disabled={!!reason || !p.canUndo} onClick={p.onUndo}>Undo typography</button><button disabled={!!reason || !p.canRedo} onClick={p.onRedo}>Redo typography</button></div>
      <fieldset className="item-properties" disabled={!!reason}><legend>Shared proportional fonts</legend><ContractFields family={p.family} values={values} onChange={(path,value)=>p.onEdit(text=>itemValue(text,path,value),"Change game font")}/></fieldset>
      <details><summary>Font references and preserved metadata</summary><p>Regular TTF files directly in this project's assets/Fonts. Missing or unsuitable assignments remain editable; validation explains the affected role and characters.</p><pre className="raw">{JSON.stringify(p.family.context?.fonts,null,2)}</pre><pre className="raw">{JSON.stringify(Object.fromEntries(Object.entries(values).filter(([k])=>!(k in (p.family.descriptor.schema.properties || {})))),null,2)}</pre></details>
    </>}
    {view==="typography-preview" && <>
      <p>Render all thirteen roles and a representative reader with the candidate profile using the game. Other document previews use the saved profile. Preview requires valid fonts and does not grant publication authority.</p>
      <button disabled={p.busy || !!reason} onClick={()=>p.onPreview({})}>Preview game typography</button>
      {problem && <p className="notice warning">{problem}</p>}
      {frame && !problem && <><p data-testid="typography-preview-state" className={p.previewStale ? "notice warning":"notice"}>{p.previewStale ? "Stale preview — render current source and resources." : "Current production typography preview"}</p>
        <img className="reader-frame" alt="Thirteen game font roles at retained nominal sizes" src={frame.specimen.image}/>
        <img className="reader-frame" alt="Production reader using candidate typography" src={frame.reader.image}/>
        <p>{frame.setup}</p><table><thead><tr><th>Role</th><th>Requested face</th><th>Resolved resource</th><th>Size / sample pixels</th></tr></thead><tbody>{frame.roles.map(r=><tr key={r.role}><td>{r.label}</td><td>{r.requested}</td><td>{r.resolved}</td><td>{r.size} / {r.width}×{r.height}</td></tr>)}</tbody></table>
        {frame.diagnostics.map((d,i)=><p className="notice warning" key={i}>{d.field}: {d.message}</p>)}
        <details><summary>Typography evidence</summary><pre className="raw" data-testid="typography-preview-receipt">{JSON.stringify({...frame,specimen:{...frame.specimen,image:undefined},reader:{...frame.reader,image:undefined}},null,2)}</pre></details>
      </>}
    </>}
  </section>;
}
