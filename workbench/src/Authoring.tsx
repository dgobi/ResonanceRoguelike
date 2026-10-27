import { invoke } from "@tauri-apps/api/core";
import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { LayoutEditor } from "./LayoutEditor";
import { PoolEditor } from "./PoolEditor";
import { ContentEditor, contentViews, type ContentNavigation } from "./ContentEditor";
import { familyProblem, type ContentFamily } from "./content";
import { previewProblem, type FamilyPreview } from "./familyData";
import { CreatureEditor } from "./CreatureEditor";
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
  type CreatureContext,
} from "./protocol";
import { type RequestLease } from "./requests";
import type { Disk, DiskSubscription } from "./workspace";
import { currentVerdict, scalarEdit, sourceDiff, syntax } from "./draft";
import { requireCovered, type Candidate } from "./reopen";
import { Checkpoints, type RegisterRecovery, type RecoveryStatus } from "./recovery";

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
  family?: ContentFamily;
  family_preview?: FamilyPreview | null;
  creature_context?: CreatureContext;
};
export function Authoring({
  document,
  onDirty,
  onApplied,
  onError,
  busy,
  beginRequest,
  cancelVersion,
  canvasHost,
  diskPreview,
  seed,
  onCancel,
  active = true,
  onPool,
  trail,
  onReturn,
  dependencyVersion = 0,
  onItem, poolEntryFocus, contentNavigation, selectedCreatureId,
  subscribeDisk,
  registerRecovery,
}: {
  document: Inspection;
  onDirty: (dirty: boolean) => void;
  onApplied: (path: string, receipt: unknown, covered?: () => void) => Promise<void>;
  onError: (e: Failure | null) => void;
  busy: string;
  beginRequest: (label: string) => RequestLease;
  cancelVersion: number;
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
  poolEntryFocus?: number;
  contentNavigation?: ContentNavigation;
  selectedCreatureId?: string;
  subscribeDisk: DiskSubscription;
  registerRecovery?: RegisterRecovery;
}) {
  const pool = document.route === "contextual_loot_pool";
  const content = document.family;
  const contentProblem = content ? familyProblem(content) : "";
  const view = content ? contentViews[content.id] : undefined;
  const variantOnly = content && (contentProblem || !content.descriptor.policy.operations.includes("edit"));
  const creature = document.route === "creature_definition";
  const submap = document.route === "authored_submap";
  const writable = !(content || creature || submap) || document.editable && (!content || !familyProblem(content));
  const revocation = useRef<Promise<unknown>>(Promise.resolve());
  function revoke() {
    const next = revocation.current.catch(() => {}).then(() => invoke("invalidate_document", {token: document.document_token}));
    revocation.current = next;
    void next.catch(() => {}); // Callers retain the rejection; no obsolete global error handler.
    return next;
  }
  const recovered=document.recovery;
  const [restored,setRestored]=useState(!!recovered);
  const initial:Candidate={text:recovered?.draft ?? document.raw,variant:recovered?.variant ?? false,variantId:recovered?.variant_id ?? ""};
  const acknowledged = useRef(initial);
  const editVersion = useRef(0);
  const applying = useRef(false);
  const [pendingEdit, setPendingEdit] = useState(false);
  const [draft, setDraft] = useState(initial.text),
    [editing, setEditing] = useState(!!recovered);
  const [tab, setTab] = useState("properties"),
    [verdict, setVerdict] = useState<Verdict | null>(null);
  const [variant, setVariant] = useState(initial.variant),
    [variantId, setVariantId] = useState(initial.variantId);
  const [disk, setDisk] = useState<Disk | null>(null),
    [confirm, setConfirm] = useState(false);
  const [localError, setLocalError] = useState("");
  const [saved, setSaved] = useState<({path:string; after_sha256:string; handoff_id?:string} & {candidate:Candidate}) | null>(recovered?.published ? {...recovered.published,candidate:initial} : null);
  const savedRef=useRef(saved);savedRef.current=saved;
  const closingOwner=useRef(document.document_token!);
  const intent = useRef({variant,variantId});
  const [recoveryStatus,setRecoveryStatus]=useState<RecoveryStatus|null>(recovered ? {state:"saved",generation:recovered.generation} : null);
  const checkpoints=useRef<Checkpoints|null>(null);
  if(!checkpoints.current && content)checkpoints.current=new Checkpoints(()=>invoke("checkpoint_document",{token:document.document_token}),setRecoveryStatus);
  const [evidenceVersion, setEvidenceVersion] = useState(dependencyVersion);
  const [previewEvidence,setPreviewEvidence]=useState<{frame:FamilyPreview;text:string;version:number;dependencies:number;stale:boolean}|null>(null);
  const [focus, setFocus] = useState<{ cell: Cell; layer: Layer } | null>(null);
  const history = useRef(new CanvasHistory()),
    gesture = useRef<string | null>(null);
  const [, updateHistory] = useState(0);
  const version = useRef(0),
    latest = useRef(draft),
    mounted = useRef(true);
  const dirty = draft !== document.raw || variant || !!variantId || !!saved || restored;
  const parsed = syntax(draft);
  const sourceId = content ? `${view?.sourceId}-${document.document_token}` : creature ? "creature-draft-json" : pool ? "pool-draft-json" : "draft-json";
  let values: Record<string, unknown> = {};
  try {
    values = JSON.parse(draft.replace(/^\uFEFF/, "")) || {};
  } catch {
    /* diagnostics below */
  }
  const target = variant
    ? `${document.path === "roguelike/docs/examples/g17_authored_creature_room.json" ? "roguelike/data/layouts" : document.path.slice(0, document.path.lastIndexOf("/"))}/${variantId}.json`
    : document.path;
  useEffect(() => {
    version.current++;
    setVerdict(null);
    setPreviewEvidence(p=>p ? {...p,stale:true} : p);
    setConfirm(false);
      if (submap) revoke();
  }, [dependencyVersion, seed]);
  useEffect(() => { setConfirm(false); }, [active]);
  useEffect(() => { version.current++; setVerdict(null); setConfirm(false); setPreviewEvidence(p=>p ? {...p,stale:true} : p); }, [cancelVersion]);
  useEffect(() => {
    onDirty(dirty);
  }, [dirty, onDirty]);
  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
      version.current++;
      checkpoints.current?.stop();
    };
  }, []);
  async function flushRecovery(){
    await revocation.current.catch(()=>{});
    // Force a host snapshot too: completed-publication facts can advance the
    // checkpoint independently of frontend edit callbacks.
    await checkpoints.current?.flush();
    const result=await invoke<{generation:number;token:string}>("checkpoint_document",{token:document.document_token,handoffId:savedRef.current?.handoff_id});
    closingOwner.current=result.token;
    setRecoveryStatus({state:"saved",generation:result.generation});
  }
  async function discardRecovery(){
    await revocation.current.catch(()=>{});
    checkpoints.current?.stop();
    try{closingOwner.current=await invoke<string>("discard_document_draft",{token:document.document_token,handoffId:savedRef.current?.handoff_id});}
    catch(e){setRecoveryStatus({state:"error",generation:0,message:asFailure(e).message});throw e;}
    finally{checkpoints.current=content ? new Checkpoints(()=>invoke("checkpoint_document",{token:document.document_token}),setRecoveryStatus) : null;}
    setRecoveryStatus(null);
  }
  useEffect(()=>registerRecovery?.(document.document_token!,{flush:flushRecovery,discard:discardRecovery,handoff:()=>savedRef.current?.handoff_id,owner:()=>closingOwner.current}),[document.document_token,registerRecovery]);
  useEffect(() => subscribeDisk(document.document_token!, () => {
    const revision = version.current;
    return row => {
      if (!mounted.current || revision !== version.current) return;
      if (row.disk) setDisk(row.disk);
      if (row.error || row.disk?.dependencies_changed || row.disk?.changed) {
        version.current++; setVerdict(null); setConfirm(false);
        setPreviewEvidence(p=>p ? {...p,stale:true} : p);
        if (row.error) setLocalError(row.error.message);
      }
    };
  }), [document.document_token, subscribeDisk]);
  function change(text: string, visual = false, nextIntent=intent.current) {
    if (applying.current || busy.includes("applying") || busy.includes("repository")) return;
    // WebView textarea events may repeat the same normalized CRLF value on
    // focus changes. A no-op must not start another acknowledgement/render loop.
    if (text === latest.current && nextIntent.variant===intent.current.variant && nextIntent.variantId===intent.current.variantId) return;
    if (!visual) {
      history.current.clear();
      gesture.current = null;
    }
    const edit = ++editVersion.current;
    onDirty(true);
    const candidate={text,...nextIntent};
    const admitted = content ? revocation.current.catch(()=>{}).then(()=>invoke<number>("edit_document",{
      token:document.document_token,sequence:edit,draft:text,variant:nextIntent.variant,variantId:nextIntent.variantId,
    })) : revoke();
    revocation.current=admitted;void admitted.catch(()=>{});
    intent.current=nextIntent;setVariant(nextIntent.variant);setVariantId(nextIntent.variantId);
    setPendingEdit(true);
    latest.current = text;
    version.current++;
    setDraft(text);
    setPreviewEvidence(p=>p ? {...p,stale:true} : p);
    setVerdict(null);
    setConfirm(false);
    setLocalError("");
    void admitted.then(generation => {
      acknowledged.current = candidate;
      if(content)checkpoints.current?.accepted(generation as number);
      if (mounted.current && editVersion.current === edit) setPendingEdit(false);
    }, error => {
      if (mounted.current && editVersion.current === edit) {
        onError(asFailure(error));
        latest.current = acknowledged.current.text;
        intent.current={variant:acknowledged.current.variant,variantId:acknowledged.current.variantId};
        setDraft(acknowledged.current.text);setVariant(acknowledged.current.variant);setVariantId(acknowledged.current.variantId);
        setPendingEdit(false);
        history.current.clear();
        setLocalError("Edit was not accepted. Publication is in progress.");
      }
    });
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
  async function validate(showDiff = true, previewInputs?:Record<string,number>) {
    const v = ++version.current,
      text = latest.current;
    const request = beginRequest(previewInputs ? "Rendering registered preview…" : "Validating unsaved draft…");
    setPreviewEvidence(p=>p ? {...p,stale:true} : p);
    setVerdict(null);
    onError(null);
    try {
      await revocation.current;
      if (!request.current() || v !== version.current) return;
      const r = await call<Verdict>("validate_document", {
        token: document.document_token,
        draft: text,
        variantId: variant ? variantId : null,
        seed,
        previewInputs: previewInputs || null,
      });
      if (
        mounted.current && request.current() &&
        currentVerdict(v, version.current, text, latest.current)
      ) {
        setVerdict(r.result);
        if(previewInputs && r.result.family_preview) {
          const problem=previewProblem(r.result.family_preview);
          if(problem) throw new Error(problem);
          setPreviewEvidence({frame:r.result.family_preview,text,version:cancelVersion,dependencies:dependencyVersion,stale:false});
        }
        if (content || creature || submap) { setEvidenceVersion(dependencyVersion); setDisk(d=>d ? {...d, dependencies_changed:false} : d); }
        if (!r.result.valid || showDiff)
          setTab(r.result.valid ? "diff" : "problems");
      }
    } catch (e) {
      if (mounted.current && request.current() && v === version.current) onError(asFailure(e));
    } finally {
      request.finish();
    }
  }
  async function apply() {
    if (pendingEdit || applying.current || !verdict?.review_token) return;
    applying.current = true;
    const candidate = {text:latest.current,...intent.current};
    setConfirm(false);
    const request = beginRequest("Revalidating and applying one file…");
    onError(null);
    try {
      if(content)await flushRecovery();
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
      if (!request.current()) return;
      setSaved({...r.result,candidate});
      setVerdict(null);
      await onApplied(r.result.path, r.result, () => requireCovered(candidate,{text:latest.current,...intent.current}));
    } catch (e) {
      if (request.current()) {
        onError(asFailure(e));
        setVerdict(null);
        onDirty(latest.current !== document.raw);
      }
    } finally {
      applying.current = false;
      request.finish();
    }
  }
  async function recoverReopen() {
    if (!saved) return;
    const request = beginRequest("Reopening saved file…");
    onError(null);
    try {
      if(!saved.handoff_id && recovered)throw new Error("This receipt is historical. Keep this draft for recovery and use Recover drafts → Reconcile saved file. No write will be repeated.");
      const covered=()=>requireCovered(saved.candidate,{text:latest.current,...intent.current});
      covered();
      await revocation.current;
      covered();
      await onApplied(saved.path, saved, covered);
    }
    catch (e) { if (request.current()) onError(asFailure(e)); }
    finally { request.finish(); }
  }
  const reason = saved ? "File saved. Retry verified reopen before publishing again." : pendingEdit ? "Waiting for edit acknowledgement." : !editing
    ? "Begin editing to create a draft."
    : (variantOnly || creature || submap) && !variant
      ? "Create a unique new variant before publication."
    : !dirty
      ? "No unsaved source changes."
      : parsed.diagnostics.length
        ? "Correct JSON syntax first."
        : variant && !variantId
          ? "Enter a new variant ID."
          : disk?.changed
            ? "Disk changed: inspect and reload or keep your draft."
            : !verdict?.valid || !verdict.review_token
              ? "Validate this exact draft before applying."
              : busy
                ? "Wait for the active request."
                : "";
  return (
    <section className="authoring" data-testid="authoring" data-edit-pending={pendingEdit}>
      {content && <p className="notice" data-testid="recovery-status">
        {recoveryStatus?.state==="pending" ? "Recovery pending · checkpoints within 500 ms of accepted edits" : recoveryStatus?.state==="error" ? `Unable to save recovery: ${recoveryStatus.message}` : recoveryStatus?.state==="saved" ? `Recovery checkpoint saved · generation ${recoveryStatus.generation}` : "Recovery available for accepted item, recipe and text edits"}
        {recoveryStatus?.state==="error" && <button onClick={()=>void flushRecovery().catch(e=>onError(asFailure(e)))}>Retry recovery save</button>}
      </p>}
      {saved && <div className="notice warning" data-testid="saved-reopen-failed">
        <strong>File saved; reopen failed or incomplete.</strong>
        <p>{saved.path}. This draft and the save receipt are retained.</p>
        <pre className="raw">{JSON.stringify(saved, null, 2)}</pre>
        <button disabled={!!busy} onClick={()=>void recoverReopen()}>Retry verified reopen</button>
      </div>}
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
      {content && canvasHost && createPortal(<div hidden={!active}><ContentEditor
        family={verdict?.family || content} navigation={contentNavigation || {onOpen:()=>{}}}
        draft={draft} path={target} dirty={dirty} validated={!!verdict?.valid}
        evidenceStale={!!disk?.changed || !!disk?.dependencies_changed || evidenceVersion !== dependencyVersion}
        disabled={!writable ? "Read-only source or unsupported capability." : !editing ? "Begin edit to change this definition." : disk?.changed ? "Disk changed. Draft retained; reload or reconcile in Source." : busy.includes("applying") ? "Publication in progress." : ""}
        busy={!!busy} onCancel={onCancel} onSource={()=>setTab("source")} onProbe={()=>void validate(false)}
        preview={previewEvidence?.frame || null} previewStale={!previewEvidence || previewEvidence.stale || previewEvidence.text!==draft || previewEvidence.frame.path!==target || previewEvidence.version!==cancelVersion || previewEvidence.dependencies!==dependencyVersion || !!disk?.changed || !!disk?.dependencies_changed}
        onPreview={inputs=>void validate(false,inputs)}
        onEdit={visualEdit} onUndo={()=>historyStep(false)} onRedo={()=>historyStep(true)} canUndo={!!history.current.undoStack.length} canRedo={!!history.current.redoStack.length}
      /></div>, canvasHost)}
      {creature && canvasHost && createPortal(<div hidden={!active}><CreatureEditor
        draft={draft} path={target} context={verdict?.creature_context || document.creature_context} selectedId={selectedCreatureId}
        active={active} dirty={dirty} validated={!!verdict?.valid} evidenceStale={!!disk?.changed || !!disk?.dependencies_changed || evidenceVersion !== dependencyVersion}
        disabled={!writable ? "Read-only creature family or unresolved source." : !editing ? "Begin edit to change creature properties." : disk?.changed ? "Disk changed. Draft retained; reload or reconcile in Source." : busy.includes("applying") ? "Publication in progress." : ""}
        busy={!!busy} beginRequest={beginRequest} cancelVersion={cancelVersion} onCancel={onCancel} onSource={()=>setTab("source")} onFactory={()=>void validate(false)}
        onEdit={visualEdit} onUndo={()=>historyStep(false)} onRedo={()=>historyStep(true)} canUndo={!!history.current.undoStack.length} canRedo={!!history.current.redoStack.length}
      /></div>, canvasHost)}
      {active && !pool && !content && !creature && canvasHost &&
        createPortal(
          <LayoutEditor
            draft={draft}
            authoredSubmap={submap}
            sourcePath={target}
            catalog={document.catalog}
            previewDisabled={!writable || !!disk?.changed || pendingEdit}
            disabled={
              !writable ? "Read-only source. Open a supported layout in data/layouts to author a variant." : !editing
                ? submap ? "Begin edit to place creatures." : "Begin edit to paint."
                : disk?.changed
                  ? "Disk changed: reload or reconcile in Source before editing."
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
            diskPreview={submap && (disk?.changed || disk?.dependencies_changed || evidenceVersion !== dependencyVersion) ? null : diskPreview}
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
      {submap && document.path.includes("/docs/examples/") && <p className="notice">Read-only G17 example. Begin edit creates an in-memory creature draft; publication can only create a new file in data/layouts. Saved preview uses the example sidecar; draft preview uses the actual generated arrival.</p>}
      <p
        className={disk?.changed ? "notice warning" : "notice"}
        data-testid="draft-state"
      >
        {pendingEdit ? "Edit pending" : disk?.changed
          ? "Externally changed · unsaved draft retained"
          : dirty
            ? "Unsaved draft"
            : editing
              ? "Editing · no changes"
              : "Read-only · source unchanged"}
      </p>
      <p className="muted small">
        {creature ? "creature_definition" : content ? document.route : pool ? "contextual_loot_pool" : `${document.route} · ${document.width} × ${document.height} · ${document.special_count} specials`} · file {document.sha256.slice(0, 12)}
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
            disabled={!!busy || !!saved}
            onClick={() => void (async()=>{
              if(content)await discardRecovery();else await revoke();
              latest.current=document.raw;intent.current={variant:false,variantId:""};acknowledged.current={text:document.raw,...intent.current};
              setDraft(document.raw);setEditing(false);setVariant(false);setVariantId("");setSaved(null);setRestored(false);setVerdict(null);history.current.clear();
            })().catch(e=>onError(asFailure(e)))}
          >
            Discard / Revert
          </button>
          <button
            disabled={!!busy}
            onClick={() => {
              change(latest.current,false,{...intent.current,variant:!intent.current.variant});
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
              let text=latest.current;try{text=scalarEdit(text,"id",e.target.value);}catch{/* Keep invalid text exact while retaining target intent. */}
              change(text,false,{...intent.current,variantId:e.target.value});
            }}
          />
          <small>
            {submap ? "Saving a layout does not automatically make it appear in a new campaign. Only a new layout file is created; no access sidecar is written." : creature ? "Creates a new ID/file beside the source. No worldgen pool, saved actor or authored room is reassigned." : content ? content.descriptor.publication_note
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
          {!content && !creature && !submap && <label>
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
          {!pool && !content && !creature && !submap && <label>
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
            {submap ? "Creature-only mode uses the same source draft, history and validation. Terrain, decor, arrival, other specials and unknown metadata stay read-only. Validation uses the real generated arrival; no separate access sidecar is required." : creature ? "Actor name and effective HP share this exact source draft. All complex fields and description remain read-only; publication requires a unique variant." : content ? view?.hint
              : pool ? "Description is retained metadata. Edit item IDs, weights and roll bounds in the table. Unknown fields remain in Source."
              : <>Description is retained metadata. Weight is a supported nonnegative
            scalar; current planned selection uses separate profiles. Geometry,
            specials and all other fields remain available in Source.</>}
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
          <label htmlFor={sourceId}>
            {editing ? "Draft JSON" : "Source JSON"}
          </label>
          <textarea
            id={sourceId}
            className="source-editor"
            spellCheck={false}
            value={draft}
            readOnly={!editing || busy.includes("applying") || busy.includes("repository")}
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
              {!pool && !content && !creature && diagnosticCell(d, layoutModel(draft).model) && (
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
              : creature ? "Creature checks use the current loader and actual isolated CreatureFactory. No ongoing AI, combat or world selection is executed." : content ? view?.hint : pool ? "Pool validation uses the current loader and container-pool validator. No population is sampled here."
              : submap ? "Draft validation uses the real authored-submap scene, generated arrival and initial actor occupancy. Source cells and translated scene cells are distinct."
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
            disabled={!!busy || !dirty || pendingEdit}
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
            {variantOnly || creature || submap ? "Apply variant" : "Review & apply"}
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
              {submap ? "This creates one new authored layout file. Saving a layout does not automatically make it appear in a new campaign. Existing source, arrival context and world selection are unchanged." : creature ? "This creates one new creature definition. It does not join worldgen pools, replace existing instances, or change any authored room. Complex behavior fields remain read-only." : content ? content.descriptor.publication_note
                : pool && variant ? "Creates one new pool. No structure or world is changed; the pool may remain unused until explicitly referenced."
                : variant
                ? "This creates a new definition. It does not add entries to current town or roadside selection profiles. Older flat-pool contexts can discover new definitions."
                : "This changes the meaning of an existing ID. Saved pending worlds may depend on its old content. Prefer a new variant for changed identity or meaning."}
            </p>
            <p>
              {creature ? "Exact creature bytes passed original source entitlement and real factory construction. The host rechecks current dependencies and the reviewed bytes before publishing." : content ? "Exact source passed the registered semantic adapter. The host rechecks the original source, descriptor, dependencies and reviewed bytes before publication."
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
