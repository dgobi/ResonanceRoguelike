import { useEffect, useRef, useState } from "react";
import { Application, Container, Graphics, Sprite, Texture } from "pixi.js";
// Pixi's official static shader/uniform implementations for a strict CSP.
// Despite the module name, this removes the need to permit unsafe-eval.
import "pixi.js/unsafe-eval";
import type { Preview } from "./protocol";
import {
  type Camera,
  fitCamera,
  screenToCell,
  TILE,
  zoomAt,
} from "./coordinates";

const colors: Record<string, number> = {
  wall: 0x252d32,
  old_wall: 0x687274,
  floor: 0x424c47,
  worn_stone: 0x77715c,
  flagstone: 0x5d6863,
  door_closed: 0xc79855,
  door_open: 0x89ae98,
  stairs_up: 0xe9ddbc,
  stairs_down: 0xcabc9a,
  stele: 0x9c9bb3,
};
export function MapView({
  preview,
  onCell,
  onError,
}: {
  preview: Pick<Preview,"terrain"|"width"|"height"|"legend"|"decor"|"items"|"containers"|"actors"> & {spawn?:[number,number]};
  onCell: (cell: [number, number] | null) => void;
  onError: (error: unknown) => void;
}) {
  const element = useRef<HTMLDivElement>(null),
    controls = useRef<{
      fit: () => void;
      zoom: (factor: number) => void;
    } | null>(null);
  const callbacks = useRef({ onCell, onError });
  callbacks.current = { onCell, onError };
  const [zoom, setZoom] = useState(100);
  useEffect(() => {
    const host = element.current!;
    let disposed = false,
      initialized = false;
    const app = new Application();
    let cleanup = () => {};
    async function init() {
      await app.init({
        resizeTo: host,
        background: "#171e22",
        antialias: false,
        resolution: window.devicePixelRatio,
        autoDensity: true,
        preference: "webgl",
      });
      initialized = true;
      if (disposed) {
        app.destroy(true, { children: true });
        return;
      }
      host.appendChild(app.canvas);
      app.canvas.setAttribute(
        "aria-label",
        "Generated map. Drag to pan, scroll to zoom. Arrow keys pan; Home fits.",
      );
      app.canvas.tabIndex = 0;
      const world = new Container();
      app.stage.addChild(world);
      for (let y = 0; y < 43; y++)
        for (let x = 0; x < 80; x++) {
          const id = preview.terrain[y][x],
            sprite = new Sprite(Texture.WHITE);
          sprite.position.set(x * TILE, y * TILE);
          sprite.width = TILE - 0.6;
          sprite.height = TILE - 0.6;
          sprite.tint =
            colors[id] ??
            (id.includes("water")
              ? 0x426c83
              : preview.legend[id].walkable
                ? 0x536957
                : 0x5f646c);
          world.addChild(sprite);
        }
      const markers = new Graphics();
      for (const row of preview.decor)
        markers.rect(row.x * TILE + 5, row.y * TILE + 5, 6, 6).fill(0xc1b2d9);
      for (const row of preview.items)
        markers.circle(row.x * TILE + 8, row.y * TILE + 8, 2.5).fill(0xe9d39a);
      for (const row of preview.containers)
        markers
          .rect(row.x * TILE + 3, row.y * TILE + 3, 10, 10)
          .stroke({ width: 2, color: 0xe0ac6e });
      for (const row of preview.actors)
        markers.circle(row.x * TILE + 8, row.y * TILE + 8, 5).fill(0xe28b83);
      if (preview.spawn)
        markers
          .circle(preview.spawn[0] * TILE + 8, preview.spawn[1] * TILE + 8, 6)
          .stroke({ width: 2, color: 0xdef4e3 });
      world.addChild(markers);
      const selection = new Graphics();
      world.addChild(selection);
      let camera: Camera = fitCamera(host.clientWidth, host.clientHeight);
      function apply() {
        if(disposed || !app.renderer || world.destroyed || !host.clientWidth || !host.clientHeight)return;
        world.position.set(camera.x, camera.y);
        world.scale.set(camera.scale);
        setZoom(Math.round(camera.scale * 100));
        host.dataset.camera = JSON.stringify(camera);
        app.render();
      }
      function fit() {
        if(disposed || !app.renderer || !host.clientWidth || !host.clientHeight)return;
        camera = fitCamera(host.clientWidth, host.clientHeight);
        apply();
      }
      controls.current = {
        fit,
        zoom: (factor) => {
          camera = zoomAt(
            camera,
            factor,
            host.clientWidth / 2,
            host.clientHeight / 2,
          );
          apply();
        },
      };
      let dragging = false,
        last = [0, 0];
      function point(e: PointerEvent | WheelEvent) {
        const r = host.getBoundingClientRect();
        return [e.clientX - r.left, e.clientY - r.top];
      }
      function inspect(px: number, py: number) {
        if(disposed || selection.destroyed || !app.renderer)return;
        const cell = screenToCell(px, py, camera);
        callbacks.current.onCell(cell);
        selection.clear();
        if (cell)
          selection
            .rect(cell[0] * TILE, cell[1] * TILE, TILE, TILE)
            .stroke({ width: 1.5 / camera.scale, color: 0xf4e9cb });
        app.render();
      }
      const down = (e: PointerEvent) => {
        if(disposed || !app.renderer)return;
        if (e.button !== 0) return;
        dragging = true;
        last = point(e);
        app.canvas.setPointerCapture(e.pointerId);
        app.canvas.focus();
        inspect(...(last as [number, number]));
      };
      const move = (e: PointerEvent) => {
        const p = point(e);
        if (dragging) {
          camera.x += p[0] - last[0];
          camera.y += p[1] - last[1];
          apply();
        }
        last = p;
        inspect(...(p as [number, number]));
      };
      const up = () => {
        dragging = false;
      };
      const wheel = (e: WheelEvent) => {
        e.preventDefault();
        const p = point(e);
        camera = zoomAt(camera, Math.exp(-e.deltaY * 0.0015), p[0], p[1]);
        apply();
        inspect(...(p as [number, number]));
      };
      const key = (e: KeyboardEvent) => {
        const delta: Record<string, [number, number]> = {
          ArrowLeft: [32, 0],
          ArrowRight: [-32, 0],
          ArrowUp: [0, 32],
          ArrowDown: [0, -32],
        };
        if (e.key === "Home") {
          e.preventDefault();
          fit();
        } else if (delta[e.key]) {
          e.preventDefault();
          camera.x += delta[e.key][0];
          camera.y += delta[e.key][1];
          apply();
        }
      };
      app.canvas.addEventListener("pointerdown", down);
      app.canvas.addEventListener("pointermove", move);
      app.canvas.addEventListener("pointerup", up);
      app.canvas.addEventListener("pointercancel", up);
      app.canvas.addEventListener("wheel", wheel, { passive: false });
      app.canvas.addEventListener("keydown", key);
      const resize = new ResizeObserver(() => {
        if(disposed || !app.renderer || !host.clientWidth || !host.clientHeight)return;
        app.renderer.resize(host.clientWidth, host.clientHeight);
        fit();
      });
      resize.observe(host);
      app.stop();
      apply();
      host.dataset.ready = "true";
      cleanup = () => {
        resize.disconnect();
        controls.current = null;
        app.canvas.removeEventListener("pointerdown", down);
        app.canvas.removeEventListener("pointermove", move);
        app.canvas.removeEventListener("pointerup", up);
        app.canvas.removeEventListener("pointercancel", up);
        app.canvas.removeEventListener("wheel", wheel);
        app.canvas.removeEventListener("keydown", key);
      };
    }
    init().catch((e) => {if (!disposed) callbacks.current.onError(e);});
    return () => {
      disposed = true;
      cleanup();
      if (initialized && app.renderer) app.destroy(true, { children: true });
    };
  }, [preview]);
  return (
    <div className="map-shell">
      <div className="map-tools">
        <span>
          REVEALED LOCAL MAP <b>80 × 43</b>
        </span>
        <div>
          <button
            onClick={() => controls.current?.zoom(0.8)}
            aria-label="Zoom out"
          >
            −
          </button>
          <span className="zoom">{zoom}%</span>
          <button
            onClick={() => controls.current?.zoom(1.25)}
            aria-label="Zoom in"
          >
            +
          </button>
          <button onClick={() => controls.current?.fit()}>Fit map</button>
        </div>
      </div>
      <div className="map-canvas" ref={element} data-testid="map" />
      <div className="map-foot">
        <span>Origin (0, 0) · x → · y ↓</span>
        <span>Drag to pan · Scroll to zoom · Home to fit</span>
      </div>
    </div>
  );
}
