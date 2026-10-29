import { useCallback, useEffect, useLayoutEffect, useRef, useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import { listen } from "@tauri-apps/api/event";
import { Authoring } from "./Authoring";
import {RoomTestPanel} from './RoomTestPanel';
import {RecoveryPanel,type RecoveryRow} from "./RecoveryPanel";
import type {RecoveryControl,RecoveredDraft} from "./recovery";
import {reconcileRead} from "./reopen";
import { WorkspaceMonitor, installDocument, type Documents, type OpenDocument, type Sweep } from "./workspace";
import { MapView } from "./MapView";
import { requestLease } from "./requests";
import {
  asFailure,
  call,
  request,
  validatePreview,
  type Identity,
  type Asset,
  type Inspection,
  type Preview,
  type Failure,
  type Diagnostic,
  type SourceTrail,
  type ItemTrail,
} from "./protocol";

function Diagnostics({ rows }: { rows: Diagnostic[] }) {
  return (
    <ul className="diagnostics">
      {rows.map((d, i) => (
        <li key={i} className={d.severity}>
          <b>{d.code}</b>
          <code>{d.field || "document"}</code>
          <p>{d.message}</p>
          <small>{d.correction}</small>
          <details>
            <summary>Source location</summary>
            <code>
              {d.path} · {d.asset}
            </code>
          </details>
        </li>
      ))}
    </ul>
  );
}
const short = (value?: string | null) =>
  value ? value.slice(0, 12) : "unavailable";
function verifyReopened(document: Inspection, receipt: unknown) {
  const expected = (receipt as {after_sha256?: string})?.after_sha256;
  if (!expected || document.sha256 !== expected)
    throw {code: "EXTERNAL_MODIFICATION_CONFLICT", message: "The reopened file differs from the published bytes.",
      remedy: "Publication completed, but a later change or reopen conflict occurred. Your draft is retained; inspect the transaction receipt and reload the target before continuing."};
}
export default function App() {
  const [path, setPath] = useState(""),
    [identity, setIdentity] = useState<Identity | null>(null),
    [assets, setAssets] = useState<Asset[]>([]),
    [selected, setSelected] = useState("");
  const [inspection, setInspection] = useState<Inspection | null>(null),
    [fixture, setFixture] = useState<Inspection | null>(null),
    [preview, setPreview] = useState<Preview | null>(null);
  const [requestBusy, setBusy] = useState(""),
    [error, setError] = useState<Failure | null>(null),
    [status, setStatus] = useState(
      "Opening the configured Resonance project…",
    ),
    [cell, setCell] = useState<[number, number] | null>(null),
    [seed, setSeed] = useState("20261023"),
    [tab, setTab] = useState<"properties" | "source">("properties");
  const [checkingDisk, setCheckingDisk] = useState(false);
  const busy = requestBusy || (checkingDisk ? "Checking saved files…" : "");
  const [dirty, setDirty] = useState(false),
    [search, setSearch] = useState(""),
    [category, setCategory] = useState("");
  const [contentDocuments, renderDocuments] = useState<Documents>({});
  const contentRef = useRef(contentDocuments);
  const recoveryControls=useRef(new Map<string,RecoveryControl>());
  const registerRecovery=useCallback((token:string,control:RecoveryControl)=>{
    recoveryControls.current.set(token,control);return ()=>{if(recoveryControls.current.get(token)===control)recoveryControls.current.delete(token);};
  },[]);
  const [recoveryOpen,setRecoveryOpen]=useState(false);
  const [recoveryVersion,setRecoveryVersion]=useState(0);
  const [resolvingDrafts,setResolvingDrafts]=useState(false);
  function setContentDocuments(update: Documents | ((current:Documents)=>Documents)) {
    const next = typeof update === "function" ? update(contentRef.current) : update;
    contentRef.current = next; renderDocuments(next);
  }
  const [activeContent, setActiveContent] = useState("");
  const [legacyReturn,setLegacyReturn]=useState<OpenDocument["returnLocation"]>();
  const contentDirty = Object.values(contentDocuments).some(d=>d.dirty);
  const scrollPositions = useRef(new Map<string, number[]>());
  useLayoutEffect(() => {
    const key = activeContent || "legacy-structure";
    const surfaces = [...document.querySelectorAll<HTMLElement>(".preview-pane, .inspector")];
    const position = scrollPositions.current.get(key) || [0, 0];
    surfaces.forEach((s,i)=>s.scrollTop=position[i]);
    // Capture while this document is visible. Layout cleanup runs after React
    // hides its panels, when the browser may already have clamped scrollTop.
    const remember = () => scrollPositions.current.set(key, surfaces.map(s=>s.scrollTop));
    surfaces.forEach(s=>s.addEventListener("scroll", remember));
    const selectedTab = document.querySelector<HTMLElement>(".document-tabs [aria-current]");
    if (selectedTab?.parentElement) {
      const strip=selectedTab.parentElement, item=selectedTab.getBoundingClientRect(), bounds=strip.getBoundingClientRect();
      if(item.left<bounds.left)strip.scrollLeft+=item.left-bounds.left;
      else if(item.right>bounds.right)strip.scrollLeft+=item.right-bounds.right;
    }
    return () => { surfaces.forEach(s=>s.removeEventListener("scroll", remember)); };
  }, [activeContent]);
  const [support, setSupport] = useState("");
  const [catalogPage, setCatalogPage] = useState(0);
  useEffect(()=>setCatalogPage(0),[search,category,support,assets]);
  const [dependencyVersion, setDependencyVersion] = useState(0);
  const [pending, setPending] = useState<null | (() => void)>(null);
  const [pendingFiles, setPendingFiles] = useState<string[]>([]);
  const dirtyFiles = useRef<string[]>([]);
  dirtyFiles.current = [dirty ? inspection?.path : null,
    ...Object.values(contentDocuments).filter(d=>d.dirty).map(d=>d.document.path)].filter((p):p is string=>!!p);
  const [canvasHost, setCanvasHost] = useState<HTMLDivElement | null>(null);
  const dirtyRef = useRef(false);
  dirtyRef.current = dirty || contentDirty;
  useEffect(() => {
    const unlisten = listen("authoring-close-requested", () => {
      const close = () => {
        void invoke("finish_close").catch((e) => setError(asFailure(e)));
      };
      if (dirtyRef.current) { setPendingFiles(dirtyFiles.current); setPending(() => close); }
      else close();
    });
    return () => {
      void unlisten.then((f) => f());
    };
  }, []);
  function protect(action: () => void) {
    if (dirtyRef.current) {
      setPendingFiles(dirtyFiles.current);
      setPending(() => action);
      return true;
    }
    return false;
  }
  function pendingOwners(){return Object.entries(contentRef.current).filter(([,entry])=>pendingFiles.includes(entry.document.path));}
  const canKeepRecovery=!!pendingFiles.length && pendingFiles.every(path=>Object.values(contentDocuments).some(e=>e.document.path===path));
  async function resolvePending(keep:boolean){
    setResolvingDrafts(true);
    try{
      for(const [token] of pendingOwners()){
        const control=recoveryControls.current.get(token);if(!control)throw new Error("Draft is still opening; keep editing and try again.");
        if(keep)await control.flush();else await control.discard();
      }
      const action=pending;setPending(null);action?.();setRecoveryVersion(v=>v+1);
    }catch(e){setError(asFailure(e));}finally{setResolvingDrafts(false);}
  }
  async function recoverDraft(row:RecoveryRow,target?:string,expected?:string){
    const asset=target || row.source;
    const existing=Object.entries(contentRef.current).find(([,e])=>e.document.path===asset);
    if(existing){activateContent(existing[0]);setRecoveryOpen(false);throw new Error("This file already has an open owner. Its draft was focused and preserved. Close it deliberately before recovering this copy.");}
    if(!identity || identity.source.root.toLowerCase().replaceAll("\\","/")!==row.project.toLowerCase().replaceAll("\\","/"))throw new Error("Open this recovery record's project normally before editing. The stored text remains available here.");
    setBusy("Recovering stored draft…");let opened:Inspection|undefined;
    try{
      const catalog=await request<{assets:Asset[]}>("describe");setAssets(catalog.result.assets);
      opened=(await call<Inspection>("open_document",{asset,expectedSha256:expected})).result;
      if(target)await invoke("reconcile_recovery",{token:opened.document_token,key:row.key,generation:row.generation});
      else opened={...opened,recovery:await invoke<RecoveredDraft>("restore_recovery",{token:opened.document_token,key:row.key,generation:row.generation})};
      setContentDocuments(d=>{const next=installDocument(d,opened!,opened!.id);if(!target)next[opened!.document_token!].dirty=true;return next;});
      activateContent(opened.document_token!);setRecoveryOpen(false);setRecoveryVersion(v=>v+1);
      setError(null);
      setStatus(target ? "Saved bytes reconciled without another write." : "Exact draft recovered. Validate again; previous reviews and previews grant no authority.");
    }catch(e){if(opened)await invoke("close_document",{token:opened.document_token}).catch(()=>{});throw e;}finally{setBusy("");}
  }
  const epoch = useRef(0);
  const monitor = useRef(new WorkspaceMonitor());
  const monitorReady = useRef(false);
  monitorReady.current = !!identity && !busy;
  useEffect(() => {
    const check = () => void monitor.current.check(async()=> {
      setCheckingDisk(true);
      try { return (await call<Sweep>("workspace_disk")).result; }
      finally { setCheckingDisk(false); }
    }, ()=>monitorReady.current)
      .catch(e=>{ const error=asFailure(e); if (!["BUSY","CANCELLED"].includes(error.code)) setError(error); });
    const timer = setInterval(check, 3000);
    return () => { clearInterval(timer); monitor.current.reset(); };
  }, []);
  const [cancelVersion, setCancelVersion] = useState(0);
  function beginRequest(label: string) {
    const lease = requestLease(epoch, () => setBusy(""));
    setBusy(label);
    return lease;
  }
  function clear() {
    monitor.current.reset();
    setDirty(false);
    setContentDocuments({}); setActiveContent("");
    setIdentity(null);
    setAssets([]);
    setSelected("");
    setInspection(null);
    setFixture(null);
    setPreview(null);
    setCell(null);
    setError(null);
  }
  async function loadAsset(asset: string, token: number, generate = true, reopened?: Inspection) {

    setActiveContent("");
    setSelected(asset);
    setFixture(null);
    setPreview(null);
    setCell(null);
    setBusy("Validating source…");
    const editable =
      asset.startsWith("roguelike/data/buildings/") &&
      !asset.includes("/plaza/") || (asset.startsWith("roguelike/data/layouts/") && asset != "roguelike/data/layouts/starting_lab.json") || asset === "roguelike/docs/examples/g17_authored_creature_room.json";
    const inspected = reopened ? {result: reopened} : editable
      ? await call<Inspection>("open_document", { asset })
      : await request<Inspection>("inspect", { asset });
    if (token !== epoch.current) return;
    setInspection(inspected.result);
    setDirty(false);
    if (!inspected.result.valid) {
      setStatus("Production validation failed. Review the diagnostics.");
      return;
    }
    if (generate) {
      const numericSeed = Number(seed);
      if (
        !Number.isInteger(numericSeed) ||
        numericSeed < 0 ||
        numericSeed > 2147483647
      )
        throw {
          code: "INVALID_SEED",
          message: "Enter an integer seed from 0 to 2147483647.",
          remedy: "Correct the seed and generate again.",
        };
      setBusy("Generating production scene…");
      const generated = await request<Preview>("preview", {
        asset,
        seed: numericSeed,
      });
      if (token !== epoch.current) return;
      const result = validatePreview(generated.result);
      if (
        result.source.game_source_sha256 !==
          inspected.result.source.game_source_sha256 ||
        result.source.catalog_sha256 !== inspected.result.source.catalog_sha256
      )
        throw {
          code: "SOURCE_CHANGED",
          message:
            "Game source or data changed between validation and preview.",
          remedy: "Refresh source to obtain a coherent preview.",
        };
      setPreview({ ...result, host_ms: generated.elapsed });
      setIdentity((previous) =>
        previous ? { ...previous, source: result.source } : previous,
      );
      setStatus(
        result.passed
          ? "Saved source preview passed. Draft results are shown in the editor."
          : "Preview generated with production occupancy failures. Inspect diagnostics.",
      );
    }
  }
  useEffect(() => { void open(); }, []);
  async function open(value?: string, discard = false) {
    if (busy.includes("applying")) return;
    if (!discard && protect(() => void open(value, true))) return;
    monitor.current.reset();
    setCancelVersion(v=>v+1);
    const token = ++epoch.current;
    setBusy("Checking repository and runtime…");
    setStatus("Opening repository…");
    try {
      const info = await call<Identity>("open_project", { path: value ?? null });
      if (token !== epoch.current) return;
      clear();
      setIdentity(info.result);
      setRecoveryVersion(v=>v+1);
      setPath(info.result.source.root);
      setBusy("Discovering supported layouts…");
      const catalog = await request<{ assets: Asset[] }>("describe");
      if (token !== epoch.current) return;
      setAssets(catalog.result.assets);
      if (catalog.result.assets.length)
        await loadAsset(
          (
            catalog.result.assets.find((a) => a.id === "starting_lab") ||
            catalog.result.assets[0]
          ).path,
          token,
        );
      else
        setStatus(
          "Compatible project, but no supported authored layouts were found.",
        );
    } catch (e) {
      if (token === epoch.current) {
        setError(asFailure(e));
        setStatus("Integration needs attention.");
      }
    } finally {
      if (token === epoch.current) setBusy("");
    }
  }
  async function pick() {
    try {
      const result = await invoke<string | null>("choose_project");
      if (result) await open(result);
    } catch (e) {
      setError(asFailure(e));
    }
  }
  async function refresh(asset = selected, discard = false) {
    if (!discard && dirty) {setPendingFiles([inspection!.path]);setPending(()=>()=>void refresh(asset,true));return;}
    const token = ++epoch.current;
    setError(null);
    try {
      await loadAsset(asset, token);
    } catch (e) {
      if (token === epoch.current) setError(asFailure(e));
    } finally {
      if (token === epoch.current) setBusy("");
    }
  }
  async function negativeControl() {
    const token = ++epoch.current;
    setBusy("Validating disposable invalid fixture…");
    setError(null);
    try {
      const result = await request<Inspection>("inspect", {
        asset: selected,
        invalid_fixture: true,
      });
      if (token === epoch.current) {
        setFixture(result.result);
        setStatus(
          result.result.valid
            ? "Unexpected: invalid fixture passed."
            : "Invalid fixture rejected by the production validator. Shipped source preserved.",
        );
      }
    } catch (e) {
      if (token === epoch.current) setError(asFailure(e));
    } finally {
      if (token === epoch.current) setBusy("");
    }
  }
  async function cancel(close = false, discard = false) {
    if (close && !discard && protect(() => void cancel(true, true))) return;
    try {
      await invoke(close ? "close_project" : "cancel_worker");
    } catch (e) {
      setError(asFailure(e));
      return;
    }
    ++epoch.current;
    monitor.current.reset();
    setCancelVersion(v => v + 1);
    setError(null);
    setBusy("");
    if (close) clear();
    setStatus(
      close
        ? "Project closed. Source files preserved."
        : "Cancelled. Temporary preview work discarded; run again to retry.",
    );
  }
  const [receipt, setReceipt] = useState<unknown>(null);
  function openPool(id:string, context:SourceTrail|null=null, _discard=false, _reload=false, origin="") {
    const from=origin ? contentRef.current[origin] : undefined;
    return openContent("pool",id,undefined,false,false,null,{token:from?.document.document_token || "legacy-structure",label:`container ${context?.id || "source"}`,focus:document.activeElement as HTMLElement,location:context?.draft ? {text:context.draft,index:context.index}:undefined},context);
  }
  const opening = useRef(new Map<string, Promise<void>>());
  function activateContent(token:string) { setActiveContent(token); }
  async function openContent(family:string,id:string,assetPath?:string,discard=false,reload=false,trailContext:ItemTrail|null=null,origin?:OpenDocument["origin"],poolTrail?:SourceTrail|null) {
    const matches=assets.filter(a=>a.family_id === family && a.id === id && (!assetPath || a.path === assetPath)), asset=matches[0];
    if (!matches.length || matches.length !== 1 && !assetPath) { setError({code:"CONTENT_SOURCE",message:`${id} has ${matches.length} catalogue sources.`,remedy:"Select a specific source file to inspect ambiguity."}); return; }
    const existing=Object.values(contentRef.current).find(d=>d.document.path===asset.path);
    const existingToken=existing?.document.document_token;
    const activate=(key:string)=>{
      setContentDocuments(d=>d[key] ? {...d,[key]:{...d[key],selectedId:id,...(poolTrail!==undefined ? {poolTrail} : {}),...(origin ? {origin,trail:trailContext} : trailContext ? {trail:trailContext} : {})}} : d);
      activateContent(key);
    };
    if (!reload && existingToken) {
      activate(existingToken); return;
    }
    if(existing?.dirty && !discard) {setPendingFiles([existing.document.path]);setPending(()=>()=>void openContent(family,id,assetPath,true,reload,trailContext,origin));return;}
    const key=asset.path;
    if(opening.current.has(key)) return opening.current.get(key);
    const token=++epoch.current;setBusy("Opening content source…");setError(null);
    const task=(async()=>{
      try {
        const r=await call<Inspection>("open_document",{asset:asset.path,replaceToken:reload && existingToken ? recoveryControls.current.get(existingToken)?.owner() || existingToken : null});if(token!==epoch.current)return;
        setContentDocuments(d=>installDocument(d,r.result,id,reload ? existingToken : undefined));activate(r.result.document_token!);
        setStatus(`Opened ${asset.path}. References and previews use saved dependencies.`);
      } catch(e) {if(token===epoch.current)setError(asFailure(e));} finally {if(token===epoch.current)setBusy("");}
    })();
    opening.current.set(key,task);
    try {await task;} finally {if(opening.current.get(key)===task)opening.current.delete(key);}
  }
  async function closeContent(token:string, discard=false) {
    const entry=contentRef.current[token]; if(!entry)return;
    if(entry.dirty && !discard) {setPendingFiles([entry.document.path]);setPending(()=>()=>void closeContent(token,true));return;}
    try {
      await invoke("close_document",{token:recoveryControls.current.get(token)?.owner() || token,handoffId:recoveryControls.current.get(token)?.handoff()});
      setContentDocuments(d=>{const next={...d};delete next[token];return next;});
      setActiveContent(active=>active===token ? Object.keys(contentRef.current).at(-1) || "" : active);
    } catch(e) {setError(asFailure(e));}
  }
  function returnToOrigin(entry:OpenDocument) {
    const origin=entry.origin; if(!origin)return;
    if(contentRef.current[origin.token]) {setContentDocuments(d=>({...d,[origin.token]:{...d[origin.token],returnLocation:origin.location}}));activateContent(origin.token);}
    else if(origin.token==="legacy-structure" && inspection) {setLegacyReturn(origin.location);setActiveContent("");}
    else {setError({code:"ORIGIN_UNAVAILABLE",message:`The originating ${origin.label} was closed or replaced.`,remedy:"Open its file deliberately from the catalogue; no other document was selected."});return;}
    requestAnimationFrame(()=>{if(!origin.location && origin.focus?.isConnected)origin.focus.focus({preventScroll:true});});
  }
  async function refreshContentContexts(token:number) {
    for (const [key,entry] of Object.entries(contentRef.current)) {
      const refreshed=await request<Inspection>("inspect",{asset:entry.document.path});
      if(token!==epoch.current)return;
      const next=refreshed.result;
      setContentDocuments(current=>{
        const live=current[key];
        if(live?.document.document_token!==entry.document.document_token || live.document.path!==next.path || live.document.sha256!==next.sha256 || live.document.family?.descriptor_sha256!==next.family?.descriptor_sha256 || JSON.stringify(live.document.family?.effective_operations)!==JSON.stringify(next.family?.effective_operations))return current;
        return {...current,[key]:{...live,document:{...live.document,family:next.family}}};
      });
    }
  }
  async function contentApplied(owner:string,asset:string,result:unknown,covered:()=>void=()=>{}) {
    covered();
    const token=epoch.current; setReceipt(result); setDependencyVersion(v=>v+1);
    const originating=contentRef.current[owner];
    if(!originating)throw new Error("File saved; originating document is no longer open.");
    const catalog=await request<{assets:Asset[]}>("describe"); if(token!==epoch.current)return;
    setAssets(catalog.result.assets);
    const handoffId=(result as {handoff_id?:string}).handoff_id;
    const guard=()=>{if(token!==epoch.current || !contentRef.current[owner])throw new Error("Origin changed during reopening; recovery retained.");covered();};
    const reopened=await reconcileRead(guard,
      ()=>call<Inspection>("open_document",{asset,replaceToken:owner,expectedSha256:(result as {after_sha256:string}).after_sha256,handoffId}),
      async reopened=>{verifyReopened(reopened.result,result);if(handoffId)await invoke("acknowledge_reopen",{handoffId});},
      reopened=>{setContentDocuments(d=>installDocument(d,reopened.result,reopened.result.id,owner));setActiveContent(active=>active===owner ? reopened.result.document_token! : active);});
    if(inspection?.document_token){
      const refreshed=await request<Inspection>("inspect",{asset:inspection.path});if(token!==epoch.current)return;
      setInspection(current=>current?.path===refreshed.result.path && current.sha256===refreshed.result.sha256 ? {...current,catalog:refreshed.result.catalog}:current);
    }
    await refreshContentContexts(token);if(token!==epoch.current)return;
    setStatus(`Saved and byte-checked reopen: ${asset}. ${reopened.result.family?.descriptor.publication_note || ""}`);
  }
  async function applied(asset: string, result: unknown) {
    const token = epoch.current;
    setDependencyVersion(v => v + 1);
    setReceipt(result);
    const catalog = await request<{ assets: Asset[] }>("describe");
    if (token !== epoch.current) return;
    setAssets(catalog.result.assets);
    // Verify before replacing the mounted draft; failure retains its exact text.
    const reopened = await call<Inspection>("open_document", {asset});
    if (token !== epoch.current) return;
    verifyReopened(reopened.result, result);
    setDirty(false);
    await loadAsset(asset, token, true, reopened.result);
    if (token !== epoch.current) return;
    setStatus(`Applied and reopened ${asset}. Current selection profiles unchanged.`);
  }
  const visibleAssets = assets.filter(
    (a) =>
      (!category || a.category === category || a.route === category) && (!support || (support === "supported" ? a.editable : !a.editable)) &&
      `${a.id} ${a.name || ""} ${a.category || ""} ${a.path} ${a.result_item || ""} ${a.execution_class || ""} ${a.editable ? "supported" : "read-only"}`
        .toLowerCase()
        .includes(search.toLowerCase()),
  );
  const tile = cell && preview ? preview.terrain[cell[1]][cell[0]] : null;
  const objects =
    cell && preview
      ? [
          ...preview.decor,
          ...preview.items,
          ...preview.containers,
          ...preview.actors,
        ].filter((p) => p.x === cell[0] && p.y === cell[1])
      : [];
  return (
    <main>
      <header className="topbar">
        <div className="brand">
          <span className="brandmark">R</span>
          <div>
            <h1>
              Resonance <em>Workbench</em>
            </h1>
            <p>Content editor</p>
          </div>
        </div>
        <div className="top-meta">
          <span className="chip">W4C</span>
          <span className="read-only">
            ◈ {dirty || contentDirty ? "Unsaved draft" : "Read-only by default"}
          </span>
        </div>
      </header>
      <div
        className={
          "workspace " +
          (inspection?.document_token || !!activeContent ? "authoring-workspace" : "")
        }
      >
        <aside className="sidebar">
          <section>
            <div className="eyebrow">01 / PROJECT</div>
            <h2>Source connection</h2>
            <p className="muted">
              The validated project opens automatically. Change it here to relocate.
            </p>
            <button className="primary full" onClick={pick} disabled={!!busy}>
              Change Project <span>↗</span>
            </button>
            <form
              onSubmit={(e) => {
                e.preventDefault();
                void open(path);
              }}
            >
              <label htmlFor="project-path">Repository directory</label>
              <input
                id="project-path"
                value={path}
                onChange={(e) => setPath(e.target.value)}
                placeholder="G:\GameDev\RoguelikeProject"
                spellCheck={false}
              />
              <button className="full" disabled={!path || !!busy}>
                Open directory
              </button>
            </form>
            <button className="full" onClick={()=>setRecoveryOpen(true)}>Recover drafts</button>
            {identity && (
              <div className="project-details">
                <div className="health" data-testid="startup-ready">● Integration ready · {identity.host_runtime.mode} · protocol {identity.protocol}</div>
                <code data-testid="active-project">{identity.source.root}</code>
                {identity.project_selection.notices.map((notice, i) => <p className="muted" key={i}>{notice}</p>)}
                {identity.host_runtime.notice && <p className="muted">{identity.host_runtime.notice}</p>}
                <dl>
                  <dt>Branch</dt>
                  <dd>{identity.source.branch || "No Git branch"}</dd>
                  <dt>Revision</dt>
                  <dd title={identity.source.commit || ""}>
                    {short(identity.source.commit)}
                  </dd>
                  <dt>Game files</dt>
                  <dd>
                    {identity.source.game_dirty === null
                      ? "Git unavailable"
                      : identity.source.game_dirty
                        ? "Uncommitted changes"
                        : "Clean"}
                  </dd>
                  <dt>Contract</dt>
                  <dd>{identity.contract}</dd>
                </dl>
                <details>
                  <summary>Runtime & source identity</summary>
                  <p>
                    Python {identity.runtime.python}
                    <br />
                    Bridge {identity.worker_version} · protocol{" "}
                    {identity.protocol}
                  </p>
                  <code>{identity.runtime.executable}</code>
                  <code>{identity.host_runtime.bridge}</code>
                  <p>{identity.creature_contract} · {identity.families?.map(f=>f.contract).join(" · ")}</p>
                  <p>Project: {identity.project_selection.selected_from}</p>
                  <p>
                    Game SHA {short(identity.source.game_source_sha256)}
                    <br />
                    Catalog SHA {short(identity.source.catalog_sha256)}
                  </p>
                </details>
                <button className="full quiet" onClick={() => cancel(true)}>
                  Close project
                </button>
              </div>
            )}
          </section>
          <section className="content-section">
            <div className="eyebrow">02 / CONTENT</div>
            <h2>
              Content definitions <span className="count">{assets.length}</span>
            </h2>
            <p className="muted">
              Buildings, pools, items, recipes, texts and creatures
            </p>
            <button className="full" onClick={()=>{setCategory("creatures");setSearch("");}}>Creatures</button>
            <label>
              Search ID, name or path
              <input
                aria-label="Search ID, name or path"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </label>
            <label>
              Category / route
              <select
                aria-label="Category / route"
                value={category}
                onChange={(e) => setCategory(e.target.value)}
              >
                <option value="">All supported content</option>
                {[...new Set(["creature_definition", "recipe_definition", "item_definition", ...assets.map((a) => a.category || a.route)])]
                  .sort()
                  .map((c) => (
                    <option key={c} value={c}>
                      {c}
                    </option>
                  ))}
              </select>
            </label>
            <label>Support<select aria-label="Support status" value={support} onChange={e=>setSupport(e.target.value)}><option value="">All</option><option value="supported">Supported for writing</option><option value="read-only">Read-only</option></select></label>
            <div className="asset-list">
              {visibleAssets.slice(catalogPage * 100, (catalogPage + 1) * 100).map((a) => (
                <button
                  key={a.path + (a.pointer || "")}
                  className={"asset " + (a.path === (activeContent ? contentDocuments[activeContent]?.document.path : selected) ? "selected" : "")}
                  disabled={!!busy || a.route === "plaza"}
                  title={`${a.path} · ${a.provenance} · ${a.validation}${a.editable ? "" : " · read-only"}`}
                  data-asset={a.path}
                  onClick={() => a.family_id ? void openContent(a.family_id,a.id,a.path) : a.route === "contextual_loot_pool" ? void openPool(a.id) : void refresh(a.path)}
                >
                  <span className="asset-icon">▦</span>
                  <span>
                    <strong>{a.id}</strong>
                    <small>
                      {a.family_id ? `${a.name || a.id} · ${a.execution_class || a.category || a.family_id}` : a.route === "creature_definition" ? `${a.name} · ${a.category}` : a.route === "contextual_loot_pool" ? "Contextual loot pool" : `${a.width} × ${a.height} · ${a.category || a.route}`}
                      <br />
                      {a.path}{a.pointer || ""}
                      <br />
                      {a.path === inspection?.path
                        ? inspection.valid
                          ? "Source valid"
                          : "Source invalid"
                        : a.validation}{" "}
                      · {a.editable ? "editable" : "read-only"}
                    </small>
                  </span>
                </button>
              ))}
            </div>
            {visibleAssets.length > 100 && <div className="edit-actions"><button disabled={catalogPage === 0} onClick={()=>setCatalogPage(v=>v-1)}>Previous page</button><small>{catalogPage+1} / {Math.ceil(visibleAssets.length/100)}</small><button disabled={(catalogPage+1)*100 >= visibleAssets.length} onClick={()=>setCatalogPage(v=>v+1)}>Next page</button></div>}
            {!assets.length && (
              <p className="empty-small">
                Supported definitions appear here after a successful connection.
              </p>
            )}
          </section>
          <section className="scope">
            <span className="eyebrow">THIS WORKSPACE</span>
            <p>Draft → validate → review → apply</p>
            <small>
              Building, pool, room, creature, item, recipe, text and typography drafts share tabs and recovery. Campaigns are never opened.
            </small>
          </section>
        </aside>
        <section className="preview-pane">
          {(inspection?.document_token || !!activeContent) && (
            <>
              <div className="building-controls">
                <nav className="document-tabs" aria-label="Open content documents">
                  {Object.entries(contentDocuments).map(([token,entry])=><button key={token} data-document-tab={entry.document.path}
                    title={entry.document.path} aria-current={activeContent===token ? "page" : undefined}
                    onClick={()=>activateContent(token)}>
                    <strong>{entry.dirty ? "● " : ""}{entry.selectedId || entry.document.path}</strong><small>{entry.document.path}</small>
                  </button>)}
                </nav>
                {!!activeContent && <button disabled={busy.includes("applying")} onClick={()=>setActiveContent("")}>Show structure</button>}
                {activeContent && contentDocuments[activeContent] && <>
                  <button disabled={!!busy} onClick={()=>{const entry=contentRef.current[activeContent];void openContent(entry.document.family!.id,entry.selectedId,entry.document.path,false,true,entry.trail,entry.origin);}}>Reload document</button>
                  <button disabled={busy.includes("applying")} onClick={()=>void closeContent(activeContent)}>Close document</button>
                </>}
                <label>
                  Preview seed
                  <input
                    aria-label="Draft preview seed"
                    value={seed}
                    onChange={(e) => setSeed(e.target.value)}
                    disabled={!!busy}
                  />
                </label>
                <button onClick={() => refresh()} disabled={!!busy || !!activeContent}>
                  ↻ Generate / refresh
                </button>
              </div>
              <div ref={setCanvasHost} className="layout-host" />
              {receipt !== null && (
                <details className="context" data-testid="apply-receipt">
                  <summary>Applied file · transaction receipt</summary>
                  <pre className="raw">{JSON.stringify(receipt, null, 2)}</pre>
                </details>
              )}
            </>
          )}
          <div
            className="saved-preview-pane"
            style={{
              display: inspection?.document_token || !!activeContent ? "none" : "contents",
            }}
          >
            <div className="pane-heading">
              <div>
                <div className="eyebrow">03 / PRODUCTION PREVIEW</div>
                <h2>
                  {inspection
                    ? inspection.id.replaceAll("_", " ")
                    : "Generation preview"}
                </h2>
              </div>
              <div className="generation-controls">
                <label>
                  Seed
                  <input
                    aria-label="Generation seed"
                    value={seed}
                    onChange={(e) => setSeed(e.target.value)}
                    inputMode="numeric"
                    disabled={!!busy}
                  />
                </label>
                <button
                  onClick={() => refresh()}
                  disabled={!selected || !!busy}
                >
                  ↻ Generate / refresh
                </button>
              </div>
            </div>
            <div className="canvas-area">
              {preview && !inspection?.document_token ? (
                <MapView
                  preview={preview}
                  onCell={setCell}
                  onError={(e) =>
                    setError({
                      code: "VIEWPORT_FAILED",
                      message: String(e),
                      remedy:
                        "Check WebView2 graphics support, then reopen the app.",
                    })
                  }
                />
              ) : (
                <div className="canvas-empty">
                  <div className="empty-symbol">⌖</div>
                  <h3>
                    {busy
                      ? "Loading source"
                      : identity
                        ? "Ready for a production preview"
                        : "Generation preview"}
                  </h3>
                  <p>
                    {busy ||
                      "Connect a Resonance repository to see a generated local map, its terrain IDs and authored objects."}
                  </p>
                  <span>
                    80 columns · 43 rows · authoritative Python generation
                  </span>
                </div>
              )}
              {busy && (
                <div className="busy-overlay" role="status">
                  <span className="spinner" />
                  {busy}
                  <button onClick={() => cancel()}>Cancel</button>
                </div>
              )}
            </div>
            {inspection?.document_token && (
              <p className="render-note">
                Preview is from the on-disk source. Unsaved drafts are not
                rendered; their validation appears in the editor.
              </p>
            )}
            {receipt !== null && !inspection?.document_token && (
              <details className="context" data-testid="apply-receipt">
                <summary>Applied file · transaction receipt</summary>
                <pre>{JSON.stringify(receipt, null, 2)}</pre>
              </details>
            )}
            <div className="legend">
              <span>
                <i style={{ background: "#424c47" }} />
                Ground
              </span>
              <span>
                <i style={{ background: "#687274" }} />
                Walls
              </span>
              <span>
                <i style={{ background: "#c79855" }} />
                Doors
              </span>
              <span>
                <i style={{ background: "#e9d39a" }} />
                Items
              </span>
              <span>
                <i style={{ background: "#e0ac6e" }} />
                Containers
              </span>
              <span>
                <i style={{ background: "#c1b2d9" }} />
                Decor
              </span>
              <span>
                <i style={{ background: "#def4e3" }} />
                Arrival
              </span>
            </div>
            <div className="provenance">
              <div>
                <span className="eyebrow">GENERATION RECEIPT</span>
                <p>
                  {preview
                    ? `${preview.elapsed_ms.toFixed(1)} ms generation · ${preview.host_ms} ms worker request · seed ${preview.seed}`
                    : "No scene generated yet"}
                </p>
                <small>
                  {preview
                    ? `Scene seed ${preview.scene_seed} · ${preview.generation_revision} · terrain ${short(preview.terrain_sha256)}`
                    : "Generation runs in a cancellable local process."}
                </small>
              </div>
              <span className="pill">
                {preview ? "Production data" : "Awaiting source"}
              </span>
            </div>
            <p className="render-note">
              Production-data-backed Workbench rendering. Revealed terrain and
              initial objects; no player FOV or game-renderer fidelity claim.
            </p>
            {preview && (
              <details className="context">
                <summary>Controlled generation context</summary>
                <p>{preview.context}</p>
                <code>{JSON.stringify(preview.scene_address)}</code>
                {!preview.passed && (
                  <pre>
                    {JSON.stringify(preview.occupant_diagnostics, null, 2)}
                  </pre>
                )}
              </details>
            )}
          </div>
        </section>
        <aside className="inspector">
          <RoomTestPanel document={activeContent ? contentDocuments[activeContent]?.document : undefined} dirty={!!(activeContent&&contentDocuments[activeContent]?.dirty)} dependencyVersion={dependencyVersion}/>
          <div className="eyebrow">04 / INSPECTOR</div>
          {!inspection?.document_token && !activeContent && (
            <div className="tabs">
              <button
                className={tab === "properties" ? "active" : ""}
                onClick={() => setTab("properties")}
              >
                Properties
              </button>
              <button
                className={tab === "source" ? "active" : ""}
                onClick={() => setTab("source")}
              >
                Source JSON
              </button>
            </div>
          )}
          {Object.entries(contentDocuments).map(([token,entry])=><div key={token} data-document-inspector={entry.document.path} hidden={activeContent!==token}><Authoring
            document={entry.document} onDirty={dirty=>setContentDocuments(d=>d[token] && d[token].dirty!==dirty ? {...d,[token]:{...d[token],dirty}}:d)}
            onApplied={(path,result,covered)=>contentApplied(token,path,result,covered)} onError={setError} registerRecovery={registerRecovery}
            subscribeDisk={monitor.current.subscribe} busy={busy} beginRequest={beginRequest} cancelVersion={cancelVersion} canvasHost={canvasHost} diskPreview={null} seed={Number(seed)}
            active={activeContent===token} onCancel={()=>void cancel()} dependencyVersion={dependencyVersion}
            onPool={(id,context)=>void openPool(id,context,false,false,token)}
            contentNavigation={{poolTrail:entry.poolTrail,returnLocation:entry.returnLocation,
              onPoolItem:(id,index,text,path)=>void openContent("item",id,undefined,false,false,{poolId:entry.selectedId,path,index,itemId:id,structure:entry.poolTrail},{token,label:`pool ${entry.selectedId} row ${index+1}`,focus:null,location:{text,index,itemId:id}}),selectedId:entry.selectedId,trail:entry.trail,relatedRoom:entry.document.family?.id==="assignment" && entry.origin ? contentDocuments[entry.origin.token]?.selectedId : undefined,
              onReturn:entry.origin ? ()=>returnToOrigin(entry):undefined,returnLabel:entry.origin ? `Return to ${entry.origin.label}`:undefined,
              onPool:id=>void openPool(id,null,false,false,token),onOpen:(target,id,path,location)=>void openContent(target,id,path,false,false,null,{token,location,label:`${entry.document.family!.id} ${entry.selectedId}`,focus:document.activeElement as HTMLElement})}} /></div>)}
          <div hidden={!!activeContent}>{inspection?.document_token ? (
            <Authoring
              key={inspection.document_token}
              document={inspection}
              subscribeDisk={monitor.current.subscribe}
              onDirty={setDirty}
              onApplied={applied}
              onError={setError}
              busy={busy}
              beginRequest={beginRequest}
              cancelVersion={cancelVersion}
              canvasHost={canvasHost}
              diskPreview={preview}
              seed={Number(seed)}
              onCancel={() => void cancel()}
              active={!activeContent}
              onPool={(id, context) => void openPool(id, context)}
              contentNavigation={{returnLocation:legacyReturn,onOpen:()=>{}}}
              dependencyVersion={dependencyVersion}
            />
          ) : inspection ? (
            tab === "source" ? (
              <pre className="raw">{inspection.raw}</pre>
            ) : (
              <>
                <h2>{inspection.id}</h2>
                <p className="asset-description">{inspection.description}</p>
                <code className="filepath">{inspection.path}</code>
                <dl>
                  <dt>Source shape</dt>
                  <dd>
                    {inspection.width} × {inspection.height}
                  </dd>
                  <dt>Special records</dt>
                  <dd>{inspection.special_count}</dd>
                  <dt>Preview origin</dt>
                  <dd>{preview?.origin.join(", ") || "—"}</dd>
                  <dt>Source bytes</dt>
                  <dd>
                    {inspection.source_unchanged ? "Unchanged" : "Check source"}
                  </dd>
                  <dt>File SHA-256</dt>
                  <dd title={inspection.sha256}>{short(inspection.sha256)}</dd>
                </dl>
                <div
                  className={
                    "validation " + (inspection.valid ? "pass" : "fail")
                  }
                >
                  <strong>
                    {inspection.valid
                      ? "✓ Production validator passed"
                      : "× Production validation failed"}
                  </strong>
                  <small>structure_contract.compile_structure</small>
                  <span>
                    {inspection.diagnostics.length} diagnostic
                    {inspection.diagnostics.length !== 1 ? "s" : ""}
                  </span>
                </div>
                <details>
                  <summary>
                    {inspection.diagnostics.length} production diagnostics
                  </summary>
                  <Diagnostics rows={inspection.diagnostics} />
                </details>
                <div className="tile-inspection">
                  <div className="eyebrow">TILE UNDER CURSOR</div>
                  <h3 data-testid="cell">
                    {cell ? `(${cell[0]}, ${cell[1]})` : "Select a cell"}
                  </h3>
                  <code data-testid="tile-id">
                    {tile || "Hover or click a cell"}
                  </code>
                  {tile && preview && (
                    <p>
                      {preview.legend[tile].walkable
                        ? "Walkable terrain"
                        : "Terrain blocks movement"}{" "}
                      ·{" "}
                      {preview.legend[tile].transparent
                        ? "Transparent"
                        : "Opaque"}
                    </p>
                  )}
                  {objects.length > 0 && (
                    <pre>{JSON.stringify(objects, null, 2)}</pre>
                  )}
                </div>
                <button
                  className="full"
                  onClick={negativeControl}
                  disabled={!!busy}
                >
                  Test invalid disposable fixture
                </button>
                <p className="muted small">
                  Copies this definition to a temporary folder and deliberately
                  breaks its declared width.
                </p>
                {fixture && (
                  <div className="fixture" data-testid="fixture-result">
                    <strong>
                      {fixture.valid
                        ? "Unexpected pass"
                        : "Invalid fixture correctly rejected"}
                    </strong>
                    <Diagnostics
                      rows={fixture.diagnostics.filter(
                        (d) => d.severity === "error",
                      )}
                    />
                    <small>
                      Original bytes preserved. Temporary fixture removed.
                    </small>
                  </div>
                )}
              </>
            )
          ) : (
            <p className="empty-small">
              Select a supported layout to inspect its source and production
              validation results.
            </p>
          )}</div>
        </aside>
      </div>
      {pending && (
        <div className="modal-shade">
          <section
            className="confirmation"
            role="dialog"
            aria-label="Unsaved draft"
          >
            <h2>Resolve unsaved drafts</h2>
            <ul>{pendingFiles.map(path=><li key={path}><code>{path}</code></li>)}</ul>
            <p>
              Keep registered drafts in recovery, or deliberately discard their copies. Published files are unchanged by these choices.
            </p>
            <div className="edit-actions">
              <button className="primary" disabled={resolvingDrafts} onClick={() => setPending(null)}>
                Keep editing
              </button>
              {canKeepRecovery ? <button disabled={resolvingDrafts} onClick={()=>void resolvePending(true)}>Keep for Recovery and Close</button> : <p>Legacy structure and pool drafts are memory-only. Resolve those drafts first to keep registered drafts for recovery.</p>}
              <button disabled={resolvingDrafts} onClick={()=>void resolvePending(false)}>
                Discard and continue
              </button>
            </div>
          </section>
        </div>
      )}
      <RecoveryPanel open={recoveryOpen} onClose={()=>setRecoveryOpen(false)} onRestore={recoverDraft} onError={setError} refreshVersion={recoveryVersion}/>
      <footer
        className={"runtime " + (error ? "runtime-error" : "")}
        aria-live="polite"
      >
        <span className={"status-dot " + (busy ? "working" : "")} />
        <div>
          <strong>
            {error ? `${error.code} · ${error.message}` : busy || status}
          </strong>
          {error && <p>{error.remedy}</p>}
        </div>
        <span className="runtime-tag">LOCAL / OFFLINE · W4C</span>
      </footer>
    </main>
  );
}
