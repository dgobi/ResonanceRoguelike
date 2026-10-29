import { findNodeAtLocation } from "jsonc-parser";
import { syntax } from "./draft";
import type { Diagnostic } from "./protocol";

export type Cell = [number, number];
export type Layer = "terrain" | "decor" | "specials";
export type Catalog = {
  terrain: Record<string, { walkable: boolean; transparent: boolean }>;
  decor: Record<
    string,
    { name: string; description?:string; container: boolean; blocks_movement: boolean; path?:string; resolved?:boolean; supported?:boolean; reason?:string; properties?:{blocks_movement:boolean;declared_blocks_sight:boolean;light_emit:number;cosmetic_fx?:string|null;interaction?:string|null;stationary_fire:boolean;sight_note:string} }
  >;
  loot_pools: string[];
  creatures?: ReferenceChoice[];
  items?: ReferenceChoice[];
  texts?: ReferenceChoice[];
  pools?: ReferenceChoice[];
};
export type ReferenceChoice = {id:string;name:string;path:string;paths?:string[];resolved?:boolean;readable?:boolean};
export type Special = {
  x: number;
  y: number;
  type?: string;
  kind?: string;
  decor_id?: string;
  loot_pools?: string[];
  [key: string]: unknown;
};
export type Layout = {
  width: number;
  height: number;
  layers: string[];
  legend: Record<string, string | null>;
  decor_layer?: (string | null)[][];
  special_tiles?: Special[];
  legend_weights?: Record<string, unknown>;
  player_start?: { x: number; y: number };
  exit_direction?: string;
  exit_x?: number;
  exit_y?: number;
  placement?: {
    targets?: { x: number; y: number; kind: string }[];
    entrances?: { x: number; y: number }[];
  };
};

// This only determines whether visual controls can safely address native values.
// Python remains the schema, reference, placement and publication authority.
export function layoutModel(text: string): {
  model: Layout | null;
  reason: string;
} {
  if (syntax(text).diagnostics.length)
    return {
      model: null,
      reason: "Correct JSON in Source to resume the canvas.",
    };
  const r = JSON.parse(text.replace(/^\uFEFF/, ""));
  const rows: unknown = r?.layers;
  if (
    !Array.isArray(rows) ||
    !rows.length ||
    rows.some((v) => typeof v !== "string")
  )
    return {
      model: null,
      reason: "Canvas requires native layers: an array of terrain strings.",
    };
  const w = Array.from(rows[0] as string).length,
    h = rows.length;
  if (
    !w ||
    w > 80 ||
    h > 43 ||
    rows.some((v) => Array.from(v).length !== w) ||
    (r.width !== undefined && r.width !== w) ||
    (r.height !== undefined && r.height !== h)
  )
    return {
      model: null,
      reason:
        "Resolve dimensions/ragged rows in Source (maximum 80 × 43). Trailing spaces are significant.",
    };
  if (
    !r.legend ||
    Array.isArray(r.legend) ||
    typeof r.legend !== "object" ||
    Object.entries(r.legend).some(
      ([k, v]) =>
        Array.from(k).length !== 1 || (v !== null && typeof v !== "string"),
    ) ||
    rows.some((v) => Array.from(v as string).some((c) => !(c in r.legend)))
  )
    return {
      model: null,
      reason: "Resolve missing or unsupported legend entries in Source.",
    };
  // Current g2-3 accepts an array of rows, with only string/null cells. Preserve
  // historical array/object cells exactly and make them inspect-only.
  if (
    r.decor_layer !== undefined &&
    (!Array.isArray(r.decor_layer) ||
      r.decor_layer.length !== h ||
      r.decor_layer.some(
        (row: unknown) =>
          !Array.isArray(row) ||
          row.length !== w ||
          row.some((v) => v !== null && typeof v !== "string"),
      ))
  )
    return {
      model: null,
      reason:
        "Unsupported decor shape retained in Source. g2-3 requires nested rows of ID/null cells; no values were converted.",
    };
  if (
    r.special_tiles !== undefined &&
    (!Array.isArray(r.special_tiles) ||
      r.special_tiles.some(
        (s: Special) =>
          !s ||
          typeof s !== "object" ||
          !Number.isInteger(s.x) ||
          !Number.isInteger(s.y) ||
          s.x < 0 ||
          s.y < 0 ||
          s.x >= w ||
          s.y >= h,
      ))
  )
    return {
      model: null,
      reason:
        "Resolve special coordinates/record shapes in Source to resume visual editing.",
    };
  return { model: { ...r, width: w, height: h }, reason: "" };
}

export function appendValue(source:string,path:(string|number)[],value:unknown):string {
  const {tree,bom,diagnostics}=syntax(source);
  if(diagnostics.length || !tree)throw Error("Correct strict JSON before visual editing.");
  const node=findNodeAtLocation(tree,path);
  if(!node)return valueEdit(source,path,[value]);
  if(node.type!=="array")throw Error("Expected an ordered source array.");
  const last=node.children?.at(-1),offset=(last ? last.offset+last.length : node.offset+1)+bom;
  return source.slice(0,offset)+(last ? "," : "")+JSON.stringify(value)+source.slice(offset);
}
export function removeValue(source:string,path:(string|number)[]):string {
  const {tree,bom,diagnostics}=syntax(source);
  if(diagnostics.length || !tree)throw Error("Correct strict JSON before visual editing.");
  const parent=findNodeAtLocation(tree,path.slice(0,-1)),key=path.at(-1);
  if(!parent)throw Error("Missing source parent.");
  const nodes=parent.children || [],index=parent.type==="array" ? Number(key) : nodes.findIndex(n=>n.children?.[0].value===key);
  const node=nodes[index];if(!node)return source;
  let start=node.offset,end=start+node.length;
  if(index<nodes.length-1)end=nodes[index+1].offset;
  else if(index>0)start=nodes[index-1].offset+nodes[index-1].length;
  return source.slice(0,start+bom)+source.slice(end+bom);
}
export const recordKind=(s:Special)=>String(s.type??s.kind);
export const directEditable=(s:Special)=>["item","container","creature","decor"].includes(recordKind(s)) && !(s.type && s.kind && s.type!==s.kind);
export function addRecord(source:string,cell:Cell,kind:"item"|"container"|"creature"|"decor",id:string):string {
  const {model,reason}=layoutModel(source);if(!model)throw Error(reason);
  if(cell[0]<0||cell[1]<0||cell[0]>=model.width||cell[1]>=model.height)throw Error("Choose a source cell within the room.");
  return appendValue(source,["special_tiles"],{type:kind,x:cell[0],y:cell[1],...({item:{item_id:id},creature:{creature_id:id},container:{decor_id:id,loot_pools:[]},decor:{decor_id:id}}[kind])});
}
export function editDecor(source:string,index:number,update:{x:number;y:number;decor_id:string}):string {
  const {model,reason}=layoutModel(source);if(!model)throw Error(reason);
  const row=model.special_tiles?.[index];if(!row||recordKind(row)!=="decor"||!directEditable(row))throw Error("Select a direct decor record.");
  if(![update.x,update.y].every(Number.isInteger)||update.x<0||update.y<0||update.x>=model.width||update.y>=model.height)throw Error("Use integer source coordinates within the room.");
  for(const [key,value] of Object.entries(update))if(row[key]!==value)source=valueEdit(source,["special_tiles",index,key],value);
  return source;
}
export function editItem(source:string,index:number,update:{x:number;y:number;item_id:string;text_id?:string}):string {
  const {model,reason}=layoutModel(source);if(!model)throw Error(reason);
  const row=model.special_tiles?.[index];if(!row||recordKind(row)!=="item"||!directEditable(row))throw Error("Select a direct item record.");
  if(![update.x,update.y].every(Number.isInteger)||update.x<0||update.y<0||update.x>=model.width||update.y>=model.height)throw Error("Use integer source coordinates within the room.");
  for(const [key,value] of Object.entries(update))if(value!==undefined && row[key]!==value)source=valueEdit(source,["special_tiles",index,key],value);
  if(update.text_id===undefined && "text_id" in row)source=removeValue(source,["special_tiles",index,"text_id"]);
  return source;
}
export function deleteRecord(source:string,index:number):string {
  const {model,reason}=layoutModel(source);if(!model)throw Error(reason);
  if(!model.special_tiles?.[index]||!directEditable(model.special_tiles[index]))throw Error("Select a supported direct record.");
  return removeValue(source,["special_tiles",index]);
}
export function resizeRoom(source:string,width:number,height:number,fill:string):string {
  const {model,reason}=layoutModel(source);if(!model)throw Error(reason);
  if(![width,height].every(Number.isInteger)||width<1||height<1||width>80||height>43)throw Error("Resize within 1–80 × 1–43.");
  if(!(fill in model.legend)||Array.from(fill).length!==1)throw Error("Choose an existing fill glyph.");
  const raw=JSON.parse(source.replace(/^\uFEFF/,""));
  if(raw.decor_layer!==undefined)throw Error("Retained inactive decor_layer locks resizing; it will not be cropped or normalized.");
  function protectedCoordinates(value:unknown,path:string){
    if(!value||typeof value!=="object")return;
    if(Array.isArray(value)){value.forEach((v,i)=>protectedCoordinates(v,`${path}[${i}]`));return;}
    const r=value as Record<string,unknown>;
    if(Number.isInteger(r.x)&&Number.isInteger(r.y) && (Number(r.x)>=width||Number(r.y)>=height))throw Error(`Resize strands ${path} at (${r.x}, ${r.y}); resolve it first.`);
    Object.entries(r).forEach(([k,v])=>protectedCoordinates(v,`${path}.${k}`));
  }
  protectedCoordinates(raw,"room");
  if((raw.exit_x!==undefined&&raw.exit_x>=width)||(raw.exit_y!==undefined&&raw.exit_y>=height))throw Error("Resize strands retained exit coordinates; resolve them first.");
  for(let y=0;y<Math.min(height,model.height);y++){
    const row=Array.from(model.layers[y]),next=row.slice(0,width).join("")+fill.repeat(Math.max(0,width-row.length));
    if(next!==model.layers[y])source=stringCharacters(source,["layers",y],next);
  }
  for(let y=model.height-1;y>=height;y--)source=removeValue(source,["layers",y]);
  for(let y=model.height;y<height;y++)source=appendValue(source,["layers"],fill.repeat(width));
  if("width" in raw)source=valueEdit(source,["width"],width);
  if("height" in raw)source=valueEdit(source,["height"],height);
  return source;
}

export function valueEdit(
  source: string,
  path: (string | number)[],
  value: unknown,
): string {
  const { tree, diagnostics, bom } = syntax(source);
  if (diagnostics.length || !tree)
    throw new Error("Correct strict JSON before visual editing.");
  const node = findNodeAtLocation(tree, path),
    text = JSON.stringify(value);
  if (node)
    return (
      source.slice(0, node.offset + bom) +
      text +
      source.slice(node.offset + bom + node.length)
    );
  const parent = findNodeAtLocation(tree, path.slice(0, -1));
  if (parent?.type !== "object" || typeof path.at(-1) !== "string")
    throw new Error("Unsupported missing value; edit Source explicitly.");
  const offset = parent.offset + parent.length - 1 + bom;
  return (
    source.slice(0, offset) +
    `${parent.children?.length ? "," : ""}${JSON.stringify(path.at(-1))}:${text}` +
    source.slice(offset)
  );
}

// A row is a JSON string, whose source spans need not match character offsets.
// Keep untouched escape spellings (including surrogate pairs) when painting or
// resizing another cell in that row. The compiler indexes Unicode characters.
export function stringCharacters(source:string,path:(string|number)[],value:string):string {
  const {tree,bom,diagnostics}=syntax(source),node=tree&&findNodeAtLocation(tree,path);
  if(diagnostics.length||node?.type!=="string")throw Error("Expected a strict JSON string row.");
  const start=node.offset+bom+1,end=node.offset+bom+node.length-1,body=source.slice(start,end),tokens:{raw:string;value:string}[]=[];
  for(let i=0;i<body.length;){
    const a=i;
    if(body[i]==="\\"){
      if(body[i+1]==="u"){
        const code=parseInt(body.slice(i+2,i+6),16);i+=6;
        if(code>=0xd800&&code<=0xdbff&&body.slice(i,i+2)==="\\u"){
          const low=parseInt(body.slice(i+2,i+6),16);if(low>=0xdc00&&low<=0xdfff)i+=6;
        }
      }else i+=2;
    }else i+=String.fromCodePoint(body.codePointAt(i)!).length;
    const raw=body.slice(a,i);tokens.push({raw,value:JSON.parse('"'+raw+'"') as string});
  }
  const next=Array.from(value).map((char,i)=>tokens[i]?.value===char?tokens[i].raw:JSON.stringify(char).slice(1,-1)).join("");
  return source.slice(0,start)+next+source.slice(end);
}

export function paint(
  source: string,
  cells: Cell[],
  layer: "terrain" | "decor",
  value: string | null,
): string {
  const { model, reason } = layoutModel(source);
  if (!model) throw new Error(reason);
  const unique = [...new Map(cells.map((c) => [c.join(","), c])).values()];
  for (const [x, y] of unique)
    if (
      !Number.isInteger(x) ||
      !Number.isInteger(y) ||
      x < 0 ||
      y < 0 ||
      x >= model.width ||
      y >= model.height
    )
      throw new Error("Cell outside source footprint.");
  if (layer === "terrain") {
    if (value === null || !(value in model.legend))
      throw new Error("Choose an existing legend glyph.");
    const rows = new Map<number, string[]>();
    for (const [x, y] of unique) {
      if (!rows.has(y)) rows.set(y, Array.from(model.layers[y]));
      rows.get(y)![x] = value;
    }
    for (const [y, row] of rows)
      if (row.join("") !== model.layers[y])
        source = stringCharacters(source, ["layers", y], row.join(""));
  } else {
    if (!model.decor_layer) {
      if (value === null || !unique.length) return source;
      source = valueEdit(
        source,
        ["decor_layer"],
        Array.from({ length: model.height }, () =>
          Array(model.width).fill(null),
        ),
      );
    }
    for (const [x, y] of unique)
      if (model.decor_layer?.[y][x] !== value)
        source = valueEdit(source, ["decor_layer", y, x], value);
  }
  return source;
}

export function containerEditable(s: Special): boolean {
  return (
    (s.type ?? s.kind) === "container" &&
    !(s.type && s.kind && s.type !== s.kind) &&
    (s.decor_id === undefined || typeof s.decor_id === "string") &&
    (s.loot_pools === undefined ||
      (Array.isArray(s.loot_pools) &&
        s.loot_pools.every((v) => typeof v === "string")))
  );
}

export function creatureEditable(s: Special): boolean {
  return (s.type ?? s.kind) === "creature" && !(s.type && s.kind && s.type !== s.kind);
}
export function editCreature(source: string, index: number, update: {x: number; y: number; creature_id: string}): string {
  const {model, reason} = layoutModel(source);
  if (!model) throw new Error(reason);
  const record = model.special_tiles?.[index];
  if (!record || !creatureEditable(record)) throw new Error("Select a direct creature record.");
  if (![update.x, update.y].every(Number.isInteger) || update.x < 0 || update.y < 0 || update.x >= model.width || update.y >= model.height)
    throw new Error("Use integer source coordinates inside the grid.");
  for (const [key, value] of Object.entries(update))
    if (record[key] !== value) source = valueEdit(source, ["special_tiles", index, key], value);
  return source;
}
export function addCreature(source: string, cell: Cell, creatureId: string): string {
  const {model, reason} = layoutModel(source);
  if (!model) throw new Error(reason);
  const record = {type:"creature", x:cell[0], y:cell[1], creature_id:creatureId};
  if (!model.special_tiles) return valueEdit(source, ["special_tiles"], [record]);
  const {tree, bom} = syntax(source), node = findNodeAtLocation(tree!, ["special_tiles"])!;
  const last = node.children?.at(-1);
  const offset = (last ? last.offset + last.length : node.offset + 1) + bom;
  return source.slice(0,offset) + (node.children?.length ? "," : "") + JSON.stringify(record) + source.slice(offset);
}
export function removeCreature(source: string, index: number): string {
  const {model, reason} = layoutModel(source);
  if (!model) throw new Error(reason);
  if (!model.special_tiles?.[index] || !creatureEditable(model.special_tiles[index])) throw new Error("Select a direct creature record.");
  const {tree, bom} = syntax(source), nodes = findNodeAtLocation(tree!, ["special_tiles"])!.children!, node = nodes[index];
  let start = node.offset, end = start + node.length;
  if (index < nodes.length-1) end = nodes[index+1].offset;
  else if (index > 0) start = nodes[index-1].offset + nodes[index-1].length;
  return source.slice(0,start+bom) + source.slice(end+bom);
}
export function editContainer(
  source: string,
  index: number,
  update: { x: number; y: number; decor_id: string; loot_pools: string[] },
  followTargets: boolean,
): string {
  const { model, reason } = layoutModel(source);
  if (!model) throw new Error(reason);
  const record = model.special_tiles?.[index];
  if (!record || !containerEditable(record))
    throw new Error("Only direct container records are visually editable.");
  if (
    ![update.x, update.y].every(Number.isInteger) ||
    update.x < 0 ||
    update.y < 0 ||
    update.x >= model.width ||
    update.y >= model.height
  )
    throw new Error("Container coordinates must be inside the footprint.");
  for (const [key, value] of Object.entries(update))
    if (JSON.stringify(record[key]) !== JSON.stringify(value))
      source = valueEdit(source, ["special_tiles", index, key], value);
  if (followTargets && (record.x !== update.x || record.y !== update.y)) {
    model.placement?.targets?.forEach((t, i) => {
      if (t.kind === "container" && t.x === record.x && t.y === record.y) {
        source = valueEdit(source, ["placement", "targets", i, "x"], update.x);
        source = valueEdit(source, ["placement", "targets", i, "y"], update.y);
      }
    });
  }
  return source;
}

export function lineCells(a: Cell, b: Cell): Cell[] {
  let [x, y] = a;
  const [ex, ey] = b,
    dx = Math.abs(ex - x),
    dy = -Math.abs(ey - y),
    sx = x < ex ? 1 : -1,
    sy = y < ey ? 1 : -1;
  let err = dx + dy;
  const out: Cell[] = [];
  for (;;) {
    out.push([x, y]);
    if (x === ex && y === ey) break;
    const e = 2 * err;
    if (e >= dy) {
      err += dy;
      x += sx;
    }
    if (e <= dx) {
      err += dx;
      y += sy;
    }
  }
  return out;
}
export function rectangle(a: Cell, b: Cell): Cell[] {
  const out: Cell[] = [];
  for (let y = Math.min(a[1], b[1]); y <= Math.max(a[1], b[1]); y++)
    for (let x = Math.min(a[0], b[0]); x <= Math.max(a[0], b[0]); x++)
      out.push([x, y]);
  return out;
}

export class CanvasHistory {
  undoStack: { before: string; after: string; label: string }[] = [];
  redoStack: typeof this.undoStack = [];
  clear() {
    this.undoStack = [];
    this.redoStack = [];
  }
  record(before: string, after: string, label: string) {
    if (before !== after) {
      this.undoStack.push({ before, after, label });
      if (this.undoStack.length > 100) this.undoStack.shift();
      this.redoStack = [];
    }
  }
  undo(current: string) {
    const e = this.undoStack.at(-1);
    if (!e || e.after !== current) {
      this.clear();
      return current;
    }
    this.undoStack.pop();
    this.redoStack.push(e);
    return e.before;
  }
  redo(current: string) {
    const e = this.redoStack.at(-1);
    if (!e || e.before !== current) {
      this.clear();
      return current;
    }
    this.redoStack.pop();
    this.undoStack.push(e);
    return e.after;
  }
}
export function diagnosticCell(
  d: Diagnostic,
  model: Layout | null,
): { cell: Cell; layer: Layer } | null {
  if (!model) return null;
  if (d.source_xy) return { cell: d.source_xy, layer: d.layer || "terrain" };
  const special = d.field.match(/^special_tiles\[(\d+)\]/);
  if (special) {
    const s = model.special_tiles?.[Number(special[1])];
    if (s) return { cell: [s.x, s.y], layer: "specials" };
  }
  const decor = d.field.match(/^decor_layer\[(\d+)\]\[(\d+)\]/);
  if (decor)
    return { cell: [Number(decor[2]), Number(decor[1])], layer: "decor" };
  return null;
}
