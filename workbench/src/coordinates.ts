export const COLS = 80,
  ROWS = 43,
  TILE = 16;
export type Camera = { x: number; y: number; scale: number };
export function fitCamera(
  width: number,
  height: number,
  cols = COLS,
  rows = ROWS,
): Camera {
  const scale = Math.max(
    0.1,
    Math.min((width - 48) / (cols * TILE), (height - 48) / (rows * TILE)),
  );
  return {
    x: (width - cols * TILE * scale) / 2,
    y: (height - rows * TILE * scale) / 2,
    scale,
  };
}
export function screenToCell(
  px: number,
  py: number,
  camera: Camera,
  cols = COLS,
  rows = ROWS,
): [number, number] | null {
  // Compare screen bounds before division: floating point rounding at the
  // bottom edge must not turn row 43 into the last visible row.
  if (
    px < camera.x ||
    py < camera.y ||
    px >= camera.x + cols * TILE * camera.scale ||
    py >= camera.y + rows * TILE * camera.scale
  )
    return null;
  const x = Math.floor((px - camera.x) / (TILE * camera.scale)),
    y = Math.floor((py - camera.y) / (TILE * camera.scale));
  return x >= 0 && y >= 0 && x < cols && y < rows ? [x, y] : null;
}
export function zoomAt(
  camera: Camera,
  factor: number,
  x: number,
  y: number,
): Camera {
  const scale = Math.max(0.2, Math.min(6, camera.scale * factor)),
    ratio = scale / camera.scale;
  return {
    x: x - (x - camera.x) * ratio,
    y: y - (y - camera.y) * ratio,
    scale,
  };
}
