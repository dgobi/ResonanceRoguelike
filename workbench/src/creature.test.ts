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
  it("nested sight and prose edits preserve BOM, key order, escaping and sibling bytes",()=>{
    const original='\uFEFF'+source.replace(/\r?\n/g,"\r\n").replace('"base_hp": 14','"metadata": {"exact":[1e2, "λ\\n", null]},\r\n  "base_hp": 14');
    const sight=creatureValue(original,"perception.sight_radius",3);
    expect(sight).toBe(original.replace(/"sight_radius": \d+/, '"sight_radius": 3'));
    const description=creatureValue(sight,"description",'New "literal" prose');
    expect(JSON.parse(description.slice(1)).description).toBe('New "literal" prose');
    expect(description).toContain('"metadata": {"exact":[1e2, "λ\\n", null]}');
    expect(description.startsWith('\uFEFF')).toBe(true);
    expect(()=>creatureValue(description,"tile","barrow_wight")).toThrow("Read-only");
    expect(()=>creatureValue(description,"perception.faction","player")).toThrow("Read-only");
  });
  it("keeps independent source histories for two creatures",()=>{
    const wight=readFileSync(new URL("../../roguelike/data/entities/creatures/barrow_wight.json",import.meta.url),"utf8");
    const a=new CanvasHistory(),b=new CanvasHistory();
    const one=creatureValue(source,"damage_dice","2d5"),two=creatureValue(wight,"hp",37);
    a.record(source,one,"attack");b.record(wight,two,"hp");
    expect(a.undo(one)).toBe(source);expect(b.undo(two)).toBe(wight);expect(a.redo(source)).toBe(one);
  });
  it("edits hearing through one exact span and undo without changing source siblings",()=>{
    const text='\uFEFF'+source.replace(/\r?\n/g,'\r\n');
    const changed=creatureValue(text,'perception.hearing_radius',0),history=new CanvasHistory();
    expect(changed).toBe(text.replace('"hearing_radius": 6','"hearing_radius": 0'));
    history.record(text,changed,'Hearing radius');
    expect(history.undo(changed)).toBe(text);expect(history.redo(text)).toBe(changed);
  });
});
