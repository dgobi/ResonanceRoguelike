import { expect, test } from "vitest";
import { requestLease } from "./requests";

test("a cancelled completion cannot clear a newer parked editor request", () => {
  const epoch = { current: 0 };
  let busy = "old";
  const old = requestLease(epoch, () => { busy = ""; });
  ++epoch.current; // accepted cancellation
  const next = requestLease(epoch, () => { busy = ""; });
  busy = "new";
  old.finish();
  expect(old.current()).toBe(false);
  expect(busy).toBe("new");
  next.finish();
  expect(busy).toBe("");
});

test("refused cancellation leaves the current publication owner intact", () => {
  const epoch = { current: 0 };
  let completed = false;
  const publication = requestLease(epoch, () => { completed = true; });
  // A BUSY response does not advance the App epoch.
  expect(publication.current()).toBe(true);
  publication.finish();
  expect(completed).toBe(true);
});
