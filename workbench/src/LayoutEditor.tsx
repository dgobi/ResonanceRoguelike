import {BuildingGeometry,PlacementControls,DeleteSurfaceRecord} from "./BuildingControls";
import {entranceCells,matchingGoals,type Placement} from "./building";
import { useMemo, useState } from "react";
import { LayoutCanvas, type Tool } from "./LayoutCanvas";
import { MapView } from "./MapView";
import {RoomGeometry,ItemFields,DecorFields,DecorSummary} from "./RoomControls";
import {
  containerEditable,
  creatureEditable, addCreature, editCreature, removeCreature,
  addRecord,deleteRecord,recordKind,
  diagnosticCell,
  editContainer,
  layoutModel,
  paint,
  type Catalog,
  type Cell,
  type Layer,
  type Special,
} from "./layout";
import type { Diagnostic, Preview } from "./protocol";

export type LayoutProps = {
  draft: string;
  authoredSubmap?: boolean;
  sourcePath?: string;
  catalog?: Catalog;
  disabled: string;
  previewDisabled: boolean;
  diagnostics: Diagnostic[];
  preview: Preview | null;
  diskPreview: Preview | null;
  previewHash?: string;
  previewBusy: boolean;
  onPreview: () => void;
  onCancel: () => void;
  onEdit: (edit: (source: string) => string, label: string) => void;
  onGesture: (active: boolean) => void;
  onUndo: () => void;
  onRedo: () => void;
  canUndo: boolean;
  canRedo: boolean;
  onError: (e: unknown) => void;
  focus: { cell: Cell; layer: Layer; index?:number } | null;
  onPool?: (id: string, index: number, record: Special) => void;
  onLinked?: (family:string,id:string,path?:string,location?:{text:string;index:number})=>void;
};
export function LayoutEditor(p: LayoutProps) {
  const parsed = useMemo(() => layoutModel(p.draft), [p.draft]),
    m = parsed.model;
  const [layer, setLayer] = useState<Layer>(p.authoredSubmap ? "specials" : "terrain"),
    [tool, setTool] = useState<Tool>("select"),
    [view, setView] = useState("source");
  const [visible, setVisible] = useState<Record<Layer, boolean>>({
    terrain: true,
    decor: true,
    specials: true,
  });
  const [selected, setSelected] = useState<Cell | null>(null),
    [hover, setHover] = useState<Cell | null>(null),
    [specialIndex, setSpecialIndex] = useState<number | null>(null);
  const [search, setSearch] = useState(""),
    [glyph, setGlyph] = useState(""),
    [decor, setDecor] = useState("");
  const [runtimeCell, setRuntimeCell] = useState<Cell | null>(null);
  const [placing, setPlacing] = useState(false), [creatureId, setCreatureId] = useState("");
  const [placementKind,setPlacementKind]=useState<"creature"|"item"|"container"|"decor">(p.authoredSubmap?"creature":"item"),[itemId,setItemId]=useState(""),[containerId,setContainerId]=useState("crate");
  const placementId=placementKind==="creature"?creatureId:placementKind==="item"?itemId:placementKind==="decor"?decor:containerId;
  const [overlay,setOverlay]=useState("");
  const [orientation,setOrientation]=useState(0);
  const [lastFocus, setLastFocus] = useState(p.focus);
  if (p.focus !== lastFocus) {
    setLastFocus(p.focus);
    if (p.focus) {
      setSelected(p.focus.cell);
      const index = p.focus.index ??
        (m?.special_tiles?.findIndex(
          (s) => s.x === p.focus!.cell[0] && s.y === p.focus!.cell[1],
        ) ?? -1);
      setSpecialIndex(index >= 0 ? index : null);
      setLayer(p.focus.layer);
      setVisible((v) => ({ ...v, [p.focus!.layer]: true }));
      setView("source");
    }
  }
  const activeGlyph =
    m && glyph in m.legend ? glyph : m ? Object.keys(m.legend)[0] : "";
  const disabled =
    p.disabled ||
    parsed.reason ||
    (!p.catalog
      ? "Live catalog unavailable: repair source dependencies and reopen."
      : "");
  const activeDisabled =
    disabled || (!visible[layer] ? "Show the active layer to paint it." : "");
  const palette = Object.entries(m?.legend || {}).filter(([g, id]) =>
    `${g} ${id}`.toLowerCase().includes(search.toLowerCase()),
  );
  const decorators = Object.entries(p.catalog?.decor || {}).filter(([id, r]) =>
    `${id} ${r.name}`.toLowerCase().includes(search.toLowerCase()),
  );
  const specials = m?.special_tiles || [],
    s = specialIndex !== null ? specials[specialIndex] : undefined;
  const problems = useMemo(
    () =>
      p.diagnostics
        .map((d) => diagnosticCell(d, m))
        .filter((v) => v !== null)
        .map((v) => v.cell),
    [p.diagnostics, m],
  );
  function select(c: Cell) {
    setSelected(c);
    if (placing && !disabled && placementId) {
      p.onEdit(source => placementKind==="creature"?addCreature(source,c,placementId):addRecord(source,c,placementKind,placementId), `Add ${placementKind}`);
      setSpecialIndex(specials.length); setPlacing(false); return;
    }
    if(!p.authoredSubmap){const profile=m?.placement as Placement|undefined;const ei=profile?.entrances?.findIndex(e=>e&&entranceCells(e).some(([x,y])=>x===c[0]&&y===c[1]));const ti=profile?.targets?.findIndex(t=>t&&t.x===c[0]&&t.y===c[1]);setOverlay(ei!==undefined&&ei>=0?`entrances:${ei}`:ti!==undefined&&ti>=0?`targets:${ti}`:"");}
    const at = specials.map((s,i)=>({s,i})).filter(({s})=>s.x===c[0] && s.y===c[1]);
    const i = (at.find(({s})=>creatureEditable(s)) || at[0])?.i ?? -1;
    setSpecialIndex(i >= 0 ? i : null);
  }
  function stroke(cells: Cell[]) {
    if (activeDisabled || layer === "specials" || p.authoredSubmap && layer==="decor" || !m || !p.catalog) return;
    const empty = Object.keys(m.legend).find((g) => m.legend[g] === null);
    const value =
      layer === "terrain"
        ? tool === "erase"
          ? empty
          : activeGlyph
        : tool === "erase"
          ? null
          : decor;
    if (value === undefined || (value === "" && layer === "decor")) return;
    if (
      layer === "terrain" &&
      m.legend[value as string] !== null &&
      !p.catalog.terrain[m.legend[value as string]!]
    )
      return;
    if (layer === "decor" && value !== null && !p.catalog.decor[value]) return;
    p.onEdit(
      (source) => paint(source, cells, layer as "terrain" | "decor", value),
      tool === "rectangle" ? "Rectangle fill" : "Brush stroke",
    );
  }
  const frame = view === "draft" ? p.preview : p.diskPreview;
  const shown = frame?.orientations ? frame.orientations[orientation] ?? frame.orientations[0] : frame;
  const at =
    selected && m
      ? {
          glyph: Array.from(m.layers[selected[1]] || "")[selected[0]],
          decor: m.decor_layer?.[selected[1]]?.[selected[0]] ?? null,
        }
      : null;
  return (
    <section className="layout-editor" data-testid="layout-editor">
      <div className="pane-heading">
        <div>
          <div className="eyebrow">03 / VISUAL AUTHORING</div>
          <h2>Structure editor</h2>
        </div>
        <div className="tool-buttons">
          {p.previewBusy && (
            <button
              disabled={p.disabled === "Publication in progress."}
              onClick={p.onCancel}
            >
              Cancel authoring request
            </button>
          )}
          <button
            className="primary"
            disabled={
              p.previewDisabled ||
              !!parsed.reason ||
              p.previewBusy
            }
            onClick={() => {
              setView("draft");
              p.onPreview();
            }}
          >
            Preview draft
          </button>
        </div>
      </div>
      {p.authoredSubmap && <p className="notice">Authored underground room · source x,y. Terrain, arrival and direct contents share exact Source, history and durable recovery. Markers are provisional until production validation. Floor items can overlap; actor and container occupancy have separate game rules.</p>}
      <div className="layout-views tabs">
        <button
          className={view === "source" ? "active" : ""}
          onClick={() => setView("source")}
        >
          Authored layout
        </button>
        <button
          className={view === "draft" ? "active" : ""}
          onClick={() => setView("draft")}
        >
          Draft production preview
        </button>
        <button
          className={view === "disk" ? "active" : ""}
          onClick={() => setView("disk")}
        >
          Saved production preview
        </button>
      </div>
      {view === "source" ? (
        <>
          <div className="layout-toolbar">
            <label>
              Active layer
              <select
                aria-label="Active layer"
                value={layer}
                onChange={(e) => setLayer(e.target.value as Layer)}
              >
                <option value="terrain">Terrain / legend</option>
                {!p.authoredSubmap && <option value="decor">Decor</option>}
                <option value="specials">Placed records</option>
              </select>
            </label>
            <div className="tool-buttons">
              {(
                [
                  ["select", "Select · V"],
                  ["pencil", "Pencil · B"],
                  ["erase", "Erase · E"],
                  ["rectangle", "Fill · R"],
                  ["pan", "Pan · H"],
                ] as [Tool, string][]
              ).map(([t, label]) => (
                <button
                  key={t}
                  aria-label={label}
                  className={tool === t ? "active" : ""}
                  disabled={
                    ["pencil", "erase", "rectangle"].includes(t) &&
                    (!!activeDisabled ||
                      layer === "specials" ||
                      (t === "erase" &&
                        layer === "terrain" &&
                        !Object.values(m?.legend || {}).includes(null)))
                  }
                  onClick={() => setTool(t)}
                  title={
                    t === "erase"
                      ? "Decor: null. Terrain: an existing null-mapped glyph only."
                      : label
                  }
                >
                  {label}
                </button>
              ))}
            </div>
            <button
              onClick={p.onUndo}
              disabled={!p.canUndo || !!disabled}
              title="Ctrl+Z with canvas focus"
            >
              Undo canvas
            </button>
            <button
              onClick={p.onRedo}
              disabled={!p.canRedo || !!disabled}
              title="Ctrl+Shift+Z with canvas focus"
            >
              Redo canvas
            </button>
          </div>
          {<div className="layout-toolbar">
            <label>Record kind<select aria-label="Placement kind" value={placementKind} onChange={e=>{setPlacementKind(e.target.value as typeof placementKind);setPlacing(false);}}>{(p.authoredSubmap?["creature","item","container","decor"]:["item","container"]).map(k=><option key={k}>{k}</option>)}</select></label>
            {placementKind==="creature"?<label>Existing creature<select aria-label="Placement creature" value={creatureId} disabled={!!disabled} onChange={e=>setCreatureId(e.target.value)}>
              <option value="">Choose creature…</option>{p.catalog?.creatures?.map(c=><option key={c.id} value={c.id} disabled={c.resolved===false}>{c.id} · {c.name} · {c.path}{c.resolved===false?" · ambiguous / unsupported":""}</option>)}
            </select></label>:placementKind==="item"?<label>Existing item<select aria-label="Placement item" value={itemId} disabled={!!disabled} onChange={e=>setItemId(e.target.value)}><option value="">Choose item…</option>{p.catalog?.items?.map(c=><option key={c.id} value={c.id} disabled={!c.resolved}>{c.id} · {c.name} · {c.path}{c.readable?" · readable":""}{!c.resolved?" · ambiguous / unsupported":""}</option>)}</select></label>:placementKind==="decor"?<label>Saved decor<select aria-label="Placement decor" value={decor} disabled={!!disabled} onChange={e=>{setDecor(e.target.value);setPlacing(false);}}><option value="">Choose furnishing…</option>{Object.entries(p.catalog?.decor??{}).map(([id,r])=><option key={id} value={id}>{id} · {r.name}{!r.supported?" · unavailable":""}</option>)}</select></label>:<label>Container decor<select aria-label="Placement container" value={containerId} disabled={!!disabled} onChange={e=>setContainerId(e.target.value)}>{Object.entries(p.catalog?.decor??{}).filter(([,r])=>r.container).map(([id,r])=><option key={id} value={id} disabled={r.resolved===false}>{id} · {r.path}{r.resolved===false?" · ambiguous":""}</option>)}</select></label>}
            <button disabled={!!disabled || !placementId || placementKind==="decor" && !p.catalog?.decor[decor]?.supported} className={placing ? "active" : ""} onClick={()=>{setPlacing(!placing);setTool("select");setLayer("specials");setVisible(v=>({...v,specials:true}));}}>{placing ? "Cancel placement" : `Place ${placementKind}`}</button>
            {placementKind==="decor"&&p.catalog&&<DecorSummary id={decor} catalog={p.catalog}/>}
            {placing && <span>Click a source cell. Validate to check admission.</span>}
          </div>}
          <div className="layer-visibility">
            {(["terrain", "decor", "specials"] as Layer[]).map((l) => (
              <label key={l}>
                <input
                  type="checkbox"
                  checked={visible[l]}
                  onChange={(e) =>
                    setVisible((v) => ({ ...v, [l]: e.target.checked }))
                  }
                />
                Show {l}
              </label>
            ))}
            <span data-testid="layout-hover">
              {hover ? `(${hover.join(", ")})` : "Move over a source cell"}
            </span>
          </div>
          {activeDisabled && (
            <p className="notice warning" data-testid="canvas-disabled">
              {activeDisabled}
            </p>
          )}
          <div className="layout-surface">
            {m && p.catalog ? (
              <LayoutCanvas
                model={m}
                catalog={p.catalog}
                layer={layer}
                visible={visible}
                tool={tool}
                disabled={!!activeDisabled}
                selected={selected}
                hovered={hover}
                authoredSubmap={p.authoredSubmap}
                focusCell={p.focus?.cell || null}
                problems={problems}
                onSelect={select}
                onHover={setHover}
                onPaint={stroke}
                onGesture={p.onGesture}
                onError={p.onError}
                onShortcut={(key) => {
                  if (key === "undo") p.onUndo();
                  else if (key === "redo") p.onRedo();
                  else
                    setTool(
                      (
                        {
                          b: "pencil",
                          v: "select",
                          e: "erase",
                          r: "rectangle",
                          h: "pan",
                        } as Record<string, Tool>
                      )[key],
                    );
                }}
              />
            ) : (
              <div className="canvas-empty">
                <h3>Canvas paused</h3>
                <p>
                  {parsed.reason ||
                    "The current dependency catalog is unavailable."}
                </p>
                <span>Your exact draft remains in Source.</span>
              </div>
            )}
          </div>
          <div className="layout-details">
            <div className="layout-palette">
              <label>
                Palette search
                <input
                  aria-label="Palette search"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                />
              </label>
              {layer === "terrain" ? (
                <label>
                  Existing legend glyph
                  <select
                    aria-label="Terrain brush"
                    value={activeGlyph}
                    onChange={(e) => setGlyph(e.target.value)}
                  >
                    {palette.map(([g, id]) => (
                      <option
                        key={g}
                        value={g}
                        disabled={id !== null && !p.catalog?.terrain[id]}
                      >
                        {JSON.stringify(g)} → {id ?? (p.authoredSubmap?"initial wall fill":"leave underlying terrain")}
                        {!p.authoredSubmap && m?.legend_weights?.[g] ? " · retained inactive legend_weights" : ""}
                      </option>
                    ))}
                  </select>
                </label>
              ) : layer === "decor" && !p.authoredSubmap ? (
                <label>
                  Live decor ID
                  <select
                    aria-label="Decor brush"
                    value={decor}
                    onChange={(e) => setDecor(e.target.value)}
                  >
                    <option value="">Choose decor…</option>
                    {decorators.map(([id, r]) => (
                      <option key={id} value={id}>
                        {id} · {r.name}
                        {r.blocks_movement ? " · blocks movement" : ""}
                      </option>
                    ))}
                  </select>
                </label>
              ) : (
                <label>
                  Placed record
                  <select
                    aria-label="Placed record"
                    value={specialIndex ?? ""}
                    onChange={(e) => {
                      const i = Number(e.target.value);
                      setSpecialIndex(i);
                      setSelected([specials[i].x, specials[i].y]);
                    }}
                  >
                    <option value="" disabled>
                      Select a record…
                    </option>
                    {specials.map((s, i) => (
                      <option key={i} value={i}>
                        #{i} {s.type ?? s.kind ?? "unknown"} {String(s.decor_id??s.item_id??s.creature_id??"")} ({s.x}, {s.y})
                      </option>
                    ))}
                  </select>
                </label>
              )}
              <p className="muted small">
                {p.authoredSubmap ? "Placed records use source-array indices. Select overlapping records individually above. Generated arrival and physical stairs are reserved by the game." : <>Terrain leaves other layers intact. Decor replaces only the
                selected native cell. A null terrain glyph retains the test
                context’s ground. legend_weights remains inactive on this route.</>}
              </p>
              <p className="muted small">
                Source, properties, canvas, records and placement controls share this document’s undo/redo history on the surface building route.
              </p>
            </div>
            <div className="cell-details">
              <h3 data-testid="layout-selected">
                {selected
                  ? `Source cell (${selected.join(", ")})`
                  : "Select a cell"}
              </h3>
              {at && m && (
                <p>
                  <code>
                    {JSON.stringify(at.glyph)} →{" "}
                    {m.legend[at.glyph] ?? "underlying terrain"}
                  </code>
                  <br />
                  {p.authoredSubmap ? "Inactive decor_layer (not used by this route)" : "Decor"}: <code>{JSON.stringify(at.decor)}</code>
                </p>
              )}
              {s && specialIndex !== null && p.catalog ? (
                <>
                  <code>
                    {p.sourcePath} · special_tiles[{specialIndex}] · {s.type ?? s.kind}
                  </code>
                  {containerEditable(s) && <div className="source-links">
                    {(s.loot_pools || []).map((id, i) => <button key={i} disabled={p.previewBusy}
                      onClick={() => p.onPool?.(id, specialIndex, s)}>Open pool {id}</button>)}
                    <small>Declared draft references. Apply container edit before opening a changed selection.</small>
                  </div>}
                  {<div className="source-links">{[["creature",s.creature_id,p.catalog.creatures],["item",s.item_id,p.catalog.items],["text",s.text_id,p.catalog.texts]].map(([family,id,choices])=>{const row=(choices as Catalog["items"])?.find(r=>r.id===id&&r.resolved!==false);return typeof id==="string"&&<button key={String(family)} disabled={!row||p.previewBusy} onClick={()=>p.onLinked?.(String(family),id,row?.path,{text:p.draft,index:specialIndex})}>Open linked {String(family)} {id}{!row?" · missing / ambiguous":""}</button>;})}</div>}
                  {p.authoredSubmap && creatureEditable(s) ? <CreatureFields key={`${specialIndex}:${JSON.stringify(s)}`} record={s} catalog={p.catalog} disabled={!!disabled}
                    onApply={value=>p.onEdit(source=>editCreature(source,specialIndex,value),"Move / edit creature")}
                    onDelete={()=>{p.onEdit(source=>removeCreature(source,specialIndex),"Delete creature");setSpecialIndex(null);}} /> : recordKind(s)==="item" ? <ItemFields key={`${specialIndex}:${JSON.stringify(s)}`} record={s} catalog={p.catalog} disabled={!!disabled} surfaceDraft={!p.authoredSubmap?p.draft:undefined} index={specialIndex} onEdit={p.onEdit} onDelete={()=>{p.onEdit(source=>deleteRecord(source,specialIndex),"Delete item");setSpecialIndex(null);}}/> : p.authoredSubmap && recordKind(s)==="decor" ? <DecorFields key={`${specialIndex}:${JSON.stringify(s)}`} record={s} catalog={p.catalog} disabled={!!disabled} index={specialIndex} onEdit={p.onEdit} onDelete={()=>{p.onEdit(source=>deleteRecord(source,specialIndex),"Delete decor");setSpecialIndex(null);}}/> : containerEditable(s) ? (
                    <ContainerFields
                      key={`${specialIndex}:${JSON.stringify(s)}`}
                      record={s}
                      catalog={p.catalog}
                      followTargets={!p.authoredSubmap}
                      goalIndices={!p.authoredSubmap?matchingGoals(p.draft,s):[]}
                      disabled={!!disabled}
                      onApply={(value, follow) =>
                        p.onEdit(
                          (source) =>
                            editContainer(source, specialIndex, value, follow),
                          "Edit / move container",
                        )
                      }
                    />
                  ) : (
                    <p className="notice">
                      Inspect-only record. Fields and nested values are
                      preserved; edit supported details in Source.
                    </p>
                  )}
                  {p.authoredSubmap&&containerEditable(s)&&<button disabled={!!disabled} onClick={()=>{p.onEdit(source=>deleteRecord(source,specialIndex),"Delete container");setSpecialIndex(null);}}>Delete container</button>}
                  {!p.authoredSubmap&&["item","container"].includes(recordKind(s))&&<DeleteSurfaceRecord draft={p.draft} record={s} index={specialIndex} disabled={!!disabled} onEdit={p.onEdit} onDeleted={()=>setSpecialIndex(null)}/>}
                  <details>
                    <summary>Complete source record</summary>
                    <pre className="raw">{JSON.stringify(s, null, 2)}</pre>
                  </details>
                </>
              ) : null}
            </div>
          </div>
          {!p.authoredSubmap&&m&&p.catalog&&<><BuildingGeometry key={`${m.width}:${m.height}`} model={m} draft={p.draft} catalog={p.catalog} disabled={!!disabled} onEdit={p.onEdit}/><PlacementControls draft={p.draft} disabled={!!disabled} onEdit={p.onEdit} selected={overlay} onSelect={(cell,kind,index)=>{setSelected(cell);setOverlay(`${kind}:${index}`);setTool("select");}}/></>}
          {p.authoredSubmap&&m&&p.catalog&&<RoomGeometry model={m} draft={p.draft} catalog={p.catalog} disabled={!!disabled} onEdit={p.onEdit}/>}
        </>
      ) : (
        <>
          <p className="notice" data-testid="preview-provenance">
            {view === "draft"
              ? p.preview
                ? `Current unsaved draft ${p.previewHash?.slice(0, 12)} · real production output`
                : "No current draft preview. Preview draft to validate and generate these exact unsaved bytes."
              : "Saved source snapshot · does not include unsaved changes"}
          </p>
          {p.previewBusy && (
            <p role="status" className="notice">
              Validating and generating…{" "}
              <button onClick={p.onCancel}>Cancel preview</button>
            </p>
          )}
          {shown?.error&&<p className="notice warning">{shown.error}</p>}
          {frame?.orientations&&<label>Production orientation<select aria-label="Production orientation" value={orientation} onChange={e=>{setOrientation(Number(e.target.value));setRuntimeCell(null);}}>{frame.orientations.map((r,i)=><option key={i} value={i}>{r.rotation}° · mirror {String(r.mirror)} · {r.passed?'passed':'failed'}</option>)}</select><small>Switching views never changes source coordinates or definitions. All permitted combinations are validated together; legacy flip_v is separate.</small></label>}
          <div className="layout-surface">
            {shown?.terrain ? (
              <MapView
                preview={shown}
                onCell={setRuntimeCell}
                onError={p.onError}
              />
            ) : (
              <div className="canvas-empty">
                <h3>Production preview pending</h3>
                <p>
                  Invalid or obsolete output is cleared. Inspect Problems for
                  current failures.
                </p>
              </div>
            )}
          </div>
          {shown?.terrain && (
            <>
              <p className="muted">{shown.context}</p>
              {!p.authoredSubmap&&<><p>Source coordinates → transformed coordinates → scene origin ({shown.origin.join(", ")}).</p><details open><summary>Realized direct records and native access</summary><pre className="raw" data-testid="building-production-records">{JSON.stringify({records:shown.population_receipts,record_access:shown.record_access,access:shown.access},null,2)}</pre></details></>}
              {p.authoredSubmap && <>
                <p data-testid="scene-coordinates">Scene origin ({shown.origin.join(", ")}) · authored start ({shown.authored_start?.join(", ")}) · actual arrival ({shown.spawn.join(", ")}) · {shown.actors.length} instantiated actor(s).</p>
                <table className="placement-actors"><thead><tr><th>Source record / creature</th><th>Source x,y</th><th>Scene x,y</th><th>Actual class / count</th></tr></thead><tbody>
                  {shown.population_receipts?.filter(r=>r.kind==="creature").map(r=><tr key={r.record_id}><td>#{r.source_index} · {r.creature_definition?.id}</td><td>{r.source_xy.join(", ")}</td><td>{r.xy.join(", ")}</td><td>{r.actor_classes?.join(", ")} · {r.actual_count}</td></tr>)}
                </tbody></table>
                <table className="placement-decor"><thead><tr><th>Source record / furnishing</th><th>Source x,y</th><th>Scene x,y</th><th>Observed placement / declared properties</th></tr></thead><tbody>{shown.population_receipts?.filter(r=>r.kind==="decor").map(r=><tr key={r.record_id}><td>#{r.source_index} · {r.realized_decor?.id}</td><td>{r.source_xy.join(", ")}</td><td>{r.xy.join(", ")}</td><td>{r.actual_count} placed · movement {r.realized_decor?.blocks_movement?"blocked":"allowed"} · light radius {r.realized_decor?.light_emit} · declared sight blocking {String(r.realized_decor?.declared_blocks_sight)}</td></tr>)}</tbody></table>
                <details open><summary>Realized contents, arrival and static access</summary><pre className="raw" data-testid="placement-receipt">{JSON.stringify({source_path:shown.source_path,source_sha256:shown.source_sha256,draft_sha256:shown.draft_sha256,source:shown.source,seed:shown.seed,scene_seed:shown.scene_seed,scene_address:shown.scene_address,origin:shown.origin,authored_start:shown.authored_start,spawn:shown.spawn,stairs:shown.stairs,access:shown.access,access_source:shown.access_source,records:shown.population_receipts},null,2)}</pre></details>
              </>}
              <p className="muted">
                Seed {shown.seed} · scene {shown.scene_seed} ·{" "}
                {shown.generation_revision} · {shown.elapsed_ms} ms generation
              </p>
              <p className="muted">{shown.rendering}</p>
              <details>
                <summary>
                  Production objects and access evidence
                  {runtimeCell ? ` at (${runtimeCell.join(", ")})` : ""}
                </summary>
                <pre className="raw" data-testid="runtime-objects">
                  {JSON.stringify(
                    runtimeCell
                      ? {
                          terrain:
                            shown.terrain[runtimeCell[1]][runtimeCell[0]],
                          decor: shown.decor.filter(
                            (o) =>
                              o.x === runtimeCell[0] && o.y === runtimeCell[1],
                          ),
                          containers: shown.containers.filter(
                            (o) =>
                              o.x === runtimeCell[0] && o.y === runtimeCell[1],
                          ),
                          items: shown.items.filter(
                            (o) =>
                              o.x === runtimeCell[0] && o.y === runtimeCell[1],
                          ),
                        }
                      : { containers: shown.containers, access: shown.access },
                    null,
                    2,
                  )}
                </pre>
              </details>
            </>
          )}
        </>
      )}
    </section>
  );
}

function CreatureFields({record, catalog, disabled, onApply, onDelete}: {
  record: Special; catalog: Catalog; disabled: boolean;
  onApply: (v:{x:number;y:number;creature_id:string})=>void; onDelete:()=>void;
}) {
  const [x,setX]=useState(String(record.x)), [y,setY]=useState(String(record.y)), [id,setId]=useState(String(record.creature_id || ""));
  return <fieldset className="container-fields" disabled={disabled}><legend>Direct creature · source coordinates</legend>
    <label>Creature ID<select aria-label="Marker creature ID" value={id} onChange={e=>setId(e.target.value)}>
      {!catalog.creatures?.some(c=>c.id===id) && <option value={id}>{id} · unresolved</option>}
      {catalog.creatures?.map(c=><option key={c.id} value={c.id} disabled={c.resolved===false}>{c.id} · {c.path}{c.resolved===false?" · ambiguous / unsupported":""}</option>)}
    </select></label>
    <div className="coordinate-fields"><label>Source X<input aria-label="Creature source X" type="number" step="1" value={x} onChange={e=>setX(e.target.value)}/></label>
    <label>Source Y<input aria-label="Creature source Y" type="number" step="1" value={y} onChange={e=>setY(e.target.value)}/></label></div>
    <button disabled={!x || !y || !Number.isInteger(Number(x)) || !Number.isInteger(Number(y)) || !catalog.creatures?.some(c=>c.id===id&&c.resolved!==false)} onClick={()=>onApply({x:Number(x),y:Number(y),creature_id:id})}>Apply creature edit</button>
    <button onClick={onDelete}>Delete creature</button><small>Initial occupancy is checked by production validation. Invalid placements stay in the draft.</small>
  </fieldset>;
}

function ContainerFields({
  record,
  catalog,
  disabled,
  onApply,
  followTargets=true,
  goalIndices=[],
}: {
  record: Special;
  catalog: Catalog;
  disabled: boolean;
  followTargets?:boolean;
  goalIndices?:number[];
  onApply: (
    v: { x: number; y: number; decor_id: string; loot_pools: string[] },
    follow: boolean,
  ) => void;
}) {
  const [x, setX] = useState(String(record.x)),
    [y, setY] = useState(String(record.y)),
    [decor, setDecor] = useState(record.decor_id ?? "crate"),
    [pools, setPools] = useState(record.loot_pools ?? []),
    [follow, setFollow] = useState(true);
  const valid =
    x !== "" &&
    y !== "" &&
    Number.isInteger(Number(x)) &&
    Number.isInteger(Number(y)) &&
    catalog.decor[decor]?.container && catalog.decor[decor]?.resolved!==false &&
    pools.every((p) => catalog.loot_pools.includes(p));
  return (
    <fieldset className="container-fields" disabled={disabled}>
      <legend>Direct container</legend>
      <div className="coordinate-fields">
        <label>
          X
          <input
            aria-label="Container X"
            type="number"
            value={x}
            onChange={(e) => setX(e.target.value)}
          />
        </label>
        <label>
          Y
          <input
            aria-label="Container Y"
            type="number"
            value={y}
            onChange={(e) => setY(e.target.value)}
          />
        </label>
      </div>
      <label>
        Container decor
        <select
          aria-label="Container decor"
          value={decor}
          onChange={(e) => setDecor(e.target.value)}
        >
          {!catalog.decor[decor]?.container && (
            <option value={decor}>{decor} · invalid reference</option>
          )}
          {Object.entries(catalog.decor)
            .filter(([, r]) => r.container)
            .map(([id,r]) => (
              <option key={id} value={id} disabled={r.resolved===false}>{id}{r.path?` · ${r.path}`:""}{r.resolved===false?" · ambiguous":""}</option>
            ))}
        </select>
      </label>
      <label>Existing loot pools (each rolls independently)</label>
      {pools.map((pool, i) => (
        <div className="pool-row" key={i}>
          <select
            aria-label={`Loot pool ${i + 1}`}
            value={pool}
            onChange={(e) =>
              setPools(pools.map((v, n) => (n === i ? e.target.value : v)))
            }
          >
            {!catalog.loot_pools.includes(pool) && (
              <option value={pool}>{pool} · invalid reference</option>
            )}
            {catalog.loot_pools.map((id) => (
              <option key={id} value={id}>{id}{catalog.pools?.find(r=>r.id===id)?.path?` · ${catalog.pools.find(r=>r.id===id)?.path}`:""}</option>
            ))}
          </select>
          <button
            aria-label={`Remove loot pool ${i + 1}`}
            onClick={() => setPools(pools.filter((_, n) => n !== i))}
          >
            −
          </button>
        </div>
      ))}
      <button
        onClick={() => setPools([...pools, catalog.loot_pools[0]])}
        disabled={!catalog.loot_pools.length}
      >
        Add existing pool
      </button>
      {followTargets&&<label className="check-label">
        <input
          type="checkbox"
          checked={follow}
          onChange={(e) => setFollow(e.target.checked)}
        />
        Move matching container access targets with this record
      </label>}
      {followTargets&&<p>Companion proposal: {goalIndices.map(i=>`placement.targets[${i}] → (${x}, ${y})`).join("; ")||"No exact matching goals"}. Other goals remain unchanged.</p>}
      <button
        className="primary full"
        disabled={!valid}
        onClick={() =>
          onApply(
            { x: Number(x), y: Number(y), decor_id: decor, loot_pools: pools },
            follow&&followTargets,
          )
        }
      >
        Apply container edit
      </button>
    </fieldset>
  );
}
