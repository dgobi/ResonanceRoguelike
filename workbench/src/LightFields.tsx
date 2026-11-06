import { ScalarControl } from './ContractControls';
import type { ContentFamily } from './content';

export function LightFields(p:{family:ContentFamily;values:Record<string,unknown>;
  onChange:(path:(string|number)[],value:unknown)=>void}) {
  const value=p.values.light as Record<string,unknown>;
  const schema=p.family.descriptor.schema.properties?.light;
  if(!schema || !value || typeof value!=='object')return null;
  return <fieldset><legend>Cosmetic light</legend>
    <p>Falloff and flicker affect appearance within the mechanical footprint. Inherited color and visual radius stay fixed. Use, offhand ownership, fuel consumption and heat tier stay fixed to the source.</p>
    {Object.entries(schema.properties||{}).map(([key,s])=><label key={key}>{s.title}<ScalarControl schema={s} references={p.family.references} value={value[key]} onChange={v=>p.onChange(['light',key],v)}/></label>)}
  </fieldset>;
}
