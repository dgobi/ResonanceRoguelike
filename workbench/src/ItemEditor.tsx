import { ContractFields, ScalarControl, OrderedRecords, KeyedNumberMap } from "./ContractControls";
import { rowDefaults, type ContentFamily } from "./content";
import { useMemo, useState } from "react";
import { itemModel, itemValue, keywordEntry } from "./item";
import type { ItemContext, ItemTrail } from "./protocol";

export function ItemEditor(p: {
  family: ContentFamily; variant:boolean; evidenceStale: boolean; draft: string; path: string; context?: ItemContext; selectedId?: string; dirty: boolean; validated: boolean;
  disabled: string; busy: boolean; onCancel: () => void; onReturn?: () => void; returnLabel?: string; trail?: ItemTrail | null;
  onRecipe?: (id: string, path: string) => void;
  onItem?: (id:string,path:string)=>void;
  onPool?: (id: string) => void; onSource: () => void; onProbe: () => void;
  onEdit: (edit: (text: string) => string, label: string) => void;
  onUndo: () => void; onRedo: () => void; canUndo: boolean; canRedo: boolean;
}) {
  const parsed = useMemo(() => itemModel(p.draft), [p.draft]);
  const record = p.context?.records.find(r => r.id === p.selectedId) || p.context?.records[0];
  const cap = record?.capability;
  const values = parsed.model || record?.definition || {};
  const [view, setView] = useState("Properties"), [tag, setTag] = useState("");
  const reason = p.disabled || parsed.reason || (!cap?.editable ? cap?.reason || "Capability unavailable." : "");
  const evidenceCurrent = !p.evidenceStale && (!p.dirty || p.validated);
  const edit = (path: (string | number)[], value: unknown) => p.onEdit(s => itemValue(s, path, value), "Edit item property");
  const keywords = values.keywords === undefined ? [] : values.keywords;
  const keywordShape = Array.isArray(keywords) && keywords.every(k => k && typeof k === "object" && !Array.isArray(k));
  const sourceJump = () => p.onSource();
  return <section className="item-editor" data-testid="item-editor">
    <div className="pane-heading"><div><h2>Item definition</h2><code>{String(values.id || record?.id || "Invalid source")} · {p.path}</code></div>
      <div className="edit-actions">{p.onReturn && <button onClick={p.onReturn} disabled={p.busy}>{p.returnLabel || "Return to pool"}</button>}
      {p.busy && <button onClick={p.onCancel} disabled={p.disabled === "Publication in progress."}>Cancel authoring request</button>}</div></div>
    {p.trail && <nav className="source-trail" aria-label="Item source trail">
      {p.trail.structure && <code>{p.trail.structure.sourcePath} → special_tiles[{p.trail.structure.index}] ({p.trail.structure.x}, {p.trail.structure.y})</code>}
      <button disabled={p.busy} onClick={p.onReturn}>Pool {p.trail.poolId} · entry {p.trail.index + 1}</button>
      <code>{p.trail.path} → items[{p.trail.index}].item_id = {p.trail.itemId}</code>
      <small>Declared reference when opened. Pool and structure drafts retained; item publication changes no references.</small>
    </nav>}
    <div className="tabs">{p.family.descriptor.views.map(key=>({"item-properties":"Properties",references:"References",recipes:"Recipes","use-binding":"Use binding",factory:"Factory result"})[key]).filter((v):v is string=>!!v).map(v => <button key={v} className={view === v ? "active" : ""} onClick={() => setView(v)}>{v}</button>)}<button onClick={sourceJump}>Show source</button></div>
    {reason && <p className="notice warning" data-testid="item-disabled">{reason}</p>}
    {!evidenceCurrent && <p className="notice">References, use binding and factory evidence below belong to the opened source. Validate the exact draft to refresh them.</p>}
    {view === "Properties" && <>
      <div className="edit-actions"><button onClick={p.onUndo} disabled={!!reason || !p.canUndo}>Undo item</button><button onClick={p.onRedo} disabled={!!reason || !p.canRedo}>Redo item</button><small>Raw source and variant-ID edits clear item history.</small></div>
      <p className="muted">{cap?.reason}. Category: {String(values.category ?? "not declared")} · appearance: {String(values.tile ?? "factory default")}</p>
      {cap?.editable ? <fieldset disabled={!!reason} className="item-properties"><legend>Common item properties · {cap.supply_class}</legend>
        <ContractFields family={p.family} values={values} onChange={edit} />
        {cap.supply_class && cap.supply_class!=="material" && <><h3>{cap.supply_class} use</h3><ContractFields family={p.family} values={values} view={cap.supply_class} disabledFields={p.variant ? [] : ["slot"]} nullableFields={["nutrition","hydration","heal_amount","eat_message","drink_message","empty_form"]} onChange={edit}/></>}
        {cap.equipment_class==="armour" && <><p>1–32 layers. Name and material are presentation; AV is summed. Coverage and preserved row metadata are read-only and do not select protected body parts.</p><OrderedRecords family={p.family} values={values} view="armour" disabled={!!reason} onEdit={p.onEdit}/></>}
        {cap.equipment_class==="satchel" && p.family.descriptor.schema.properties?.weight_reductions && <KeyedNumberMap family={p.family} field="weight_reductions" schema={p.family.descriptor.schema.properties.weight_reductions} value={values.weight_reductions} disabled={!!reason} onEdit={p.onEdit}/>}
        {record?.equipment && <section data-testid="equipment-definition"><p>{evidenceCurrent ? "Validated definition interpretation" : "Opened definition; validate edits"} · {record.equipment.equipment_class} · {record.equipment.slot}</p>
          <p>{record.equipment.explanation}</p>{record.equipment.base_range && <p>Declared base damage: {record.equipment.base_range.join("–")}</p>}{record.equipment.summed_av!==undefined && <p>Summed equipped AV contribution: {record.equipment.summed_av}</p>}
          <small>{record.equipment.scope}</small><details><summary>Retained behavior and definition evidence</summary><pre className="raw">{JSON.stringify(record.equipment,null,2)}</pre></details></section>}
        {record?.effective_use && <p className="notice" data-testid="effective-dose">{evidenceCurrent ? "Validated saved-input interpretation: " : "Opened-source interpretation; validate edits: "}{record.effective_use.explanation}</p>}
        {record?.return_item && <p className="notice">Saved return: <button disabled={p.busy || !evidenceCurrent} onClick={()=>p.onItem?.(record.return_item!.id,record.return_item!.path)}>Open return {record.return_item.id}</button><small>{record.return_item.label} · {record.return_item.editable ? "Editable source" : "Reference-only source"}</small></p>}
        {p.family.descriptor.schema.properties?.keywords && <><h3>Keywords</h3><small>{cap.tier_note}</small>
        {keywordShape ? <table className="pool-table"><thead><tr><th>Tag ID</th><th>Tier</th><th>Action</th></tr></thead><tbody>{keywords.map((kw, i) => <tr key={i}>
          {Object.entries(p.family.descriptor.schema.properties?.keywords.items?.properties || {}).map(([key,schema])=><td key={key}><ScalarControl schema={schema} value={kw[key]} references={p.family.references} label={`${schema.title} ${i+1}`} onChange={value=>edit(["keywords",i,key],value)} /></td>)}
          <td><button onClick={() => p.onEdit(s => keywordEntry(s, i), "Remove keyword")}>Remove keyword {i+1}</button></td></tr>)}</tbody></table> : <p className="notice warning">Repair keywords in Source; expected an array of records.</p>}
          <div className="edit-actions"><label>Add keyword<select aria-label="New keyword" value={tag} onChange={e => setTag(e.target.value)}><option value="">Choose tag ID</option>{(p.family.references[p.family.descriptor.schema.properties?.keywords.items?.properties?.tag["x-reference"] || ""] || []).map(r => <option key={r.id} value={r.id}>{r.label}</option>)}</select></label>
          <button disabled={!keywordShape || !tag} onClick={() => p.onEdit(s => keywordEntry(s, -1, tag, rowDefaults(p.family.descriptor.schema.properties!.keywords, tag)), "Add keyword")}>Add keyword</button></div></>}
      </fieldset> : <pre className="raw">{JSON.stringify(record?.definition, null, 2)}</pre>}
      <p className="muted small">Unknown fields and nested data remain in Source. IDs are the machine identity; renaming the display name does not change references.</p>
      <p className="muted small">Category and use identity stay fixed to the original source. Harvest/gather metadata does not enroll variants in discovery. Liquid metadata does not enable partial-volume drinking. Saving a variant does not migrate owned instances. Reset keeps its captured inputs; Test latest saved version captures saved revisions.</p>
    </>}
    {view === "References" && <><h3>Referenced by pools · declared JSON references</h3>
      <p className="muted small">Saved contextual pool files only. This is not an acquisition or world-selection guarantee.</p>
      {!record?.pools.length && <p>No saved pool references. This item may be unreferenced.</p>}
      <table className="pool-table"><tbody>{record?.pools.map(r => <tr key={r.path+r.pointer+r.index}><td><button disabled={!r.unique || !!r.pointer || p.busy} onClick={() => p.onPool?.(r.id)}>{r.id}</button><code>{r.path}{r.pointer}</code></td><td>{r.field}</td></tr>)}</tbody></table>
      <h3>Dependencies</h3><table className="pool-table"><thead><tr><th>Evidence</th><th>Reference</th><th>Source / field</th></tr></thead><tbody>{record?.dependencies.map((r,i) => <tr key={i}><td>{r.kind}{r.resolved !== undefined && <small>{r.resolved ? "Reference ID validated" : "Unresolved reference"}</small>}</td><td>{String(r.id)}</td><td>{r.field}<small>{r.paths?.join(", ")}</small><small>{r.note}</small></td></tr>)}</tbody></table></>}
    {view === "Recipes" && <><p>Opened item/source snapshot. Exact declared output references and potential ingredient predicates are distinct from availability or successful crafting.</p>
      {[true,false].map(produces=><section key={String(produces)}><h3>{produces ? "Produces this item" : "Potential ingredient matches"}</h3><table className="pool-table"><thead><tr><th>Recipe / source</th><th>Evidence</th><th>Execution class</th></tr></thead><tbody>{record?.recipes?.filter(r=>produces ? r.produces : r.fields.length>0).map(r=><tr key={r.path+r.pointer}><td><button data-recipe-link={r.path} data-recipe-relation={produces ? "output" : "ingredient"} disabled={p.busy} onClick={()=>p.onRecipe?.(r.id,r.path)}>{r.id}</button><code>{r.path}{r.pointer}</code></td><td>{produces ? "Declared result_item reference" : "Potential tag match"}<small>{produces ? "Exact item ID" : r.fields.join(", ")}</small></td><td>{r.execution_class}</td></tr>)}</tbody></table></section>)}<p>Tag/tier predicates only. Quantities, reusable-material choices, knowledge, access and ambient conditions are unverified.</p></>}
    {view === "Use binding" && <><h3>{record?.use.status || "Unavailable"}</h3><dl><dt>Declared on_use</dt><dd>{record?.use.present===false ? "Absent" : JSON.stringify(record?.use.declared ?? null)}</dd><dt>Validated effective binding</dt><dd>{String(record?.use.effective ?? "None")}</dd><dt>Actual consumer</dt><dd>{record?.use.consumer}</dd><dt>Handler</dt><dd>{record?.use.handler || "None"}{record?.use.line ? ` · source line ${record.use.line}` : ""}</dd></dl><p>{record?.use.scope}</p>{record?.use.notes.map(n => <p className="notice" key={n}>{n}</p>)}<p>Ordinary interactive use was not executed.</p></>}
    {view === "Factory result" && <><button disabled={p.busy || !cap?.editable || !!parsed.reason} onClick={p.onProbe}>Validate and construct exact item</button>{record?.factory && evidenceCurrent ? <><h3>Unowned factory construction</h3><p>{record.factory.consumer}</p><p>{record.factory.scope}</p><code>{record.factory.path} · exact source {record.factory.definition_sha256.slice(0,12)}<br />Game {record.factory.source.game_source_sha256.slice(0,12)} · catalogue {record.factory.source.catalog_sha256?.slice(0,12)}</code>
      <small>Observed {record.factory.observed_at_utc} · loaded catalogue {record.factory.loaded_catalog_sha256.slice(0,12)}</small>
      <table className="pool-table"><thead><tr><th>Property</th><th>Stored declaration</th><th>Factory instance</th></tr></thead><tbody>{record.factory.comparisons.map(r => <tr key={r.field}><td>{r.field}</td><td>{r.present===false ? "Absent" : JSON.stringify(r.declared)}</td><td>{JSON.stringify(r.instance)} · {r.equal ? r.present===false ? "factory default" : "matches" : "differs"}</td></tr>)}</tbody></table>
      <details><summary>Factory receipt</summary><pre className="raw" data-testid="item-factory-receipt">{JSON.stringify(record.factory,null,2)}</pre></details></> : <p>No current factory result. Validate the draft or repair the source diagnostics.</p>}</>}
  </section>;
}
