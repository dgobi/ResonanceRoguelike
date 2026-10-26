import { useEffect, useRef, useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import { listen } from "@tauri-apps/api/event";
import { Authoring } from "./Authoring";
import { MapView } from "./MapView";
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
      "Choose a local Resonance repository to begin.",
    ),
    [cell, setCell] = useState<[number, number] | null>(null),
    [seed, setSeed] = useState("20261023"),
    [tab, setTab] = useState<"properties" | "source">("properties");
  const [dirty, setDirty] = useState(false),
    [search, setSearch] = useState(""),
    [category, setCategory] = useState("");
  const [poolDocument, setPoolDocument] = useState<Inspection | null>(null);
  const [poolActive, setPoolActive] = useState(false), [poolDirty, setPoolDirty] = useState(false);
  const [trail, setTrail] = useState<SourceTrail | null>(null), [dependencyVersion, setDependencyVersion] = useState(0);
  const [pending, setPending] = useState<null | (() => void)>(null);
  const [canvasHost, setCanvasHost] = useState<HTMLDivElement | null>(null);
  const dirtyRef = useRef(false);
  dirtyRef.current = dirty || poolDirty;
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
  function clear() {
    setDirty(false);
    setPoolDocument(null); setPoolActive(false); setPoolDirty(false); setTrail(null);
    setIdentity(null);
    setAssets([]);
    setSelected("");
    setInspection(null);
    setFixture(null);
    setPreview(null);
    setCell(null);
    setError(null);
  }
  async function loadAsset(asset: string, token: number, generate = true) {
    setPoolActive(false);
    setSelected(asset);
    setFixture(null);
    setInspection(null);
    setPreview(null);
    setCell(null);
    setBusy("Validating source…");
    const editable =
      asset.startsWith("roguelike/data/buildings/") &&
      !asset.includes("/plaza/");
    const inspected = editable
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
          ? "Ready · production validation and initial occupancy passed."
          : "Preview generated with production occupancy failures. Inspect diagnostics.",
      );
    }
  }
  async function open(value: string, discard = false) {
    if (!discard && protect(() => void open(value, true))) return;
    const token = ++epoch.current;
    clear();
    setPath(value);
    setBusy("Checking repository and runtime…");
    setStatus("Opening repository…");
    try {
      const info = await call<Identity>("open_project", { path: value });
      if (token !== epoch.current) return;
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
    ++epoch.current;
    try {
      await invoke(close ? "close_project" : "cancel_worker");
    } catch (e) {
      setError(asFailure(e));
      setBusy("");
      return;
    }
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
    if (!reload && poolDocument?.path === asset.path) { setTrail(context); setPoolActive(true); return; }
    if (poolDirty && !discard) { setPending(() => () => void openPool(id, context, true, reload)); return; }
    setBusy("Opening contextual pool…"); setError(null);
    try {
      const r = await call<Inspection>("open_document", {asset: asset.path});
      setPoolDocument(r.result); setPoolDirty(false); setPoolActive(true); setTrail(context);
      setStatus(`Opened ${asset.path}.`);
    } catch (e) { setError(asFailure(e)); } finally { setBusy(""); }
  }
  async function poolApplied(asset: string, result: unknown) {
    setPoolDirty(false); setReceipt(result);
    const catalog = await request<{ assets: Asset[] }>("describe");
    setAssets(catalog.result.assets);
    setInspection(d => d?.catalog ? {...d, catalog: {...d.catalog, loot_pools: catalog.result.assets.filter(a => a.route === "contextual_loot_pool").map(a => a.id).sort()}} : d);
    setDependencyVersion(v => v + 1);
    const r = await call<Inspection>("open_document", {asset});
    setPoolDocument(r.result);
    setStatus(`Pool saved and reopened: ${asset}. No container references changed.`);
  }
  async function applied(asset: string, result: unknown) {
    setDirty(false);
    setDependencyVersion(v => v + 1);
    setReceipt(result);
    const catalog = await request<{ assets: Asset[] }>("describe");
    setAssets(catalog.result.assets);
    await refresh(asset, true);
    setStatus(
      `Applied and reopened ${asset}. Current selection profiles unchanged.`,
    );
  }
  const visibleAssets = assets.filter(
    (a) =>
      (!category || a.category === category || a.route === category) &&
      `${a.id} ${a.name || ""} ${a.path}`
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
          <span className="chip">W3A · BUILDINGS & LOOT POOLS</span>
          <span className="read-only">
            ◈ {dirty || poolDirty ? "Unsaved draft" : "Read-only by default"}
          </span>
        </div>
      </header>
      <div
        className={
          "workspace " +
          (inspection?.document_token || poolActive ? "authoring-workspace" : "")
        }
      >
        <aside className="sidebar">
          <section>
            <div className="eyebrow">01 / PROJECT</div>
            <h2>Source connection</h2>
            <p className="muted">
              Open the game checkout to inspect its live rules and content.
            </p>
            <button className="primary full" onClick={pick} disabled={!!busy}>
              Choose repository <span>↗</span>
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
                <div className="health">● Integration ready</div>
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
              Edit ordinary buildings and contextual loot pools
            </p>
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
                {[...new Set(assets.map((a) => a.category || a.route))]
                  .sort()
                  .map((c) => (
                    <option key={c} value={c}>
                      {c}
                    </option>
                  ))}
              </select>
            </label>
            <div className="asset-list">
              {visibleAssets.map((a) => (
                <button
                  key={a.path}
                  className={"asset " + (a.path === (poolActive ? poolDocument?.path : selected) ? "selected" : "")}
                  disabled={!!busy || a.route === "plaza"}
                  title={`${a.path} · ${a.provenance} · ${a.validation}${a.editable ? "" : " · read-only"}`}
                  data-asset={a.path}
                  onClick={() => a.route === "contextual_loot_pool" ? void openPool(a.id) : void refresh(a.path)}
                >
                  <span className="asset-icon">▦</span>
                  <span>
                    <strong>{a.id}</strong>
                    <small>
                      {a.route === "contextual_loot_pool" ? "Contextual loot pool" : `${a.width} × ${a.height} · ${a.category || a.route}`}
                      <br />
                      {a.path}
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
              One building and one pool draft can stay open. Items are read-only. Campaigns are never opened.
            </small>
          </section>
        </aside>
        <section className="preview-pane">
          {(inspection?.document_token || poolActive) && (
            <>
              <div className="building-controls">
                {poolDocument && <button disabled={!!busy} onClick={() => setPoolActive(!poolActive)}>{poolActive ? "Show structure" : `Show pool ${poolDocument.id}`}</button>}
                {poolActive && poolDocument && <button disabled={!!busy} onClick={() => void openPool(poolDocument.id, trail, false, true)}>Reload pool</button>}
                <label>
                  Preview seed
                  <input
                    aria-label="Draft preview seed"
                    value={seed}
                    onChange={(e) => setSeed(e.target.value)}
                    disabled={!!busy}
                  />
                </label>
                <button onClick={() => refresh()} disabled={!!busy || poolActive}>
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
              display: inspection?.document_token || poolActive ? "none" : "contents",
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
          {!inspection?.document_token && !poolActive && (
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
          {poolDocument && <div hidden={!poolActive}><Authoring key={poolDocument.document_token}
            document={poolDocument} onDirty={setPoolDirty} onApplied={poolApplied} onError={setError}
            busy={busy} setBusy={setBusy} canvasHost={canvasHost} diskPreview={null} seed={Number(seed)}
            active={poolActive} onCancel={() => void cancel()} trail={trail}
            onReturn={() => setPoolActive(false)} dependencyVersion={dependencyVersion} /></div>}
          <div hidden={poolActive}>{inspection?.document_token ? (
            <Authoring
              key={inspection.document_token}
              document={inspection}
              onDirty={setDirty}
              onApplied={applied}
              onError={setError}
              busy={busy}
              setBusy={setBusy}
              canvasHost={canvasHost}
              diskPreview={preview}
              seed={Number(seed)}
              onCancel={() => void cancel()}
              active={!poolActive}
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
        <span className="runtime-tag">LOCAL / OFFLINE · W3A</span>
      </footer>
    </main>
  );
}
