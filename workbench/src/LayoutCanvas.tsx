import { useEffect, useRef, useState } from "react";
import {
  Application,
  Container,
  Graphics,
  Sprite,
  Text,
  Texture,
} from "pixi.js";
import "pixi.js/unsafe-eval";
import {
  fitCamera,
  screenToCell,
  zoomAt,
  TILE,
  type Camera,
} from "./coordinates";
import {
  lineCells,
  rectangle,
  type Cell,
  type Layout,
  type Layer,
  type Catalog,
} from "./layout";

export type Tool = "select" | "pencil" | "erase" | "rectangle" | "pan";
type Props = {
  model: Layout;
  catalog: Catalog;
  layer: Layer;
  visible: Record<Layer, boolean>;
  tool: Tool;
  disabled: boolean;
  selected: Cell | null;
  hovered?: Cell | null;
  authoredSubmap?: boolean;
  focusCell: Cell | null;
  problems: Cell[];
  onSelect: (cell: Cell) => void;
  onHover: (cell: Cell | null) => void;
  onPaint: (cells: Cell[]) => void;
  onGesture: (active: boolean) => void;
  onShortcut: (key: string) => void;
  onError: (error: unknown) => void;
};
export function LayoutCanvas(props: Props) {
  const element = useRef<HTMLDivElement>(null),
    latest = useRef(props);
  latest.current = props;
  const controls = useRef<{
    draw: () => void;
    fit: () => void;
    zoom: (factor: number) => void;
    focus: (cell: Cell) => void;
  } | null>(null);
  const [zoom, setZoom] = useState(100);
  useEffect(() => {
    const host = element.current!,
      app = new Application();
    let disposed = false,
      ready = false,
      cleanup = () => {};
    async function init() {
      await app.init({
        resizeTo: host,
        background: "#151d21",
        antialias: false,
        resolution: window.devicePixelRatio,
        autoDensity: true,
        preference: "webgl",
      });
      ready = true;
      if (disposed) {
        app.destroy(true, { children: true });
        return;
      }
      host.appendChild(app.canvas);
      app.canvas.tabIndex = 0;
      app.canvas.setAttribute("aria-label", latest.current.authoredSubmap ? "Authored submap canvas" : "Authored building canvas");
      const world = new Container(),
        terrain = new Container(),
        decor = new Graphics(),
        specials = new Graphics(),
        warnings = new Graphics(),
        selection = new Graphics();
      world.addChild(terrain, decor, specials, warnings, selection);
      app.stage.addChild(world);
      const tiles: { sprite: Sprite; text: Text }[] = [];
      let camera: Camera = fitCamera(
        host.clientWidth,
        host.clientHeight,
        latest.current.model.width,
        latest.current.model.height,
      );
      const apply = () => {
        if(disposed || !app.renderer || world.destroyed || !host.clientWidth || !host.clientHeight)return;
        world.position.set(camera.x, camera.y);
        world.scale.set(camera.scale);
        host.dataset.camera = JSON.stringify(camera);
        setZoom(Math.round(camera.scale * 100));
        app.render();
      };
      const mark = () => {
        if(disposed || selection.destroyed)return;
        selection.clear();
        const h = latest.current.hovered;
        if (h) selection.rect(h[0]*TILE,h[1]*TILE,TILE,TILE).stroke({width:1/camera.scale,color:0x8bd5ef});
        const c = latest.current.selected;
        if (c)
          selection
            .rect(c[0] * TILE, c[1] * TILE, TILE, TILE)
            .stroke({ width: 2 / camera.scale, color: 0xffe2a1 });
      };
      const draw = () => {
        if(disposed || !app.renderer || world.destroyed)return;
        const p = latest.current,
          m = p.model;
        host.dataset.shape = JSON.stringify([m.width, m.height]);
        let i = 0;
        for (let y = 0; y < m.height; y++)
          for (let x = 0; x < m.width; x++, i++) {
            if (!tiles[i]) {
              const sprite = new Sprite(Texture.WHITE),
                text = new Text({
                  text: "",
                  resolution: window.devicePixelRatio * 6,
                  style: {
                    fontFamily: "Consolas,monospace",
                    fontSize: 10,
                    fill: 0xe3e4d6,
                  },
                });
              terrain.addChild(sprite, text);
              tiles.push({ sprite, text });
            }
            const { sprite, text } = tiles[i],
              glyph = Array.from(m.layers[y])[x],
              id = m.legend[glyph];
            text.resolution = window.devicePixelRatio * 6;
            sprite.visible = text.visible = true;
            sprite.position.set(x * TILE, y * TILE);
            sprite.width = sprite.height = TILE - 0.5;
            sprite.tint =
              id === null
                ? 0x20292e
                : id.includes("door")
                  ? 0x80643f
                  : p.catalog.terrain[id]?.walkable
                    ? 0x44574e
                    : 0x29343d;
            text.text = glyph === " " ? "·" : glyph;
            text.position.set(x * TILE + 4, y * TILE + 1);
          }
        for (; i < tiles.length; i++)
          tiles[i].sprite.visible = tiles[i].text.visible = false;
        terrain.visible = p.visible.terrain;
        decor.visible = p.visible.decor;
        specials.visible = p.visible.specials;
        decor.clear();
        if (!p.authoredSubmap) m.decor_layer?.forEach((row, y) =>
          row.forEach((v, x) => {
            if (v !== null)
              decor.circle(x * TILE + 12, y * TILE + 12, 3).fill(0xc2ace6);
          }),
        );
        specials.clear();
        m.special_tiles?.forEach((s) => {
          if ((s.type ?? s.kind) === "creature") {
            specials.poly([s.x*TILE+8,s.y*TILE+1,s.x*TILE+15,s.y*TILE+8,s.x*TILE+8,s.y*TILE+15,s.x*TILE+1,s.y*TILE+8]).fill(0xed8996);
            return;
          }
          const container = (s.type ?? s.kind) === "container";
          specials
            .rect(s.x * TILE + 2, s.y * TILE + 2, 12, 12)
            .stroke({ width: 1.6, color: container ? 0xffc77f : 0x8bd5ef });
          if (!container)
            specials
              .moveTo(s.x * TILE + 3, s.y * TILE + 3)
              .lineTo(s.x * TILE + 13, s.y * TILE + 13)
              .stroke({ width: 1, color: 0x8bd5ef });
        });
        if (p.authoredSubmap && m.player_start) {
          const {x,y}=m.player_start;
          specials.circle(x*TILE+8,y*TILE+8,6).stroke({width:1.5,color:0xffffff});
        }
        warnings.clear();
        for (const [x, y] of p.problems) {
          warnings
            .poly([
              x * TILE + 8,
              y * TILE + 1,
              x * TILE + 15,
              y * TILE + 14,
              x * TILE + 1,
              y * TILE + 14,
            ])
            .stroke({ width: 1.5, color: 0xffa58c });
        }
        mark();
        apply();
      };
      const fit = () => {
        if(disposed || !app.renderer || !host.clientWidth || !host.clientHeight)return;
        camera = fitCamera(
          host.clientWidth,
          host.clientHeight,
          latest.current.model.width,
          latest.current.model.height,
        );
        apply();
      };
      controls.current = {
        draw,
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
        focus: ([x, y]) => {
          camera.x = host.clientWidth / 2 - (x + 0.5) * TILE * camera.scale;
          camera.y = host.clientHeight / 2 - (y + 0.5) * TILE * camera.scale;
          mark();
          apply();
        },
      };
      let active = false,
        panning = false,
        lastPoint: Cell = [0, 0],
        lastCell: Cell | null = null,
        first: Cell | null = null,
        gestureTool: Tool = "select";
      const point = (e: PointerEvent | WheelEvent): Cell => {
        const r = app.canvas.getBoundingClientRect();
        return [e.clientX - r.left, e.clientY - r.top];
      };
      const cell = (p: Cell) =>
        screenToCell(
          ...p,
          camera,
          latest.current.model.width,
          latest.current.model.height,
        );
      const end = () => {
        if (active) latest.current.onGesture(false);
        active = false;
        panning = false;
        first = lastCell = null;
      };
      const down = (e: PointerEvent) => {
        if(disposed)return;
        if (e.button !== 0 && e.button !== 1) return;
        app.canvas.focus();
        app.canvas.setPointerCapture(e.pointerId);
        lastPoint = point(e);
        const c = cell(lastPoint),
          p = latest.current;
        gestureTool = p.tool;
        panning = e.button === 1 || p.tool === "pan" || e.altKey;
        if (panning) return;
        if (!c) return;
        p.onSelect(c);
        lastCell = first = c;
        if (
          !p.disabled &&
          p.layer !== "specials" &&
          ["pencil", "erase", "rectangle"].includes(p.tool)
        ) {
          active = true;
          p.onGesture(true);
          if (p.tool !== "rectangle") p.onPaint([c]);
        }
      };
      const move = (e: PointerEvent) => {
        if(disposed)return;
        const pt = point(e),
          p = latest.current;
        if (panning) {
          camera.x += pt[0] - lastPoint[0];
          camera.y += pt[1] - lastPoint[1];
          apply();
        }
        lastPoint = pt;
        const c = cell(pt);
        p.onHover(c);
        if (active && p.disabled) {
          end();
          return;
        }
        if (
          active &&
          c &&
          lastCell &&
          gestureTool !== "rectangle" &&
          (c[0] !== lastCell[0] || c[1] !== lastCell[1])
        )
          p.onPaint(lineCells(lastCell, c));
        if (active && c) {
          lastCell = c;
          p.onSelect(c);
        }
      };
      const up = (e: PointerEvent) => {
        if(disposed)return;
        const c = cell(point(e));
        if (
          active &&
          !latest.current.disabled &&
          gestureTool === "rectangle" &&
          first &&
          c
        )
          latest.current.onPaint(rectangle(first, c));
        end();
      };
      const wheel = (e: WheelEvent) => {
        if(disposed)return;
        e.preventDefault();
        end();
        const pt = point(e);
        camera = zoomAt(camera, Math.exp(-e.deltaY * 0.0015), ...pt);
        apply();
      };
      const key = (e: KeyboardEvent) => {
        if(disposed)return;
        if (
          (e.ctrlKey || e.metaKey) &&
          ["z", "y"].includes(e.key.toLowerCase())
        ) {
          e.preventDefault();
          end();
          latest.current.onShortcut(
            e.key.toLowerCase() === "y" || e.shiftKey ? "redo" : "undo",
          );
          return;
        }
        if (e.ctrlKey || e.metaKey || e.altKey) return;
        if (e.key === "Home") {
          e.preventDefault();
          fit();
        } else if (["b", "v", "e", "r", "h"].includes(e.key.toLowerCase())) {
          end();
          latest.current.onShortcut(e.key.toLowerCase());
        }
      };
      app.canvas.addEventListener("pointerdown", down);
      app.canvas.addEventListener("pointermove", move);
      app.canvas.addEventListener("pointerup", up);
      app.canvas.addEventListener("pointercancel", end);
      app.canvas.addEventListener("lostpointercapture", end);
      app.canvas.addEventListener("blur", end);
      app.canvas.addEventListener("wheel", wheel, { passive: false });
      app.canvas.addEventListener("keydown", key);
      const observer = new ResizeObserver(() => {
        if(disposed || !app.renderer || !host.clientWidth || !host.clientHeight)return;
        app.renderer.resize(
          host.clientWidth,
          host.clientHeight,
          window.devicePixelRatio,
        );
        fit();
      });
      observer.observe(host);
      app.stop();
      draw();
      host.dataset.ready = "true";
      cleanup = () => {
        observer.disconnect();
        controls.current = null;
        app.canvas.removeEventListener("pointerdown",down);
        app.canvas.removeEventListener("pointermove",move);
        app.canvas.removeEventListener("pointerup",up);
        app.canvas.removeEventListener("pointercancel",end);
        app.canvas.removeEventListener("lostpointercapture",end);
        app.canvas.removeEventListener("blur",end);
        app.canvas.removeEventListener("wheel",wheel);
        app.canvas.removeEventListener("keydown",key);
      };
    }
    void init().catch((e) => {if(!disposed)latest.current.onError(e);});
    return () => {
      disposed = true;
      cleanup();
      if (ready && app.renderer) app.destroy(true, { children: true });
    };
  }, []);
  useEffect(() => {
    controls.current?.draw();
  }, [
    props.model,
    props.catalog,
    props.visible,
    props.problems,
    props.selected,
    props.hovered,
  ]);
  useEffect(() => {
    if (props.focusCell) controls.current?.focus(props.focusCell);
  }, [props.focusCell]);
  return (
    <div className="map-shell layout-map">
      <div className="map-tools">
        <span>
          AUTHORED SOURCE{" "}
          <b>
            {props.model.width} × {props.model.height}
          </b>
        </span>
        <div>
          <button
            aria-label="Layout zoom out"
            onClick={() => controls.current?.zoom(0.8)}
          >
            −
          </button>
          <span>{zoom}%</span>
          <button
            aria-label="Layout zoom in"
            onClick={() => controls.current?.zoom(1.25)}
          >
            +
          </button>
          <button onClick={() => controls.current?.fit()}>Fit layout</button>
        </div>
      </div>
      <div ref={element} className="map-canvas" data-testid="layout-map" />
      <div className="map-foot">
        <span>
          Glyph = terrain · ● decor · □ container · ◆ creature · × other record · ○ intended arrival · △ problem
        </span>
        <span>Alt/middle drag: pan · Wheel: zoom</span>
      </div>
    </div>
  );
}
