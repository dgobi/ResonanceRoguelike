import {expect,test} from "vitest";
import {renderToStaticMarkup} from "react-dom/server";
import {TypographyEditor} from "./TypographyEditor";
import type {ContentFamily} from "./content";
import type {ContentProps} from "./ContentEditor";
import {familyProblem} from "./content";
import {itemValue} from "./item";
import {CanvasHistory} from "./layout";
import {previewProblem} from "./familyData";

const family:ContentFamily={id:"typography",contract:"game-typography-1",descriptor_sha256:"a".repeat(64),compatible:true,problems:[],references:{"project-fonts":[{id:"Junicode.ttf",label:"Junicode"},{id:"IMFellEnglish-Regular.ttf",label:"IM Fell English Regular"}]},context:{records:[{id:"game_typography",pointer:"",definition:{},capability:{contract:"game-typography-1",editable:true,reason:"Eligible"},diagnostics:[]}],fonts:[]},descriptor:{vocabulary:"resonance-controls-1",policy:{operations:["edit"],root:"roguelike/data/display/typography.json",identity:"id"},views:["typography-roles","typography-preview"],publication_note:"Fonts apply at the next game initialization.",schema:{$schema:"https://json-schema.org/draft/2020-12/schema",type:"object",properties:{id:{type:"string",readOnly:true},font_ui_large:{type:"string",title:"Headings","x-reference":"project-fonts"},font_ui_normal:{type:"string",title:"Ordinary prose","x-reference":"project-fonts"}}}}};
const source='\uFEFF{\r\n "id":"game_typography", "version":1,\r\n "font_ui_large":"Junicode.ttf", "font_ui_normal":"Junicode.ttf",\r\n "metadata": {"exact":[1e2, null, "λ\\n"]}\r\n}\r\n';
test("ordinary role controls keep exact metadata and independent history",()=>{
  expect(familyProblem(family)).toBe("");
  const heading=itemValue(source,["font_ui_large"],"IMFellEnglish-Regular.ttf"),prose=itemValue(heading,["font_ui_normal"],"FoulisGreek.ttf");
  expect(prose).toContain('"metadata": {"exact":[1e2, null, "λ\\n"]}');expect(prose.endsWith("\r\n")).toBe(true);
  const history=new CanvasHistory();history.record(source,heading,"heading");history.record(heading,prose,"prose");expect(history.undo(prose)).toBe(heading);expect(history.undo(heading)).toBe(source);expect(history.redo(source)).toBe(heading);
  const no=()=>{};const props:ContentProps={sourceFamily:family,variant:false,active:true,cancelVersion:0,beginRequest:()=>({current:()=>true,finish:no}),family,navigation:{onOpen:no},draft:prose,path:family.descriptor.policy.root,dirty:true,validated:false,disabled:"",busy:false,evidenceStale:false,onCancel:no,onSource:no,onProbe:no,preview:null,previewStale:true,onPreview:no,onEdit:()=>{throw Error("render wrote source");},onUndo:no,onRedo:no,canUndo:true,canRedo:false};
  const html=renderToStaticMarkup(<TypographyEditor {...props}/>);expect(html).toContain('aria-label="Headings"');expect(html).toContain('aria-label="Ordinary prose"');expect(html).toContain("next game initialization");expect(html).toContain("FoulisGreek.ttf");
});
test("typography has a distinct bounded preview shape",()=>{
  expect(previewProblem({kind:"typography-preview",image:"data:image/png;base64,AA==",width:960,height:640})).toBeTruthy();
  expect(previewProblem({kind:"reader-frame",specimen:{},reader:{}})).toBeTruthy();
});
