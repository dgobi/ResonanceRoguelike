import { useMemo, useState } from "react";
import { ContractFields, OrderedRecords } from "./ContractControls";
import { itemModel, itemValue } from "./item";
import type { ContentProps } from "./ContentEditor";
import { previewProblem } from "./familyData";

export function TextEditor(p:ContentProps) {
  const [view,setView]=useState("text-pages"), [page,setPage]=useState(0), [scroll,setScroll]=useState(0);
  const parsed=useMemo(()=>itemModel(p.draft),[p.draft]);
  if(p.family.id!=="text") return null;
  const context=p.family.context, record=context?.records[0], cap=record?.capability;
  const values=parsed.model || record?.definition || {}, pages=Array.isArray(values.pages) ? values.pages : [];
  const reason=p.disabled || (parsed.reason ? "Repair JSON in Source to resume page controls." : "") || (!cap?.editable ? cap?.reason || "Capability unavailable." : "");
  const frame=p.preview, problem=frame ? previewProblem(frame) : "";
  const selectedPage=Math.min(page,Math.max(0,pages.length-1));
  const stale=p.previewStale || frame?.inputs.page!==selectedPage || frame?.inputs.scroll!==scroll;
  const titles:Record<string,string>={"text-pages":"Pages","text-references":"Binding and metadata","reader-preview":"Reader preview"};
  return <section className="item-editor text-editor" data-testid="text-editor">
    <div className="pane-heading"><div><h2>Found text</h2><code>{String(values.id || record?.id || "Invalid source")} · {p.path}</code></div>{p.busy && <button disabled={p.disabled==="Publication in progress."} onClick={p.onCancel}>Cancel authoring request</button>}</div>
    <p>{cap?.reason}</p><p className="notice">{p.family.descriptor.publication_note}</p>
    <div className="tabs">{p.family.descriptor.views.map(v=><button key={v} className={view===v ? "active" : ""} onClick={()=>setView(v)}>{titles[v]}</button>)}<button onClick={p.onSource}>Show source</button></div>
    {reason && <p className="notice warning">{reason}</p>}
    {view==="text-pages" && <>
      <div className="edit-actions"><button disabled={!!reason || !p.canUndo} onClick={p.onUndo}>Undo text</button><button disabled={!!reason || !p.canRedo} onClick={p.onRedo}>Redo text</button><small>Raw and variant-ID edits clear history.</small></div>
      <fieldset className="item-properties" disabled={!!reason}><legend>Reader properties</legend><ContractFields family={p.family} values={values} onChange={(path,value)=>p.onEdit(text=>itemValue(text,path,value),"Edit text property")}/></fieldset>
      <OrderedRecords family={p.family} values={values} disabled={!!reason} onEdit={p.onEdit}/>
    </>}
    {view==="text-references" && <><p>{context?.inspection_note}</p><p>{context?.binding_note}</p><p className="muted">{context?.reference_coverage}</p>
      {p.evidenceStale || p.dirty && !p.validated ? <p>Saved reference evidence is stale. Validate to refresh.</p> : record?.references.map((r,i)=><p key={i}>{r.kind} · <code>{r.path}{r.pointer}</code></p>)}
      <h3>Preserved root metadata</h3><pre className="raw">{JSON.stringify(Object.fromEntries(Object.entries(values).filter(([key])=>!Object.keys(p.family.descriptor.schema.properties || {}).includes(key))),null,2)}</pre>
    </>}
    {view==="reader-preview" && <>
      <p>Render the exact draft with the production reader and saved resources. Ordinary letter style; fresh empty language knowledge. Preview does not grant publication authority.</p>
      <div className="edit-actions"><label>Preview page<select aria-label="Preview page" disabled={p.busy} value={selectedPage} onChange={e=>{setPage(Number(e.target.value));setScroll(0);}}>{pages.map((_,i)=><option key={i} value={i}>Page {i+1}</option>)}</select></label>
        <button disabled={p.busy || !cap?.editable || !!parsed.reason || !pages.length} onClick={()=>p.onPreview({page:selectedPage,scroll})}>Preview exact text</button>
        <button disabled={p.busy || !frame || frame.page!==selectedPage} onClick={()=>setScroll(0)}>Top</button>
        <button disabled={p.busy || !frame || frame.page!==selectedPage} onClick={()=>setScroll(Math.max(0,scroll-(frame?.viewport_height || 1)))}>Scroll up</button>
        <button disabled={p.busy || !frame || frame.page!==selectedPage} onClick={()=>setScroll(Math.min(frame?.max_scroll || 0,scroll+(frame?.viewport_height || 1)))}>Scroll down</button>
        <button disabled={p.busy || !frame || frame.page!==selectedPage} onClick={()=>setScroll(frame?.max_scroll || 0)}>End</button>
      </div><p>Selected offset: {scroll} px. Render after selecting a page or scroll position.</p>
      {problem && <p className="notice warning">{problem}</p>}
      {frame && !problem && <><p data-testid="reader-preview-state" className={stale ? "notice warning" : "notice"}>{stale ? "Stale preview — render the current source, dependencies and selection." : "Current production reader preview"}</p>
        <img className="reader-frame" alt={`Production reader page ${frame.page+1}, scroll ${frame.scroll}`} src={frame.image}/>
        <p>{frame.setup}</p><p>Page {frame.page+1} · scroll {frame.scroll}/{frame.max_scroll} px · {frame.total_rows} visual rows</p>
        <details><summary>Reader evidence</summary><pre className="raw" data-testid="reader-preview-receipt">{JSON.stringify({...frame,image:undefined},null,2)}</pre></details>
      </>}
    </>}
  </section>;
}
