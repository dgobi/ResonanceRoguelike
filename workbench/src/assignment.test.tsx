import {expect,test} from "vitest";
import {renderToStaticMarkup} from "react-dom/server";
import {AssignmentEditor} from "./AssignmentEditor";
import {OrderedRecords} from "./ContractControls";
import {previewProblem} from "./familyData";
import {recordRow} from "./orderedRecords";
import {CanvasHistory} from "./layout";
import type {ContentFamily} from "./content";
import type {ContentProps} from "./ContentEditor";
const path="roguelike/data/generation/authored_submap_selection.json";
const raw={id:"authored_submap_selection",version:1,enabled:false,target_type:"barrow",authored_chance:0,candidates:[]};
const family:ContentFamily={id:"assignment",contract:"authored-submap-selection-1",descriptor_sha256:"a".repeat(64),compatible:true,problems:[],references:{},effective_operations:["edit"],descriptor:{vocabulary:"resonance-controls-1",policy:{operations:["edit"],root:path,identity:"id"},views:["world-assignment"],publication_note:"Assignment changes apply to newly created worlds. Same-ID room edits apply to pending scenes.",schema:{type:"object",properties:{candidates:{type:"array","x-control":"ordered-records",items:{type:"object",properties:{layout_id:{type:"string"},weight:{type:"number"}}}}}}},context:{records:[{id:raw.id,definition:raw,capability:{editable:true,reason:""},diagnostics:[]}],rooms:[{id:"room_a",label:"Readable hall · room_a",path:"roguelike/data/layouts/room_a.json",eligible:true,reason:""}]}};
test("assignment enrollment stages one row with exact metadata/history and no enablement",()=>{
  const before='\uFEFF{\r\n "enabled":false,"candidates":[],"meta":{"exact":[1e2,null,"λ"]}\r\n}\r\n';
  const after=recordRow(before,"candidates","add",-1,{layout_id:"room_a",weight:1});
  expect(after).toContain('"enabled":false');expect(after).toContain('"meta":{"exact":[1e2,null,"λ"]}');expect(after.endsWith("\r\n")).toBe(true);
  const h=new CanvasHistory();h.record(before,after,"add");expect(h.undo(after)).toBe(before);expect(h.redo(before)).toBe(after);
  expect(JSON.parse(recordRow('{"candidates":[{"layout_id":"room_a","weight":1}]}',"candidates","remove",0)).candidates).toEqual([]);
  const html=renderToStaticMarkup(<OrderedRecords family={family} values={{candidates:[{layout_id:"room_a",weight:1}]}} disabled={false} allowEmpty onEdit={()=>{throw Error("render mutation");}}/>);
  expect(html).toContain('aria-label="remove candidates 1"');expect(html).not.toContain('aria-label="remove candidates 1" disabled');
});
test("editor distinguishes saved membership, draft candidate and a bounded saved sample",()=>{
  const no=()=>{};const p:ContentProps={sourceFamily:family,family,navigation:{relatedRoom:"room_a",onOpen:no},variant:false,active:true,cancelVersion:0,beginRequest:()=>({current:()=>true,finish:no}),draft:JSON.stringify({...raw,candidates:[{layout_id:"room_a",weight:1}]}),path,dirty:true,validated:false,disabled:"",busy:false,evidenceStale:false,onCancel:no,onSource:no,onProbe:no,preview:null,previewStale:true,onPreview:no,onEdit:no,onUndo:no,onRedo:no,canUndo:true,canRedo:false};
  const html=renderToStaticMarkup(<AssignmentEditor {...p}/>);expect(html).toContain('Current profile draft: candidate');expect(html).toContain('Saved enabled profile: not enrolled');expect(html).toContain('Readable hall');expect(html).toContain('Apply and byte-check reopen');
  expect(previewProblem({kind:"assignment-preview",width:32,height:32})).toBeTruthy();
});
