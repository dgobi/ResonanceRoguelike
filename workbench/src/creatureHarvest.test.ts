import {describe,it,expect} from "vitest";
import {recordRow} from "./orderedRecords";
import {itemValue,removeItemProperty} from "./item";
import {CanvasHistory} from "./layout";

describe("nested exact-source harvest edits",()=>{
  const source='\uFEFF{\r\n "id":"x", "butcher_yield":{"meta":[1e2,"λ\\n"], "tiers":[{ "min_cutting_tier":1, "meta":true, "yields":[{ "item_id":"a", "meta":{"z":null}}, {"item_id":"a","quantity_max":2} ]}, {}]}, "other": [1, 2]\r\n}';
  it("moves complete tier/output spans and history restores exact BOM/CRLF metadata",()=>{
    const history=new CanvasHistory();
    const moved=recordRow(source,["butcher_yield","tiers",0,"yields"],"down",0);
    expect(moved).toContain('{"item_id":"a","quantity_max":2}, { "item_id":"a", "meta":{"z":null}}');
    const tiers=recordRow(moved,["butcher_yield","tiers"],"down",0);
    history.record(source,tiers,"reorder harvest");expect(history.undo(tiers)).toBe(source);expect(history.redo(source)).toBe(tiers);
    expect(tiers).toContain('"meta":[1e2,"λ\\n"]');expect(tiers).toContain('"other": [1, 2]');expect(tiers).toContain('\r\n');
  });
  it("preserves empty/default shapes until explicit add, set or remove",()=>{
    const empty='{"id":"x", "butcher_yield":{}}';
    const tier=recordRow(empty,["butcher_yield","tiers"],"add",-1,{});
    const output=recordRow(tier,["butcher_yield","tiers",0,"yields"],"add",-1,{item_id:"a"});
    expect(JSON.parse(output).butcher_yield).toEqual({tiers:[{yields:[{item_id:"a"}]}]});
    const nullDecay=itemValue(output,["butcher_yield","decay_turns"],null);
    expect(JSON.parse(nullDecay).butcher_yield.decay_turns).toBeNull();
    expect(removeItemProperty(nullDecay,["butcher_yield","decay_turns"])).toBe(output);
    expect(JSON.parse(recordRow(output,["butcher_yield","tiers",0,"yields"],"remove",0)).butcher_yield.tiers[0].yields).toEqual([]);
    expect(JSON.parse(removeItemProperty(output,["butcher_yield"]))).toEqual({id:"x"});
  });
  it("keeps repeated rows independent and refuses malformed paths",()=>{
    const one=itemValue(source,["butcher_yield","tiers",0,"yields",1,"quantity_max"],3);
    expect(one).toBe(source.replace('"quantity_max":2','"quantity_max":3'));
    expect(()=>recordRow('{"butcher_yield":{"tiers":null}}',["butcher_yield","tiers"],"add",-1,{})).toThrow();
  });
});
