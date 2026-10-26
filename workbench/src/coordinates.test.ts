import { describe, expect, it } from "vitest";
import { fitCamera, screenToCell, zoomAt, TILE } from "./coordinates";
describe("80 × 43 rectangular coordinate contract", () => {
  it("maps known production arrival and all edges without swapping axes", () => {
    const c = fitCamera(1400, 800);
    for (const [x, y] of [
      [0, 0],
      [79, 42],
      [15, 20],
      [66, 16],
      [1, 42],
    ]) {
      expect(
        screenToCell(
          c.x + (x + 0.5) * TILE * c.scale,
          c.y + (y + 0.5) * TILE * c.scale,
          c,
        ),
      ).toEqual([x, y]);
    }
    expect(screenToCell(c.x - 0.01, c.y, c)).toBeNull();
    expect(screenToCell(c.x + 80 * TILE * c.scale, c.y, c)).toBeNull();
    expect(screenToCell(c.x, c.y + 43 * TILE * c.scale, c)).toBeNull();
  });
  it("keeps the cursor cell fixed during zoom and supports pan", () => {
    const c = { x: -143, y: 22, scale: 1.8 },
      x = 730,
      y = 408;
    expect(screenToCell(x, y, zoomAt(c, 1.7, x, y))).toEqual(
      screenToCell(x, y, c),
    );
    expect(
      screenToCell(x + 30, y - 20, { ...c, x: c.x + 30, y: c.y - 20 }),
    ).toEqual(screenToCell(x, y, c));
  });
});
