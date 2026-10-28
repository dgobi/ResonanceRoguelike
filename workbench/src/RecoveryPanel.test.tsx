import {beforeEach,expect,test,vi} from "vitest";
import type {ReactElement,ReactNode} from "react";
// Execute the component's actual handlers with deterministic hook storage. No
// abstract selection model: assertions inspect its rendered JSX and IPC calls.
const hooks=vi.hoisted(()=>({slots:[] as unknown[],index:0,effects:[] as (()=>void)[]}));
vi.mock("react",()=>({
  useState:(initial:unknown)=>{const i=hooks.index++;if(!(i in hooks.slots))hooks.slots[i]=initial;return [hooks.slots[i],(v:unknown)=>{hooks.slots[i]=typeof v==="function"?v(hooks.slots[i]):v;}];},
  useRef:(initial:unknown)=>{const i=hooks.index++;return hooks.slots[i]??(hooks.slots[i]={current:initial});},
  useEffect:(effect:()=>void|(()=>void),deps:unknown[])=>{const i=hooks.index++,old=hooks.slots[i] as {deps:unknown[];cleanup?:()=>void}|undefined;if(!old || deps.some((d,n)=>d!==old.deps[n]))hooks.effects.push(()=>{old?.cleanup?.();hooks.slots[i]={deps,cleanup:effect()};});},
}));
vi.mock("@tauri-apps/api/core",()=>({invoke:vi.fn()}));
import {invoke} from "@tauri-apps/api/core";
import {RecoveryPanel,type RecoveryRow} from "./RecoveryPanel";
const a:RecoveryRow={key:"A",project:"project",source:"a.json",family:"text",generation:1,captured_ms:1,status:"draft"};
const b:RecoveryRow={...a,key:"B",source:"b.json",generation:7};
const detail=(r:RecoveryRow)=>({key:r.key,record:{...r,baseline:"original",draft:`exact ${r.key}`,target:`saved-${r.key}.json`,variant:true,variant_id:"saved",contract:"v1"},status:"draft",disk:"disk"});
function deferred<T>(){let resolve!:(value:T)=>void;const promise=new Promise<T>(r=>resolve=r);return {promise,resolve};}
const tick=async()=>{for(let i=0;i<10;i++)await Promise.resolve();};
function nodes(value:ReactNode):ReactElement<Record<string,unknown>>[]{if(Array.isArray(value))return value.flatMap(nodes);if(!value || typeof value!=="object" || !("props" in value))return [];const e=value as ReactElement<Record<string,unknown>>;return [e,...nodes(e.props.children as ReactNode)];}
function words(value:ReactNode):string{if(Array.isArray(value))return value.map(words).join("");if(value && typeof value==="object" && "props" in value)return words((value as ReactElement<{children:ReactNode}>).props.children);return typeof value==="string"||typeof value==="number"?String(value):"";}
function setup(){
  const props={open:true,onClose:vi.fn(),onRestore:vi.fn(async()=>{}),onError:vi.fn(),refreshVersion:0};let tree:ReactNode;
  const render=()=>{hooks.index=0;tree=RecoveryPanel(props);hooks.effects.splice(0).forEach(f=>f());};
  const click=(label:string)=>{const el=nodes(tree).find(e=>e.type==="button" && words(e.props.children as ReactNode)===label);expect(el, label).toBeTruthy();(el!.props.onClick as ()=>void)();render();};
  const select=(key:string)=>{const el=nodes(tree).find(e=>e.props["data-recovery-key"]===key);expect(el).toBeTruthy();(el!.props.onClick as ()=>void)();render();};
  return {props,render,click,select,draft:()=>nodes(tree).find(e=>e.props["aria-label"]==="Recovered exact draft")?.props.value,text:()=>words(tree)};
}
beforeEach(()=>{hooks.slots=[];hooks.index=0;hooks.effects=[];vi.mocked(invoke).mockReset();});
test("delayed A/B inspection binds displayed draft, discard identity and confirmation",async()=>{
  const da=deferred<ReturnType<typeof detail>>(),db=deferred<ReturnType<typeof detail>>();
  vi.mocked(invoke).mockImplementation((cmd,args)=>cmd==="list_recovery"?Promise.resolve({records:[a,b],notices:[]}):cmd==="inspect_recovery"?((args as {key:string}).key==="A"?da.promise:db.promise):Promise.resolve(undefined));
  const ui=setup();ui.render();await tick();ui.render();ui.select("A");ui.select("B");da.resolve(detail(a));await tick();ui.render();expect(ui.draft()).toBeUndefined();
  db.resolve(detail(b));await tick();ui.render();expect(ui.draft()).toBe("exact B");ui.click("Discard selected draft…");expect(ui.text()).toContain("project · b.json · generation 7");ui.click("Confirm discard recovery");await tick();
  expect(invoke).toHaveBeenCalledWith("discard_recovery",{key:"B",generation:7});
});
test("close/reopen rejects pending inspection and reconciliation uses the displayed target",async()=>{
  const late=deferred<ReturnType<typeof detail>>();let calls=0;
  vi.mocked(invoke).mockImplementation(cmd=>cmd==="list_recovery"?Promise.resolve({records:[a,b],notices:[]}):++calls===1?late.promise:Promise.resolve(detail(b)));
  const ui=setup();ui.render();await tick();ui.render();ui.select("A");ui.click("Keep for later");ui.props.open=false;ui.render();ui.props.open=true;ui.render();await tick();ui.render();ui.select("B");await tick();ui.render();expect(ui.draft()).toBe("exact B");
  ui.click("Reconcile saved file");late.resolve(detail(a));await tick();ui.render();expect(ui.props.onRestore).toHaveBeenCalledWith(b,"saved-B.json",undefined);expect(ui.draft()).toBeUndefined();
});
test("obsolete list responses and retained handlers cannot revive selection after action",async()=>{
  const old=deferred<{records:RecoveryRow[];notices:string[]}>();let lists=0;
  vi.mocked(invoke).mockImplementation(cmd=>cmd==="list_recovery"?(++lists===1?old.promise:Promise.resolve({records:[b],notices:[]})):Promise.resolve(detail(b)));
  const ui=setup();ui.render();ui.click("Refresh recovery list");await tick();ui.render();old.resolve({records:[a],notices:[]});await tick();ui.render();ui.select("B");await tick();ui.render();ui.click("Recover selected draft");await tick();ui.render();expect(ui.props.onRestore).toHaveBeenCalledWith(b);expect(ui.draft()).toBeUndefined();
});
