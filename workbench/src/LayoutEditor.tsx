import { useMemo, useState } from "react";
import { LayoutCanvas, type Tool } from "./LayoutCanvas";
import { MapView } from "./MapView";
import {
  containerEditable,
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

type Props = {
  draft: string;
  catalog?: Catalog;
  disabled: string;
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
  focus: { cell: Cell; layer: Layer } | null;
};
export function LayoutEditor(p: Props) {
  const parsed = useMemo(() => layoutModel(p.draft), [p.draft]),
    m = parsed.model;
  const [layer, setLayer] = useState<Layer>("terrain"),
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
  const [lastFocus, setLastFocus] = useState(p.focus);
  if (p.focus !== lastFocus) {
    setLastFocus(p.focus);
    if (p.focus) {
      setSelected(p.focus.cell);
      const index =
        m?.special_tiles?.findIndex(
          (s) => s.x === p.focus!.cell[0] && s.y === p.focus!.cell[1],
        ) ?? -1;
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
    const i = specials.findIndex((s) => s.x === c[0] && s.y === c[1]);
    setSpecialIndex(i >= 0 ? i : null);
  }
  function stroke(cells: Cell[]) {
    if (activeDisabled || layer === "specials" || !m || !p.catalog) return;
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
  const shown = view === "draft" ? p.preview : p.diskPreview;
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
          <h2>Build a furnished place</h2>
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
              (!!p.disabled && p.disabled !== "Begin edit to paint.") ||
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
                <option value="decor">Decor</option>
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
                        {JSON.stringify(g)} → {id ?? "leave underlying terrain"}
                        {m?.legend_weights?.[g] ? " · weighted at runtime" : ""}
                      </option>
                    ))}
                  </select>
                </label>
              ) : layer === "decor" ? (
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
                        #{i} {s.type ?? s.kind ?? "unknown"} ({s.x}, {s.y})
                      </option>
                    ))}
                  </select>
                </label>
              )}
              <p className="muted small">
                Terrain leaves other layers intact. Decor replaces only the
                selected native cell. A null terrain glyph retains the test
                context’s ground. Weighted glyphs resolve in production preview.
              </p>
              <p className="muted small">
                Raw/property edits clear canvas history. Undo applies only to
                complete visual operations since the last such edit.
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
                  Decor: <code>{JSON.stringify(at.decor)}</code>
                </p>
              )}
              {s && specialIndex !== null && p.catalog ? (
                <>
                  <code>
                    special_tiles[{specialIndex}] · {s.type ?? s.kind}
                  </code>
                  {containerEditable(s) ? (
                    <ContainerFields
                      key={`${specialIndex}:${JSON.stringify(s)}`}
                      record={s}
                      catalog={p.catalog}
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
                  <details>
                    <summary>Complete source record</summary>
                    <pre className="raw">{JSON.stringify(s, null, 2)}</pre>
                  </details>
                </>
              ) : null}
            </div>
          </div>
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
          <div className="layout-surface">
            {shown ? (
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
          {shown && (
            <>
              <p className="muted">{shown.context}</p>
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

function ContainerFields({
  record,
  catalog,
  disabled,
  onApply,
}: {
  record: Special;
  catalog: Catalog;
  disabled: boolean;
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
    catalog.decor[decor]?.container &&
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
            .map(([id]) => (
              <option key={id}>{id}</option>
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
              <option key={id}>{id}</option>
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
      <label className="check-label">
        <input
          type="checkbox"
          checked={follow}
          onChange={(e) => setFollow(e.target.checked)}
        />
        Move matching container access targets with this record
      </label>
      <button
        className="primary full"
        disabled={!valid}
        onClick={() =>
          onApply(
            { x: Number(x), y: Number(y), decor_id: decor, loot_pools: pools },
            follow,
          )
        }
      >
        Apply container edit
      </button>
    </fieldset>
  );
}
