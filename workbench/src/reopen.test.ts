import {expect, test} from "vitest";
import {requireCovered} from "./reopen";
test("reopen covers exact accepted text and target, including invalid text and metadata",()=>{
  const saved={text:'\ufeff{\r\n "unknown": "λ\\n',variant:true,variantId:"letter"};
  expect(()=>requireCovered(saved,{...saved})).not.toThrow();
  for(const current of [{...saved,text:saved.text+"sentinel"},{...saved,variant:false},{...saved,variantId:"newer"}])
    expect(()=>requireCovered(saved,current)).toThrow();
});
