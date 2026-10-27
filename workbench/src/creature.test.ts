import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { creatureModel, creatureValue } from "./creature";
import { CanvasHistory } from "./layout";
import { sourceDiff } from "./draft";

describe("ordinary creature exact draft", () => {
  const source = readFileSync(new URL("../../roguelike/data/entities/creatures/hollow_revenant.json", import.meta.url), "utf8");
  it("changes both HP authorities with only two focused spans and one history entry", () => {
    const history = new CanvasHistory();
    const edited = creatureValue(source, "hp", 19);
    expect(edited).toBe(source.replace('"base_hp": 14', '"base_hp": 19').replace('"max_hp": 14', '"max_hp": 19'));
    history.record(source, edited, "Effective HP");
    expect(history.undo(edited)).toBe(source); expect(history.redo(source)).toBe(edited);
    expect(sourceDiff(source,edited,"source","variant")).toContain('+  "base_hp": 19');
    const value = JSON.parse(edited), original = JSON.parse(source);
    for(const key of Object.keys(original).filter(k=>!["base_hp","fighter"].includes(k))) expect(value[key]).toEqual(original[key]);
  });
  it("leaves no-op bytes, nested metadata, CRLF and literal prose intact", () => {
    const text = source.replace(/\r?\n/g,"\r\n").replace('"base_hp": 14', '"unknown": { "ordered": [true, null, [1, 2]] },\r\n  "base_hp": 14');
    expect(creatureValue(text,"hp",14)).toBe(text);
    expect(creatureValue(text,"name","Hollow Revenant")).toBe(text);
    expect(creatureValue(text,"name","Revenant variant")).toBe(text.replace('"name": "Hollow Revenant"','"name": "Revenant variant"'));
  });
  it("freezes invalid/duplicate JSON and never repairs an unsupported shape implicitly", () => {
    for(const raw of ['{"id":','{"id":"a","id":"b"}','[]']) {
      expect(creatureModel(raw).model).toBeNull(); expect(()=>creatureValue(raw,"hp",19)).toThrow();
    }
    expect(()=>creatureValue('{"base_hp":14}',"hp",19)).toThrow("fighter");
  });
});
