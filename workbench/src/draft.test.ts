import { describe, it, expect } from "vitest";
import { readFileSync } from "node:fs";
import { applyPatch } from "diff";
import { currentVerdict, scalarEdit, sourceDiff, syntax } from "./draft";

describe("byte preserving authoring", () => {
  for (const name of ["commercial/workshop_b", "commercial/apothecary_b"]) {
    it(`edits only the scalar text span in ${name}`, () => {
      const original = readFileSync(
        `../roguelike/data/buildings/${name}.json`,
        "utf8",
      );
      const before = JSON.parse(original),
        changed = scalarEdit(original, "description", "W1 edited description");
      expect(JSON.parse(changed)).toEqual({
        ...before,
        description: "W1 edited description",
      });
      expect(
        changed.replace(
          '"W1 edited description"',
          JSON.stringify(before.description),
        ),
      ).toBe(original);
      expect(
        applyPatch(original, sourceDiff(original, changed, "source", "target")),
      ).toBe(changed);
    });
  }
  it("retains BOM, CRLF, nested arrays, specials, unknown fields and ordering", () => {
    const original =
      '\uFEFF{\r\n "id":"a", "unknown":{"deep":[[1,"x"]]}, "description":"old", "decor_layer":[[null,"d"]], "special_tiles":[{"x":1,"y":2,"text_id":"t"}]\r\n}\r\n';
    expect(scalarEdit(original, "description", "new")).toBe(
      original.replace('"old"', '"new"'),
    );
    expect(syntax(scalarEdit(original, "weight", 2)).diagnostics).toEqual([]);
  });
  it("rejects JSONC and ambiguous syntax before property edits", () => {
    for (const source of [
      '{"x":1,}',
      '{/*comment*/"x":1}',
      '{"x":1,"x":2}',
      '{"x":NaN}',
      '{"x":"bad\n"}',
    ]) {
      expect(syntax(source).diagnostics.length).toBeGreaterThan(0);
      expect(() => scalarEdit(source, "description", "x")).toThrow();
    }
  });
  it("an earlier valid response cannot replace the verdict of a later draft", () => {
    expect(currentVerdict(1, 2, "old", "new")).toBe(false);
    expect(currentVerdict(1, 2, "same", "same")).toBe(false);
    expect(currentVerdict(2, 2, "new", "new")).toBe(true);
  });
});
