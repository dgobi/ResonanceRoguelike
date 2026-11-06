import { ScalarControl } from './ContractControls';
import type { ContentFamily } from './content';

export function MaterialResponseFields(p:{family:ContentFamily;values:Record<string,unknown>;disabled:boolean;
  onChange:(path:(string|number)[],value:unknown)=>void}) {
  const raw=p.values.material_response;
  const value=raw && typeof raw==='object' && !Array.isArray(raw)?raw as Record<string,unknown>:null;
  const schema=p.family.descriptor.schema.properties?.material_response;
  if(!schema)return null;
  return <fieldset disabled={p.disabled}><legend>Material contact response</legend>
    <p>Mark exactly one quantity-one component as primary. Its exact saved tag tier selects the lower or higher contact band; this replaces the output dose's base contacts. Coating doses cannot be primary materials.</p>
    {!value?<button onClick={()=>p.onChange(['material_response'],{version:1,primary_role:'primary',tag:'binding',high_tier:2,low_hits:6,high_hits:12})}>Enable material response</button>:<>
      {Object.entries(schema.properties||{}).filter(([,s])=>!s.readOnly).map(([key,s])=><label key={key}>{s.title}<ScalarControl schema={s} references={p.family.references} value={value[key]} onChange={v=>p.onChange(['material_response',key],v)}/></label>)}
    </>}
  </fieldset>;
}
