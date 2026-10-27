export type RequestLease = { current: () => boolean; finish: () => void };

// The App and parked editors share the same generation. An old finally handler
// can finish its own request only, including after cancellation and navigation.
export function requestLease(epoch: { current: number }, finish: () => void): RequestLease {
  const token = ++epoch.current;
  const current = () => token === epoch.current;
  return { current, finish: () => { if (current()) finish(); } };
}
