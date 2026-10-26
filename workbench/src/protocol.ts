import { invoke } from "@tauri-apps/api/core";
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
};
export type Inspection = Asset & {
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
  if (envelope.protocol !== 2 || typeof envelope.id !== "string")
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
