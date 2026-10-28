import {useEffect,useRef,useState} from "react";
import {invoke} from "@tauri-apps/api/core";
import {asFailure,type Failure} from "./protocol";
export type RecoveryRow={key:string;project:string;source:string;family:string;generation:number;captured_ms:number;status:string;published?:{path:string;after_sha256:string;generation:number}|null};
type Detail={key:string;record:RecoveryRow & {baseline:string;draft:string;target:string;variant:boolean;variant_id:string;contract:string};status:string;disk:string|null};
export function RecoveryPanel({open,onClose,onRestore,onError,refreshVersion}:{open:boolean;onClose:()=>void;onRestore:(row:RecoveryRow,target?:string,expected?:string)=>Promise<void>;onError:(e:Failure)=>void;refreshVersion:number}){
  const [rows,setRows]=useState<RecoveryRow[]>([]),[notices,setNotices]=useState<string[]>([]);
  const [selected,setSelected]=useState<RecoveryRow|null>(null),[detail,setDetail]=useState<Detail|null>(null),[busy,setBusy]=useState(false),[discard,setDiscard]=useState(false);
  const inspection=useRef(0),listing=useRef(0),verified=useRef<RecoveryRow|null>(null),acting=useRef(false);
  function clear(){inspection.current++;verified.current=null;setSelected(null);setDetail(null);setDiscard(false);}
  async function refresh(){const request=++listing.current;clear();try{const r=await invoke<{records:RecoveryRow[];notices:string[]}>("list_recovery");if(request!==listing.current)return;setRows(r.records);setNotices(r.notices);}catch(e){if(request===listing.current)onError(asFailure(e));}}
  useEffect(()=>{if(open)void refresh();else clear();return ()=>{listing.current++;inspection.current++;verified.current=null;};},[open,refreshVersion]);
  async function select(row:RecoveryRow){
    if(acting.current)return;listing.current++;clear();setSelected(row);const request=inspection.current;
    try{const result=await invoke<Detail>("inspect_recovery",{key:row.key});if(request!==inspection.current)return;
      if(result.key!==row.key || result.record.generation!==row.generation || result.record.project!==row.project || result.record.source!==row.source || result.record.family!==row.family){clear();onError(asFailure(new Error("Recovery identity or generation changed. Refresh the list.")));return;}
      verified.current=row;setDetail(result);
    }catch(e){if(request===inspection.current)onError(asFailure(e));}
  }
  async function act(row:RecoveryRow,action:()=>Promise<void>){
    if(acting.current || verified.current!==row)return;
    acting.current=true;setBusy(true);clear();listing.current++;
    try{await action();await refresh();}catch(e){onError(asFailure(e));await refresh();}finally{acting.current=false;setBusy(false);}
  }
  if(!open)return null;
  return <div className="modal-shade"><section className="confirmation recovery-panel" role="dialog" aria-label="Recover drafts">
    <h2>Recover drafts</h2>
    <p>Creature, item, recipe, found-text and game typography drafts. Stored copies remain readable when the project or worker is unavailable. Recovery requires fresh validation before publication.</p>
    <button onClick={()=>void refresh()} disabled={busy}>Refresh recovery list</button>
    {!rows.length && <p>No durable drafts in this recovery store.</p>}
    <div className="recovery-list">{rows.map(row=><button key={row.key} data-recovery-key={row.key} aria-current={selected?.key===row.key ? "true":undefined} onClick={()=>void select(row)} disabled={busy}>
      <strong>{row.family} · {row.source}</strong><br/><small>{row.project}<br/>{new Date(row.captured_ms).toLocaleString()} · generation {row.generation}<br/>{row.status}{row.published ? " · Publication completed; reconciliation pending":""}</small>
    </button>)}</div>
    {notices.map(n=><p className="notice warning" key={n}>{n}</p>)}
    {detail && selected && <div data-testid="recovery-detail">
      <p>{detail.status}. Historical contract: {detail.record.contract}. Variant: {detail.record.variant ? detail.record.variant_id : "existing source"}.</p>
      <label>Recovered exact draft<textarea aria-label="Recovered exact draft" className="source-editor" readOnly value={detail.record.draft}/></label>
      <div className="edit-actions"><button onClick={()=>void navigator.clipboard.writeText(detail.record.draft).catch(e=>onError(asFailure(e)))}>Copy recovered draft</button>
      <button disabled={busy} onClick={()=>void act(selected,()=>onRestore(selected))}>Recover selected draft</button>
      <button disabled={busy} onClick={()=>void act(selected,()=>onRestore(selected,detail.record.published?.path || detail.record.target,detail.record.published?.after_sha256))}>Reconcile saved file</button>
      <button disabled={busy} onClick={()=>setDiscard(true)}>Discard selected draft…</button></div>
      <details><summary>Compare baseline and current disk</summary>
        <label>Original baseline<textarea className="source-editor" aria-label="Original baseline" readOnly value={detail.record.baseline}/></label>
        <label>Current disk<textarea className="source-editor" aria-label="Current disk" readOnly value={detail.disk ?? "Source unavailable"}/></label>
      </details>
      {discard && <div className="notice warning"><p>Delete recovery copy for {selected.project} · {selected.source} · generation {selected.generation}? Published content files are unchanged.</p><button disabled={busy} onClick={()=>void act(selected,()=>invoke("discard_recovery",{key:selected.key,generation:selected.generation}))}>Confirm discard recovery</button><button onClick={()=>setDiscard(false)}>Keep recovery copy</button></div>}
    </div>}
    <button className="primary" disabled={busy} onClick={()=>{clear();listing.current++;onClose();}}>Keep for later</button>
  </section></div>;
}
