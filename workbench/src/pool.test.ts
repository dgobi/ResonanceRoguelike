import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { poolEntry, poolModel, poolValue } from "./pool";
import { CanvasHistory } from "./layout";
import { currentVerdict } from "./draft";

const source = '\uFEFF{\r\n  "id": "sample", "roll_count": [1, 2],\r\n  "items": [ {"item_id":"wood_bundle", "weight": 5, "note":{"nested":[[null,1]]}}, {"item_id":"wood_bundle","weight":2} ],\r\n  "unknown": { "keep": true }\r\n}\r\n';
describe("contextual pool draft", () => {
  it("opens byte exactly and changes only the requested value span", () => {
    expect(poolModel(source).model?.items?.length).toBe(2);
    expect(poolValue(source, ["items", 0, "weight"], 9)).toBe(source.replace('"weight": 5', '"weight": 9'));
    expect(poolValue(source, ["items", 1, "item_id"], "flint_shard")).toBe(source.replace('"item_id":"wood_bundle","weight":2', '"item_id":"flint_shard","weight":2'));
  });
  it("retains repeated entries, metadata and untouched fields through add/remove", () => {
    const added = poolEntry(source, -1, "flint_shard"), removed = poolEntry(added, 2);
    const parse = (s: string) => JSON.parse(s.replace(/^\uFEFF/, ""));
    expect(parse(removed)).toEqual(parse(source));
    expect(added).toContain('"unknown": { "keep": true }');
    expect(removed.startsWith('\uFEFF')).toBe(true);
    expect(poolModel(poolEntry('{"id":"empty"}', -1, "wood_bundle")).model?.items?.length).toBe(1);
  });
  it("invalid JSON and unsupported shapes cannot be overwritten by stale table state", () => {
    for (const s of ['{"id":', '{"items":[[]]}', '{"items":{}}', '{"id":"a","id":"b"}']) {
      expect(poolModel(s).model).toBeNull();
      expect(() => poolValue(s, ["items", 0, "weight"], 5)).toThrow();
    }
    expect(currentVerdict(2, 3, source, source + " ")).toBe(false);
  });
  it("table history cannot undo a later raw-source edit", () => {
    const h = new CanvasHistory(), after = poolValue(source, ["items", 0, "weight"], 9);
    h.record(source, after, "Weight");
    expect(h.undo(after)).toBe(source); expect(h.redo(source)).toBe(after);
    h.clear(); expect(h.undo(after + " ")).toBe(after + " ");
  });
  it("retains the plain UI wording correction without scanning authored game text", () => {
    const app = readFileSync(new URL("./App.tsx", import.meta.url), "utf8");
    const editor = readFileSync(new URL("./LayoutEditor.tsx", import.meta.url), "utf8");
    for (const phrase of ["A place to understand the world", "Your world, under the lens", "Reading the living source", "Build a furnished place"])
      expect(app + editor).not.toContain(phrase);
  });
});
