import { useMemo, useState } from "react";
import { recipeModel, recipeRow, recipeValue } from "./recipe";
import type { RecipeContext } from "./protocol";

export function RecipeEditor(p: {
  draft: string; path: string; context?: RecipeContext; selectedId?: string; dirty: boolean; validated: boolean;
  disabled: string; busy: boolean; evidenceStale: boolean; onCancel: () => void; onReturn?: () => void;
  onItem: (id: string, path?: string) => void; onSource: () => void; onProbe: () => void;
  onEdit: (edit: (text: string) => string, label: string) => void;
  onUndo: () => void; onRedo: () => void; canUndo: boolean; canRedo: boolean;
}) {
  const parsed = useMemo(() => recipeModel(p.draft), [p.draft]);
  const record = p.context?.records.find(r => r.id === p.selectedId) || p.context?.records[0];
  const cap = record?.capability, values = parsed.model || record?.definition || {};
  const [view, setView] = useState("Requirements"), [preset, setPreset] = useState("eligible");
  const [tags, setTags] = useState<Record<string,string>>({});
  // This is only a UI guard using the game-owned capability's exclusion list.
  // Python independently rechecks current bytes; this is never a publication verdict.
  const outside = cap?.excluded_fields.some(k => k in values) || (values.passive_processing !== undefined && values.passive_processing !== false);
  const reason = p.disabled || parsed.reason || (!cap?.editable ? cap?.reason || "Capability unavailable." : outside ? "Not supported: current source has excluded recipe mechanics. Draft retained; inspect Source." : "");
  const evidenceCurrent = !p.evidenceStale && (!p.dirty || p.validated);
  const evidence = p.validated && evidenceCurrent ? record?.probe : null;
  const sample = evidence?.cases.find(c => c.preset === preset);
  const edit = (path: (string | number)[], value: unknown) => p.onEdit(s => recipeValue(s,path,value), "Edit recipe field");
  const links = (role: string, index: number) => record?.candidates.find(r => r.role === role && r.index === index)?.matches || [];
  const groups = [["components","Required items"],["tools","Tools · retained"],["requires_ambient","Ambient conditions"]];
  return <section className="item-editor recipe-editor" data-testid="recipe-editor">
    <div className="pane-heading"><div><h2>Recipe</h2><code>{String(values.id || record?.id || "Invalid source")} · {p.path}</code></div>
      <div className="edit-actions">{p.onReturn && <button onClick={p.onReturn} disabled={p.busy}>Return to item</button>}
        {p.busy && <button onClick={p.onCancel} disabled={p.disabled === "Publication in progress."}>Cancel authoring request</button>}</div></div>
    <p>{cap?.execution_class || "Unknown"} · {cap?.editable ? "Supported family" : "Not supported for writing"}</p>
    <div className="tabs">{["Requirements","Output","Test requirements"].map(v => <button key={v} className={view === v ? "active" : ""} onClick={() => setView(v)}>{v}</button>)}<button onClick={p.onSource}>Show source</button></div>
    {reason && <p className="notice warning" data-testid="recipe-disabled">{reason}</p>}
    <p className="notice">{p.context?.visibility}</p>
    {!evidenceCurrent && <p className="notice warning">Source or dependencies changed. Validate to refresh catalogue matches and requirement evidence; drafts are retained.</p>}
    {view === "Requirements" && <>
      {cap?.editable && <><div className="edit-actions"><button disabled={!!reason || !p.canUndo} onClick={p.onUndo}>Undo recipe</button><button disabled={!!reason || !p.canRedo} onClick={p.onRedo}>Redo recipe</button><small>Raw and variant-ID edits clear recipe history.</small></div>
      <fieldset disabled={!!reason} className="item-properties"><legend>Immediate recipe properties</legend>
        <label>Name<input aria-label="Recipe name" value={typeof values.name === "string" ? values.name : ""} onChange={e=>edit(["name"],e.target.value)} /></label>
        <label>Description<textarea aria-label="Recipe description" value={typeof values.description === "string" ? values.description : ""} onChange={e=>edit(["description"],e.target.value)} /></label>
        <label>Category<select aria-label="Recipe category" value={typeof values.category === "string" ? values.category : ""} onChange={e=>edit(["category"],e.target.value)}><option value="">Uncategorized</option>{p.context?.categories.map(c=><option key={c}>{c}</option>)}</select></label>
        <label><input aria-label="Recipe known" type="checkbox" checked={values.known !== false} onChange={e=>edit(["known"],e.target.checked)} /> Known at startup (default: true)<small>False displays an unknown recipe and blocks CraftScreen execution; no learning route is established.</small></label>
      </fieldset></>}
      {!cap?.editable && <p className="asset-description">{String(values.description || "")}</p>}
      {groups.map(([field,title]) => {
        const registry = field === "requires_ambient" ? p.context?.ambient_tags : p.context?.keywords;
        const rows = values[field] === undefined ? [] : values[field];
        const validRows = Array.isArray(rows) && rows.every(r=>r && typeof r === "object" && !Array.isArray(r));
        return <section key={field}><h3>{title}</h3>
          <p className="muted small">{field === "requires_ambient" ? "Conditions, not automatically consumed item inputs. Any matching ambient source satisfies a row; quantity is not consumed." : field === "tools" ? "Distinct physical instances fill tool slots and remain in inventory. Defaults: minimum tier 1, quantity 1." : "Ordered physical requirements. Each instance fills one slot. Repeated requirements stay separate. Defaults: minimum tier 1, quantity 1."}</p>
          {validRows ? <div className="recipe-table-scroll"><table className="pool-table"><thead><tr><th>Row</th><th>Tag</th><th>Minimum tier</th>{field !== "requires_ambient" && <th>Quantity</th>}<th>{cap?.editable ? "Edit / potential tag matches" : "Potential tag matches"}</th></tr></thead><tbody>
            {rows.map((row,i)=><tr key={i}><td>{i+1}</td><td>{cap?.editable ? <select disabled={!!reason} aria-label={`${field} tag ${i+1}`} value={typeof row.tag === "string" ? row.tag : ""} onChange={e=>edit([field,i,"tag"],e.target.value)}>
              {!registry?.[String(row.tag)] && <option value={String(row.tag || "")}>Unknown tag</option>}{Object.keys(registry || {}).sort().map(k=><option key={k}>{k}</option>)}</select> : String(row.tag)}</td>
              <td>{cap?.editable ? <input disabled={!!reason} aria-label={`${field} tier ${i+1}`} type="number" min={cap.tier_min} max={cap.tier_max} step="1" value={typeof row.min_tier === "number" ? row.min_tier : row.min_tier === undefined ? 1 : ""} onChange={e=>{if(e.target.value !== "") edit([field,i,"min_tier"],Number(e.target.value));}} /> : String(row.min_tier ?? 1)}</td>
              {field !== "requires_ambient" && <td>{cap?.editable ? <input disabled={!!reason} aria-label={`${field} quantity ${i+1}`} type="number" min="1" max={cap.quantity_max} step="1" value={typeof row.quantity === "number" ? row.quantity : row.quantity === undefined ? 1 : ""} onChange={e=>{if(e.target.value !== "") edit([field,i,"quantity"],Number(e.target.value));}} /> : String(row.quantity ?? 1)}</td>}
              <td>{cap?.editable && <div className="edit-actions">{(["up","down","remove"] as const).map(action=><button key={action} disabled={!!reason || action === "up" && i === 0 || action === "down" && i === rows.length-1} aria-label={`${action} ${field} ${i+1}`} onClick={()=>p.onEdit(s=>recipeRow(s,field,action,i),`${action} requirement`)}>{action === "up" ? "↑" : action === "down" ? "↓" : "Remove"}</button>)}</div>}
              {field !== "requires_ambient" && (evidenceCurrent ? <details><summary>Potential tag matches ({links(field,i).length})</summary>{links(field,i).map(m=><div key={m.path+m.pointer}><button disabled={p.busy} onClick={()=>p.onItem(m.id,m.path)}>{m.id}</button><small>{m.path}{m.pointer}{!m.automatic_material && field === "components" ? " · explicit material choice required" : ""}</small></div>)}<small>Tag/tier only; quantities, knowledge, access and ambient conditions are unverified here.</small></details> : <small>Validate to refresh matches.</small>)}</td></tr>)}
          </tbody></table></div> : <p className="notice warning">Repair {field} in Source; expected an array of requirement records.</p>}
          {cap?.editable && <div className="edit-actions"><label>Add {title.toLowerCase()}<select disabled={!!reason} aria-label={`New ${field} tag`} value={tags[field] || ""} onChange={e=>setTags({...tags,[field]:e.target.value})}><option value="">Choose tag ID</option>{Object.keys(registry || {}).sort().map(k=><option key={k}>{k}</option>)}</select></label><button disabled={!!reason || !validRows || !tags[field]} onClick={()=>p.onEdit(s=>recipeRow(s,field,"add",-1,tags[field]),"Add requirement")}>Add {field} row</button></div>}
        </section>;
      })}
      {values.requires_single_item !== undefined && <><h3>Single-item conjunction · read-only</h3><pre className="raw">{JSON.stringify(values.requires_single_item,null,2)}</pre><p>All tags must hold on each physical item. List form uses one item; object form uses max_quantity (default 1).</p>{links("requires_single_item",0).map(m=><button key={m.path+m.pointer} disabled={p.busy} onClick={()=>p.onItem(m.id,m.path)}>{m.id}</button>)}</>}
    </>}
    {view === "Output" && <>
      <h3>Declared output</h3><code>{values.result_item !== undefined ? `result_item = ${JSON.stringify(values.result_item)}` : `result_tile = ${JSON.stringify(values.result_tile)}`}</code>
      {cap?.editable && <label>Output item<select disabled={!!reason} aria-label="Recipe output item" value={String(values.result_item || "")} onChange={e=>edit(["result_item"],e.target.value)}>{!p.context?.items.some(i=>i.id===values.result_item) && <option value={String(values.result_item || "")}>Unresolved item</option>}{p.context?.items.map(i=><option key={i.id} value={i.id}>{i.id} · {i.name}</option>)}</select></label>}
      <p>{evidenceCurrent && record?.output.resolved ? "Catalogue-resolved item reference" : "Reference not currently resolved"}</p>
      {evidenceCurrent && record?.output.sources.map(s=><div key={s.path+s.pointer}><button disabled={p.busy} onClick={()=>p.onItem(record.output.id!,s.path)}>Open output item {record.output.id}</button><code>{s.path}{s.pointer}</code></div>)}
      <p>Only the separate test receipt records an observed factory output or inventory exchange.</p>
    </>}
    {view === "Test requirements" && <>
      <button disabled={p.busy || !cap?.editable || !!parsed.reason || !!outside} onClick={p.onProbe}>Validate and test exact recipe</button>
      <p>Builds synthetic disposable inventory from actual item definitions and explicit ambient records. No campaign is opened.</p>
      {evidence ? <><p>{evidence.scope}</p><code>{evidence.path} · source {evidence.source_sha256.slice(0,12)}<br />Game {evidence.source.game_source_sha256.slice(0,12)} · catalogue {evidence.source.catalog_sha256.slice(0,12)}</code>
        <label>Fixture<select aria-label="Recipe fixture" value={preset} onChange={e=>setPreset(e.target.value)}><option value="eligible">Candidate inventory + ambient</option><option value="missing_items">No physical inputs</option><option value="missing_ambient">No ambient sources</option></select></label>
        {sample && <><h3>{sample.eligible ? "Game-owned eligibility: requirements met in this fixture" : "Game-owned eligibility: missing requirements"}</h3>
          <table className="pool-table"><thead><tr><th>Physical instance</th><th>Definition</th><th>Keywords / role</th></tr></thead><tbody>{sample.inventory.map(i=><tr key={i.instance}><td>{i.instance}</td><td>{i.item_id}<small>{i.source}</small></td><td>{JSON.stringify(i.keywords)}<small>{sample.materials.includes(i.instance) ? "Selected material" : sample.retained_tools.includes(i.instance) ? "Selected retained tool" : "Not committed as material"}</small></td></tr>)}</tbody></table>
          <p>Ambient fixture: <code>{JSON.stringify(sample.ambient)}</code></p>
          {sample.missing.map((r,i)=><p className="notice warning" key={i}>{r.ambient ? "Ambient condition" : r.role === "tool" ? "Tool" : "Material"}: {r.tag} ≥ {r.min_tier} · have {r.have}, need {r.need}</p>)}
          <p>Selected instances: {sample.selected.join(", ") || "None"}</p><p>Production inventory exchange: {sample.committed === null ? "Not attempted (requirements missing)" : sample.committed ? "Accepted in disposable fixture" : "Rejected; materials retained"}</p>
          <p>Before: {sample.before.join(", ") || "Empty"}<br />After: {sample.after.join(", ") || "Empty"}</p>
          {sample.output && <><h3>Observed factory output: {sample.output.item_id}</h3><pre className="raw">{JSON.stringify(sample.output,null,2)}</pre></>}
        </>}<details><summary>Production probe receipt</summary><pre className="raw" data-testid="recipe-probe-receipt">{JSON.stringify(evidence,null,2)}</pre></details>
      </> : <p>No current probe evidence. Validate the exact source to run the fixtures.</p>}
    </>}
  </section>;
}
