import {useEffect,useRef,useState} from 'react';
import {invoke} from '@tauri-apps/api/core';
import type {Inspection} from './protocol';
import {sourceOperations} from './content';

type Status={status:string;preparing?:boolean;session_id?:string;pid?:number;newer_saved?:boolean;error?:string;last_action_error?:unknown;diagnostics?:string;captured?:{snapshot_id:string;room_path:string;room_sha256:string;manifest_sha256:string;runtime_sha256:string;captured_ms:number;seed:number};validation?:{profile?:string;diagnostics?:unknown[]};readiness?:unknown};
export function RoomTestPanel({document,dirty,dependencyVersion}:{document?:Inspection;dirty:boolean;dependencyVersion:number}){
 const [state,setState]=useState<Status>({status:'stopped'}),[pending,setPending]=useState(false),[error,setError]=useState('');
 const mounted=useRef(true);
 async function refresh(action='status'){try{const next=await invoke<Status>('room_test_action',{action});if(mounted.current)setState(next);}catch(e){if(mounted.current)setError(JSON.stringify(e));}}
 useEffect(()=>{mounted.current=true;void refresh();const timer=setInterval(()=>void refresh(),1000);return()=>{mounted.current=false;clearInterval(timer);};},[]);
 useEffect(()=>{void refresh('refresh');const focus=()=>void refresh('refresh');window.addEventListener('focus',focus);return()=>window.removeEventListener('focus',focus);},[dependencyVersion]);
 async function action(action:string){setError('');setPending(true);try{const next=await invoke<Status>('room_test_action',{action,token:document?.document_token});if(mounted.current)setState(next);}catch(e){if(mounted.current)setError(JSON.stringify(e));}finally{if(mounted.current)setPending(false);}}
 const eligible=document?.family?.id==='room'&&document.route==='authored_submap'&&document.path.startsWith('roguelike/data/layouts/')&&sourceOperations(document.family).includes('edit');
 const captured=state.captured;
 return <section className="room-test-panel" data-testid="room-test-panel" aria-label="Disposable room test">
  <strong>Test room in game · {state.preparing?'preparing':state.status}</strong>
  <p>Uses saved room, saved dependencies and saved typography. Other parked drafts remain open and are excluded. Gameplay and F5/F9 saves belong to a disposable session.</p>
  {document?.family?.id==='room'&&!eligible&&<p>Save the template as an eligible ordinary room variant first. Protected, ambiguous and unsupported sources cannot launch.</p>}
  {dirty&&eligible&&<p>Save and reopen this room, or discard/reconcile its draft, before capturing a new test.</p>}
  <div className="tool-buttons">
   <button disabled={!eligible||dirty||pending||state.preparing||state.status==='running'||state.status==='starting'} onClick={()=>void action('test')}>Test room</button>
   <button disabled={!captured||pending||state.preparing} onClick={()=>void action('reset')}>Reset current test</button>
   <button disabled={!eligible||dirty||pending||state.preparing} onClick={()=>void action('latest')}>Test latest saved version</button>
   <button disabled={!pending&&!state.preparing&&!['starting','running'].includes(state.status)} onClick={()=>void action('stop')}>{state.preparing?'Cancel test preparation':'Stop'}</button>
  </div>
  {captured&&<><p>Captured {captured.room_path} · {new Date(captured.captured_ms).toLocaleString()} · seed {captured.seed}</p>
   <p>{state.validation?.profile||'Normal player components; lit tallow torch, crow jerky, water flask, crude blade, leather jack and moist pebble. Normal needs, combat and death.'}</p>
   {state.newer_saved&&<p className="notice warning">Newer saved inputs detected. This test retains its captured version; use Test latest saved version deliberately.</p>}
   <details><summary>Captured identities and diagnostics</summary><pre className="raw">{JSON.stringify({...captured,session_id:state.session_id,pid:state.pid,readiness:state.readiness,validation:state.validation},null,2)}</pre><pre className="raw">{state.diagnostics}</pre></details>
  </>}
  {!!(error||state.error||state.last_action_error)&&<p role="alert">{error||state.error||JSON.stringify(state.last_action_error)}</p>}
 </section>;
}
