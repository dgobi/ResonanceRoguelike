import {useState} from "react";
import {ContractFields, OrderedRecords} from "./ContractControls";
import type {ContentProps} from "./ContentEditor";
import {itemModel,itemValue} from "./item";
import {recordRow} from "./orderedRecords";

export function AssignmentEditor(p:ContentProps){
  const [seed,setSeed]=useState("20261028");
  if(p.family.id!=="assignment")return null;
  const parsed=itemModel(p.draft),values=parsed.model||{},rows=Array.isArray(values.candidates)?values.candidates:[];
  const rooms=p.family.context?.rooms||[],focused=rooms.find(r=>r.id===p.navigation.relatedRoom);
  const saved=p.sourceFamily.id==="assignment"?p.sourceFamily.context?.records[0]?.definition:{};
  const has=(records:unknown,id:string)=>Array.isArray(records)&&records.some(r=>r?.layout_id===id);
  const reason=p.disabled||(parsed.reason?"Repair JSON in Source to resume controls.":"");
  const frame=p.preview?.kind==="assignment-preview"?p.preview:null;
  return <section className="item-editor" data-testid="assignment-editor">
    <div className="pane-heading"><div><h2>World assignment</h2><code>{p.path}</code></div>{p.busy&&<button onClick={p.onCancel}>Cancel assignment request</button>}</div>
    <p className="notice">{p.family.descriptor.publication_note}</p>
    {reason&&<p className="notice warning">{reason}</p>}
    {p.navigation.relatedRoom&&<div className="notice" data-testid="assignment-membership"><strong>Saved room: {p.navigation.relatedRoom}</strong>
      <p>Current profile draft: {has(rows,p.navigation.relatedRoom)?"candidate":"not a candidate"}. Saved enabled profile: {saved?.enabled===true&&has(saved.candidates,p.navigation.relatedRoom)?"candidate":"not enrolled"}.</p>
      {!focused?.eligible&&<p className="warning">{focused?.reason||"Room is missing, nested or not uniquely eligible in saved inputs."}</p>}
      <button disabled={!!reason||!focused?.eligible||has(rows,p.navigation.relatedRoom)} onClick={()=>p.onEdit(text=>recordRow(text,"candidates","add",-1,{layout_id:p.navigation.relatedRoom,weight:1}),"Add saved room candidate")}>Add this room</button>
      <p>Adding stages a candidate only. Deliberately choose enablement, type, chance and weights, then validate and apply. Membership and weight do not guarantee selection.</p>
    </div>}
    <div className="edit-actions"><button disabled={!!reason||!p.canUndo} onClick={p.onUndo}>Undo assignment</button><button disabled={!!reason||!p.canRedo} onClick={p.onRedo}>Redo assignment</button><button onClick={p.onSource}>Show assignment source</button></div>
    <fieldset className="item-properties" disabled={!!reason}><legend>New-world settings</legend><ContractFields family={p.family} values={values} onChange={(path,value)=>p.onEdit(text=>itemValue(text,path,value),"Change assignment setting")}/></fieldset>
    <OrderedRecords family={p.family} values={values} disabled={!!reason} allowEmpty onEdit={p.onEdit}/>
    {rows.map((row,i)=>{const id=typeof row?.layout_id==="string"?row.layout_id:"",room=rooms.find(r=>r.id===id);return <p key={i}><code>{id||"Choose saved room"}</code> · {room?.label||"Missing room"} {room?.path&&<button onClick={()=>p.navigation.onOpen("room",id,room.path)}>Open candidate room {i+1}</button>}{room&&!room.eligible&&<span className="warning">{room.reason}</span>}</p>;})}
    <details><summary>Saved room eligibility</summary>{rooms.map(r=><p key={r.id}><code>{r.id}</code> · {r.eligible?"eligible saved ordinary room":r.reason}</p>)}<p>Publish a documentation template as an ordinary room first. The starting laboratory is protected. Inactive missing/ineligible references are warnings; malformed fields, duplicate IDs and invalid weights remain errors.</p></details>
    <h3>Saved assignment sample</h3><p>Run one explicit ordinary new-world generation. Saved dependencies only; no rooms are constructed. Room preview checks contents/static access; Test room uses its controlled foyer. This sample records assignment metadata.</p>
    <label>Assignment preview seed<input aria-label="Assignment preview seed" type="number" min={0} max={2147483647} value={seed} onChange={e=>setSeed(e.target.value)}/></label>
    <button disabled={p.busy||p.dirty||!Number.isSafeInteger(Number(seed))||Number(seed)<0||Number(seed)>2147483647} onClick={()=>p.onPreview({seed:Number(seed)})}>Preview saved assignments</button>
    {p.dirty&&<p>Apply and byte-check reopen the profile before previewing saved assignments.</p>}
    {frame&&<><p data-testid="assignment-preview-state" className={p.previewStale||frame.seed!==Number(seed)?"notice warning":"notice"}>{p.previewStale||frame.seed!==Number(seed)?"Stale assignment sample — preview saved inputs again.":"Current saved assignment sample"}</p>
      <p>Seed {frame.seed} · {frame.width} × {frame.height} · {frame.plan_mode} · {frame.target_type} · chance {frame.authored_chance}. Matching: {frame.matching_count}; authored: {frame.authored_count}; procedural: {frame.procedural_count}.</p>
      <p><code>{frame.profile_path}</code> · {frame.contract} · SHA-256 <code>{frame.profile_sha256}</code></p>
      {!frame.rows.length&&<p>No authored candidates selected for this seed.</p>}
      <table><thead><tr><th>Chunk</th><th>SubMap / type / seed</th><th>Selected saved room</th></tr></thead><tbody>{frame.rows.map(r=><tr key={r.submap_id}><td>{r.chunk.join(", ")}</td><td>{r.submap_id} · {r.type} · {r.seed}</td><td><button onClick={()=>p.navigation.onOpen("room",r.layout_id,r.path)}>{rooms.find(v=>v.id===r.layout_id)?.label||r.layout_id}</button><code>{r.path}</code></td></tr>)}</tbody></table>
      {frame.truncated>0&&<p>{frame.truncated} further assignments omitted from this table. The entire world was generated.</p>}
      <details><summary>Assignment evidence</summary><pre className="raw" data-testid="assignment-preview-receipt">{JSON.stringify(frame,null,2)}</pre></details></>}
  </section>;
}
