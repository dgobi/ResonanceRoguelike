import { useEffect, useRef, useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import { listen } from "@tauri-apps/api/event";
import { Authoring } from "./Authoring";
import { contentViews } from "./ContentEditor";
import type { ContentFamily } from "./content";
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
  const [busy, setBusy] = useState(""),
    [error, setError] = useState<Failure | null>(null),
    [status, setStatus] = useState(
      "Opening the configured Resonance project…",
    ),
    [cell, setCell] = useState<[number, number] | null>(null),
    [seed, setSeed] = useState("20261023"),
    [tab, setTab] = useState<"properties" | "source">("properties");
  const [dirty, setDirty] = useState(false),
    [search, setSearch] = useState(""),
    [category, setCategory] = useState("");
  const [poolDocument, setPoolDocument] = useState<Inspection | null>(null);
  const [poolActive, setPoolActive] = useState(false), [poolDirty, setPoolDirty] = useState(false);
  const [contentDocuments, setContentDocuments] = useState<Record<string,{document:Inspection; dirty:boolean; selectedId:string}>>({});
  const [activeContent, setActiveContent] = useState("");
  const itemDocument = contentDocuments.item?.document, recipeDocument = contentDocuments.recipe?.document;
  const itemActive = activeContent === "item", recipeActive = activeContent === "recipe";
  const contentDirty = Object.values(contentDocuments).some(d=>d.dirty);
  const setItemActive = (active:boolean) => setActiveContent(current=>active ? "item" : current === "item" ? "" : current);
  const setRecipeActive = (active:boolean) => setActiveContent(current=>active ? "recipe" : current === "recipe" ? "" : current);
  const [creatureDocument, setCreatureDocument] = useState<Inspection | null>(null), [creatureActive, setCreatureActive] = useState(false), [creatureDirty, setCreatureDirty] = useState(false);
  const [selectedCreatureId, setSelectedCreatureId] = useState("");
  const itemReturnFocus = useRef<string | null>(null);
  const recipeReturnRelation = useRef("ingredient");
  useEffect(() => {
    if (recipeActive || !itemActive || !itemReturnFocus.current) return;
    const path = itemReturnFocus.current;
    const frame = requestAnimationFrame(() => {
      document.querySelector<HTMLButtonElement>(`[data-recipe-link="${path}"][data-recipe-relation="${recipeReturnRelation.current}"]`)?.focus();
      itemReturnFocus.current = null;
    });
    return () => cancelAnimationFrame(frame);
  }, [recipeActive, itemActive]);
  const [support, setSupport] = useState("");
  const [catalogPage, setCatalogPage] = useState(0);
  useEffect(()=>setCatalogPage(0),[search,category,support,assets]);
  const [itemTrail, setItemTrail] = useState<ItemTrail | null>(null);
  const [trail, setTrail] = useState<SourceTrail | null>(null), [dependencyVersion, setDependencyVersion] = useState(0);
  const [pending, setPending] = useState<null | (() => void)>(null);
  const [canvasHost, setCanvasHost] = useState<HTMLDivElement | null>(null);
  const dirtyRef = useRef(false);
  dirtyRef.current = dirty || poolDirty || contentDirty || creatureDirty;
  useEffect(() => {
    const unlisten = listen("authoring-close-requested", () => {
      const close = () => {
        void invoke("finish_close").catch((e) => setError(asFailure(e)));
      };
      if (dirtyRef.current) setPending(() => close);
      else close();
    });
    return () => {
      void unlisten.then((f) => f());
    };
  }, []);
  function protect(action: () => void) {
    if (dirtyRef.current) {
      setPending(() => action);
      return true;
    }
    return false;
  }
  const epoch = useRef(0);
  const [cancelVersion, setCancelVersion] = useState(0);
  function beginRequest(label: string) {
    const lease = requestLease(epoch, () => setBusy(""));
    setBusy(label);
    return lease;
  }
  function clear() {
    setDirty(false);
    setPoolDocument(null); setPoolActive(false); setPoolDirty(false); setTrail(null);
    setContentDocuments({}); setActiveContent(""); setItemTrail(null);
    setCreatureDocument(null); setCreatureActive(false); setCreatureDirty(false); setSelectedCreatureId("");
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
    setCreatureActive(false);
    setPoolActive(false);
    setItemActive(false); setRecipeActive(false);
    setSelected(asset);
    setFixture(null);
    setInspection(null);
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
    const token = ++epoch.current;
    setBusy("Checking repository and runtime…");
    setStatus("Opening repository…");
    try {
      const info = await call<Identity>("open_project", { path: value ?? null });
      if (token !== epoch.current) return;
      clear();
      setIdentity(info.result);
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
    if (!discard && protect(() => void refresh(asset, true))) return;
    setDirty(false);
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
  async function openPool(id: string, context: SourceTrail | null = null, discard = false, reload = false) {
    const matches = assets.filter(a => a.route === "contextual_loot_pool" && a.id === id), asset = matches[0];
    if (matches.length !== 1) { setError({code: "POOL_SOURCE", message: `Pool ${id} resolves to ${matches.length} supported files.`, remedy: "Correct duplicate/missing IDs or refresh the project catalogue."}); return; }
    if (!reload && poolDocument?.path === asset.path) { setTrail(context); setPoolActive(true); setCreatureActive(false); setItemActive(false); setRecipeActive(false); return; }
    if (poolDirty && !discard) { setPending(() => () => void openPool(id, context, true, reload)); return; }
    setBusy("Opening contextual pool…"); setError(null);
    const token = ++epoch.current;
    try {
      const r = await call<Inspection>("open_document", {asset: asset.path});
      if (token !== epoch.current) return;
      setPoolDocument(r.result); setPoolDirty(false); setPoolActive(true); setCreatureActive(false); setItemActive(false); setRecipeActive(false); setTrail(context);
      setStatus(`Opened ${asset.path}.`);
    } catch (e) { if (token === epoch.current) setError(asFailure(e)); } finally { if (token === epoch.current) setBusy(""); }
  }
  async function openContent(family:string,id:string,assetPath?:string,discard=false,reload=false,trailContext:ItemTrail|null=null) {
    const matches=assets.filter(a=>a.family_id === family && a.id === id && (!assetPath || a.path === assetPath)), asset=matches[0];
    if (!matches.length || matches.length !== 1 && !assetPath) { setError({code:"CONTENT_SOURCE",message:`${id} has ${matches.length} catalogue sources.`,remedy:"Select a specific source file to inspect ambiguity."}); return; }
    const existing=contentDocuments[family];
    const activate=()=>{setActiveContent(family);setCreatureActive(false);if(family==="item")setItemTrail(trailContext);};
    if (!reload && existing?.document.path === asset.path) {
      setContentDocuments(d=>({...d,[family]:{...d[family],selectedId:id}})); activate(); return;
    }
    if(existing?.dirty && !discard) {setPending(()=>()=>void openContent(family,id,assetPath,true,reload,trailContext));return;}
    const token=++epoch.current;setBusy("Opening content source…");setError(null);
    try {
      const r=await call<Inspection>("open_document",{asset:asset.path});if(token!==epoch.current)return;
      setContentDocuments(d=>({...d,[family]:{document:r.result,dirty:false,selectedId:id}}));activate();
      setStatus(`Opened ${asset.path}. Semantic evidence uses the registered game contract.`);
    } catch(e) {if(token===epoch.current)setError(asFailure(e));} finally {if(token===epoch.current)setBusy("");}
  }
  function openItem(id:string,context:ItemTrail|null=null,assetPath?:string,discard=false,reload=false) {
    return openContent("item",id,assetPath,discard,reload,context);
  }
  async function openCreature(id: string, assetPath: string, discard = false, reload = false) {
    const asset = assets.find(a=>a.route === "creature_definition" && a.id === id && a.path === assetPath);
    if (!asset) return;
    if (!reload && creatureDocument?.path === asset.path) { setSelectedCreatureId(id); setCreatureActive(true); return; }
    if (creatureDirty && !discard) { setPending(()=>()=>void openCreature(id,assetPath,true,reload)); return; }
    const token=++epoch.current; setBusy("Opening creature definition…"); setError(null);
    try {
      const r=await call<Inspection>("open_document",{asset:asset.path});
      if(token !== epoch.current) return;
      setCreatureDocument(r.result); setCreatureDirty(false); setSelectedCreatureId(id); setCreatureActive(true);
      setStatus(`Opened ${asset.path}. Factory construction and world selection are separate evidence.`);
    } catch(e) { if(token === epoch.current) setError(asFailure(e)); } finally { if(token === epoch.current) setBusy(""); }
  }
  async function creatureApplied(asset: string, result: unknown) {
    const token=epoch.current; setCreatureDirty(false); setReceipt(result); setDependencyVersion(v=>v+1);
    const catalog=await request<{assets:Asset[]}>("describe"); if(token !== epoch.current) return;
    setAssets(catalog.result.assets);
    const r=await call<Inspection>("open_document",{asset}); if(token !== epoch.current) return;
    verifyReopened(r.result,result); setCreatureDocument(r.result); setSelectedCreatureId(r.result.id);
    setStatus(`Creature variant saved and reopened: ${asset}. No room, saved actor or worldgen reference changed.`);
  }
  function returnToItem() {
    itemReturnFocus.current = recipeDocument?.path || null;
    setRecipeActive(false); setItemActive(true); setCreatureActive(false);
  }
  async function refreshContentContexts(token:number) {
    for (const [family,entry] of Object.entries(contentDocuments)) {
      const refreshed=await request<Inspection>("inspect",{asset:entry.document.path});
      if(token!==epoch.current)return;
      const next=refreshed.result;
      setContentDocuments(current=>{
        const live=current[family];
        if(live?.document.document_token!==entry.document.document_token || live.document.path!==next.path || live.document.sha256!==next.sha256 || live.document.family?.descriptor_sha256!==next.family?.descriptor_sha256)return current;
        return {...current,[family]:{...live,document:{...live.document,family:next.family}}};
      });
    }
  }
  async function contentApplied(family:string,asset:string,result:unknown) {
    const token=epoch.current; setReceipt(result); setDependencyVersion(v=>v+1);
    const catalog=await request<{assets:Asset[]}>("describe"); if(token!==epoch.current)return;
    setAssets(catalog.result.assets);
    const reopened=await call<Inspection>("open_document",{asset}); if(token!==epoch.current)return;
    verifyReopened(reopened.result,result);
    setContentDocuments(d=>({...d,[family]:{document:reopened.result,dirty:false,selectedId:reopened.result.id}}));
    if(poolDocument) {
      const refreshed=await request<Inspection>("inspect",{asset:poolDocument.path});if(token!==epoch.current)return;
      setPoolDocument(d=>d?.path===refreshed.result.path && d.sha256===refreshed.result.sha256 ? {...d,pool_context:refreshed.result.pool_context}:d);
    }
    await refreshContentContexts(token);if(token!==epoch.current)return;
    setStatus(`Saved and byte-checked reopen: ${asset}. ${reopened.result.family?.descriptor.publication_note || ""}`);
  }
  async function poolApplied(asset: string, result: unknown) {
    const token = epoch.current;
    setPoolDirty(false); setReceipt(result);
    const catalog = await request<{ assets: Asset[] }>("describe");
    if (token !== epoch.current) return;
    setAssets(catalog.result.assets);
    setInspection(d => d?.catalog ? {...d, catalog: {...d.catalog, loot_pools: catalog.result.assets.filter(a => a.route === "contextual_loot_pool").map(a => a.id).sort()}} : d);
    setDependencyVersion(v => v + 1);
    const r = await call<Inspection>("open_document", {asset});
    if (token !== epoch.current) return;
    verifyReopened(r.result, result);
    setPoolDocument(r.result);
    await refreshContentContexts(token);if(token!==epoch.current)return;
    setStatus(`Pool saved and reopened: ${asset}. No container references changed.`);
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
            ◈ {dirty || poolDirty || contentDirty || creatureDirty ? "Unsaved draft" : "Read-only by default"}
          </span>
        </div>
      </header>
      <div
        className={
          "workspace " +
          (inspection?.document_token || poolActive || itemActive || recipeActive || creatureActive ? "authoring-workspace" : "")
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
              Buildings, pools, items, recipes and creatures
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
                  className={"asset " + (a.path === (creatureActive ? creatureDocument?.path : recipeActive ? recipeDocument?.path : itemActive ? itemDocument?.path : poolActive ? poolDocument?.path : selected) ? "selected" : "")}
                  disabled={!!busy || a.route === "plaza"}
                  title={`${a.path} · ${a.provenance} · ${a.validation}${a.editable ? "" : " · read-only"}`}
                  data-asset={a.path}
                  onClick={() => a.route === "creature_definition" ? void openCreature(a.id,a.path) : a.family_id ? void openContent(a.family_id,a.id,a.path) : a.route === "contextual_loot_pool" ? void openPool(a.id) : void refresh(a.path)}
                >
                  <span className="asset-icon">▦</span>
                  <span>
                    <strong>{a.id}</strong>
                    <small>
                      {a.route === "creature_definition" ? `${a.name} · ${a.category}` : a.route === "recipe_definition" ? `${a.name} · ${a.execution_class}` : a.route === "item_definition" ? `${a.name} · ${a.category}` : a.route === "contextual_loot_pool" ? "Contextual loot pool" : `${a.width} × ${a.height} · ${a.category || a.route}`}
                      <br />
                      {a.path}{a.pointer || ""}
                      <br />
                      {a.path === poolDocument?.path ? poolDocument.valid ? "Source valid" : "Source invalid" : a.path === inspection?.path
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
              Structure, pool, item, recipe and creature drafts stay open independently. Campaigns are never opened.
            </small>
          </section>
        </aside>
        <section className="preview-pane">
          {(inspection?.document_token || poolActive || itemActive || recipeActive || creatureActive) && (
            <>
              <div className="building-controls">
                {poolDocument && <button disabled={!!busy} onClick={() => {setCreatureActive(false);setPoolActive(creatureActive || recipeActive || itemActive || !poolActive); setItemActive(false); setRecipeActive(false);}}>{poolActive && !itemActive && !recipeActive && !creatureActive ? "Show structure" : `Show pool ${poolDocument.id}`}</button>}
                {Object.entries(contentDocuments).map(([family,entry])=><button key={family} disabled={!!busy} onClick={()=>{setCreatureActive(false);setActiveContent(activeContent===family && !creatureActive ? "":family);}}>{activeContent===family && !creatureActive ? `Hide ${contentViews[family as ContentFamily["id"]]?.label || family}` : `Show ${family} ${entry.selectedId}`}</button>)}
                {creatureDocument && <button disabled={!!busy} onClick={()=>setCreatureActive(!creatureActive)}>{creatureActive ? "Hide creature" : `Show creature ${selectedCreatureId}`}</button>}
                {creatureActive && creatureDocument && <button disabled={!!busy} onClick={()=>void openCreature(selectedCreatureId,creatureDocument.path,false,true)}>Reload creature</button>}
                {!creatureActive && activeContent && contentDocuments[activeContent] && <button disabled={!!busy} onClick={()=>void openContent(activeContent,contentDocuments[activeContent].selectedId,contentDocuments[activeContent].document.path,false,true,itemTrail)}>Reload {activeContent}</button>}
                {!creatureActive && !recipeActive && !itemActive && poolActive && poolDocument && <button disabled={!!busy} onClick={() => void openPool(poolDocument.id, trail, false, true)}>Reload pool</button>}
                <label>
                  Preview seed
                  <input
                    aria-label="Draft preview seed"
                    value={seed}
                    onChange={(e) => setSeed(e.target.value)}
                    disabled={!!busy}
                  />
                </label>
                <button onClick={() => refresh()} disabled={!!busy || poolActive || itemActive || recipeActive || creatureActive}>
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
              display: inspection?.document_token || poolActive || itemActive || recipeActive || creatureActive ? "none" : "contents",
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
          <div className="eyebrow">04 / INSPECTOR</div>
          {!inspection?.document_token && !poolActive && !itemActive && !recipeActive && !creatureActive && (
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
          {creatureDocument && <div hidden={!creatureActive}><Authoring key={creatureDocument.document_token}
            document={creatureDocument} onDirty={setCreatureDirty} onApplied={creatureApplied} onError={setError}
            busy={busy} beginRequest={beginRequest} cancelVersion={cancelVersion} canvasHost={canvasHost} diskPreview={null} seed={Number(seed)}
            active={creatureActive} onCancel={()=>void cancel()} selectedCreatureId={selectedCreatureId} dependencyVersion={dependencyVersion} /></div>}
          {Object.entries(contentDocuments).map(([family,entry])=><div key={entry.document.document_token} hidden={activeContent!==family || creatureActive}><Authoring
            document={entry.document} onDirty={dirty=>setContentDocuments(d=>d[family]?.document.document_token===entry.document.document_token && d[family].dirty!==dirty ? {...d,[family]:{...d[family],dirty}}:d)}
            onApplied={(path,result)=>contentApplied(family,path,result)} onError={setError}
            busy={busy} beginRequest={beginRequest} cancelVersion={cancelVersion} canvasHost={canvasHost} diskPreview={null} seed={Number(seed)}
            active={activeContent===family && !creatureActive} onCancel={()=>void cancel()} dependencyVersion={dependencyVersion}
            contentNavigation={{selectedId:entry.selectedId,trail:itemTrail,
              onReturn:family==="recipe" ? itemDocument ? returnToItem:undefined : poolDocument ? ()=>{setItemActive(false);setPoolActive(true);setCreatureActive(false);}:undefined,
              onPool:id=>void openPool(id,trail),onOpen:(target,id,path)=>{recipeReturnRelation.current=document.activeElement?.getAttribute("data-recipe-relation") || "ingredient";void openContent(target,id,path);}}} /></div>)}
          {poolDocument && <div hidden={!poolActive || itemActive || recipeActive || creatureActive}><Authoring key={poolDocument.document_token}
            document={poolDocument} onDirty={setPoolDirty} onApplied={poolApplied} onError={setError}
            busy={busy} beginRequest={beginRequest} cancelVersion={cancelVersion} canvasHost={canvasHost} diskPreview={null} seed={Number(seed)}
            active={poolActive && !itemActive && !recipeActive && !creatureActive} onCancel={() => void cancel()} trail={trail}
            onItem={(id, context) => void openItem(id, context)}
            poolEntryFocus={itemTrail?.path === poolDocument.path || itemTrail?.poolId === poolDocument.id ? itemTrail.index : undefined}
            onReturn={() => setPoolActive(false)} dependencyVersion={dependencyVersion} /></div>}
          <div hidden={poolActive || itemActive || recipeActive || creatureActive}>{inspection?.document_token ? (
            <Authoring
              key={inspection.document_token}
              document={inspection}
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
              active={!poolActive && !itemActive && !recipeActive && !creatureActive}
              onPool={(id, context) => void openPool(id, context)}
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
            <h2>Discard unsaved changes?</h2>
            <p>
              Continuing will discard the in-memory edits. The source file has
              not changed.
            </p>
            <div className="edit-actions">
              <button className="primary" onClick={() => setPending(null)}>
                Keep editing
              </button>
              <button
                onClick={() => {
                  const action = pending;
                  setPending(null);
                  action();
                }}
              >
                Discard and continue
              </button>
            </div>
          </section>
        </div>
      )}
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
