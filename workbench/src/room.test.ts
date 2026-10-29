import {describe,it,expect} from "vitest";
import {addRecord,deleteRecord,editItem,editDecor,resizeRoom,valueEdit,paint,CanvasHistory,layoutModel} from "./layout";
import {sceneProblem} from "./content";
const source='{\r\n "id":"room", "unknown":{"exact":[1e2,"\\u03bb",null]},\r\n "layers":["#####","#λ .#","#.<.#","#####"], "legend":{"#":"wall","λ":"floor"," ":null,".":"floor","<":"stairs_up"},\r\n "player_start":{"x":2,"y":2,"retained":true}, "special_tiles":[{"type":"item","x":1,"y":1,"item_id":"letter","metadata":{"n":1e2}}]\r\n}';
describe("registered room exact-source operations",()=>{
 it("keeps direct furnishings in ordered exact source across add/edit/move/remove/history and resize",()=>{
  const added=addRecord(source,[3,1],"decor","campfire_unlit");
  const moved=editDecor(added,1,{x:3,y:2,decor_id:"street_lamp_working"});
  expect(moved).toContain('"unknown":{"exact":[1e2,"\\u03bb",null]}');expect(moved).toContain('\r\n');
  expect(JSON.parse(moved).special_tiles[1]).toEqual({type:"decor",x:3,y:2,decor_id:"street_lamp_working"});
  const history=new CanvasHistory();history.record(added,moved,"Move decor");expect(history.undo(moved)).toBe(added);expect(history.redo(added)).toBe(moved);
  expect(()=>resizeRoom(moved,3,4,"#")).toThrow(/special_tiles\[1\].*3, 2/);
  expect(deleteRecord(added,1)).toBe(source);
  expect(layoutModel(valueEdit(moved,["special_tiles",1,"x"],99)).model).toBeNull();
 });
 it("uses compiler character coordinates, localized legend/arrival/painting and exact undo",()=>{
  const changed=paint(source,[[1,1]],"terrain",".");expect(JSON.parse(changed).layers[1]).toBe("#. .#");
  let next=valueEdit(changed,["legend","🜁"],"floor");next=valueEdit(next,["player_start","x"],1);
  expect(next).toContain('"unknown":{"exact":[1e2,"\\u03bb",null]}');expect(next).toContain('"retained":true');expect(next).toContain('\r\n');
  const h=new CanvasHistory();h.record(source,next,"single geometry operation");expect(h.undo(next)).toBe(source);expect(h.redo(source)).toBe(next);
 });
 it("resizes from top-left, keeps optional dimensions absent, refuses stranded/unsupported data",()=>{
  const expanded=resizeRoom(source,7,5,"#");const r=JSON.parse(expanded);expect(r.layers).toEqual(["#######","#λ .###","#.<.###","#######","#######"]);expect(r.width).toBeUndefined();expect(r.player_start).toEqual({x:2,y:2,retained:true});
  expect(expanded).toContain('"metadata":{"n":1e2}');expect(()=>resizeRoom(source,2,3,"#")).toThrow(/strands/);
  expect(()=>resizeRoom(source,81,43,"#")).toThrow(/1–80/);expect(()=>resizeRoom(valueEdit(source,["decor_layer"],Array.from({length:4},()=>Array(5).fill(null))),6,5,"#")).toThrow(/inactive/);
  const withDimensions=valueEdit(valueEdit(source,["width"],5),["height"],4);expect(JSON.parse(resizeRoom(withDimensions,6,4,"#")).width).toBe(6);
 });
 it("adds overlapping individual records, edits/removes text overrides without rewriting metadata",()=>{
  let text=addRecord(source,[1,1],"container","crate");text=addRecord(text,[1,1],"item","wood_bundle");text=editItem(text,0,{x:2,y:1,item_id:"letter",text_id:"saved_text"});
  expect(JSON.parse(text).special_tiles).toHaveLength(3);expect(text).toContain('"metadata":{"n":1e2}');text=editItem(text,0,{x:2,y:1,item_id:"letter"});expect(JSON.parse(text).special_tiles[0]).not.toHaveProperty("text_id");
  text=deleteRecord(text,1);expect(JSON.parse(text).special_tiles.map((s:{type:string})=>s.type)).toEqual(["item","item"]);expect(text).toContain('"unknown":{"exact":[1e2,"\\u03bb",null]}');
 });
 it("freezes unsafe visual edits while preserving invalid exact source",()=>{
  const invalid=source.slice(0,-1);expect(layoutModel(invalid).model).toBeNull();expect(()=>resizeRoom(invalid,6,5,"#")).toThrow();expect(()=>addRecord(invalid,[1,1],"item","letter")).toThrow();
 });
 it("preserves unpainted literal escapes in the same row, including supplementary characters",()=>{
  const escaped=source.replace('#λ .#','#\\u03bb .#');const next=paint(escaped,[[3,1]],"terrain","#");expect(next).toContain('#\\u03bb ##');
  const astral=source.replace('#λ .#','#\\uD83D\\uDD01 .#').replace('"λ":"floor"','"🔁":"floor"');
  expect(paint(astral,[[3,1]],"terrain","#")).toContain('#\\uD83D\\uDD01 ##');expect(resizeRoom(escaped,6,4,"#")).toContain('#\\u03bb .##');
 });
 it("negotiates structured scene results independently of reader PNG frames",()=>{
  const scene={route:"authored_submap",layout_contract:"authored-room-2",valid:true,passed:true,width:80,height:43,terrain:Array.from({length:43},()=>Array(80).fill("floor")),spawn:[1,1],origin:[0,0],authored_start:[1,1],legend:{floor:{}},scene_seed:"18446744073709551615",population_receipts:[],access:[{target:"return",passed:true}]};
  expect(sceneProblem(scene)).toBe("");expect(sceneProblem({...scene,layout_contract:"direct-creatures-1"})).toMatch(/registered scene/);expect(sceneProblem({...scene,population_receipts:[{kind:"item",record_id:"special[0]",source_index:0,objects:[],actors:[],xy:[1]}]})).toMatch(/population/);
 });
});
