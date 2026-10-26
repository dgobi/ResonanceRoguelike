import { useEffect, useRef, useState } from "react";
import {
  call,
  asFailure,
  type Diagnostic,
  type Inspection,
  type Failure,
} from "./protocol";
import { currentVerdict, scalarEdit, sourceDiff, syntax } from "./draft";

type Verdict = {
  valid: boolean;
  diagnostics: Diagnostic[];
  draft_sha256: string;
  review_token?: string;
  limitations: string;
  path: string;
  worker_version: string;
  contract: string;
};
type Disk = {
  changed: boolean;
  raw: string;
  sha256: string;
  recovery_files: string[];
};
export function Authoring({
  document,
  onDirty,
  onApplied,
  onError,
  busy,
  setBusy,
}: {
  document: Inspection;
  onDirty: (dirty: boolean) => void;
  onApplied: (path: string, receipt: unknown) => Promise<void>;
  onError: (e: Failure | null) => void;
  busy: string;
  setBusy: (s: string) => void;
}) {
  const [draft, setDraft] = useState(document.raw),
    [editing, setEditing] = useState(false);
  const [tab, setTab] = useState("properties"),
    [verdict, setVerdict] = useState<Verdict | null>(null);
  const [variant, setVariant] = useState(false),
    [variantId, setVariantId] = useState("");
  const [disk, setDisk] = useState<Disk | null>(null),
    [confirm, setConfirm] = useState(false);
  const [localError, setLocalError] = useState("");
  const version = useRef(0),
    latest = useRef(draft),
    mounted = useRef(true);
  const dirty = draft !== document.raw;
  const parsed = syntax(draft);
  let values: Record<string, unknown> = {};
  try {
    values = JSON.parse(draft.replace(/^\uFEFF/, "")) || {};
  } catch {
    /* diagnostics below */
  }
  const target = variant
    ? `${document.path.slice(0, document.path.lastIndexOf("/"))}/${variantId}.json`
    : document.path;
  useEffect(() => {
    onDirty(dirty);
  }, [dirty, onDirty]);
  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
      version.current++;
    };
  }, []);
  useEffect(() => {
    let stopped = false;
    const check = async () => {
      if (busy) return;
      try {
        const d = await call<Disk>("document_disk", {
          token: document.document_token,
        });
        if (!stopped) setDisk(d.result);
      } catch (e) {
        if (!stopped) onError(asFailure(e));
      }
    };
    void check();
    const timer = setInterval(() => void check(), 3000);
    return () => {
      stopped = true;
      clearInterval(timer);
    };
  }, [document.document_token, busy, onError]);
  function change(text: string) {
    latest.current = text;
    version.current++;
    setDraft(text);
    setVerdict(null);
    setConfirm(false);
    setLocalError("");
  }
  function property(
    key: "id" | "description" | "weight",
    value: string | number,
  ) {
    try {
      change(scalarEdit(latest.current, key, value));
    } catch (e) {
      setLocalError(String(e));
    }
  }
  async function validate() {
    const v = ++version.current,
      text = latest.current;
    setBusy("Validating unsaved draft…");
    setVerdict(null);
    onError(null);
    try {
      const r = await call<Verdict>("validate_document", {
        token: document.document_token,
        draft: text,
        variantId: variant ? variantId : null,
      });
      if (
        mounted.current &&
        currentVerdict(v, version.current, text, latest.current)
      ) {
        setVerdict(r.result);
        setTab(r.result.valid ? "diff" : "problems");
      }
    } catch (e) {
      if (mounted.current && v === version.current) onError(asFailure(e));
    } finally {
      if (mounted.current) setBusy("");
    }
  }
  async function apply() {
    setConfirm(false);
    setBusy("Revalidating and applying one file…");
    onError(null);
    try {
      const r = await call<{
        path: string;
        before_sha256: string;
        after_sha256: string;
        variant: boolean;
      }>("apply_document", {
        token: document.document_token,
        reviewToken: verdict?.review_token,
        confirmed: true,
      });
      onDirty(false);
      await onApplied(r.result.path, r.result);
    } catch (e) {
      onError(asFailure(e));
      setVerdict(null);
    } finally {
      setBusy("");
    }
  }
  const reason = !editing
    ? "Begin editing to create a draft."
    : !dirty
      ? "No unsaved source changes."
      : parsed.diagnostics.length
        ? "Correct JSON syntax first."
        : variant && !variantId
          ? "Enter a new variant ID."
          : disk?.changed
            ? "Disk changed: inspect and reload or keep your draft."
            : !verdict?.valid
              ? "Validate this exact draft before applying."
              : busy
                ? "Wait for the active request."
                : "";
  return (
    <section className="authoring" data-testid="authoring">
      <h2>{document.id}</h2>
      <code className="filepath">{document.path}</code>
      <p
        className={disk?.changed ? "notice warning" : "notice"}
        data-testid="draft-state"
      >
        {disk?.changed
          ? "Externally changed · unsaved draft retained"
          : dirty
            ? "Unsaved draft"
            : editing
              ? "Editing · no changes"
              : "Read-only · source unchanged"}
      </p>
      <p className="muted small">
        ordinary_building · {document.width} × {document.height} ·{" "}
        {document.special_count} specials · file {document.sha256.slice(0, 12)}
      </p>
      {!!disk?.recovery_files.length && (
        <p className="notice warning">
          Recovery files require inspection: {disk.recovery_files.join(", ")}.
          Source is reopened from disk; no recovery file is silently applied.
        </p>
      )}
      {!editing ? (
        <button
          className="primary full"
          disabled={!!busy}
          onClick={() => setEditing(true)}
        >
          Begin edit
        </button>
      ) : (
        <div className="edit-actions">
          <button
            disabled={!!busy}
            onClick={() => {
              change(document.raw);
              setEditing(false);
              setVariant(false);
              setVariantId("");
            }}
          >
            Discard / Revert
          </button>
          <button
            disabled={!!busy}
            onClick={() => {
              setVariant(!variant);
              setVerdict(null);
              version.current++;
            }}
          >
            {" "}
            {variant ? "Use existing target" : "Save as new variant"}
          </button>
        </div>
      )}
      {editing && variant && (
        <label>
          New variant ID
          <input
            aria-label="New variant ID"
            value={variantId}
            disabled={!!busy}
            onChange={(e) => {
              setVariantId(e.target.value);
              property("id", e.target.value);
            }}
          />
          <small>
            Saved beside the source. Current procedural selection profiles are
            unchanged. Legacy flat-pool contexts may discover added files.
          </small>
        </label>
      )}
      <div className="tabs author-tabs">
        {["properties", "source", "problems", "diff"].map((t) => (
          <button
            key={t}
            className={tab === t ? "active" : ""}
            onClick={() => setTab(t)}
          >
            {t[0].toUpperCase() + t.slice(1)}
          </button>
        ))}
      </div>
      {tab === "properties" && (
        <div className="typed-fields">
          <label>
            Description
            <textarea
              aria-label="Description"
              value={
                typeof values.description === "string" ? values.description : ""
              }
              readOnly={!editing}
              disabled={
                !!parsed.diagnostics.length || busy.includes("applying")
              }
              onChange={(e) => property("description", e.target.value)}
            />
          </label>
          <label>
            Legacy corner-scatter weight
            <input
              aria-label="Legacy corner-scatter weight"
              type="number"
              min="0"
              step="any"
              value={typeof values.weight === "number" ? values.weight : ""}
              readOnly={!editing}
              disabled={
                !!parsed.diagnostics.length || busy.includes("applying")
              }
              onChange={(e) => {
                if (
                  e.target.value !== "" &&
                  Number.isFinite(Number(e.target.value))
                )
                  property("weight", Number(e.target.value));
              }}
            />
          </label>
          <p className="muted small">
            Description is retained metadata. Weight is a supported nonnegative
            scalar; current planned selection uses separate profiles. Geometry,
            specials and all other fields remain available in Source.
          </p>
          <div className={"validation " + (document.valid ? "pass" : "fail")}>
            <strong>
              {document.valid
                ? "✓ Production validator passed"
                : "× Source validation failed"}
            </strong>
            <small>
              On-disk source only; an edited draft needs its own validation.
            </small>
          </div>
        </div>
      )}
      {tab === "source" && (
        <>
          <label htmlFor="draft-json">
            {editing ? "Draft JSON" : "Source JSON"}
          </label>
          <textarea
            id="draft-json"
            className="source-editor"
            spellCheck={false}
            value={draft}
            readOnly={!editing || busy.includes("applying")}
            onChange={(e) => {
              // textarea normalizes line breaks. Preserve the opened document's CRLF
              // convention for consciously edited raw text; property edits use spans.
              const text = document.raw.includes("\r\n")
                ? e.target.value.replace(/\r?\n/g, "\r\n")
                : e.target.value;
              change(text);
            }}
          />
        </>
      )}
      {tab === "problems" && (
        <div className="problem-list">
          {parsed.diagnostics.map((d, i) => (
            <p className="notice warning" key={i}>
              JSON {d.line}:{d.column} · {d.message}
            </p>
          ))}
          {(verdict?.diagnostics || document.diagnostics).map((d, i) => (
            <article
              key={i}
              className={"notice " + (d.severity === "error" ? "warning" : "")}
            >
              <b>
                {d.severity} · {d.code}
              </b>
              <p>
                {d.path} · {d.field}
                {d.line ? ` · ${d.line}:${d.column}` : ""}
              </p>
              <p>{d.message}</p>
              <small>{d.correction}</small>
            </article>
          ))}
          <p className="muted">
            {dirty && !verdict
              ? "Displayed source diagnostics are from the opened file. Validate the draft for a current verdict."
              : "Warnings remain warnings. This check does not prove placement, reachability or population."}
          </p>
        </div>
      )}
      {tab === "diff" && (
        <>
          <p className="muted small">
            Exact opened source → current draft. Target: {target}
          </p>
          <pre className="diff" data-testid="source-diff">
            {sourceDiff(document.raw, draft, document.path, target)}
          </pre>
        </>
      )}
      {!!parsed.diagnostics.length && (
        <p className="notice warning">
          Invalid JSON · line {parsed.diagnostics[0].line}, column{" "}
          {parsed.diagnostics[0].column}: {parsed.diagnostics[0].message}
        </p>
      )}
      {localError && <p role="alert">{localError}</p>}
      {verdict && (
        <div
          className={"validation " + (verdict.valid ? "pass" : "fail")}
          data-testid="draft-verdict"
        >
          <strong>
            {verdict.valid
              ? "Draft contract and references passed"
              : "Draft rejected"}
          </strong>
          <small>
            {verdict.draft_sha256.slice(0, 12)} · worker{" "}
            {verdict.worker_version} · {verdict.contract}
          </small>
          <p>{verdict.limitations}</p>
        </div>
      )}
      {editing && (
        <div className="edit-actions">
          <button
            disabled={!!busy || !dirty}
            title={
              !dirty
                ? "Change the draft first"
                : "Checks the exact unsaved bytes with the game"
            }
            onClick={validate}
          >
            Validate draft
          </button>
          <button
            className="primary"
            disabled={!!reason}
            title={reason || "Review and confirm this file"}
            onClick={() => {
              setTab("diff");
              setConfirm(true);
            }}
          >
            Review & apply
          </button>
        </div>
      )}
      {editing && reason && <p className="muted small">{reason}</p>}
      {disk?.changed && (
        <details>
          <summary>Disk version · draft is retained</summary>
          <pre className="raw">{disk.raw}</pre>
        </details>
      )}
      {confirm && (
        <div className="modal-shade">
          <section
            className="confirmation"
            role="dialog"
            aria-label="Confirm single-file apply"
          >
            <h2>Apply this one content file?</h2>
            <code>{target}</code>
            <p>
              {variant
                ? "This creates a new definition. It does not add entries to current town or roadside selection profiles. Older flat-pool contexts can discover new definitions."
                : "This changes the meaning of an existing ID. Saved pending worlds may depend on its old content. Prefer a new variant for changed identity or meaning."}
            </p>
            <p>
              Current draft: valid contract and references. Placement and
              population are unverified.
            </p>
            <pre className="diff">
              {sourceDiff(document.raw, draft, document.path, target)}
            </pre>
            <div className="edit-actions">
              <button onClick={() => setConfirm(false)}>Keep editing</button>
              <button className="primary" onClick={apply}>
                Confirm apply one file
              </button>
            </div>
          </section>
        </div>
      )}
    </section>
  );
}
