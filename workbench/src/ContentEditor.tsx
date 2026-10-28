import { CreatureEditor } from "./CreatureEditor";
import type { RequestLease } from "./requests";
import { ItemEditor } from "./ItemEditor";
import { RecipeEditor } from "./RecipeEditor";
import { TextEditor } from "./TextEditor";
import { TypographyEditor } from "./TypographyEditor";
import {LayoutEditor,type LayoutProps} from "./LayoutEditor";
import type { FamilyPreview } from "./familyData";
import { familyProblem, type ContentFamily } from "./content";
import type { ItemTrail } from "./protocol";

export type ContentNavigation = {selectedId?: string; trail?: ItemTrail | null; onReturn?: ()=>void; returnLabel?: string;
  onPool?: (id:string)=>void; onOpen: (family:string,id:string,path?:string)=>void};
export type ContentProps = {sourceFamily:ContentFamily; variant:boolean; active:boolean; cancelVersion:number; beginRequest:(label:string)=>RequestLease; family: ContentFamily; navigation: ContentNavigation; draft:string; path:string; dirty:boolean; validated:boolean;
  spatial?:LayoutProps;
  disabled:string; busy:boolean; evidenceStale:boolean; onCancel:()=>void; onSource:()=>void; onProbe:()=>void;
  preview:FamilyPreview|null; previewStale:boolean; onPreview:(inputs:Record<string,number>)=>void;
  onEdit:(edit:(text:string)=>string,label:string)=>void; onUndo:()=>void; onRedo:()=>void; canUndo:boolean; canRedo:boolean};
type Props = ContentProps;

// Specialist views receive the same document commands as ordinary controls.
// This registration contains presentation only, never mutable review authority.
export const contentViews = {
  room:{label:"room",sourceId:"room-draft-json",hint:"Terrain, arrival, direct contents and linked references share this exact source, history and recovery. Validate realized geometry, population and static access before publication.",render:(p:Props)=><section data-testid="room-editor"><p className="notice">{p.family.descriptor.publication_note}</p>{p.navigation.onReturn&&<button onClick={p.navigation.onReturn}>{p.navigation.returnLabel}</button>}<button onClick={p.onSource}>Show room source</button>{p.sourceFamily.id==="room"&&p.sourceFamily.context?.records[0]?.capability.reason&&<p className="notice warning">{p.sourceFamily.context.records[0].capability.reason}</p>}{p.spatial&&<LayoutEditor {...p.spatial}/>}</section>},
  creature:{label:"creature",sourceId:"creature-draft-json",hint:"Common Actor controls share exact Source, history, recovery and publication. Special bindings retain their stable ID.",render:(p:Props)=><CreatureEditor {...p}/>},
  item: {label:"item", sourceId:"item-draft-json", hint:"Component controls share this exact source draft. References, use binding and factory results distinguish declarations from observed instances.",
    render:(p:Props)=>p.family.id === "item" && <ItemEditor {...p} context={p.family.context || undefined} {...p.navigation} onRecipe={(id,path)=>p.navigation.onOpen("recipe",id,path)} />},
  recipe: {label:"recipe", sourceId:"recipe-draft-json", hint:"Recipe controls share this exact source draft. Eligibility and observed output have separate receipts. Publication creates a new ID/file.",
    render:(p:Props)=>p.family.id === "recipe" && <RecipeEditor {...p} context={p.family.context || undefined} {...p.navigation} onItem={(id,path)=>p.navigation.onOpen("item",id,path)} />},
  text: {label:"text", sourceId:"text-draft-json", hint:"Reader properties and ordered pages share this exact source. Create a unique variant, preview, validate and deliberately publish.",render:(p:Props)=><TextEditor {...p}/>},
  typography:{label:"typography",sourceId:"typography-draft-json",hint:"Shared proportional game roles, fixed sizes. Publish the singleton profile; changes apply at next game initialization.",render:(p:Props)=><TypographyEditor {...p}/>},
};
export function ContentEditor(p:Props) {
  const problem = familyProblem(p.family);
  if (problem) return <section className="item-editor"><p className="notice warning">{problem}. Inspect or repair exact Source.</p><button onClick={p.onSource}>Show source</button></section>;
  return <>{p.navigation.onReturn&&<button disabled={p.busy} onClick={p.navigation.onReturn}>{p.navigation.returnLabel||"Return to origin"}</button>}{contentViews[p.family.id].render({...p,navigation:{...p.navigation,onReturn:undefined}})}</>;
}
