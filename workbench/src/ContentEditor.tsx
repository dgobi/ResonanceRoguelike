import { ItemEditor } from "./ItemEditor";
import { RecipeEditor } from "./RecipeEditor";
import { familyProblem, type ContentFamily } from "./content";
import type { ItemTrail } from "./protocol";

export type ContentNavigation = {selectedId?: string; trail?: ItemTrail | null; onReturn?: ()=>void;
  onPool?: (id:string)=>void; onOpen: (family:string,id:string,path?:string)=>void};
type Props = {family: ContentFamily; navigation: ContentNavigation; draft:string; path:string; dirty:boolean; validated:boolean;
  disabled:string; busy:boolean; evidenceStale:boolean; onCancel:()=>void; onSource:()=>void; onProbe:()=>void;
  onEdit:(edit:(text:string)=>string,label:string)=>void; onUndo:()=>void; onRedo:()=>void; canUndo:boolean; canRedo:boolean};

// Specialist views receive the same document commands as ordinary controls.
// This registration contains presentation only, never mutable review authority.
export const contentViews = {
  item: {label:"item", sourceId:"item-draft-json", hint:"Component controls share this exact source draft. References, use binding and factory results distinguish declarations from observed instances.",
    render:(p:Props)=>p.family.id === "item" && <ItemEditor {...p} context={p.family.context || undefined} {...p.navigation} onRecipe={(id,path)=>p.navigation.onOpen("recipe",id,path)} />},
  recipe: {label:"recipe", sourceId:"recipe-draft-json", hint:"Recipe controls share this exact source draft. Eligibility and observed output have separate receipts. Publication creates a new ID/file.",
    render:(p:Props)=>p.family.id === "recipe" && <RecipeEditor {...p} context={p.family.context || undefined} {...p.navigation} onItem={(id,path)=>p.navigation.onOpen("item",id,path)} />},
};
export function ContentEditor(p:Props) {
  const problem = familyProblem(p.family);
  if (problem) return <section className="item-editor"><p className="notice warning">{problem}. Inspect or repair exact Source.</p><button onClick={p.onSource}>Show source</button></section>;
  return contentViews[p.family.id].render(p);
}
