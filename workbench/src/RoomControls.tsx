import {useState} from "react";
import {editItem, resizeRoom, valueEdit, type Catalog, type Layout, type Special} from "./layout";

type Edit=(operation:(source:string)=>string,label:string)=>void;
export function RoomGeometry({model:m,draft,catalog,disabled,onEdit}:{model:Layout;draft:string;catalog:Catalog;disabled:boolean;onEdit:Edit}) {
 const [width,setWidth]=useState(String(m.width)),[height,setHeight]=useState(String(m.height)),[fill,setFill]=useState(Object.keys(m.legend)[0]);
 const [glyph,setGlyph]=useState(""),[terrain,setTerrain]=useState("__null__");
 const [x,setX]=useState(String(m.player_start?.x??0)),[y,setY]=useState(String(m.player_start?.y??0));
 const [direction,setDirection]=useState(m.exit_direction??"south"),[exitX,setExitX]=useState(String(m.exit_x??m.width-2)),[exitY,setExitY]=useState(String(m.exit_y??m.height-2));
 const raw=JSON.parse(draft.replace(/^\uFEFF/,""));
 const coordinate=(a:string,b:string)=>a!==""&&b!==""&&[Number(a),Number(b)].every(Number.isInteger)&&Number(a)>=0&&Number(b)>=0&&Number(a)<m.width&&Number(b)<m.height;
 return <details className="room-geometry" open><summary>Room geometry, arrival and return</summary>
  <fieldset disabled={disabled}><legend>Legend mapping</legend>
   <label>One character<input aria-label="Legend glyph" value={glyph} onChange={e=>setGlyph(e.target.value)}/></label>
   <label>Existing terrain<select aria-label="Legend terrain" value={terrain} onChange={e=>setTerrain(e.target.value)}><option value="__null__">null · keep initial wall fill</option>{Object.keys(catalog.terrain).map(id=><option key={id}>{id}</option>)}</select></label>
   <button disabled={Array.from(glyph).length!==1} onClick={()=>onEdit(s=>valueEdit(s,["legend",glyph],terrain==="__null__"?null:terrain),"Set legend mapping")}>Set legend mapping</button>
   <small>Null leaves the authored submap's initial wall fill. It does not create empty floor. Explicit stairs_up terrain is painted using its legend glyph.</small>
  </fieldset>
  <fieldset disabled={disabled}><legend>Deliberate rectangular resize · current {m.width} × {m.height}</legend>
   <label>Width<input aria-label="Room width" type="number" min="1" max="80" value={width} onChange={e=>setWidth(e.target.value)}/></label>
   <label>Height<input aria-label="Room height" type="number" min="1" max="43" value={height} onChange={e=>setHeight(e.target.value)}/></label>
   <label>Fill glyph<select aria-label="Resize fill glyph" value={fill} onChange={e=>setFill(e.target.value)}>{Object.keys(m.legend).map(g=><option key={g} value={g}>{JSON.stringify(g)} → {m.legend[g]??"initial wall"}</option>)}</select></label>
   <p>Top-left source anchor: retain coordinates and significant spaces; extend right/bottom with the selected glyph, or deliberately crop terrain at right/bottom. Records, arrivals and metadata are never moved or cropped. A resize that strands retained coordinates is refused. Inactive decor layers lock resizing. Centering and position-derived loot can change, including with the same preview seed.</p>
   <button onClick={()=>onEdit(s=>resizeRoom(s,Number(width),Number(height),fill),"Resize room (top-left anchor)")}>Apply resize (top-left anchor)</button>
  </fieldset>
  <fieldset disabled={disabled}><legend>Authored player_start · source coordinates</legend>
   <label>X<input aria-label="Arrival X" type="number" value={x} onChange={e=>setX(e.target.value)}/></label><label>Y<input aria-label="Arrival Y" type="number" value={y} onChange={e=>setY(e.target.value)}/></label>
   <button disabled={!coordinate(x,y)} onClick={()=>onEdit(s=>valueEdit(valueEdit(s,["player_start","x"],Number(x)),["player_start","y"],Number(y)),"Set authored arrival")}>Apply arrival</button>
   <small>The white source marker is authored player_start. Production preview separately reports the actual game-selected arrival after population safety checks.</small>
  </fieldset>
  <fieldset disabled={disabled}><legend>Fallback return settings</legend>
   <p>Any explicit stairs_up suppresses exit_direction, exit_x and exit_y. Otherwise north/south uses exit_y and the horizontal midpoint; east/west uses exit_x and the vertical midpoint. Direction does not select an edge. Preview shows the produced stairs and reachability.</p>
   <label>Direction<select aria-label="Fallback exit direction" value={direction} onChange={e=>setDirection(e.target.value)}>{["north","south","east","west"].map(d=><option key={d}>{d}</option>)}</select></label>
   <label>exit_x<input aria-label="Fallback exit X" type="number" value={exitX} onChange={e=>setExitX(e.target.value)}/></label><label>exit_y<input aria-label="Fallback exit Y" type="number" value={exitY} onChange={e=>setExitY(e.target.value)}/></label>
   <button disabled={!coordinate(exitX,exitY)} onClick={()=>onEdit(s=>valueEdit(valueEdit(valueEdit(s,["exit_direction"],direction),["exit_x"],Number(exitX)),["exit_y"],Number(exitY)),"Set fallback exit")}>Apply fallback return</button>
  </fieldset>
  <details><summary>Retained inactive fields</summary><p>decor_layer, legend_weights, top-level stairs_up, type, rotatable and tags do not activate those behaviors on this route. Containers provide physical furnishings.</p><pre className="raw">{JSON.stringify(Object.fromEntries(["decor_layer","legend_weights","stairs_up","type","rotatable","tags"].map(k=>[k,k in raw?raw[k]:"(absent)"])),null,2)}</pre></details>
 </details>;
}

export function ItemFields({record,catalog,disabled,index,onEdit,onDelete}:{record:Special;catalog:Catalog;disabled:boolean;index:number;onEdit:Edit;onDelete:()=>void}) {
 const [x,setX]=useState(String(record.x)),[y,setY]=useState(String(record.y)),[id,setId]=useState(String(record.item_id??""));
 const [binding,setBinding]=useState("text_id" in record),[text,setText]=useState(String(record.text_id??""));
 const carrier=catalog.items?.find(r=>r.id===id), valid=carrier?.resolved && [Number(x),Number(y)].every(Number.isInteger)&&x!==""&&y!==""&&(!binding||carrier.readable&&catalog.texts?.some(r=>r.id===text&&r.resolved));
 return <fieldset disabled={disabled}><legend>Direct item · one actual factory object</legend>
  <label>Item ID<select aria-label="Marker item ID" value={id} onChange={e=>setId(e.target.value)}>{!catalog.items?.some(r=>r.id===id)&&<option value={id}>{id} · missing</option>}{catalog.items?.map(r=><option key={r.id} value={r.id} disabled={!r.resolved}>{r.id} · {r.name} · {r.path}{!r.resolved?" · ambiguous / unsupported":""}{r.readable?" · readable":""}</option>)}</select></label>
  <label>Source X<input aria-label="Item source X" type="number" value={x} onChange={e=>setX(e.target.value)}/></label><label>Source Y<input aria-label="Item source Y" type="number" value={y} onChange={e=>setY(e.target.value)}/></label>
  <label><input aria-label="Override readable text" type="checkbox" checked={binding} onChange={e=>setBinding(e.target.checked)}/>Override text_id on this carrier</label>
  {binding&&<label>Saved text<select aria-label="Marker text ID" value={text} onChange={e=>setText(e.target.value)}><option value="">Choose saved text…</option>{!catalog.texts?.some(r=>r.id===text)&&text&&<option value={text}>{text} · missing</option>}{catalog.texts?.map(r=><option key={r.id} value={r.id} disabled={!r.resolved}>{r.id} · {r.name} · {r.path}{!r.resolved?" · ambiguous":""}</option>)}</select></label>}
  <p>{binding?carrier?.readable?"Explicit carrier retained; the actual placed readable instance receives this text_id.":"This carrier is inert. Choose a saved readable carrier whose constructed on_use is read, or remove the override.":"No record text override. The carrier keeps its definition's default behavior/binding."} Underground placement does not substitute text_item_map carriers.</p>
  <button disabled={!valid} onClick={()=>onEdit(s=>editItem(s,index,{x:Number(x),y:Number(y),item_id:id,...(binding?{text_id:text}:{})}),"Move / edit item")}>Apply item edit</button><button onClick={onDelete}>Delete item</button>
 </fieldset>;
}
