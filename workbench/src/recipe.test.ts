import { describe, expect, it } from "vitest";
import { recipeModel, recipeRow, recipeValue } from "./recipe";
import { CanvasHistory } from "./layout";
import { currentVerdict } from "./draft";

describe("one exact recipe draft", () => {
  const raw = '\ufeff{\r\n "id":"bile", "description":"Keep this wording.", "components": [{"tag":"caustic", "quantity":1,"metadata":[[1,true]]}, { "tag": "viscous", "quantity":2}], "unknown":{"nested":[null,{"x":3}]}}\r\n';
  it("opens without serialization and changes only the selected scalar", () => {
    expect(recipeModel(raw).model?.id).toBe("bile");
    expect(recipeValue(raw,["components",0,"quantity"],1)).toBe(raw);
    expect(recipeValue(raw,["components",0,"quantity"],3)).toBe(raw.replace('"quantity":1','"quantity":3'));
  });
  it("reorders exact row spans with nested metadata and leaves separators intact", () => {
    const a='{"tag":"caustic", "quantity":1,"metadata":[[1,true]]}', b='{ "tag": "viscous", "quantity":2}';
    const moved=recipeRow(raw,"components","down",0);
    expect(moved).toBe(raw.replace(a+", "+b,b+", "+a));
    expect(recipeRow(moved,"components","up",1)).toBe(raw);
    const added=recipeRow(raw,"components","add",-1,"caustic");
    expect(recipeModel(added).model?.components).toHaveLength(3);
    expect(recipeRow(added,"components","remove",2)).toBe(raw);
    expect(recipeRow(raw,"tools","add",-1,"vessel")).toContain('"unknown":{"nested":[null,{"x":3}]}');
  });
  it("freezes invalid/duplicate-key JSON and isolates history and stale revisions", () => {
    for(const s of ['{"id":','{"id":"x","id":"y"}']) {
      expect(recipeModel(s).model).toBeNull(); expect(()=>recipeRow(s,"components","add",0,"fuel")).toThrow();
    }
    const recipe=new CanvasHistory(), item=new CanvasHistory(), changed=recipeValue(raw,["components",1,"quantity"],3);
    recipe.record(raw,changed,"quantity"); item.record("item","changed item","weight");
    expect(recipe.undo(changed)).toBe(raw); expect(recipe.redo(raw)).toBe(changed);
    expect(item.undo("changed item")).toBe("item");
    expect(currentVerdict(1,2,raw,changed)).toBe(false);
  });
});
