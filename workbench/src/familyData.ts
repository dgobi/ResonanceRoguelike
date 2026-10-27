import type { Diagnostic, Source } from "./protocol";
export type TextContext = {
  records: {id:string; pointer:string; definition:Record<string,unknown>; diagnostics:Diagnostic[];
    capability:{contract:string; editable:boolean; reason:string}; references:{path:string; pointer:string; kind:string}[]}[];
  reference_coverage:string; inspection_note:string; binding_note:string;
};
export type ReaderFrame = {
  kind:"reader-frame"; image:string; image_sha256:string; width:number; height:number; inputs:{page:number;scroll:number};
  page:number;scroll:number;max_scroll:number;viewport_height:number;visible_rows:number[];total_rows:number;marker_types:string[];
  draft_sha256:string;path:string;source:Source;contract:string;descriptor_sha256:string;runtime:{python:string;dependencies:Record<string,string>};
  observed_at_utc:string;setup:string;consumer:string;dependencies:string;
};
export type FamilyPreview = ReaderFrame;
export function previewProblem(value: unknown): string {
  if (!value || typeof value !== "object") return "Missing preview";
  const v=value as Partial<ReaderFrame>;
  if(v.kind!=="reader-frame" || typeof v.image!=="string" || v.image.length>2800000 || !/^data:image\/png;base64,[A-Za-z0-9+/]+=*$/.test(v.image)) return "Invalid bounded PNG preview";
  if(v.width!==960 || v.height!==640 || !v.inputs || ![v.page,v.scroll,v.max_scroll,v.viewport_height,v.total_rows,v.inputs.page,v.inputs.scroll].every(n=>Number.isSafeInteger(n) && Number(n)>=0)) return "Malformed preview coordinates";
  if(![v.image_sha256,v.draft_sha256,v.descriptor_sha256].every(h=>typeof h==="string" && /^[a-f0-9]{64}$/.test(h)) || !v.source || typeof v.contract!=="string" || typeof v.setup!=="string") return "Malformed preview identity";
  return "";
}
export type FactoryResult = {item_id: string; instance: Record<string, unknown>; comparisons: {field: string; declared: unknown; instance: unknown; equal: boolean}[]; consumer: string; scope: string; definition_sha256: string; source: Source; path: string; observed_at_utc: string; loaded_catalog_sha256: string};
export type ItemRecord = {
  id: string; pointer: string; definition: Record<string, unknown>; diagnostics: Diagnostic[];
  capability: {contract: string; editable: boolean; fields: string[]; reason: string; weight_unit: string; tier_min: number; tier_max: number; tier_note: string; stack_note: string};
  use: {declared: unknown; status: string; consumer: string; handler: string | null; line: number | null; scope: string; notes: string[]};
  pools: {id: string; path: string; pointer: string; index: number; field: string; unique: boolean}[];
  dependencies: {kind: string; field: string; id: string; resolved?: boolean; paths?: string[]; note?: string}[];
  factory: FactoryResult | null;
  recipes: RecipeRelation[];
};
export type RecipeRelation = {id: string; path: string; pointer: string; produces: boolean; fields: string[]; execution_class: string};
export type RecipeProbe = {
  path: string; recipe_id: string; source_sha256: string; source: Source; consumer: string; scope: string; observed_at_utc: string;
  cases: {preset: string; eligible: boolean; missing: {tag: string; min_tier: number; have: number; need: number; ambient?: boolean; role?: string}[];
    inventory: {instance: string; item_id: string; source: string; keywords: unknown; consumed_on_use: boolean}[];
    ambient: unknown[]; selected: string[]; materials: string[]; retained_tools: string[]; before: string[]; after: string[];
    committed: boolean | null; output: {item_id: string; properties: Record<string, unknown>; in_inventory: boolean} | null}[];
};
export type RecipeRecord = {
  id: string; pointer: string; definition: Record<string, unknown>; diagnostics: Diagnostic[];
  capability: {contract: string; editable: boolean; reason: string; execution_class: string; fields: string[]; excluded_fields: string[]; tier_min: number; tier_max: number; quantity_max: number; slots_max: number};
  output: {id: string | null; resolved: boolean; sources: {path: string; pointer: string}[]};
  candidates: {role: string; index: number; matches: {id: string; path: string; pointer: string; automatic_material: boolean}[]}[];
  probe: RecipeProbe | null;
};
export type RecipeContext = {records: RecipeRecord[]; keywords: Record<string, unknown>; ambient_tags: Record<string, unknown>; categories: string[]; items: {id: string; name: string}[]; visibility: string};
export type ItemContext = {records: ItemRecord[]; keywords: Record<string, {display?: string; description?: string}>; snapshot: string};
