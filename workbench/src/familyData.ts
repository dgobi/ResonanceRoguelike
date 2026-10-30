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
export type TypographyContext = {records:{id:string;pointer:string;definition:Record<string,unknown>;diagnostics:Diagnostic[];capability:{contract:string;editable:boolean;reason:string}}[]; fonts:{id:string;label:string;sha256:string}[]};
type PngFrame = {image:string;image_sha256:string;width:number;height:number};
export type TypographyPreview = Pick<ReaderFrame,"draft_sha256"|"path"|"source"|"contract"|"descriptor_sha256"|"runtime"|"observed_at_utc"|"setup"|"dependencies"> & {
  kind:"typography-preview";inputs:Record<string,never>;specimen:PngFrame;reader:PngFrame & {page:number;scroll:number;max_scroll:number;setup:string};
  roles:{role:string;label:string;requested:string;resolved:string;sha256:string;size:number;fallback:false;sample:string;width:number;height:number}[];
  diagnostics:Diagnostic[];fallback:false;
};
export type AssignmentPreview = Pick<ReaderFrame,"draft_sha256"|"path"|"source"|"contract"|"descriptor_sha256"|"runtime"|"observed_at_utc"|"setup"|"dependencies"> & {
  kind:"assignment-preview";inputs:{seed:number};seed:number;width:number;height:number;plan_mode:string;generation_revision:string;
  profile_path:string;profile_sha256:string;target_type:string;authored_chance:number;enabled:boolean;matching_count:number;authored_count:number;procedural_count:number;truncated:number;
  rows:{chunk:[number,number];submap_id:string;type:string;seed:number;layout_id:string;path:string}[];
};
export type SelectionPlacement={id:string;asset:string;owner:string;role:string;profile:string;path:string;chunk:[number,number];origin:[number,number];rotation:number;mirror:boolean;frontage_entrance:string;frontage:Record<string,unknown>;entrances:Record<string,unknown>[];entrance_cells:{id:string;cells:[number,number][]}[]};
export type SelectionPreview = Pick<ReaderFrame,"draft_sha256"|"path"|"source"|"contract"|"descriptor_sha256"|"runtime"|"observed_at_utc"|"setup"|"dependencies"> & {
  kind:"selection-preview";inputs:{seed:number;placement_id?:string;plan_identity?:string;input_identity?:string};seed:number;width:number;height:number;plan_mode:string;
  profile_path:string;profile_sha256:string;input_identity:string;input_files:Record<string,string>;plan_identity:string;captured_selection:Record<string,unknown>;resolved_selection_sha256:string;selection_matches_saved_resolve:true;
  selected_count:number;shown_count:number;truncated:number;rows:SelectionPlacement[];
  summary:{profile:string;role:string;asset:string;path:string;weight:number;base_weight:number;max_per_settlement:number;selected:number;eligible:true}[];
  scene:(Pick<import("./protocol").Preview,"terrain"|"width"|"height"|"decor"|"items"|"containers"|"actors"> & {legend:import("./protocol").Preview["legend"];chunk:[number,number];placement:SelectionPlacement;records:Record<string,unknown>[];access:unknown[];note:string;passed:true})|null;
};
export type FamilyPreview = ReaderFrame | TypographyPreview | AssignmentPreview | SelectionPreview;
const png=(v:Partial<PngFrame>|undefined,width:number,height:number)=>!!v && v.width===width && v.height===height && typeof v.image==="string" && v.image.length<=2800000 && /^data:image\/png;base64,[A-Za-z0-9+/]+=*$/.test(v.image) && typeof v.image_sha256==="string" && /^[a-f0-9]{64}$/.test(v.image_sha256);
export function previewProblem(value: unknown): string {
  if (!value || typeof value !== "object") return "Missing preview";
  if((value as {kind?:string}).kind==="selection-preview"){
    const v=value as Partial<SelectionPreview>,hash=(h:unknown)=>typeof h==="string"&&/^[a-f0-9]{64}$/.test(h);
    if(v.width!==128||v.height!==128||v.plan_mode!=="shared-v1"||v.contract!=="settlement-membership-1"||v.profile_path!=="roguelike/data/generation/settlement_profiles.json"||!v.source||v.seed!==v.inputs?.seed||v.selection_matches_saved_resolve!==true)return "Malformed saved selection identity";
    if(![v.profile_sha256,v.draft_sha256,v.descriptor_sha256,v.input_identity,v.plan_identity,v.resolved_selection_sha256].every(hash)||![v.seed,v.selected_count,v.shown_count,v.truncated].every(n=>Number.isSafeInteger(n)&&Number(n)>=0)||Number(v.shown_count)+Number(v.truncated)!==v.selected_count)return "Malformed saved selection binding/counts";
    if(!v.input_files||Object.entries(v.input_files).some(([p,h])=>!p.startsWith("roguelike/")||!hash(h))||!Array.isArray(v.rows)||v.rows.length>200||v.rows.length!==v.shown_count||v.rows.some(r=>!r.id||!r.asset||!["grid","roadside","landmark"].includes(r.profile)||!r.path.startsWith("roguelike/data/buildings/")||!Array.isArray(r.chunk)||r.chunk.length!==2||!Array.isArray(r.entrance_cells))||!Array.isArray(v.summary))return "Malformed selection rows/dependencies";
    if(v.scene && (!v.inputs?.placement_id||v.scene.placement.id!==v.inputs.placement_id||v.scene.width!==80||v.scene.height!==43||v.scene.terrain.length!==43||v.scene.terrain.some(r=>r.length!==80)||!v.scene.passed||!Array.isArray(v.scene.records)))return "Malformed selected construction";
    return "";
  }
  if((value as {kind?:string}).kind==="assignment-preview"){
    const v=value as Partial<AssignmentPreview>;
    if(v.width!==128||v.height!==128||v.plan_mode!=="shared-v1"||v.contract!=="authored-submap-selection-1"||v.profile_path!=="roguelike/data/generation/authored_submap_selection.json"||!v.source||!v.inputs||v.seed!==v.inputs.seed||typeof v.enabled!=="boolean"||!["barrow","cave","vault"].includes(String(v.target_type))||typeof v.authored_chance!=="number"||v.authored_chance<0||v.authored_chance>1)return "Malformed assignment preview identity";
    if(![v.profile_sha256,v.draft_sha256,v.descriptor_sha256].every(h=>typeof h==="string"&&/^[a-f0-9]{64}$/.test(h))||![v.seed,v.matching_count,v.authored_count,v.procedural_count,v.truncated].every(n=>Number.isSafeInteger(n)&&Number(n)>=0)||Number(v.authored_count)+Number(v.procedural_count)!==v.matching_count)return "Malformed assignment counts/source";
    if(!Array.isArray(v.rows)||v.rows.length>100||v.rows.length+Number(v.truncated)!==v.authored_count||v.rows.some(r=>!Array.isArray(r.chunk)||r.chunk.length!==2||r.chunk.some(n=>!Number.isSafeInteger(n)||n<0||n>=128)||typeof r.submap_id!=="string"||r.type!==v.target_type||!Number.isSafeInteger(r.seed)||typeof r.layout_id!=="string"||!/^roguelike\/data\/layouts\/[^/]+\.json$/.test(r.path)))return "Malformed assignment rows";
    return "";
  }
  if((value as {kind?:string}).kind==="typography-preview"){
    const v=value as Partial<TypographyPreview>;
    if(!png(v.specimen,960,960) || !png(v.reader,960,640) || v.fallback!==false || !v.inputs || Object.keys(v.inputs).length) return "Invalid typography preview frames";
    if(!Array.isArray(v.roles) || v.roles.length!==13 || new Set(v.roles.map(r=>r.role)).size!==13 || v.roles.some(r=>!r.role.startsWith("font_") || typeof r.requested!=="string" || typeof r.resolved!=="string" || !/^[a-f0-9]{64}$/.test(r.sha256) || r.fallback!==false || ![r.size,r.width,r.height].every(n=>Number.isSafeInteger(n)&&n>0)))return "Malformed typography role evidence";
    if(![v.draft_sha256,v.descriptor_sha256].every(h=>typeof h==="string" && /^[a-f0-9]{64}$/.test(h)) || !v.source || typeof v.contract!=="string" || typeof v.setup!=="string" || !Array.isArray(v.diagnostics))return "Malformed typography preview identity";
    return "";
  }
  const v=value as Partial<ReaderFrame>;
  if(v.kind!=="reader-frame" || typeof v.image!=="string" || v.image.length>2800000 || !/^data:image\/png;base64,[A-Za-z0-9+/]+=*$/.test(v.image)) return "Invalid bounded PNG preview";
  if(v.width!==960 || v.height!==640 || !v.inputs || ![v.page,v.scroll,v.max_scroll,v.viewport_height,v.total_rows,v.inputs.page,v.inputs.scroll].every(n=>Number.isSafeInteger(n) && Number(n)>=0)) return "Malformed preview coordinates";
  if(![v.image_sha256,v.draft_sha256,v.descriptor_sha256].every(h=>typeof h==="string" && /^[a-f0-9]{64}$/.test(h)) || !v.source || typeof v.contract!=="string" || typeof v.setup!=="string") return "Malformed preview identity";
  return "";
}
export type FactoryResult = {item_id: string; instance: Record<string, unknown>; comparisons: {field: string; declared: unknown; present?:boolean; effective_factory_value?:unknown; instance: unknown; equal: boolean}[]; consumer: string; scope: string; definition_sha256: string; source: Source; path: string; observed_at_utc: string; loaded_catalog_sha256: string};
export type ItemRecord = {
  id: string; pointer: string; definition: Record<string, unknown>; diagnostics: Diagnostic[];
  capability: {contract: string; editable: boolean; supply_class?: string; equipment_class?:string|null; fields: string[]; reason: string; weight_unit: string; tier_min: number; tier_max: number; tier_note: string; stack_note: string};
  equipment?: {equipment_class:string;slot:string;current_definition_fields:string[];retained:Record<string,unknown>;scope:string;explanation:string;base_range?:number[];summed_av?:number}|null;
  effective_use?: {field:string;explanation:string;stored:unknown;fraction?:number;maximum?:number;configuration_sha256?:string}|null;
  return_item?: {id:string;label:string;path:string;editable:boolean;sha256:string}|null;
  use: {declared: unknown; present?:boolean;effective?:unknown;legacy?:boolean; status: string; consumer: string; handler: string | null; line: number | null; scope: string; notes: string[]};
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
