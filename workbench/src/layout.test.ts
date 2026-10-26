import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { applyPatch } from "diff";
import {
  paint,
  editContainer,
  layoutModel,
  valueEdit,
  CanvasHistory,
  lineCells,
  rectangle,
  diagnosticCell,
} from "./layout";
import { sourceDiff } from "./draft";
import { fitCamera, screenToCell, zoomAt, TILE } from "./coordinates";
const original = readFileSync(
  "../roguelike/data/buildings/commercial/apothecary_a.json",
  "utf8",
);
describe("native-layer visual authoring", () => {
  it("rich real source no-op, three-layer edits and exact unrelated spans", () => {
    const enriched = valueEdit(original, ["unknown_metadata"], {
      nested: [
        [null, "kept"],
        [1, true],
      ],
      source: "retained",
    });
    expect(layoutModel(enriched).model?.width).toBe(11);
    expect(paint(enriched, [[3, 3]], "terrain", ".")).toBe(enriched);
    const one = paint(
      enriched,
      [
        [2, 3],
        [3, 3],
        [4, 3],
      ],
      "terrain",
      "w",
    );
    const two = paint(one, [[3, 2]], "decor", "dried_herbs");
    const three = editContainer(
      two,
      0,
      { x: 2, y: 1, decor_id: "crate", loot_pools: ["storage_tools"] },
      true,
    );
    const r = JSON.parse(three),
      before = JSON.parse(enriched);
    expect(r.layers[3]).toBe("#.www.....#");
    expect(r.decor_layer[2][3]).toBe("dried_herbs");
    expect(r.special_tiles[0]).toEqual({
      ...before.special_tiles[0],
      x: 2,
      decor_id: "crate",
      loot_pools: ["storage_tools"],
    });
    expect(r.placement.targets[2]).toEqual({
      ...before.placement.targets[2],
      x: 2,
    });
    expect(r.special_tiles.slice(1)).toEqual(before.special_tiles.slice(1));
    expect(r.unknown_metadata).toEqual(before.unknown_metadata);
    let restored = valueEdit(three, ["layers", 3], before.layers[3]);
    restored = valueEdit(restored, ["decor_layer", 2, 3], null);
    for (const key of ["x", "decor_id", "loot_pools"])
      restored = valueEdit(
        restored,
        ["special_tiles", 0, key],
        before.special_tiles[0][key],
      );
    restored = valueEdit(restored, ["placement", "targets", 2, "x"], 1);
    // Only the consciously edited pool array may be reformatted.
    expect(
      restored
        .replace(
          '["alchemist_reagents"]',
          '[\n        "alchemist_reagents"\n      ]',
        )
        .replace(/\r?\n/g, "\n"),
    ).toBe(enriched.replace(/\r?\n/g, "\n"));
    expect(
      applyPatch(enriched, sourceDiff(enriched, three, "source", "target")),
    ).toBe(three);
  });
  it("preserves 60 × 16 rows, Unicode codepoints, trailing spaces, BOM and CRLF", () => {
    const raw = {
      id: "rect",
      width: 60,
      height: 16,
      legend: { ".": "floor", " ": null, "🞄": "floor" },
      layers: Array(16).fill(".".repeat(59) + " "),
      unknown: [[1, 2], [null]],
    };
    const text =
      "\uFEFF" + JSON.stringify(raw, null, 2).replace(/\n/g, "\r\n") + "\r\n";
    const edited = paint(text, [[58, 15]], "terrain", "🞄");
    const r = JSON.parse(edited.slice(1));
    expect(Array.from(r.layers[15]).length).toBe(60);
    expect(r.layers[15].endsWith("🞄 ")).toBe(true);
    expect(edited.startsWith("\uFEFF")).toBe(true);
    expect(
      edited.replace(
        JSON.stringify(r.layers[15]),
        JSON.stringify(raw.layers[15]),
      ),
    ).toBe(text);
  });
  it("preserves unsupported nested decor and disables unsafe mutation", () => {
    const unsupported = valueEdit(
      original,
      ["decor_layer", 2, 2],
      ["dried_herbs", { unknown: true }],
    );
    expect(layoutModel(unsupported).reason).toMatch(/Unsupported decor shape/);
    expect(() => paint(unsupported, [[1, 1]], "decor", null)).toThrow();
    expect(JSON.parse(unsupported).decor_layer[2][2]).toEqual([
      "dried_herbs",
      { unknown: true },
    ]);
    expect(layoutModel('{"id":').model).toBeNull();
    const weighted = valueEdit(original, ["special_tiles", 0], {
      x: 1,
      y: 1,
      type: "weighted",
      spawn_table: [{ type: "empty", weight: 1 }],
    });
    expect(layoutModel(weighted).model).not.toBeNull();
    expect(() =>
      editContainer(
        weighted,
        0,
        { x: 2, y: 2, decor_id: "crate", loot_pools: [] },
        false,
      ),
    ).toThrow();
  });
  it("groups continuous strokes/fills/moves and refuses to undo unrelated source", () => {
    const history = new CanvasHistory();
    const a = paint(original, lineCells([2, 3], [4, 3]), "terrain", "w");
    history.record(original, a, "drag");
    const b = paint(a, rectangle([2, 2], [3, 3]), "decor", "dried_herbs");
    history.record(a, b, "fill");
    const c = editContainer(
      b,
      0,
      { x: 2, y: 1, decor_id: "crate", loot_pools: [] },
      true,
    );
    history.record(b, c, "move");
    expect(history.undo(c)).toBe(b);
    expect(history.undo(b)).toBe(a);
    expect(history.undo(a)).toBe(original);
    expect(history.redo(original)).toBe(a);
    expect(history.redo(a)).toBe(b);
    expect(history.redo(b)).toBe(c);
    expect(history.undo(c + " ")).toBe(c + " ");
    expect(history.undoStack.length).toBe(0);
  });
  it("maps both corners with pan/zoom and CSS pixel coordinates at DPR 1/1.5/2", () => {
    for (const [w, h] of [
      [11, 8],
      [60, 16],
    ])
      for (const dpr of [1, 1.5, 2]) {
        let camera = fitCamera(1000, 600, w, h);
        camera = { ...camera, x: camera.x + 27, y: camera.y - 13 };
        camera = zoomAt(camera, 1.25, 500, 300);
        for (const [x, y] of [
          [0, 0],
          [w - 1, h - 1],
        ]) {
          const physical = [
            (camera.x + (x + 0.5) * TILE * camera.scale) * dpr,
            (camera.y + (y + 0.5) * TILE * camera.scale) * dpr,
          ];
          expect(
            screenToCell(physical[0] / dpr, physical[1] / dpr, camera, w, h),
          ).toEqual([x, y]);
        }
        expect(
          screenToCell(
            camera.x + w * TILE * camera.scale,
            camera.y,
            camera,
            w,
            h,
          ),
        ).toBeNull();
      }
  });
  it("locates source diagnostics without inventing coordinates", () => {
    const d = {
      severity: "error",
      code: "REFERENCE",
      path: "a",
      asset: "a",
      field: "special_tiles[1].loot_pools[0]",
      message: "bad",
      correction: "fix",
    };
    expect(diagnosticCell(d, layoutModel(original).model)).toEqual({
      cell: [9, 3],
      layer: "specials",
    });
    expect(
      diagnosticCell({ ...d, field: "width" }, layoutModel(original).model),
    ).toBeNull();
  });
});
