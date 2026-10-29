import { describe, expect, it } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import { ContractFields, KeyedNumberMap } from "./ContractControls";
import { effectiveValue, familyProblem, rowDefaults, schemaProblem, type ContentFamily, type FieldSchema } from "./content";
import { itemValue } from "./item";
import { recipeRow } from "./recipe";

const boolean:FieldSchema = {type:"boolean",title:"A supported boolean",default:true};
const schema:FieldSchema = {$schema:"https://json-schema.org/draft/2020-12/schema",type:"object",properties:{flag:boolean}};
const family:ContentFamily = {id:"item",contract:"compatible-contract",descriptor_sha256:"a".repeat(64),compatible:true,problems:[],context:null,references:{},
  descriptor:{vocabulary:"resonance-controls-1",schema,views:["item-properties"],policy:{operations:["edit","variant"],root:"roguelike/data/items/components/",identity:"id"},publication_note:"Example"}};
describe("registered ordinary controls and exact-source ownership",()=>{
  it("renders a compatible new boolean with no family field list; absence never inserts a key",()=>{
    const text='{\r\n "id":"a", "metadata":{"nested":[true,null,{"prose":"untouched"}]}\r\n}\r\n';
    const values=JSON.parse(text), edits:unknown[]=[];
    const html=renderToStaticMarkup(<ContractFields family={family} values={values} onChange={(...v)=>edits.push(v)}/>);
    expect(html).toContain('checked=""');expect(html).toContain("effective default: true");expect(edits).toEqual([]);
    expect(values).not.toHaveProperty("flag");
    const explicit=itemValue(text,["flag"],false);
    expect(explicit).toContain('"metadata":{"nested":[true,null,{"prose":"untouched"}]}');
    expect(explicit.endsWith("\r\n")).toBe(true);
    expect(itemValue(explicit,["flag"],false)).toBe(explicit);
    expect(itemValue(explicit,["flag"],true)).toBe(explicit.replace('"flag":false','"flag":true'));
  });
  it("preserves explicit false and null without normalizing either to a default",()=>{
    expect(effectiveValue(boolean,undefined)).toBe(true);expect(effectiveValue(boolean,false)).toBe(false);expect(effectiveValue(boolean,null)).toBe(null);
    const html=renderToStaticMarkup(<ContractFields family={family} values={{flag:null}} onChange={()=>{throw Error("unexpected write");}}/>);
    expect(html).toContain("Explicit null retained");expect(html).toContain('aria-invalid="true"');expect(html).not.toContain('checked=""');
    expect(()=>itemValue('{"id":',["flag"],false)).toThrow();
  });
  it("takes ordered row cells and defaults from the contract and preserves row spans",()=>{
    const requiredTier:FieldSchema={type:"integer","x-initial":1};
    expect(effectiveValue(requiredTier,undefined)).toBeUndefined();
    expect(rowDefaults({type:"array",items:{type:"object",properties:{tier:requiredTier}}},"fuel")).toEqual({tag:"fuel",tier:1});
    const row:FieldSchema={type:"array",items:{type:"object",properties:{tag:{type:"string","x-reference":"keywords"},min_tier:{type:"integer",default:2},quantity:{type:"integer",default:3}}}};
    expect(rowDefaults(row,"fuel")).toEqual({tag:"fuel",min_tier:2,quantity:3});
    const text='{ "tools":[ {"tag":"a","unknown": {"x": [null]}}, {"tag":"b", "quantity":2} ], "meta":"unchanged" }';
    const moved=recipeRow(text,"tools","down",0);
    expect(recipeRow(moved,"tools","up",1)).toBe(text);
    const added=recipeRow(text,"tools","add",-1,"fuel",rowDefaults(row,"fuel"));
    expect(added).toContain('{"tag":"a","unknown": {"x": [null]}}');
    expect(JSON.parse(added).tools[2]).toEqual({tag:"fuel",min_tier:2,quantity:3});
  });
  it("rejects unsupported or malformed descriptor vocabulary precisely",()=>{
    expect(familyProblem(family)).toBe("");
    expect(schemaProblem({...schema,allOf:[]})).toContain("unsupported schema keyword allOf");
    expect(schemaProblem({...boolean,type:"executable"})).toContain("unsupported type");
    expect(familyProblem({...family,descriptor:{...family.descriptor,vocabulary:"future"}})).toContain("vocabulary");
    expect(familyProblem({...family,references:{keywords:[{id:3}]}})).toContain("reference");
    expect(familyProblem({...family,id:"forged"})).toContain("Unregistered");
  });
  it("negotiates one bounded keyed number object and renders absence without writing defaults",()=>{
    const map:FieldSchema={type:"object",properties:{},additionalProperties:{type:"number",minimum:0,maximum:1},"x-control":"keyed-number-map","x-reference":"categories",title:"Reductions"};
    expect(schemaProblem({...schema,properties:{weight_reductions:map}})).toBe("");
    expect(schemaProblem({...schema,properties:{weight_reductions:{...map,additionalProperties:true}}})).toContain("keyed number map");
    const html=renderToStaticMarkup(<KeyedNumberMap family={family} field="weight_reductions" schema={map} value={undefined} disabled={false} onEdit={()=>{throw Error("unexpected edit");}}/>);
    expect(html).toContain("Absent in source");expect(html).toContain("effective empty map");
  });
});
