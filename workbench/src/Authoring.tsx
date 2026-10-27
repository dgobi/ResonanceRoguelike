import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { LayoutEditor } from "./LayoutEditor";
import { PoolEditor } from "./PoolEditor";
import { RecipeEditor } from "./RecipeEditor";
import { CreatureEditor } from "./CreatureEditor";
import { ItemEditor } from "./ItemEditor";
import {
  CanvasHistory,
  diagnosticCell,
  layoutModel,
  type Cell,
  type Layer,
} from "./layout";
import {
  call,
  asFailure,
  type Diagnostic,
  type Inspection,
  type Failure,
  type Preview,
  type SourceTrail,
  type ItemTrail,
  type ItemContext,
  type RecipeContext,
  type CreatureContext,
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
  preview?: Preview;
  item_context?: ItemContext;
  recipe_context?: RecipeContext;
  creature_context?: CreatureContext;
};
type Disk = {
  changed: boolean;
  dependencies_changed?: boolean;
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
  canvasHost,
  diskPreview,
  seed,
  onCancel,
  active = true,
  onPool,
  trail,
  onReturn,
  dependencyVersion = 0,
  onItem, itemTrail, selectedItemId, onItemPool, poolEntryFocus, onRecipe, onRecipeItem, selectedRecipeId, selectedCreatureId,
}: {
  document: Inspection;
  onDirty: (dirty: boolean) => void;
  onApplied: (path: string, receipt: unknown) => Promise<void>;
  onError: (e: Failure | null) => void;
  busy: string;
  setBusy: (s: string) => void;
  canvasHost: HTMLDivElement | null;
  diskPreview: Preview | null;
  seed: number;
  onCancel: () => void;
  active?: boolean;
  onPool?: (id: string, trail: SourceTrail) => void;
  trail?: SourceTrail | null;
  onReturn?: () => void;
  dependencyVersion?: number;
  onItem?: (id: string, trail: ItemTrail) => void;
  itemTrail?: ItemTrail | null;
  selectedItemId?: string;
  onItemPool?: (id: string) => void;
  poolEntryFocus?: number;
  onRecipe?: (id: string, path: string) => void;
  onRecipeItem?: (id: string, path?: string) => void;
  selectedRecipeId?: string;
  selectedCreatureId?: string;
}) {
  const pool = document.route === "contextual_loot_pool";
  const item = document.route === "item_definition";
  const recipe = document.route === "recipe_definition";
  const creature = document.route === "creature_definition";
  const writable = !(item || recipe || creature) || document.editable;
  const [draft, setDraft] = useState(document.raw),
    [editing, setEditing] = useState(false);
  const [tab, setTab] = useState("properties"),
    [verdict, setVerdict] = useState<Verdict | null>(null);
  const [variant, setVariant] = useState(false),
    [variantId, setVariantId] = useState("");
  const [disk, setDisk] = useState<Disk | null>(null),
    [confirm, setConfirm] = useState(false);
  const [localError, setLocalError] = useState("");
  const [evidenceVersion, setEvidenceVersion] = useState(dependencyVersion);
  const [focus, setFocus] = useState<{ cell: Cell; layer: Layer } | null>(null);
  const history = useRef(new CanvasHistory()),
    gesture = useRef<string | null>(null);
  const [, updateHistory] = useState(0);
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
    version.current++;
    setVerdict(null);
    setConfirm(false);
  }, [dependencyVersion]);
  useEffect(() => { version.current++; setConfirm(false); }, [active]);
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
        if (!stopped) {
          setDisk(d.result);
          if ((recipe || creature) && (d.result.dependencies_changed || d.result.changed)) { version.current++; setVerdict(null); setConfirm(false); }
        }
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
  function change(text: string, visual = false) {
    if (!visual) {
      history.current.clear();
      gesture.current = null;
    }
    latest.current = text;
    version.current++;
    setDraft(text);
    setVerdict(null);
    setConfirm(false);
    setLocalError("");
  }
  function visualEdit(edit: (text: string) => string, label: string) {
    if (!editing || disk?.changed || busy.includes("applying")) return;
    try {
      const before = latest.current,
        after = edit(before);
      if (before === after) return;
      if (gesture.current === null)
        history.current.record(before, after, label);
      change(after, true);
    } catch (e) {
      setLocalError(String(e));
    }
  }
  function canvasGesture(active: boolean) {
    if (active) gesture.current = latest.current;
    else if (gesture.current !== null) {
      history.current.record(gesture.current, latest.current, "Brush / fill");
      gesture.current = null;
      updateHistory((v) => v + 1);
    }
  }
  function historyStep(redo: boolean) {
    if (!editing || disk?.changed || busy.includes("applying")) return;
    canvasGesture(false);
    change(
      redo
        ? history.current.redo(latest.current)
        : history.current.undo(latest.current),
      true,
    );
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
  async function validate(showDiff = true) {
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
        seed,
      });
      if (
        mounted.current &&
        currentVerdict(v, version.current, text, latest.current)
      ) {
        setVerdict(r.result);
        if (recipe || creature) { setEvidenceVersion(dependencyVersion); setDisk(d=>d ? {...d, dependencies_changed:false} : d); }
        if (!r.result.valid || showDiff)
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
      onDirty(latest.current !== document.raw);
    } finally {
      setBusy("");
    }
  }
  const reason = !editing
    ? "Begin editing to create a draft."
    : (recipe || creature) && !variant
      ? "Create a unique new variant before publication."
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
      {active && canvasHost && pool && createPortal(<PoolEditor
        draft={draft} path={target} context={document.pool_context}
        disabled={!editing ? "Begin edit to change this pool." : disk?.changed ? "Disk changed. Draft retained; reload or reconcile in Source." : busy.includes("applying") ? "Publication in progress." : ""}
        diagnostics={verdict?.diagnostics || (!dirty ? document.diagnostics : [])}
        onEdit={visualEdit} onUndo={() => historyStep(false)} onRedo={() => historyStep(true)}
        canUndo={!!history.current.undoStack.length} canRedo={!!history.current.redoStack.length}
        trail={trail} onReturn={onReturn} busy={!!busy} onCancel={onCancel}
        onItem={(id, index) => onItem?.(id, {poolId: String(values.id || document.id), path: target, index, itemId: id, structure: trail})}
        focusEntry={poolEntryFocus}
      />, canvasHost)}
      {item && canvasHost && createPortal(<div hidden={!active}><ItemEditor
        draft={draft} path={target} context={verdict?.item_context || document.item_context} selectedId={selectedItemId}
        dirty={dirty} validated={!!verdict?.valid} disabled={!writable ? "Read-only item family or ambiguous source." : !editing ? "Begin edit to change this component." : disk?.changed ? "Disk changed. Draft retained; reload or reconcile in Source." : busy.includes("applying") ? "Publication in progress." : ""}
        busy={!!busy} onCancel={onCancel} trail={itemTrail} onReturn={onReturn} onPool={onItemPool} onRecipe={onRecipe} onSource={() => setTab("source")}
        onEdit={visualEdit} onUndo={() => historyStep(false)} onRedo={() => historyStep(true)} canUndo={!!history.current.undoStack.length} canRedo={!!history.current.redoStack.length}
      /></div>, canvasHost)}
      {recipe && canvasHost && createPortal(<div hidden={!active}><RecipeEditor
        draft={draft} path={target} context={verdict?.recipe_context || document.recipe_context} selectedId={selectedRecipeId}
        dirty={dirty} validated={!!verdict?.valid} evidenceStale={!!disk?.changed || !!disk?.dependencies_changed || evidenceVersion !== dependencyVersion}
        disabled={!writable ? "Read-only recipe family or ambiguous source." : !editing ? "Begin edit to change this recipe." : disk?.changed ? "Disk changed. Draft retained; reload or reconcile in Source." : busy.includes("applying") ? "Publication in progress." : ""}
        busy={!!busy} onCancel={onCancel} onReturn={onReturn} onItem={(id,path)=>onRecipeItem?.(id,path)} onSource={()=>setTab("source")}
        onProbe={()=>void validate(false)} onEdit={visualEdit} onUndo={()=>historyStep(false)} onRedo={()=>historyStep(true)} canUndo={!!history.current.undoStack.length} canRedo={!!history.current.redoStack.length}
      /></div>, canvasHost)}
      {creature && canvasHost && createPortal(<div hidden={!active}><CreatureEditor
        draft={draft} path={target} context={verdict?.creature_context || document.creature_context} selectedId={selectedCreatureId}
        active={active} dirty={dirty} validated={!!verdict?.valid} evidenceStale={!!disk?.changed || !!disk?.dependencies_changed || evidenceVersion !== dependencyVersion}
        disabled={!writable ? "Read-only creature family or unresolved source." : !editing ? "Begin edit to change creature properties." : disk?.changed ? "Disk changed. Draft retained; reload or reconcile in Source." : busy.includes("applying") ? "Publication in progress." : ""}
        busy={!!busy} setBusy={setBusy} onCancel={onCancel} onSource={()=>setTab("source")} onFactory={()=>void validate(false)}
        onEdit={visualEdit} onUndo={()=>historyStep(false)} onRedo={()=>historyStep(true)} canUndo={!!history.current.undoStack.length} canRedo={!!history.current.redoStack.length}
      /></div>, canvasHost)}
      {active && !pool && !item && !recipe && !creature && canvasHost &&
        createPortal(
          <LayoutEditor
            draft={draft}
            catalog={document.catalog}
            disabled={
              !editing
                ? "Begin edit to paint."
                : disk?.changed
                  ? "Disk changed: reload or reconcile in Source before painting."
                  : busy.includes("applying")
                    ? "Publication in progress."
                    : ""
            }
            diagnostics={
              verdict?.diagnostics || (!dirty ? document.diagnostics : [])
            }
            preview={
              verdict?.valid && verdict.preview?.passed ? verdict.preview : null
            }
            previewHash={verdict?.draft_sha256}
            diskPreview={diskPreview}
            previewBusy={!!busy}
            onPreview={() => void validate(false)}
            onCancel={onCancel}
            onEdit={visualEdit}
            onGesture={canvasGesture}
            onUndo={() => historyStep(false)}
            onRedo={() => historyStep(true)}
            canUndo={!!history.current.undoStack.length}
            canRedo={!!history.current.redoStack.length}
            onError={(e) => setLocalError(String(e))}
            focus={focus}
            onPool={(id, index, record) => onPool?.(id, {
              id: String(values.id || document.id), path: target, index, x: record.x, y: record.y,
              sourcePath: document.path, sourceHash: document.sha256,
              decor: record.decor_id || "crate", poolId: id,
            })}
          />,
          canvasHost,
        )}
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
        {creature ? "creature_definition" : recipe ? "recipe_definition" : item ? "item_definition" : pool ? "contextual_loot_pool" : `ordinary_building · ${document.width} × ${document.height} · ${document.special_count} specials`} · file {document.sha256.slice(0, 12)}
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
          disabled={!!busy || !writable}
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
            {creature ? "Creates a new ID/file beside the source. No worldgen pool, saved actor or authored room is reassigned." : recipe ? "New recipe files are auto-loaded in new sessions. Review the known/deprecated consequences before confirming." : item ? "Saved beside the source. Choose the new item ID explicitly in a new pool variant; no pool is reassigned."
              : pool ? "Saved beside the source. No container is reassigned. Return to a structure variant to link it deliberately."
              : "Saved beside the source. Current procedural selection profiles are unchanged. Legacy flat-pool contexts may discover added files."}
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
          {!item && !recipe && !creature && <label>
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
          </label>}
          {!pool && !item && !recipe && !creature && <label>
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
          </label>}
          <p className="muted small">
            {creature ? "Actor name and effective HP share this exact source draft. All complex fields and description remain read-only; publication requires a unique variant." : recipe ? "Recipe controls share this exact source draft, history and validation. Publication creates a new recipe ID/file only. Eligibility and observed output have separate receipts." : item ? "Component controls share this source draft, history and validation. Advanced definitions are read-only. Use References, Use binding and Factory result to distinguish declarations from observed instances."
              : pool ? "Description is retained metadata. Edit item IDs, weights and roll bounds in the table. Unknown fields remain in Source."
              : <>Description is retained metadata. Weight is a supported nonnegative
            scalar; current planned selection uses separate profiles. Geometry,
            specials and all other fields remain available in Source.</>}
          </p>
          <div className={"validation " + (document.valid ? "pass" : "fail")}>
            <strong>
              {document.valid
                ? item ? "✓ Source references and factory passed" : "✓ Production validator passed"
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
          <label htmlFor={creature ? "creature-draft-json" : recipe ? "recipe-draft-json" : item ? "item-draft-json" : pool ? "pool-draft-json" : "draft-json"}>
            {editing ? "Draft JSON" : "Source JSON"}
          </label>
          <textarea
            id={creature ? "creature-draft-json" : recipe ? "recipe-draft-json" : item ? "item-draft-json" : pool ? "pool-draft-json" : "draft-json"}
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
              {!pool && !item && !recipe && !creature && diagnosticCell(d, layoutModel(draft).model) && (
                <button
                  onClick={() =>
                    setFocus(diagnosticCell(d, layoutModel(draft).model))
                  }
                >
                  Locate cell / record
                </button>
              )}
            </article>
          ))}
          <p className="muted">
            {dirty && !verdict
              ? "Displayed source diagnostics are from the opened file. Validate the draft for a current verdict."
              : creature ? "Creature checks use the current loader and actual isolated CreatureFactory. No ongoing AI, combat or world selection is executed." : recipe ? "Recipe checks use the current loader and narrow game-owned contract. Tests use isolated production allocation and ownership exchange." : item ? "Item checks use the current loader, component capability, instance schema and actual factory. No interactive use is executed."
              : pool ? "Pool validation uses the current loader and container-pool validator. No population is sampled here."
              : "Draft validation includes a centered production stamp and initial population. Access checks use the declared main entrance when present."}
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
          <details>
            <summary>Draft verification receipt</summary>
            <pre className="raw" data-testid="draft-receipt">
              {JSON.stringify(verdict, null, 2)}
            </pre>
          </details>
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
            onClick={() => void validate()}
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
            {recipe || creature ? "Apply variant" : "Review & apply"}
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
              {creature ? "This creates one new creature definition. It does not join worldgen pools, replace existing instances, or change any authored room. Complex behavior fields remain read-only." : recipe ? "This creates an active recipe variant. New sessions recursively load it; known defaults to true and enables CraftScreen execution when requirements are met. known:false displays an unknown recipe and blocks execution. No learning route or personal-save compatibility is promised." : item && variant ? "Creates one new item. Existing pools and held instances are unchanged. Deliberately reference it from a new pool variant."
                : pool && variant ? "Creates one new pool. No structure or world is changed; the pool may remain unused until explicitly referenced."
                : variant
                ? "This creates a new definition. It does not add entries to current town or roadside selection profiles. Older flat-pool contexts can discover new definitions."
                : "This changes the meaning of an existing ID. Saved pending worlds may depend on its old content. Prefer a new variant for changed identity or meaning."}
            </p>
            <p>
              {creature ? "Exact creature bytes passed original source entitlement and real factory construction. The host rechecks current dependencies and the reviewed bytes before publishing." : recipe ? "Exact recipe bytes and output references passed the narrow game-owned contract. The host checks dependencies and revalidates before publication. Fixture evidence does not establish ordinary player crafting." : item ? "Exact item bytes passed source identity, component rules and real factory construction. The host repeats those checks before publishing."
                : pool ? "Current pool draft passed loader identity, item references and consumer constraints. The host rechecks the exact reviewed bytes and current dependencies before publishing."
                : <>Current draft: valid contract, references and centered production
              preview. Host rechecks these exact bytes before publishing.
              Natural selection and other transforms remain unverified.</>}
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
