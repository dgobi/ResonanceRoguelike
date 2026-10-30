import { useEffect, useRef, useState } from "react";
import { creatureModel, creatureValue } from "./creature";
import { request, asFailure, type Inspection } from "./protocol";
import type { ContentProps } from "./ContentEditor";
import { CreatureHarvest } from "./CreatureHarvest";

export function CreatureEditor(p: ContentProps) {
  const context=p.family.id==="creature" ? p.family.context : null;
  const original=p.sourceFamily.id==="creature" ? p.sourceFamily.context : null;
  const record=context?.records.find(r=>r.id===p.navigation.selectedId)||context?.records[0];
  const cap=original?.records[0]?.capability;
  const parsed=creatureModel(p.draft), values=parsed.model||record?.definition||{};
  const reason=p.disabled||parsed.reason;
  const [view,setView]=useState("Supported fields"),[reference,setReference]=useState<Inspection|null>(null),[error,setError]=useState("");
  const generation=useRef(0);
  useEffect(()=>{generation.current++;setReference(null);return()=>{generation.current++;};},[p.active,p.path,p.cancelVersion]);
  const observed=(!p.dirty||p.validated)&&!p.evidenceStale ? record?.factory : null;
  const currentRefs=!p.evidenceStale&&(!p.dirty||p.validated);
  const get=(key:string,fallback:unknown)=>{
    const v=key.split(".").reduce<unknown>((v,k)=>v&&typeof v==="object" ? (v as Record<string,unknown>)[k] : undefined,values);
    return v===undefined ? fallback : v;
  };
  const edit=(key:string,value:string|number|boolean)=>p.onEdit(s=>creatureValue(s,key,value),`Creature ${key}`);
  function number(key:string,label:string,fallback:number,step=1) {
    const value=get(key,fallback), bounds=cap?.bounds[key]||[0,1000000];
    return <label key={key}>{label}<input aria-label={label} type="number" min={bounds[0]} max={bounds[1]} step={step} value={typeof value==="number" ? value : ""} onChange={e=>{if(e.target.value!=="")edit(key,Number(e.target.value));}}/><small>{bounds[0]}–{bounds[1]}{step===1 ? ", integer" : ", finite"}</small></label>;
  }
  function text(key:string,label:string,fallback:string,maxLength:number) {
    const value=get(key,fallback);
    return <label>{label}<input aria-label={label} maxLength={maxLength} value={typeof value==="string"?value:""} onChange={e=>edit(key,e.target.value)}/></label>;
  }
  async function inspectReference(path:string) {
    const version=++generation.current;setReference(null);setError("");const lease=p.beginRequest("Inspecting layout reference…");
    try {const r=await request<Inspection>("inspect",{asset:path});if(lease.current()&&version===generation.current)setReference(r.result);}
    catch(e){if(lease.current()&&version===generation.current)setError(asFailure(e).message);}finally{lease.finish();}
  }
  return <section className="item-editor" data-testid="creature-editor">
    <div className="pane-heading"><div><h2>Creature definition</h2><code>{String(values.id||record?.id||"Invalid source")} · {p.path}</code></div>{p.busy&&<button onClick={p.onCancel}>Cancel authoring request</button>}</div>
    <div className="tabs">{["Supported fields","Harvest","Read-only fields","References","Factory result"].map(v=><button key={v} className={view===v?"active":""} onClick={()=>setView(v)}>{v}</button>)}<button onClick={p.onSource}>Show source</button></div>
    <p>{cap?.reason}</p><p>{cap?.body_note}. {cap?.special_binding ? `Special binding: ${cap.special_binding} (stable ID). Sight does not change its separate ability radius.` : "No ID-bound special ability."}</p>
    {cap?.duplication_reason&&<p className="notice">{cap.duplication_reason}</p>}
    {reason&&<p className="notice warning">{reason}</p>}
    {view==="Supported fields"&&<>
      {cap?.editable&&<><div className="edit-actions"><button disabled={!!reason||!p.canUndo} onClick={p.onUndo}>Undo creature</button><button disabled={!!reason||!p.canRedo} onClick={p.onRedo}>Redo creature</button></div>
      <fieldset className="item-properties" disabled={!!reason}><legend>Identity and prose</legend>
        {text("name","Creature name",String(values.id||""),256)}
        <label>Description<textarea aria-label="Creature description" maxLength={8192} value={typeof values.description==="string"?values.description:""} onChange={e=>edit("description",e.target.value)}/></label>
        <small>Literal text; Player is a reserved name. Description resolves through this stable ID.</small>
      </fieldset>
      <fieldset className="item-properties" disabled={!!reason}><legend>Health and attack</legend>
        <label>Effective maximum HP<input aria-label="Effective HP" type="number" min={1} max={1000000} step={1} value={Number(get("base_hp",get("fighter.max_hp",10)))} onChange={e=>{if(e.target.value!=="")edit("hp",Number(e.target.value));}}/></label>
        <small>{cap.hp_note}</small>{number("armour_value","Natural armour",0)}
        {text("damage_dice","Damage dice","1d4",6)}<small>Strict NdM: count 1–20; sides 1–100. Put addition in the separate bonus.</small>
        {number("damage_bonus","Damage bonus",0)}{text("attack_verb","Attack verb","strikes at thee",256)}
      </fieldset>
      <fieldset className="item-properties" disabled={!!reason}><legend>Perception and movement</legend>
        {number("perception.sight_radius","Sight radius",8)}
        {number("perception.hearing_radius","Hearing radius",5)}
        <small>Zero disables hearing. Mobile wandering/circling creatures investigate local sounds after losing a genuine player trail. Walls block and closed doors attenuate. Ambush and fleeing archetypes retain their special behavior.</small>
        <label>Sees in dark<input aria-label="Sees in dark" type="checkbox" checked={get("perception.sees_in_dark",false)===true} onChange={e=>edit("perception.sees_in_dark",e.target.checked)}/></label>
        {number("wander_radius","Wander radius",8)}{number("pursuit_timeout","Pursuit timeout",20)}{number("speed","Speed",1,0.01)}
        <label>AI class<select aria-label="Creature AI" disabled={!p.variant||!cap.duplicable} value={String(get("ai_type","wandering"))} onChange={e=>edit("ai_type",e.target.value)}>{cap.ai_types.map(id=><option key={id}>{id}</option>)}</select></label>
        <small>AI choice is available only for an ordinary new-ID variant. Speed supports at most two actions per turn.</small>
      </fieldset></>}
      <p className="notice">{p.sourceFamily.descriptor.publication_note}</p>
      <details><summary>Saved actors and read-only behavior</summary><p>Restoration constructs from the current definition, then reapplies stored component snapshots. Name, current/max HP, natural armour, saved sight/hearing/darkvision and wander radius retain stored values. Older rows missing a field keep existing factory fallback semantics. No running game cache or saved actor is rewritten.</p><p>Identity, same-ID AI, body structure, tile and special settings remain fixed. An ordinary variant has its deliberately selected AI and no inherited special binding.</p></details>
    </>}
    {view==="Harvest"&&cap&&<><div className="edit-actions"><button disabled={!!reason||!p.canUndo} onClick={p.onUndo}>Undo creature</button><button disabled={!!reason||!p.canRedo} onClick={p.onRedo}>Redo creature</button></div><CreatureHarvest document={p} values={values} cap={cap} disabled={!!reason}/></>}
    {view==="Read-only fields"&&<><p>fighter.power and fighter.defense are legacy/fallback values. Damage dice/bonus and natural armour are the effective controls.</p><p>Hearing drives finite local investigation for mobile wandering/circling creatures; ambush and fleeing archetypes retain their special rules. Current AI does not call Perception.is_hostile_to; faction and hostility membership do not promise targeting behavior, and an empty hostility list defaults in its constructor.</p><p>Bodies, corpse presentation, essence, abilities/effects, ranged blocks, spawn metadata, transition flags, callouts and unknown metadata stay exact. Harvest controls require the original non-ephemeral Actor entitlement.</p>{Object.entries(values).filter(([key])=>!["id","name","description","base_hp","armour_value","damage_dice","damage_bonus","attack_verb","wander_radius","pursuit_timeout","speed"].includes(key)).map(([key,value])=><details key={key}><summary>{key}{key==="fighter"||key==="perception"?" · only named common fields are editable":""}</summary><pre className="raw">{JSON.stringify(value,null,2)}</pre></details>)}</>}
    {view==="References"&&<><p>{context?.selection}</p>{!currentRefs?<p className="notice">Reference snapshot is stale. Validate or reopen.</p>:<>
      <table className="pool-table"><tbody>{record?.references.map(r=><tr key={r.path+r.field}><td>{r.route==="authored_submap"?<button disabled={p.busy} onClick={()=>void inspectReference(r.path)}>Inspect layout {r.id}</button>:<strong>Zone {r.id} · read-only</strong>}<code>{r.path}</code></td><td>{r.field}<small>{r.evidence}</small></td></tr>)}</tbody></table>
      {!record?.references.length&&<p>No saved inbound declarations found.</p>}
      <h3>Source dependencies</h3><table className="pool-table"><tbody>{record?.dependencies.map(r=><tr key={r.field}><td>{r.field}<code>{JSON.stringify(r.id)}</code></td><td>{r.active?(r.resolved?"Resolved":"Missing or ambiguous") : "Inactive / informational"}<small>{r.paths.join(", ")}</small></td><td>{r.kind}<small>{r.note}</small></td></tr>)}</tbody></table>
    </>}{error&&<p role="alert">{error}</p>}{reference&&<details open><summary>Read-only layout · {reference.path}</summary><code>{reference.sha256}</code><pre className="raw">{reference.raw}</pre></details>}</>}
    {view==="Factory result"&&<><button disabled={p.busy||!cap?.constructible||!!parsed.reason} onClick={p.onProbe}>Validate and construct exact creature</button>{observed?<><h3>Observed factory actor</h3><p>{observed.actor_class} · {observed.creature_id}</p><p>{observed.scope}</p><p>Special binding: {observed.special_binding||"none"}. Ability execution is not established by construction.</p><code>{observed.path}<br/>Source {observed.source_sha256}<br/>Game {observed.source.game_source_sha256}</code><details open><summary>Factory receipt</summary><pre className="raw" data-testid="creature-factory-receipt">{JSON.stringify(observed,null,2)}</pre></details></>:<p>No current construction result; validate the exact source/draft.</p>}</>}
  </section>;
}
