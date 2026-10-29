import { useEffect, useMemo, useRef, useState } from "react";
import { poolEntry, poolModel, poolValue, poolRow, poolDefault } from "./pool";
import type { Diagnostic, PoolContext, SourceTrail } from "./protocol";

export function PoolEditor(p: {
  draft: string; path: string; context?: PoolContext; disabled: string; diagnostics: Diagnostic[];
  onEdit: (edit: (text: string) => string, label: string) => void;
  onUndo: () => void; onRedo: () => void; canUndo: boolean; canRedo: boolean;
  trail?: SourceTrail | null; onReturn?: () => void; busy: boolean; onCancel: () => void;
  onItem?: (id: string, index: number) => void;
  focusEntry?: number;
  returnLocation?:{text:string;index:number;itemId?:string};
  onUsage?:(id:string,path:string,route:string)=>void;
}) {
  const parsed = useMemo(() => poolModel(p.draft), [p.draft]);
  const [selected, setSelected] = useState<string | null>(null);
  const itemRef = useRef<HTMLElement | null>(null);
  const editorRef = useRef<HTMLElement | null>(null);
  useEffect(() => {
    const index=p.returnLocation ? p.returnLocation.text===p.draft ? p.returnLocation.index : undefined : p.focusEntry;
    if (index === undefined) return;
    const row = editorRef.current?.querySelector<HTMLElement>(`[data-pool-entry="${index}"]`);
    row?.scrollIntoView({block:"nearest"}); row?.focus({preventScroll:true});
  }, [p.focusEntry,p.returnLocation,p.draft]);
  useEffect(() => {
    if (selected) { itemRef.current?.scrollIntoView({block: "nearest"}); itemRef.current?.focus({preventScroll: true}); }
  }, [selected]);
  const [addId, setAddId] = useState("");
  const disabled = p.disabled || parsed.reason || (!p.context ? "Item catalogue unavailable. Reopen after repairing source diagnostics." : "");
  const rows = parsed.model?.items || [], items = p.context?.items || {};
  const item = selected ? items[selected] : null;
  const rolls = parsed.model?.roll_count === undefined ? [1, 1] : parsed.model.roll_count;
  const rollsSupported = Array.isArray(rolls) && rolls.length >= 1 && rolls.length <= 2;
  const countMode=parsed.model?.roll_count===undefined ? "default" : rollsSupported ? rolls.length===1 ? "fixed" : "range" : "invalid";
  const edit = (path: (string | number)[], value: unknown) => p.onEdit(s => poolValue(s, path, value), "Edit pool field");
  return <section ref={editorRef} className="pool-editor" data-testid="pool-editor">
    <div className="pane-heading"><h2>Contextual loot pool</h2><div className="edit-actions">
      {p.onReturn && <button onClick={p.onReturn} disabled={p.busy}>Return to structure</button>}
      {p.busy && <button onClick={p.onCancel} disabled={p.disabled === "Publication in progress."}>Cancel authoring request</button>}
    </div></div>
    <nav className="source-trail" aria-label="Source trail">
      {p.trail && <><button onClick={p.onReturn} disabled={p.busy}>Structure {p.trail.id}</button>
        <code>Opened source: {p.trail.sourcePath} · {p.trail.sourceHash.slice(0, 12)}<br />Draft target: {p.trail.path} → special_tiles[{p.trail.index}] · {p.trail.decor} ({p.trail.x}, {p.trail.y})</code>
        <small>Declared reference when opened: {p.trail.poolId}. Structure draft retained; no link changes on pool save.</small></>}
      <code>→ Pool {parsed.model?.id || "invalid draft"} · {p.path}{selected ? ` → Item ${selected}` : ""}</code>
    </nav>
    <p className="muted small">{p.context?.rules}</p>
    {p.context?.records[0]?.capability.reason && <p className="notice warning">{p.context.records[0].capability.reason}</p>}
    {p.returnLocation && p.returnLocation.text!==p.draft && <p role="status" className="notice warning" data-testid="stale-pool-location">Recorded pool row {p.returnLocation.index+1} is stale: this draft changed while away. No different row was selected.</p>}
    <label>Description<textarea aria-label="Pool description" disabled={!!disabled} value={typeof parsed.model?.description==="string"?parsed.model.description:""} onChange={e=>edit(["description"],e.target.value)}/></label>
    <div className="edit-actions">
      <button onClick={p.onUndo} disabled={!!p.disabled || !p.canUndo}>Undo pool</button>
      <button onClick={p.onRedo} disabled={!!p.disabled || !p.canRedo}>Redo pool</button>
      <small>Table, Source and properties share one history.</small>
    </div>
    {disabled && <p className="notice warning" data-testid="pool-disabled">{disabled}</p>}
    <label>Count representation<select aria-label="Roll count representation" value={countMode} disabled={!!disabled} onChange={e=>p.onEdit(s=>e.target.value==="default"?poolDefault(s,["roll_count"]):poolValue(s,["roll_count"],e.target.value==="fixed"?[rollsSupported?rolls[0]:1]:[rollsSupported?rolls[0]:1,rollsSupported?rolls[rolls.length-1]:1]),"Change count representation")}>
      <option value="default">Omitted · effective [1,1]</option><option value="fixed">Single value · [n]</option><option value="range">Inclusive range · [min,max]</option>{countMode==="invalid"&&<option value="invalid">Invalid saved value</option>}</select></label>
    <fieldset className="roll-fields" disabled={!!disabled || !rollsSupported}><legend>Roll count · inclusive bounds</legend>
      {(countMode==="fixed"?[0]:[0, 1]).map(i => <label key={i}>{i ? "Maximum" : "Minimum"}<input aria-label={i ? "Maximum rolls" : "Minimum rolls"} type="number" min="0" max={Number.MAX_SAFE_INTEGER} step="1"
        value={rollsSupported ? rolls[i] ?? rolls[0] : ""} onChange={e => {
          if (e.target.value === "") return;
          const next = [...rolls]; next[i] = Number(e.target.value);
          edit(["roll_count"], next);
        }} /></label>)}
    </fieldset>
    {!rollsSupported && <p className="notice warning">Repair roll_count in Source: one or two nonnegative integers.</p>}
    <div className="pool-table-wrap"><table className="pool-table"><thead><tr><th>Entry</th><th>Item ID / name</th><th>Weight</th><th>Reference</th><th>Action</th></tr></thead>
      <tbody>{rows.map((r, i) => {
        const id = typeof r.item_id === "string" ? r.item_id : "";
        return <tr key={i} data-pool-entry={i} tabIndex={-1}><td>{i + 1}</td><td><select aria-label={`Item ID ${i + 1}`} value={id} disabled={!!disabled}
          onChange={e => edit(["items", i, "item_id"], e.target.value)}>
          {!items[id] && <option value={id}>{id || "Missing item ID"} · unresolved</option>}
          {Object.values(items).map(a => <option key={a.id} value={a.id} disabled={!a.resolved}>{a.id} · {a.name}</option>)}
        </select></td><td><input aria-label={`Weight ${i + 1}`} type="number" min="0" step="any" disabled={!!disabled}
          value={typeof r.weight === "number" ? r.weight : r.weight === undefined ? 1 : ""}
          onChange={e => { if (e.target.value !== "") edit(["items", i, "weight"], Number(e.target.value)); }} />
        <button aria-label={`Use default weight ${i+1}`} disabled={!!disabled||r.weight===undefined} onClick={()=>p.onEdit(s=>poolDefault(s,["items",i,"weight"]),"Restore omitted weight")}>Use default 1</button></td>
        <td><button disabled={!items[id]} onClick={() => setSelected(id)}>Inspect {id || "item"}</button>
          <button disabled={p.busy || !items[id]?.resolved} onClick={() => p.onItem?.(id, i)}>Open item {id || "source"}</button>
          <small>{items[id]?.resolved ? "Declared ID resolves" : "Unresolved / ambiguous"} · {items[id]?.sources.map(s=>s.path+s.pointer).join(", ")}</small>
          {p.diagnostics.filter(d => d.field.includes(`items[${i}]`)).map((d, n) => <small className="row-diagnostic" key={n}>{d.code}: {d.message}</small>)}
        </td><td>{(["up","down"] as const).map(action=><button key={action} aria-label={`${action} pool entry ${i+1}`} disabled={!!disabled||(action==="up"?i===0:i===rows.length-1)} onClick={()=>p.onEdit(s=>poolRow(s,action,i),"Reorder complete source row")}>{action}</button>)}<button aria-label={`Remove entry ${i + 1}`} disabled={!!disabled} onClick={() => p.onEdit(s => poolEntry(s, i), "Remove pool entry")}>Remove</button></td></tr>;
      })}</tbody></table></div>
    {!rows.length && <p className="notice">No entries. This pool produces no items.</p>}
    <div className="edit-actions"><label>Add item<select aria-label="New pool item" value={addId} disabled={!!disabled} onChange={e => setAddId(e.target.value)}>
      <option value="">Choose item ID</option>{Object.values(items).filter(a => a.resolved).map(a => <option key={a.id} value={a.id}>{a.id} · {a.name}</option>)}</select></label>
      <button disabled={!!disabled || !addId || rows.length>=64} onClick={() => p.onEdit(s => poolEntry(s, -1, addId), "Add pool entry")}>Add entry</button>
      <button disabled={!!disabled||rows.length>0||parsed.model?.items===undefined} onClick={()=>p.onEdit(s=>poolDefault(s,["items"]),"Restore omitted items")}>Omit empty items</button><small>{rows.length}/64 publication rows; larger sources may be reduced deliberately.</small></div>
    {item && <section ref={itemRef} tabIndex={-1} className="item-inspector" data-testid="item-inspector"><div className="pane-heading"><h3>Item source · read-only</h3><button onClick={() => setSelected(null)}>Close item</button></div>
      <b>{item.id} · {item.name}</b>{item.sources.map(s => <div key={s.path + s.pointer}><code>{s.path}{s.pointer}</code><pre className="raw">{JSON.stringify(s.definition, null, 2)}</pre></div>)}
      <small>Declared definition from the opened catalogue snapshot. This view does not establish a generated drop or gameplay effect.</small></section>}
    <details><summary>Declared direct-container references ({p.context?.references.length ?? 0})</summary>
      <p className="muted small">Saved direct containers in ordinary buildings and supported authored rooms. Weighted alternatives and other contexts are outside this partial list; an empty list does not prove unused or unreachable.</p>
      <table className="pool-table"><tbody>{p.context?.references.map(r => <tr key={r.path + r.field}><td><button disabled={p.busy} onClick={()=>p.onUsage?.(r.id,r.path,r.route)}>{r.id}</button><code>{r.path}</code></td><td>{r.field}<br />{r.decor_id} ({r.x}, {r.y})</td></tr>)}</tbody></table>
    </details>
    <details><summary>Validation and population sources</summary><p>Validated consumer: Validate draft checks these exact pool bytes through the current DataLoader and Validator.pool. See the draft verdict for its result.</p>
      <code>{p.context?.validator}<br />{p.context?.consumer}</code>
      <p>Observed generated contents: use the linked structure's Draft production preview. Its receipt records seed, source hashes and actual factory-created items. Pool editing alone produces no sample or world selection.</p></details>
  </section>;
}
