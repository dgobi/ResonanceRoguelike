import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { itemModel, itemValue, keywordEntry } from "./item";
import { CanvasHistory } from "./layout";
import { currentVerdict } from "./draft";

describe("shared item source draft", () => {
  const source = '\uFEFF{\r\n "id":"a", "name":"Authored wording", "weight":1, "keywords":[{"tag":"fuel","tier":1,"extra":[null,true]},{"tag":"fibrous","tier":1}], "unknown":{"nested":[[1,2]]}\r\n}\r\n';
  it("reads three real definitions without serialization and changes only current spans", () => {
    for (const file of ["components/wood_bundle", "tools/tallow_torch", "weapons/binding_knife"]) {
      const s = readFileSync(new URL(`../../roguelike/data/items/${file}.json`, import.meta.url), "utf8");
      expect(itemModel(s).model).not.toBeNull();
      expect(itemValue(s, ["weight"], JSON.parse(s).weight)).toBe(s);
    }
    const edited = itemValue(source, ["weight"], 1.75);
    expect(edited).toBe(source.replace('"weight":1', '"weight":1.75'));
    expect(itemValue(edited, ["keywords",0,"tier"],2)).toBe(edited.replace('"tier":1','"tier":2'));
  });
  it("preserves unknown keyword data/order and freezes invalid raw text", () => {
    const added = keywordEntry(source,-1,"cutting");
    expect(added).toContain('"extra":[null,true]');
    expect(JSON.parse(keywordEntry(added,2).slice(1))).toEqual(JSON.parse(source.slice(1)));
    for (const s of ['{"id":','{"id":1,"id":2}','[]','null']) {
      expect(itemModel(s).model).toBeNull(); expect(() => itemValue(s,["weight"],3)).toThrow();
    }
  });
  it("keeps separate item/pool/structure history and rejects late revisions", () => {
    const item = new CanvasHistory(), pool = new CanvasHistory(), structure = new CanvasHistory();
    const edited = itemValue(source,["weight"],2);
    item.record(source,edited,"weight"); pool.record("p","q","pool");
    expect(item.undo(edited)).toBe(source); expect(pool.undo("q")).toBe("p");
    expect(structure.undo("s")).toBe("s"); expect(item.redo(source)).toBe(edited);
    item.clear(); expect(item.undo(edited+" ")).toBe(edited+" ");
    expect(currentVerdict(2,3,source,edited)).toBe(false);
  });
  it("edits supplies locally while preserving nulls, omitted defaults and nested metadata",()=>{
    const s='{\r\n "id":"meal", "on_use":"eat", "nutrition":null, "eat_message":null, "harvest_from":"bush", "_essence_note":{"nested":[false,null]}, "keywords":[]\r\n}\r\n';
    expect(itemValue(s,["nutrition"],.35)).toBe(s.replace('"nutrition":null','"nutrition":0.35'));
    expect(itemValue(s,["eat_message"],"A meal.")).toBe(s.replace('"eat_message":null','"eat_message":"A meal."'));
    expect(itemValue(s,["nutrition"],null)).toBe(s);
    expect(itemValue(s,["tile"],"generic_item")).toContain('"nutrition":null');
    expect(itemValue(s,["tile"],"generic_item")).not.toContain('"weight"');
  });
});
