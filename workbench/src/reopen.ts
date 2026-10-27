// Publication bytes/intent are independent of the editor's current state.
export type Candidate = { text: string; variant: boolean; variantId: string };
export function requireCovered(saved: Candidate, current: Candidate) {
  if (saved.text !== current.text || saved.variant !== current.variant || saved.variantId !== current.variantId)
    throw {code: "NEWER_DRAFT", message: "File saved, but this draft or target changed afterwards. Your newer work is retained.",
      remedy: "Keep this draft for recovery or copy Source before deliberately discarding/reloading. Retry cannot replace newer work."};
}
// Keep the guard live through the last asynchronous acknowledgement. Tab
// replacement is synchronous only after all three coverage checks succeed.
export async function reconcileRead<T>(covered:()=>void,read:()=>Promise<T>,acknowledge:(value:T)=>Promise<void>,install:(value:T)=>void):Promise<T>{
  covered();const value=await read();covered();await acknowledge(value);covered();install(value);return value;
}
