import { effectiveValue, type FieldSchema, type ContentFamily, type References } from "./content";

export function ScalarControl(p: {schema: FieldSchema; value: unknown; references: References; label?: string; disabled?: boolean; onChange: (value: string | number | boolean) => void}) {
  const s = p.schema, value = effectiveValue(s, p.value), label = p.label || s.title || "Value";
  const common = {"aria-label":label, disabled:p.disabled || s.readOnly};
  const invalid = p.value !== undefined && (s.type === "boolean" ? typeof p.value !== "boolean" : s.type === "string" ? typeof p.value !== "string" : typeof p.value !== "number" || !Number.isFinite(p.value));
  if (s.type === "boolean") return <><input {...common} type="checkbox" checked={value === true} aria-invalid={invalid} onChange={e=>p.onChange(e.target.checked)} />{invalid && <small>Invalid explicit value: {JSON.stringify(p.value)}. Repair or deliberately replace it.</small>}</>;
  if (s["x-reference"]) return <select {...common} value={typeof value === "string" ? value : ""} aria-invalid={invalid} onChange={e=>p.onChange(e.target.value)}>
    <option value={typeof value === "string" ? value : ""}>{typeof value === "string" ? value : p.value === undefined ? "Absent" : `Invalid: ${JSON.stringify(p.value)}`}</option>
    {(p.references[s["x-reference"]] || []).filter(r=>r.id!==value).map(r=><option key={r.id} value={r.id}>{r.label}</option>)}
  </select>;
  if (s.type === "string") return s["x-control"] === "multiline"
    ? <textarea {...common} value={typeof value === "string" ? value : ""} aria-invalid={invalid} onChange={e=>p.onChange(e.target.value)} />
    : <input {...common} value={typeof value === "string" ? value : ""} aria-invalid={invalid} onChange={e=>p.onChange(e.target.value)} />;
  return <input {...common} type="number" min={s.minimum} max={s.maximum} step={s.type === "integer" ? 1 : "any"} value={typeof value === "number" ? value : ""} aria-invalid={invalid}
    onChange={e=>{if(e.target.value !== "" && Number.isFinite(Number(e.target.value))) p.onChange(Number(e.target.value));}} />;
}

export function ContractFields(p: {family: ContentFamily; values: Record<string,unknown>; view?: string; onChange: (path: (string|number)[], value: unknown)=>void}) {
  return <>{Object.entries(p.family.descriptor.schema.properties || {}).filter(([,s])=>!s.readOnly && !["array","object"].includes(s.type) && s["x-view"]===p.view).map(([key,s])=><label key={key}>
    {s.title || key}<ScalarControl schema={s} value={p.values[key]} references={p.family.references} onChange={value=>p.onChange([key],value)} />
    {p.values[key] === undefined && <small>{s.default === undefined ? "Absent in source" : `Absent in source · effective default: ${String(s.default)}`}</small>}
    {s.description && <small>{s.description}</small>}
    {p.values[key] === null && <small>Explicit null retained; validate or repair in Source.</small>}
  </label>)}</>;
}
