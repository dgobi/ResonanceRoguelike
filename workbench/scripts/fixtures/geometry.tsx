import React,{useState} from 'react';
import {createRoot} from 'react-dom/client';
import {RoomGeometry} from '../../src/RoomControls';
import {CanvasHistory,layoutModel,paint} from '../../src/layout';
const initial=JSON.stringify({id:'fixture',layers:Array(9).fill('..........'),legend:{'.':'floor','#':'wall'},player_start:{x:2,y:5},exit_direction:'south',exit_x:7,exit_y:6,metadata:{keep:'λ'}});
const history=new CanvasHistory();
function Fixture(){
 const [source,setSource]=useState(initial),[shown,setShown]=useState(true);
 const edit=(operation:(s:string)=>string,label:string)=>setSource(s=>{const next=operation(s);history.record(s,next,label);return next;});
 const m=layoutModel(source).model;
 return <><textarea aria-label="Source" value={source} onChange={e=>edit(()=>e.target.value,'Source')}/><output>{source}</output>
 <button onClick={()=>setSource(s=>history.undo(s)??s)}>Undo</button><button onClick={()=>setSource(s=>history.redo(s)??s)}>Redo</button>
 <button onClick={()=>edit(s=>paint(s,[[0,0]],'terrain','#'),'Paint')}>Paint</button><button onClick={()=>setShown(!shown)}>Switch document</button>
 <div hidden={!shown}>{m&&<RoomGeometry model={m} draft={source} catalog={{terrain:{floor:{walkable:true,transparent:true},wall:{walkable:false,transparent:false}},decor:{},loot_pools:[]}} disabled={false} onEdit={edit}/>}</div></>;
}
createRoot(document.getElementById('root')!).render(<Fixture/>);
