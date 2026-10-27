import { expect, test } from "vitest";
import { installDocument, WorkspaceMonitor, type Documents, type Sweep, type DiskRow } from "./workspace";
import type { Inspection } from "./protocol";
const doc=(token:string,path=token)=>({document_token:token,file_identity:path,path,raw:`invalid ${token}`} as Inspection);
const sweep=(...tokens:string[]):Sweep=>({documents:tokens.map(token=>({token})),dependency_scans:1,elapsed_ms:1,project_epoch:1});
const deferred=<T,>()=>{let resolve!:(t:T)=>void;const promise=new Promise<T>(r=>resolve=r);return {resolve,promise};};

test("six instances coexist; repeated open and targeted verified replacement retain unrelated entries",()=>{
  let documents:Documents={};
  for(const key of ["item1","item2","recipe1","recipe2","text1","text2"])documents=installDocument(documents,doc(key),key);
  documents.item2.dirty=true;
  const parked=documents.item2;
  expect(installDocument(documents,{...doc("item2"),raw:"disk"},"item2")).toBe(documents);
  const next=installDocument(documents,doc("saved","variant-path"),"variant","recipe1");
  expect(Object.keys(next)).toHaveLength(6);expect(next.recipe1).toBeUndefined();expect(next.item2).toBe(parked);
  expect(next.item2.document.raw).toBe("invalid item2");expect(next.item2.dirty).toBe(true);
});
test("reopen collision and closed origin cannot overwrite another owner",()=>{
  const one=installDocument({},doc("one","source"),"same-id");
  const two=installDocument(one,doc("two","other"),"same-id");
  expect(()=>installDocument(two,doc("three","other"),"same-id","one")).toThrow(/already/);
  expect(()=>installDocument(two,doc("three","third"),"same-id","closed")).toThrow(/no longer/);
  expect(two.one).toBe(one.one);
});
test("in-place verified reopen only replaces its own token regardless of selection",()=>{
  const first=installDocument({},doc("old","same-file"),"first");
  const current=installDocument(first,doc("selected","other-file"),"other");
  const next=installDocument(current,doc("fresh","same-file"),"first","old");
  expect(next.old).toBeUndefined();expect(next.fresh.document.file_identity).toBe("same-file");
  expect(next.selected).toBe(current.selected);
});
test("one shared sweep has no overlapping calls or queued scans with six mounted editors",async()=>{
  const monitor=new WorkspaceMonitor(),pending=deferred<Sweep>();let scans=0,deliveries=0;
  for(let i=0;i<6;i++)monitor.subscribe(String(i),()=>()=>deliveries++);
  const run=()=>monitor.check(()=>{scans++;return pending.promise;},()=>true);
  const first=run();await Promise.all([run(),run(),run()]);expect(scans).toBe(1);
  pending.resolve(sweep("0","1","2","3","4","5"));await first;
  expect(deliveries).toBe(6);expect(scans).toBe(1);
});
test("late sweep cannot restore a closed/replaced subscriber or cross a project reset",async()=>{
  for(const reset of [false,true]) {
    const monitor=new WorkspaceMonitor(),pending=deferred<Sweep>();let old=0,newer=0;
    const remove=monitor.subscribe("old",()=>()=>old++);
    const run=monitor.check(()=>pending.promise,()=>true);
    if(reset)monitor.reset();else{remove();monitor.subscribe("new",()=>()=>newer++);}
    pending.resolve(sweep("old","new"));await run;
    expect([old,newer]).toEqual([0,0]);
  }
});
test("sweep delivery uses captured revision, not tab selection or a later validation",async()=>{
  const monitor=new WorkspaceMonitor(),pending=deferred<Sweep>();let version=0;const rows:DiskRow[]=[];
  monitor.subscribe("recipe2",()=>{const captured=version;return row=>{if(captured===version)rows.push(row);};});
  const first=monitor.check(()=>pending.promise,()=>true);version++;
  pending.resolve(sweep("recipe2"));await first;expect(rows).toEqual([]);
  await monitor.check(async()=>sweep("recipe2"),()=>true);expect(rows.map(r=>r.token)).toEqual(["recipe2"]);
});
test("busy or rejected sweep never queues and releases only its own running flag",async()=>{
  const monitor=new WorkspaceMonitor();monitor.subscribe("one",()=>()=>{});let scans=0;
  await monitor.check(async()=>{scans++;return sweep("one");},()=>false);expect(scans).toBe(0);
  await expect(monitor.check(async()=>{throw new Error("BUSY");},()=>true)).rejects.toThrow("BUSY");
  await monitor.check(async()=>{scans++;return sweep("one");},()=>true);expect(scans).toBe(1);
});
