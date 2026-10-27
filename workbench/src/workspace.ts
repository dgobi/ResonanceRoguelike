import type { Failure, Inspection } from "./protocol";

export type OpenDocument = {
  document: Inspection; dirty: boolean; selectedId: string;
  origin?: { token: string; label: string; focus: HTMLElement | null };
  trail?: import("./protocol").ItemTrail | null;
};
export type Documents = Record<string, OpenDocument>;
export type Disk = { changed: boolean; dependencies_changed?: boolean; raw: string; sha256: string; recovery_files: string[] };
export type DiskRow = { token: string; disk?: Disk; error?: Failure };
export type Sweep = { documents: DiskRow[]; dependency_scans: number; elapsed_ms: number; project_epoch: number };
export type DiskSubscription = (token: string, capture: () => (row: DiskRow) => void) => () => void;

// One in-flight sweep, no queue. Editors capture their current local revision
// before the request, and reject a delivery if that revision is no longer live.
export class WorkspaceMonitor {
  private listeners = new Map<string, () => (row: DiskRow) => void>();
  private running = false;
  private generation = 0;
  subscribe: DiskSubscription = (token, capture) => {
    this.listeners.set(token, capture);
    return () => { if (this.listeners.get(token) === capture) this.listeners.delete(token); };
  };
  reset() { this.generation++; }
  async check(fetch: () => Promise<Sweep>, ready: () => boolean) {
    if (this.running || !ready() || !this.listeners.size) return;
    this.running = true;
    const generation = this.generation;
    const receivers = [...this.listeners].map(([token, capture]) => ({token, capture, receive: capture()}));
    try {
      const result = await fetch();
      if (generation !== this.generation) return;
      for (const {token, capture, receive} of receivers) {
        const row = result.documents.find(r => r.token === token);
        if (row && this.listeners.get(token) === capture) receive(row);
      }
      return result;
    } finally { this.running = false; }
  }
}

export function installDocument(current: Documents, document: Inspection, selectedId: string, previous?: string): Documents {
  const token = document.document_token;
  if (!token || !document.file_identity) throw new Error("Host document identity is missing.");
  if (previous && !current[previous]) throw new Error("The originating document is no longer open.");
  const owner = Object.values(current).find(d => d.document.file_identity === document.file_identity);
  if (owner && owner.document.document_token !== token && owner.document.document_token !== previous)
    throw new Error("The destination already has an open document. Its draft was retained.");
  // An ordinary open must never replace an existing instance's exact draft.
  if (!previous && current[token]) return current;
  const next = {...current};
  if (previous) delete next[previous];
  next[token] = {document, selectedId, dirty: false, origin: previous ? current[previous].origin : undefined, trail: previous ? current[previous].trail : undefined};
  return next;
}
