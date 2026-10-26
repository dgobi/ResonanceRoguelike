import { useMemo, useState } from "react";
import { itemModel, itemValue, keywordEntry } from "./item";
import type { ItemContext, ItemTrail } from "./protocol";

export function ItemEditor(p: {
  draft: string; path: string; context?: ItemContext; selectedId?: string; dirty: boolean; validated: boolean;
  disabled: string; busy: boolean; onCancel: () => void; onReturn?: () => void; trail?: ItemTrail | null;
  onPool?: (id: string) => void; onSource: () => void;
  onEdit: (edit: (text: string) => string, label: string) => void;
  onUndo: () => void; onRedo: () => void; canUndo: boolean; canRedo: boolean;
}) {
  const parsed = useMemo(() => itemModel(p.draft), [p.draft]);
  const record = p.context?.records.find(r => r.id === p.selectedId) || p.context?.records[0];
  const cap = record?.capability;
  const values = parsed.model || record?.definition || {};
  const [view, setView] = useState("Properties"), [tag, setTag] = useState("");
  const reason = p.disabled || parsed.reason || (!cap?.editable ? cap?.reason || "Capability unavailable." : "");
  const evidenceCurrent = !p.dirty || p.validated;
  const edit = (path: (string | number)[], value: unknown) => p.onEdit(s => itemValue(s, path, value), "Edit item property");
  const keywords = values.keywords === undefined ? [] : values.keywords;
  const keywordShape = Array.isArray(keywords) && keywords.every(k => k && typeof k === "object" && !Array.isArray(k));
  const sourceJump = () => p.onSource();
  return <section className="item-editor" data-testid="item-editor">
    <div className="pane-heading"><div><h2>Item definition</h2><code>{String(values.id || record?.id || "Invalid source")} · {p.path}</code></div>
      <div className="edit-actions">{p.onReturn && <button onClick={p.onReturn} disabled={p.busy}>Return to pool</button>}
      {p.busy && <button onClick={p.onCancel} disabled={p.disabled === "Publication in progress."}>Cancel authoring request</button>}</div></div>
    {p.trail && <nav className="source-trail" aria-label="Item source trail">
      {p.trail.structure && <code>{p.trail.structure.sourcePath} → special_tiles[{p.trail.structure.index}] ({p.trail.structure.x}, {p.trail.structure.y})</code>}
      <button disabled={p.busy} onClick={p.onReturn}>Pool {p.trail.poolId} · entry {p.trail.index + 1}</button>
      <code>{p.trail.path} → items[{p.trail.index}].item_id = {p.trail.itemId}</code>
      <small>Declared reference when opened. Pool and structure drafts retained; item publication changes no references.</small>
    </nav>}
    <div className="tabs">{["Properties", "References", "Use binding", "Factory result"].map(v => <button key={v} className={view === v ? "active" : ""} onClick={() => setView(v)}>{v}</button>)}<button onClick={sourceJump}>Show source</button></div>
    {reason && <p className="notice warning" data-testid="item-disabled">{reason}</p>}
    {!evidenceCurrent && <p className="notice">References, use binding and factory evidence below belong to the opened source. Validate the exact draft to refresh them.</p>}
    {view === "Properties" && <>
      <div className="edit-actions"><button onClick={p.onUndo} disabled={!!reason || !p.canUndo}>Undo item</button><button onClick={p.onRedo} disabled={!!reason || !p.canRedo}>Redo item</button><small>Raw source and variant-ID edits clear item history.</small></div>
      <p className="muted">{cap?.reason}. Category: {String(values.category ?? "not declared")} · appearance: {String(values.tile ?? "factory default")}</p>
      {cap?.editable ? <fieldset disabled={!!reason} className="item-properties"><legend>Supported component properties</legend>
        {cap.fields.includes("name") && <label>Name<input aria-label="Item name" value={typeof values.name === "string" ? values.name : ""} onChange={e => edit(["name"], e.target.value)} /></label>}
        {cap.fields.includes("description") && <label>Description<textarea aria-label="Item description" value={typeof values.description === "string" ? values.description : ""} onChange={e => edit(["description"], e.target.value)} /></label>}
        {cap.fields.includes("weight") && <label>Weight ({cap.weight_unit})<input aria-label="Item weight (kg)" type="number" min="0" step="any" value={typeof values.weight === "number" ? values.weight : ""} placeholder="Factory default: 0.1" onChange={e => {if(e.target.value !== "" && Number.isFinite(Number(e.target.value))) edit(["weight"], Number(e.target.value));}} /></label>}
        {cap.fields.includes("stackable") && <label><input aria-label="Group in inventory" type="checkbox" checked={values.stackable === true} onChange={e => edit(["stackable"], e.target.checked)} /> Group in inventory<small>{cap.stack_note}</small></label>}
        {cap.fields.includes("keywords") && <><h3>Keywords</h3><small>{cap.tier_note}</small>
        {keywordShape ? <table className="pool-table"><thead><tr><th>Tag ID</th><th>Tier</th><th>Action</th></tr></thead><tbody>{keywords.map((kw, i) => <tr key={i}>
          <td><select aria-label={`Keyword ${i+1}`} value={typeof kw.tag === "string" ? kw.tag : ""} onChange={e => edit(["keywords", i, "tag"], e.target.value)}>
            {!p.context?.keywords[String(kw.tag)] && <option value={String(kw.tag || "")}>Unknown tag</option>}{Object.keys(p.context?.keywords || {}).sort().map(k => <option key={k}>{k}</option>)}</select></td>
          <td><input aria-label={`Keyword tier ${i+1}`} type="number" min={cap.tier_min} max={cap.tier_max} step="1" value={typeof kw.tier === "number" ? kw.tier : ""} onChange={e => {if(e.target.value !== "") edit(["keywords", i, "tier"], Number(e.target.value));}} /></td>
          <td><button onClick={() => p.onEdit(s => keywordEntry(s, i), "Remove keyword")}>Remove keyword {i+1}</button></td></tr>)}</tbody></table> : <p className="notice warning">Repair keywords in Source; expected an array of records.</p>}
          <div className="edit-actions"><label>Add keyword<select aria-label="New keyword" value={tag} onChange={e => setTag(e.target.value)}><option value="">Choose tag ID</option>{Object.keys(p.context?.keywords || {}).sort().map(k => <option key={k}>{k}</option>)}</select></label>
          <button disabled={!keywordShape || !tag} onClick={() => p.onEdit(s => keywordEntry(s, -1, tag), "Add keyword")}>Add keyword</button></div></>}
      </fieldset> : <pre className="raw">{JSON.stringify(record?.definition, null, 2)}</pre>}
      <p className="muted small">Unknown fields and nested data remain in Source. IDs are the machine identity; renaming the display name does not change references.</p>
    </>}
    {view === "References" && <><h3>Referenced by pools · declared JSON references</h3>
      <p className="muted small">Saved contextual pool files only. This is not an acquisition or world-selection guarantee.</p>
      {!record?.pools.length && <p>No saved pool references. This item may be unreferenced.</p>}
      <table className="pool-table"><tbody>{record?.pools.map(r => <tr key={r.path+r.pointer+r.index}><td><button disabled={!r.unique || !!r.pointer || p.busy} onClick={() => p.onPool?.(r.id)}>{r.id}</button><code>{r.path}{r.pointer}</code></td><td>{r.field}</td></tr>)}</tbody></table>
      <h3>Dependencies</h3><table className="pool-table"><thead><tr><th>Evidence</th><th>Reference</th><th>Source / field</th></tr></thead><tbody>{record?.dependencies.map((r,i) => <tr key={i}><td>{r.kind}{r.resolved !== undefined && <small>{r.resolved ? "Reference ID validated" : "Unresolved reference"}</small>}</td><td>{String(r.id)}</td><td>{r.field}<small>{r.paths?.join(", ")}</small><small>{r.note}</small></td></tr>)}</tbody></table></>}
    {view === "Use binding" && <><h3>{record?.use.status || "Unavailable"}</h3><dl><dt>Declared on_use</dt><dd>{JSON.stringify(record?.use.declared ?? null)}</dd><dt>Actual consumer</dt><dd>{record?.use.consumer}</dd><dt>Handler</dt><dd>{record?.use.handler || "None"}{record?.use.line ? ` · source line ${record.use.line}` : ""}</dd></dl><p>{record?.use.scope}</p>{record?.use.notes.map(n => <p className="notice" key={n}>{n}</p>)}<p>Ordinary interactive use was not executed.</p></>}
    {view === "Factory result" && <>{record?.factory && evidenceCurrent ? <><h3>Observed factory instance</h3><p>{record.factory.consumer}</p><p>{record.factory.scope}</p><code>{record.factory.path} · exact source {record.factory.definition_sha256.slice(0,12)}<br />Game {record.factory.source.game_source_sha256.slice(0,12)} · catalogue {record.factory.source.catalog_sha256?.slice(0,12)}</code>
      <small>Observed {record.factory.observed_at_utc} · loaded catalogue {record.factory.loaded_catalog_sha256.slice(0,12)}</small>
      <table className="pool-table"><thead><tr><th>Property</th><th>Declared</th><th>Instance</th></tr></thead><tbody>{record.factory.comparisons.map(r => <tr key={r.field}><td>{r.field}</td><td>{JSON.stringify(r.declared)}</td><td>{JSON.stringify(r.instance)} · {r.equal ? "matches" : "differs"}</td></tr>)}</tbody></table>
      <details><summary>Factory receipt</summary><pre className="raw" data-testid="item-factory-receipt">{JSON.stringify(record.factory,null,2)}</pre></details></> : <p>No current factory result. Validate the draft or repair the source diagnostics.</p>}</>}
  </section>;
}
