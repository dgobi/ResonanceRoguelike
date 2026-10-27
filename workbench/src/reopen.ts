// Publication bytes/intent are independent of the editor's current state.
export type Candidate = { text: string; variant: boolean; variantId: string };
export function requireCovered(saved: Candidate, current: Candidate) {
  if (saved.text !== current.text || saved.variant !== current.variant || saved.variantId !== current.variantId)
    throw {code: "NEWER_DRAFT", message: "File saved, but this draft or target changed afterwards. Your newer work is retained.",
      remedy: "Keep this draft for recovery or copy Source before deliberately discarding/reloading. Retry cannot replace newer work."};
}
