import { describe,it,expect } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import { OrderedRecords } from "./ContractControls";
import { recordRow } from "./orderedRecords";
import { recordDefaults, familyProblem, type ContentFamily } from "./content";
import { itemValue } from "./item";
import { CanvasHistory } from "./layout";

const family:ContentFamily={id:"text",contract:"ordinary-found-text-1",descriptor_sha256:"a".repeat(64),compatible:true,problems:[],context:null,references:{},descriptor:{vocabulary:"resonance-controls-1",views:["text-pages","reader-preview"],policy:{operations:["variant"],root:"roguelike/data/texts/",identity:"id"},publication_note:"Variant only",schema:{$schema:"https://json-schema.org/draft/2020-12/schema",type:"object",properties:{pages:{type:"array","x-control":"ordered-records",items:{type:"object",properties:{text:{type:"string","x-control":"multiline","x-initial":""},trailing:{type:"boolean",default:false}}}}}}}};
const text='\uFEFF{\r\n "id":"a", "pages":[\r\n  { "text":"First\\n\\nquoted \\\"æ\\\" and \\\\ path", "meta": {"nested":[null,true]} },\r\n  {"text":"Second [DAMAGED] [REDACTED]", "damaged":false}\r\n ], "root_meta": {"retain": 1e2}\r\n}\r\n';
const parse=(s:string)=>JSON.parse(s.replace(/^\uFEFF/,""));
describe("ordered record source fidelity",()=>{
 it("renders missing optional booleans without any writes or inserted default",()=>{
  const html=renderToStaticMarkup(<OrderedRecords family={family} values={parse(text)} disabled={false} onEdit={()=>{throw Error("unexpected edit");}}/>);
  expect(html).toContain("effective default: false");expect(html).not.toContain('checked=""');expect(familyProblem(family)).toBe("");
  expect(recordDefaults(family.descriptor.schema.properties!.pages)).toEqual({text:""});
  expect(itemValue(text,["pages",0,"text"],parse(text).pages[0].text)).toBe(text);
 });
 it("localizes multiline Unicode escapes and carries exact objects through moves and history",()=>{
  const body='New æ — "quoted" \\ backslash\n\n[DAMAGED] [REDACTED]\nLast';
  const changed=itemValue(text,["pages",0,"text"],body);
  expect(parse(changed).pages[0].text).toBe(body);
  expect(changed.replace(JSON.stringify(body),JSON.stringify(parse(text).pages[0].text))).toBe(text);
  const moved=recordRow(changed,"pages","down",0);
  expect(moved).toContain('{ "text":'+JSON.stringify(body)+', "meta": {"nested":[null,true]} }');
  expect(recordRow(moved,"pages","up",1)).toBe(changed);
  const history=new CanvasHistory();history.record(text,changed,"body");history.record(changed,moved,"move");
  expect(history.undo(moved)).toBe(changed);expect(history.undo(changed)).toBe(text);expect(history.redo(text)).toBe(changed);
  const added=recordRow(moved,"pages","add",-1,{text:"Third"});expect(parse(added).pages[2]).toEqual({text:"Third"});
  const removed=recordRow(added,"pages","remove",0);expect(parse(removed).pages[0].meta).toEqual({nested:[null,true]});
  expect(removed).toContain('"root_meta": {"retain": 1e2}');expect(removed.endsWith("\r\n")).toBe(true);
  const explicit=itemValue(removed,["pages",0,"trailing"],false);expect(parse(explicit).pages[0].trailing).toBe(false);
  expect(itemValue(explicit,["pages",0,"trailing"],false)).toBe(explicit);
 });
 it("recomputes paths after edits and refuses invalid/ambiguous raw structures",()=>{
  const moved=recordRow(text,"pages","up",1), changed=itemValue(moved,["pages",0,"text"],"Changed second page");
  expect(parse(changed).pages[1]).toEqual(parse(text).pages[0]);
  for(const invalid of ['{"pages":','{"pages":[null]}','{"pages":{}}','{"pages":[],"pages":[]}']) expect(()=>recordRow(invalid,"pages","add",-1,{text:""})).toThrow();
  expect(familyProblem({...family,descriptor:{...family.descriptor,schema:{...family.descriptor.schema,properties:{condition:{type:"string","x-suggestions":[3]}}}}})).toContain("suggestions");
 });
});
