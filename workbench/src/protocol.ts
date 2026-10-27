export type { ItemContext, RecipeContext, ItemRecord, RecipeRecord, FactoryResult, RecipeProbe, RecipeRelation } from "./familyData";
import { familyProblem, type ContentFamily } from "./content";
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
  host_runtime: { mode: string; python: string; bridge: string; resource_directory: string; application: string; override_present: boolean; notice: string | null };
  project_selection: { root: string; selected_from: string; notices: string[] };
  creature_contract: string;
  families: ContentFamily[];
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
  family_id?: string;
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
  family?: ContentFamily;
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
  population_receipts?: {kind:string;record_id:string;source_index:number;source_xy:Cell;xy:Cell;actor_classes?:string[];actual_count:number;creature_definition?:{id:string;sha256:string};actors:unknown[]}[];
  stairs?: unknown[];
  access_source?: unknown;
  source_path?: string;
  source_sha256?: string;
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
  if (envelope.protocol !== 8 || typeof envelope.id !== "string")
    throw {
      code: "PROTOCOL_MISMATCH",
      message: "Unexpected host/worker protocol.",
      remedy: "Rebuild the matching application and worker.",
    };
  if (!envelope.ok) throw envelope.error;
  const result:unknown = envelope.result;
  if (result && typeof result === "object" && "family" in result && result.family) {
    const problem=familyProblem(result.family);
    // A negotiated unsupported descriptor remains inspectable read-only. Other
    // malformed transport cannot enter a mounted typed view.
    if (problem && !("compatible" in Object(result.family) && (result.family as {compatible?:unknown}).compatible === false))
      throw {code:"CONTENT_ENVELOPE",message:problem,remedy:"Inspect the game-owned contract and reopen its source."};
  }
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
