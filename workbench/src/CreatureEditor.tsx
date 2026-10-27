import { useEffect, useRef, useState } from "react";
import { creatureModel, creatureValue } from "./creature";
import { request, asFailure, type CreatureContext, type Inspection } from "./protocol";

export function CreatureEditor(p: {
  draft: string; path: string; context?: CreatureContext; selectedId?: string;
  disabled: string; evidenceStale: boolean; validated: boolean; dirty: boolean; active: boolean;
  busy: boolean; setBusy: (s: string) => void; onCancel: () => void; onSource: () => void; onFactory: () => void;
  onEdit: (edit: (text: string) => string, label: string) => void;
  onUndo: () => void; onRedo: () => void; canUndo: boolean; canRedo: boolean;
}) {
  const parsed = creatureModel(p.draft);
  const record = p.context?.records.find(r => r.id === p.selectedId) || p.context?.records[0];
  const cap = record?.capability, values = parsed.model || record?.definition || {};
  const reason = p.disabled || parsed.reason;
  const [view, setView] = useState("Supported fields"), [reference, setReference] = useState<Inspection | null>(null), [error, setError] = useState("");
  const generation = useRef(0);
  useEffect(() => { generation.current++; return () => {generation.current++;}; }, [p.active, p.path]);
  const observed = p.validated && !p.evidenceStale ? record?.factory : null;
  const currentRefs = !p.evidenceStale && (!p.dirty || p.validated);
  async function inspectReference(path: string) {
    const version = ++generation.current; setReference(null); setError(""); p.setBusy("Inspecting direct layout reference…");
    try { const r = await request<Inspection>("inspect", {asset:path}); if(version === generation.current) setReference(r.result); }
    catch(e) { if(version === generation.current) setError(asFailure(e).message); }
    finally { p.setBusy(""); }
  }
  return <section className="item-editor" data-testid="creature-editor">
    <div className="pane-heading"><div><h2>Creature definition</h2><code>{String(values.id || record?.id || "Invalid source")} · {p.path}</code></div>
      {p.busy && <button onClick={p.onCancel} disabled={p.disabled === "Publication in progress."}>Cancel authoring request</button>}</div>
    <div className="tabs">{["Supported fields", "Read-only fields", "Direct layout references", "Factory result"].map(v => <button key={v} className={view === v ? "active" : ""} onClick={() => setView(v)}>{v}</button>)}<button onClick={p.onSource}>Show source</button></div>
    <p className="muted small">{cap?.shape} · {cap?.contract}</p>
    {reason && <p className="notice warning">{reason}</p>}
    {view === "Supported fields" && <>
      <p>{cap?.reason}</p>
      {cap?.editable && <><div className="edit-actions"><button disabled={!!reason || !p.canUndo} onClick={p.onUndo}>Undo creature</button><button disabled={!!reason || !p.canRedo} onClick={p.onRedo}>Redo creature</button><small>Raw and variant-ID changes clear typed history.</small></div>
        <fieldset className="item-properties" disabled={!!reason}><legend>Supported fields</legend>
          <label>Actor name<input aria-label="Creature name" maxLength={256} value={typeof values.name === "string" ? values.name : ""} onChange={e=>p.onEdit(s=>creatureValue(s,"name",e.target.value),"Creature name")} /></label>
          <label>Effective HP<input aria-label="Effective HP" type="number" min={cap.hp_min} max={cap.hp_max} step="1" value={typeof values.base_hp === "number" ? values.base_hp : ""} onChange={e=>{if(e.target.value !== "") p.onEdit(s=>creatureValue(s,"hp",Number(e.target.value)),"Effective HP: base_hp and fighter.max_hp");}} /></label>
          <p>{cap.hp_note}</p><small>Authoring range: {cap.hp_min}–{cap.hp_max}, finite integers.</small>
        </fieldset></>}
      <p className="notice">{p.context?.selection}</p>
    </>}
    {view === "Read-only fields" && <><p>{cap?.description_note}</p><p>AI, attacks, perception, factions, limbs, harvest, effects, spawn declarations and unknown metadata remain read-only. No combat or encounter result is inferred.</p>
      {Object.entries(values).filter(([key])=> !["id","name","base_hp"].includes(key)).map(([key,value])=><details key={key}><summary>{key}{key === "fighter" ? " · max_hp changes with Effective HP; other values read-only" : ""}</summary><pre className="raw">{JSON.stringify(value,null,2)}</pre></details>)}
    </>}
    {view === "Direct layout references" && <>
      {!currentRefs ? <p className="notice">Reference snapshot is stale. Validate the exact draft or reload the source.</p> : <>
        <p>Saved direct authored_submap records only. These are declarations, not natural selection or observed encounters. Ordinary buildings, plazas and entrance layouts do not support creature records.</p>
        {!record?.references.length && <p>No direct authored-submap references to this ID.</p>}
        <table className="pool-table"><tbody>{record?.references.map(r=><tr key={r.path+r.field}><td><button disabled={p.busy} onClick={()=>void inspectReference(r.path)}>Inspect layout {r.id}</button><code>{r.path}</code></td><td>{r.route} · {r.field}<small>({r.x}, {r.y}) · {r.evidence}</small></td></tr>)}</tbody></table>
        <h3>Source dependencies</h3><table className="pool-table"><thead><tr><th>Reference</th><th>Resolution</th><th>Meaning</th></tr></thead><tbody>{record?.dependencies.map(r=><tr key={r.field}><td>{r.field}<code>{JSON.stringify(r.id)}</code></td><td>{r.resolved ? "Registry resolved" : "Unknown reference"}<small>{r.paths.join(", ")}</small></td><td>{r.kind}<small>{r.note}</small></td></tr>)}</tbody></table>
      </>}
      {error && <p role="alert">{error}</p>}{reference && <details open><summary>Read-only layout source · {reference.path}</summary><code>SHA-256 {reference.sha256}</code><pre className="raw">{reference.raw}</pre></details>}
    </>}
    {view === "Factory result" && <>
      <button disabled={p.busy || !cap?.editable || !!parsed.reason} onClick={p.onFactory}>Validate and construct exact creature</button>
      {observed ? <><h3>Observed factory actor</h3><p>{observed.actor_class} · {observed.creature_id}</p><p>{observed.scope}</p>
        <code>{observed.path}<br />Source {observed.source_sha256}<br />Game {observed.source.commit || "Git revision unavailable"} · source hash {observed.source.game_source_sha256}<br />Input catalogue {observed.source.catalog_sha256}</code>
        <p className="muted small">{observed.consumer} · {observed.contract} · worker {observed.worker_version} · {observed.observed_at_utc}</p>
        <table className="pool-table"><thead><tr><th>Source → component</th><th>Declared</th><th>Created instance</th></tr></thead><tbody>{observed.comparisons.map(r=><tr key={r.field}><td>{r.field}</td><td>{JSON.stringify(r.declared)}</td><td>{JSON.stringify(r.instance)}</td></tr>)}</tbody></table>
        <details><summary>Factory receipt</summary><pre className="raw" data-testid="creature-factory-receipt">{JSON.stringify(observed,null,2)}</pre></details>
      </> : <p>No current factory result. Validate the exact source/draft; changed dependencies or invalid drafts revoke prior evidence.</p>}
    </>}
  </section>;
}
