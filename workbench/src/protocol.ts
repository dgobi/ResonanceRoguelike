import { invoke } from "@tauri-apps/api/core";
import type { Catalog, Cell, Layer } from "./layout";
export type Failure = { code: string; message: string; remedy: string };
export type Source = {
  root: string;
  commit: string | null;
  branch: string | null;
  game_dirty: boolean | null;
  game_source_sha256: string;
  catalog_sha256: string;
};
export type Identity = {
  protocol: number;
  worker_version: string;
  worker_sha256: string;
  source: Source;
  runtime: {
    python: string;
    executable: string;
    dependencies: Record<string, string>;
  };
  contract: string;
  route: string;
  validator: string;
  preview: string;
  unavailable: string[];
};
export type Asset = {
  id: string;
  path: string;
  width: number;
  height: number;
  name?: string;
  category?: string;
  route: string;
  editable: boolean;
  provenance: string;
  validation: string;
  pointer?: string;
  source_paths?: string[];
  result_item?: string;
  execution_class?: string;
};
export type Diagnostic = {
  severity: string;
  code: string;
  path: string;
  asset: string;
  field: string;
  message: string;
  correction: string;
  line?: number;
  column?: number;
  source_xy?: Cell;
  layer?: Layer;
};
export type Inspection = Asset & {
  pool_context?: PoolContext;
  item_context?: ItemContext;
  recipe_context?: RecipeContext;
  creature_context?: CreatureContext;
  route: string;
  description: string;
  special_count: number;
  valid: boolean;
  diagnostics: Diagnostic[];
  raw: string;
  invalid_fixture: boolean;
  sha256: string;
  mtime_ns: string;
  source_unchanged: boolean;
  source: Source;
  document_token?: string;
  catalog?: Catalog;
};
export type SourceTrail = { id: string; path: string; sourcePath: string; sourceHash: string; index: number; x: number; y: number; decor: string; poolId: string };
export type ItemTrail = { poolId: string; path: string; index: number; itemId: string; structure?: SourceTrail | null };
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
export type CreatureFactoryResult = {
  creature_id: string; actor_class: string; instance: Record<string, unknown>;
  comparisons: {field: string; declared: unknown; instance: unknown}[];
  source: Source; path: string; source_sha256: string; loaded_catalog_sha256: string;
  observed_at_utc: string; consumer: string; scope: string; contract: string; worker_version: string;
};
export type CreatureContext = {selection: string; records: {
  id: string; pointer: string; definition: Record<string, unknown>; diagnostics: Diagnostic[];
  capability: {contract: string; editable: boolean; fields: string[]; shape: string; reason: string; hp_min: number; hp_max: number; hp_note: string; description_note: string};
  dependencies: {kind: string; field: string; id: unknown; resolved: boolean; required: boolean; paths: string[]; note: string}[];
  references: {id: string; path: string; field: string; route: string; x: number; y: number; evidence: string}[];
  factory: CreatureFactoryResult | null;
}[]};
export type ItemContext = {records: ItemRecord[]; keywords: Record<string, {display?: string; description?: string}>; snapshot: string};
export type PoolContext = {
  items: Record<string, {id: string; name: string; resolved: boolean; sources: {path: string; pointer: string; definition: Record<string, unknown>}[]}>;
  references: {id: string; path: string; field: string; x: number; y: number; decor_id: string}[];
  consumer: string; validator: string; rules: string;
};
export type Feature = {
  x: number;
  y: number;
  id?: string;
  decor_id?: string;
  blocking?: boolean;
  items?: unknown[];
};
export type Preview = {
  valid: boolean;
  passed: boolean;
  width: number;
  height: number;
  terrain: string[][];
  legend: Record<string, { walkable: boolean; transparent: boolean }>;
  decor: Feature[];
  items: Feature[];
  containers: Feature[];
  actors: Feature[];
  spawn: [number, number];
  origin: [number, number];
  asset: string;
  seed: number;
  scene_seed: string;
  scene_address: (string | number)[];
  elapsed_ms: number;
  host_ms?: number;
  source: Source;
  generation_revision: string;
  terrain_sha256: string;
  candidate_sha256: string;
  context: string;
  rendering: string;
  occupant_diagnostics: unknown[];
  draft_sha256?: string;
  access?: unknown[];
};
type Envelope<T> = {
  protocol: number;
  id: string;
  ok: boolean;
  result: T;
  error?: Failure;
  host_elapsed_ms: number;
};
export async function call<T>(
  command: string,
  args?: Record<string, unknown>,
): Promise<{ result: T; elapsed: number }> {
  const envelope = await invoke<Envelope<T>>(command, args);
  if (envelope.protocol !== 7 || typeof envelope.id !== "string")
    throw {
      code: "PROTOCOL_MISMATCH",
      message: "Unexpected host/worker protocol.",
      remedy: "Rebuild the matching application and worker.",
    };
  if (!envelope.ok) throw envelope.error;
  return { result: envelope.result, elapsed: envelope.host_elapsed_ms };
}
export function request<T>(op: string, args: Record<string, unknown> = {}) {
  return call<T>("worker_request", { request: { op, ...args } });
}
export function asFailure(error: unknown): Failure {
  if (
    error &&
    typeof error === "object" &&
    "code" in error &&
    "message" in error
  )
    return error as Failure;
  return {
    code: "DESKTOP_CONNECTION",
    message: String(error),
    remedy:
      "Launch the Tauri desktop application with npm run dev or the packaged executable.",
  };
}
export function validatePreview(value: Preview): Preview {
  if (
    !value.valid ||
    value.width !== 80 ||
    value.height !== 43 ||
    value.terrain?.length !== 43 ||
    value.terrain.some(
      (r) =>
        r.length !== 80 ||
        r.some((t) => typeof t !== "string" || !value.legend[t]),
    )
  ) {
    throw {
      code: "PREVIEW_FAILED",
      message:
        "Production preview did not return a valid 80 × 43 terrain grid.",
      remedy: "Inspect the production diagnostics and reopen the repository.",
    };
  }
  return value;
}
