import {expect, test} from "vitest";
import {requireCovered,reconcileRead} from "./reopen";
test("reopen covers exact accepted text and target, including invalid text and metadata",()=>{
  const saved={text:'\ufeff{\r\n "unknown": "λ\\n',variant:true,variantId:"letter"};
  expect(()=>requireCovered(saved,{...saved})).not.toThrow();
  for(const current of [{...saved,text:saved.text+"sentinel"},{...saved,variant:false},{...saved,variantId:"newer"}])
    expect(()=>requireCovered(saved,current)).toThrow();
});
test("delayed read and final acknowledgement never install over newer work",async()=>{
  for(const boundary of ["read","ack"]){
    const saved={text:"published",variant:true,variantId:"one"};let current={...saved},installed=false;
    let release!:()=>void;const held=new Promise<void>(r=>release=r);
    const result=reconcileRead(()=>requireCovered(saved,current),async()=>{if(boundary==="read")await held;return "verified owner";},async()=>{if(boundary==="ack")await held;},()=>installed=true);
    await Promise.resolve();current={...current,text:"accepted newer work"};release();
    await expect(result).rejects.toMatchObject({code:"NEWER_DRAFT"});expect(installed).toBe(false);expect(current.text).toBe("accepted newer work");
  }
});
test("lost response installs nothing; retry reads the established owner without publication",async()=>{
  let reads=0,installs=0;
  const read=async()=>{reads++;if(reads===1)throw Error("lost successful response");return "same host owner";};
  await expect(reconcileRead(()=>{},read,async()=>{},()=>installs++)).rejects.toThrow(/lost/);
  expect(installs).toBe(0);expect(await reconcileRead(()=>{},read,async()=>{},()=>installs++)).toBe("same host owner");expect(installs).toBe(1);
});
