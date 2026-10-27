import type { ItemContext, RecipeContext } from "./familyData";

export type FieldSchema = {
  $schema?: string; type: "string" | "number" | "integer" | "boolean" | "object" | "array";
  title?: string; description?: string; default?: string | number | boolean; readOnly?: boolean;
  minimum?: number; maximum?: number; properties?: Record<string, FieldSchema>; required?: string[];
  items?: FieldSchema; additionalProperties?: boolean;
  "x-control"?: "scalar" | "multiline" | "ordered-table"; "x-reference"?: string; "x-view"?: string; "x-initial"?: string | number | boolean;
};
export type Descriptor = {
  vocabulary: string; schema: FieldSchema; views: string[];
  policy: {operations: ("edit" | "variant")[]; root: string; identity: "id"}; publication_note: string;
};
export type References = Record<string, {id: string; label: string}[]>;
type CommonFamily = {contract: string; descriptor_sha256: string; descriptor: Descriptor; compatible: boolean; problems: string[]; references: References};
export type ContentFamily = CommonFamily & ({id: "item"; context: ItemContext | null} | {id: "recipe"; context: RecipeContext | null});

const object = (value: unknown): value is Record<string, unknown> => !!value && typeof value === "object" && !Array.isArray(value);
const schemaKeys = new Set(["$schema","type","title","description","default","readOnly","minimum","maximum","properties","required","items","additionalProperties","x-control","x-reference","x-view","x-initial"]);
export function schemaProblem(value: unknown, path = "schema", depth = 0): string {
  if (!object(value) || depth > 4) return `${path}: expected bounded schema object`;
  for (const key of Object.keys(value)) if (!schemaKeys.has(key)) return `${path}: unsupported schema keyword ${key}`;
  if (!["string","number","integer","boolean","object","array"].includes(String(value.type))) return `${path}: unsupported type`;
  if (value["x-control"] !== undefined && !["scalar","multiline","ordered-table"].includes(String(value["x-control"]))) return `${path}: unsupported control`;
  if (value.type === "object" && depth !== 0 && depth !== 2) return `${path}: only root and table-row objects are supported`;
  if (value.type === "array" && (depth !== 1 || value["x-control"] !== "ordered-table")) return `${path}: only registered ordered tables are supported`;
  if (value["x-control"] === "multiline" && value.type !== "string") return `${path}: multiline requires a string`;
  if (value["x-reference"] !== undefined && value.type !== "string") return `${path}: reference requires a string`;
  for (const key of ["default","x-initial"]) if (value[key] !== undefined && (value.type === "string" ? typeof value[key] !== "string" : value.type === "boolean" ? typeof value[key] !== "boolean" : value.type === "number" ? typeof value[key] !== "number" || !Number.isFinite(value[key]) : value.type === "integer" ? !Number.isSafeInteger(value[key]) : true)) return `${path}: unsupported or mismatched ${key}`;
  for (const key of ["title","description","x-reference","x-view"]) if (value[key] !== undefined && typeof value[key] !== "string") return `${path}: invalid ${key}`;
  for (const key of ["minimum","maximum"]) if (value[key] !== undefined && (typeof value[key] !== "number" || !Number.isFinite(value[key]))) return `${path}: invalid ${key}`;
  if (value.readOnly !== undefined && typeof value.readOnly !== "boolean") return `${path}: invalid readOnly`;
  if (value.type === "object") {
    if (!object(value.properties) || Object.keys(value.properties).length > 64) return `${path}: invalid properties`;
    if (value.required !== undefined && (!Array.isArray(value.required) || value.required.some(k => typeof k !== "string" || !(k in (value.properties as Record<string,unknown>))))) return `${path}: invalid required`;
    for (const [key, child] of Object.entries(value.properties)) { const problem = schemaProblem(child, `${path}.${key}`, depth+1); if (problem) return problem; }
  }
  if (value.type === "array") return schemaProblem(value.items, `${path}[]`, depth+1);
  return "";
}
export function familyProblem(value: unknown): string {
  if (!object(value) || !["item","recipe"].includes(String(value.id))) return "Unregistered content family";
  if (typeof value.contract !== "string" || typeof value.descriptor_sha256 !== "string" || !/^[a-f0-9]{64}$/.test(value.descriptor_sha256)) return "Malformed family identity";
  if (!object(value.descriptor)) return "Missing descriptor";
  const d = value.descriptor;
  if (d.vocabulary !== "resonance-controls-1" || !object(d.schema) || d.schema.$schema !== "https://json-schema.org/draft/2020-12/schema") return "Unsupported descriptor/control vocabulary";
  if (!object(d.policy) || d.policy.identity !== "id" || typeof d.policy.root !== "string" || !Array.isArray(d.policy.operations) || d.policy.operations.some(op=>op!=="edit" && op!=="variant")) return "Unsupported publication policy";
  if (!Array.isArray(d.views) || d.views.some(v=>typeof v!=="string") || typeof d.publication_note !== "string") return "Malformed view registration";
  const views = value.id === "item" ? ["item-properties","references","recipes","use-binding","factory"] : ["recipe-requirements","output","production-receipt"];
  if (d.views.some(v=>!views.includes(String(v)))) return "Unsupported specialized view registration";
  if (!object(value.references) || Object.values(value.references).some(rows=>!Array.isArray(rows) || rows.length>10000 || rows.some(r=>!object(r) || typeof r.id!=="string" || typeof r.label!=="string"))) return "Malformed reference provider";
  if (!Array.isArray(value.problems) || value.problems.some(p=>typeof p!=="string") || typeof value.compatible!=="boolean") return "Malformed capability result";
  if (!value.compatible) return value.problems.join("; ") || "Incompatible descriptor";
  if (value.context !== null && (!object(value.context) || !Array.isArray(value.context.records) || value.context.records.length>10000 || value.context.records.some(r=>!object(r) || !object(r.definition) || !object(r.capability) || !Array.isArray(r.diagnostics)))) return "Malformed family context";
  return schemaProblem(d.schema);
}

// Display defaults without inserting them into the exact-source draft. Explicit
// null and wrong types stay visible as invalid values, never become defaults.
export function effectiveValue(schema: FieldSchema, value: unknown): unknown {
  return value === undefined ? schema.default : value;
}
export function rowDefaults(schema: FieldSchema, tag: string): Record<string, unknown> {
  const values: Record<string,unknown> = {tag};
  for (const [key, field] of Object.entries(schema.items?.properties || {})) {
    const initial = field["x-initial"] ?? field.default;
    if (key !== "tag" && initial !== undefined) values[key] = initial;
  }
  return values;
}
