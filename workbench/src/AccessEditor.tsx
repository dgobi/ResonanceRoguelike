import type {ContentProps} from './ContentEditor';
import {ContractFields} from './ContractControls';
import {valueEdit} from './layout';

export function AccessEditor(p:ContentProps){
 let raw:Record<string,unknown>;
 try {raw=JSON.parse(p.draft.replace(/^\uFEFF/,''));}catch{return <p>Repair JSON in Source to resume controls.</p>;}
 if(p.family.id!=='access')return null;
 return <section data-testid="access-editor"><p className="notice">{p.family.descriptor.publication_note}</p>
 <p>Two explicit hosts share this fastening. Careful steps keep the equipped tool. Force and Dissolution yield no timber; the coffer always retains its original contents.</p>
 <fieldset disabled={!!p.disabled||p.busy}><legend>Fastening response</legend>
 <ContractFields family={p.family} values={raw} onChange={(path,value)=>p.onEdit(s=>valueEdit(s,path,value),'Edit fastening '+path.join('.'))}/>
 </fieldset>
 <div className="edit-actions"><button disabled={!p.canUndo||p.busy} onClick={p.onUndo}>Undo fastening</button><button disabled={!p.canRedo||p.busy} onClick={p.onRedo}>Redo fastening</button><button onClick={p.onSource}>Show fastening source</button></div>
 <h3>Saved references</h3><p>Saved room and building references; unpublished drafts are excluded. Validate to refresh. Publish this profile before placing its ID.</p>
 {(p.family.context?.references??[]).map(r=><button key={r.path+r.field} onClick={()=>p.navigation.onOpen(r.family,r.id,r.path)}>{r.id} · {r.field} · {r.path}</button>)}
 </section>;
}
