import {expect,test,vi} from "vitest";
import {Checkpoints,type RecoveryStatus} from "./recovery";
test("only accepted generations schedule bounded ordered checkpoints",async()=>{
  vi.useFakeTimers();const status:RecoveryStatus[]=[];let writes=0,current=1;
  const q=new Checkpoints(async()=>{writes++;return {generation:current};},s=>status.push(s));
  q.accepted(1);await vi.advanceTimersByTimeAsync(400);q.accepted(2);current=2;
  await vi.advanceTimersByTimeAsync(100);expect(writes).toBe(1);expect(status.at(-1)).toEqual({state:"saved",generation:2});
  q.accepted(1);await q.flush();expect(writes).toBe(1);q.stop();vi.useRealTimers();
});
test("failed checkpoint retries and disposal cannot resurrect retired work",async()=>{
  let fail=true,writes=0;const states:RecoveryStatus[]=[];
  const q=new Checkpoints(async()=>{writes++;if(fail)throw new Error("locked");return {generation:3};},s=>states.push(s));
  q.accepted(3);await expect(q.flush()).rejects.toThrow("locked");expect(states.at(-1)?.state).toBe("error");
  fail=false;await q.flush();expect(states.at(-1)?.state).toBe("saved");q.stop();q.accepted(4);await q.flush();expect(writes).toBe(2);
});
test("concurrent flushes share one write and refuse an obsolete receipt",async()=>{
  let finish!:(v:{generation:number})=>void,writes=0;
  const q=new Checkpoints(()=>{writes++;return new Promise(r=>finish=r);},()=>{});
  q.accepted(1);const a=q.flush(),b=q.flush();finish({generation:1});await Promise.all([a,b]);expect(writes).toBe(1);
  q.accepted(2);const c=q.flush();finish({generation:1});await expect(c).rejects.toThrow(/newer/);q.stop();
});
