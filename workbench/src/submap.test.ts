import {describe, expect, it} from "vitest";
import {readFileSync} from "node:fs";
import {applyPatch} from "diff";
import {addCreature, editCreature, removeCreature, layoutModel, CanvasHistory} from "./layout";
import {sourceDiff} from "./draft";
import {fitCamera, screenToCell, zoomAt, TILE} from "./coordinates";
const source = readFileSync("../roguelike/docs/examples/g17_authored_creature_room.json","utf8").replaceAll("\n","\r\n");
describe("authored-submap exact creature draft",()=>{
  it("moves only coordinate spans, preserves other records and immutable fields, exact undo/diff",()=>{
    const enriched=source.replace('"creature_id": "hollow_revenant"','"creature_id": "hollow_revenant", "source": {"nested":[true,null,[1,2]]}');
    const moved=editCreature(enriched,0,{x:6,y:3,creature_id:"hollow_revenant"});
    expect(moved).toBe(enriched.replace('"x": 7, "y": 2, "creature_id"','"x": 6, "y": 3, "creature_id"'));
    expect(JSON.parse(moved).special_tiles.slice(1)).toEqual(JSON.parse(enriched).special_tiles.slice(1));
    const history=new CanvasHistory();history.record(enriched,moved,"Move");
    expect(history.undo(moved)).toBe(enriched);expect(history.redo(enriched)).toBe(moved);
    expect(applyPatch(enriched,sourceDiff(enriched,moved,"source","variant"))).toBe(moved);
    expect(editCreature(enriched,0,{x:7,y:2,creature_id:"hollow_revenant"})).toBe(enriched);
  });
  it("add/delete preserve every other record byte span and order; invalid raw freezes",()=>{
    const added=addCreature(source,[1,1],"hollow_revenant");
    expect(JSON.parse(added).special_tiles.length).toBe(4);
    expect(removeCreature(added,3)).toBe(source);
    const removed=removeCreature(source,0);
    expect(JSON.parse(removed).special_tiles).toEqual(JSON.parse(source).special_tiles.slice(1));
    expect(removed).toContain('{"type": "item", "x": 7, "y": 2, "item_id": "wood_bundle"}');
    expect(()=>removeCreature(source,1)).toThrow();
    expect(()=>addCreature('{"id":',[0,0],"hollow_revenant")).toThrow();
    expect(()=>editCreature(source,0,{x:1.5,y:2,creature_id:"hollow_revenant"})).toThrow();
    expect(layoutModel(source.replace('"x": 7','"x": 6')).model?.special_tiles?.[0].x).toBe(6);
  });
  it("rectangular source corners remain exact under pan/zoom and CSS/DPI normalization",()=>{
    for(const dpi of [1,1.5,2]) {
      let camera=zoomAt(fitCamera(900,400,11,7),1.25,400,200);camera={...camera,x:camera.x+17,y:camera.y-21};
      for(const [x,y] of [[0,0],[10,6]]) {
        const device=[(camera.x+(x+.5)*TILE*camera.scale)*dpi,(camera.y+(y+.5)*TILE*camera.scale)*dpi];
        expect(screenToCell(device[0]/dpi,device[1]/dpi,camera,11,7)).toEqual([x,y]);
      }
    }
  });
});
