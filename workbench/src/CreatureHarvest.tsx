import type { ContentProps } from "./ContentEditor";
import type { CreatureContext } from "./protocol";
import { itemValue, removeItemProperty } from "./item";
import { recordRow } from "./orderedRecords";
import { ScalarControl } from "./ContractControls";

const object=(v:unknown):v is Record<string,unknown>=>!!v&&typeof v==="object"&&!Array.isArray(v);

// Local projection of exact source paths only. Effective rules/defaults come
// from the game runtime; validation/references/publication stay worker-owned.
export function CreatureHarvest(p:{document:ContentProps;values:Record<string,unknown>;cap:CreatureContext["records"][number]["capability"];disabled:boolean}) {
  const {document:d,values,cap}=p, rules=cap.harvest_rules, profile=values.butcher_yield;
  const edit=(path:(string|number)[],value:unknown)=>d.onEdit(s=>itemValue(s,path,value),`Harvest ${path.join(".")}`);
  const remove=(path:(string|number)[])=>d.onEdit(s=>removeItemProperty(s,path),`Remove ${path.join(".")}`);
  const row=(path:(string|number)[],action:"add"|"remove"|"up"|"down",index:number,value={})=>d.onEdit(s=>recordRow(s,path,action,index,value),`${action} harvest record`);
  function scalar(record:Record<string,unknown>,key:string,path:(string|number)[],label:string,max:number) {
    return <label>{label}<ScalarControl schema={{type:"integer",minimum:0,maximum:max,default:rules.defaults[key]}} value={record[key]} references={{}} label={label} onChange={value=>edit([...path,key],value)}/>
      <small>{record[key]===undefined?`Absent · effective default ${rules.defaults[key]}`:"Explicit value"}</small>
      {record[key]!==undefined&&<button aria-label={`Default ${label}`} onClick={()=>remove([...path,key])}>Use default (omit)</button>}</label>;
  }
  function moves(path:(string|number)[],index:number,count:number,label:string) {
    return <div className="edit-actions">{(["up","down","remove"] as const).map(action=><button key={action} aria-label={`${action} ${label}`} disabled={action==="up"&&index===0||action==="down"&&index===count-1} onClick={()=>row(path,action,index)}>{action==="up"?"Move up":action==="down"?"Move down":"Remove"}</button>)}</div>;
  }
  function metadata(record:Record<string,unknown>,known:string[]) {
    const entries=Object.entries(record).filter(([k])=>!known.includes(k));
    return entries.length>0&&<details><summary>Preserved metadata · read-only</summary><pre className="raw">{JSON.stringify(Object.fromEntries(entries),null,2)}</pre></details>;
  }
  return <section data-testid="creature-harvest"><h3>Remains and harvest</h3><p>{cap.harvest_reason}</p><p>{rules.meaning}</p>
    <p>Output choices are saved, uniquely resolved, factory-valid definitions, including items outside editable classes. Construction is unowned; actual defeat, corpse ownership and usable rewards require ordinary play.</p>
    <fieldset disabled={p.disabled||!cap.harvest_editable}><legend>Harvest profile</legend>
      {profile===undefined?<><p>Absent: no harvest profile. A non-ephemeral Actor still leaves a corpse with default decay.</p><button onClick={()=>edit(["butcher_yield"],{})}>Add harvest profile</button></>:<>
        <button onClick={()=>remove(["butcher_yield"])}>Remove harvest profile</button>
        {!object(profile)?<p role="alert">Repair the native profile object in Source; null is invalid.</p>:<>
          <label>Corpse decay<select aria-label="Corpse decay" value={profile.decay_turns===undefined?"default":profile.decay_turns===null?"none":"timed"} onChange={e=>e.target.value==="default"?remove(["butcher_yield","decay_turns"]):edit(["butcher_yield","decay_turns"],e.target.value==="none"?null:rules.defaults.decay_turns)}><option value="default">Default · omitted</option><option value="timed">Timed · explicit countdown</option><option value="none">No decay · explicit null</option></select></label>
          {profile.decay_turns!==undefined&&profile.decay_turns!==null&&scalar(profile,"decay_turns",["butcher_yield"],"Decay turns",rules.max_decay)}
          {metadata(profile,["decay_turns","tiers"])}
          {profile.tiers!==undefined&&!Array.isArray(profile.tiers)?<p role="alert">Repair tiers in Source; expected a list.</p>:<>
            {profile.tiers===undefined&&<small>tiers absent · retained until an explicit add</small>}
            {((profile.tiers||[]) as unknown[]).map((tier,i)=>!object(tier)?<p key={i} role="alert">Repair tier {i+1} in Source.</p>:<fieldset key={i}><legend>Harvest tier {i+1}</legend>
              {scalar(tier,"min_cutting_tier",["butcher_yield","tiers",i],`Cutting threshold ${i+1}`,rules.max_tier)}
              {moves(["butcher_yield","tiers"],i,(profile.tiers as unknown[]).length,`harvest tier ${i+1}`)}
              {metadata(tier,["min_cutting_tier","yields"])}
              {tier.yields!==undefined&&!Array.isArray(tier.yields)?<p role="alert">Repair yields in Source; expected a list.</p>:<>
                {tier.yields===undefined&&<small>yields absent · a selected empty tier is a successful empty harvest</small>}
                {((tier.yields||[]) as unknown[]).map((output,j)=>!object(output)?<p key={j} role="alert">Repair output {j+1} in Source.</p>:<fieldset key={j}><legend>Output {i+1}.{j+1}</legend>
                  <label>Saved output item<ScalarControl schema={{type:"string","x-reference":"harvest_items"}} value={output.item_id} references={d.family.references} label={`Harvest item ${i+1}.${j+1}`} onChange={value=>edit(["butcher_yield","tiers",i,"yields",j,"item_id"],value)}/></label>
                  {scalar(output,"quantity_min",["butcher_yield","tiers",i,"yields",j],`Minimum quantity ${i+1}.${j+1}`,rules.max_tier)}
                  {scalar(output,"quantity_max",["butcher_yield","tiers",i,"yields",j],`Maximum quantity ${i+1}.${j+1}`,rules.max_tier)}
                  {moves(["butcher_yield","tiers",i,"yields"],j,(tier.yields as unknown[]).length,`harvest output ${i+1}.${j+1}`)}
                  {metadata(output,["item_id","quantity_min","quantity_max"])}
                </fieldset>)}
                <button disabled={Array.isArray(tier.yields)&&tier.yields.length>=rules.max_rows} onClick={()=>row(["butcher_yield","tiers",i,"yields"],"add",-1,{item_id:""})}>Add output to tier {i+1}</button>
              </>}
            </fieldset>)}
            <button disabled={Array.isArray(profile.tiers)&&profile.tiers.length>=rules.max_rows} onClick={()=>row(["butcher_yield","tiers"],"add",-1,{})}>Add harvest tier</button>
          </>}
          <small>At most {rules.max_rows} tiers and rows per tier; effective maxima per tier may total at most {rules.max_outputs} physical outputs. Order and repeated IDs are meaningful. Validate to check the complete effective ranges and saved references.</small>
        </>}
      </>}
    </fieldset>
  </section>;
}
