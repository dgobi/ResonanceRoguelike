import { ScalarControl } from './ContractControls';
import type { ContentFamily } from './content';

export function VesselFields(p:{family:ContentFamily;values:Record<string,unknown>;process?:boolean;disabled:boolean;
  onChange:(path:(string|number)[],value:unknown)=>void;onEnable?:()=>void}) {
  const field=p.process?'vessel_process':'vessel', raw=p.values[field];
  const value=raw && typeof raw==='object' && !Array.isArray(raw)?raw as Record<string,unknown>:null;
  const schema=p.family.descriptor.schema.properties?.[field];
  if(!schema)return null;
  const keywords=Array.isArray(p.values.keywords)?p.values.keywords as {tag:string;tier:number}[]:[];
  return <fieldset disabled={p.disabled}><legend>{p.process?'Vessel-backed preparation':'Water vessel'}</legend>
    {!value?<><p>No registered vessel capability. Tags alone do not grant capacity.</p>
      {p.onEnable&&<button onClick={p.onEnable}>Enable water vessel</button>}</>:<>
      <p>{p.process?'Owns the selected vessel until completion or abandonment. Exact water batch; bone tincture or a material-sensitive weapon wash.':'Water only; nonstackable reusable instances. Saved capacity and water survive definition edits.'}</p>
      {Object.entries(schema.properties||{}).filter(([key])=>!['version','contents'].includes(key)).map(([key,s])=><label key={key}>{s.title}<ScalarControl schema={s} references={p.family.references} value={value[key]} onChange={v=>p.onChange([field,key],v)}/></label>)}
      {!p.process&&<label><input aria-label="Heat-suitable vessel" type="checkbox" checked={keywords.some(k=>k.tag==='heatproof'&&k.tier>=1)} onChange={e=>p.onChange(['keywords'],[...keywords.filter(k=>k.tag!=='heatproof'),...(e.target.checked?[{tag:'heatproof',tier:1}]:[])])}/>Heat-suitable vessel</label>}
    </>}
  </fieldset>;
}
