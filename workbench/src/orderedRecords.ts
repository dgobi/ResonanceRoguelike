import { findNodeAtLocation } from "jsonc-parser";
import { syntax } from "./draft";
import { valueEdit } from "./layout";

// Parse afresh for every accepted edit. Whole source slices travel with rows;
// unknown nested metadata and escaping never round-trip through a form model.
export function recordRow(text: string, field: string, action: "add" | "remove" | "up" | "down", index: number, row: Record<string,unknown> = {}) {
  const {tree, bom, diagnostics} = syntax(text);
  if (diagnostics.length || tree?.type !== "object") throw new Error("Repair JSON first.");
  const array = findNodeAtLocation(tree, [field]);
  if (!array && action === "add") return valueEdit(text, [field], [row]);
  if (array?.type !== "array") throw new Error("Repair the record array in Source first.");
  const children = array.children || [];
  if (children.some(n=>n.type!=="object")) throw new Error("Repair malformed records in Source first.");
  if (action === "add") {
    const offset = array.offset + array.length - 1 + bom;
    return text.slice(0, offset) + (children.length ? "," : "") + JSON.stringify(row) + text.slice(offset);
  }
  const node = children[index];
  if (!node) throw new Error("Record no longer exists.");
  let start = node.offset + bom, end = start + node.length;
  if (action === "remove") {
    if (index < children.length-1) end = children[index+1].offset + bom;
    else if (index > 0) start = children[index-1].offset + children[index-1].length + bom;
    return text.slice(0,start) + text.slice(end);
  }
  const other = children[index + (action === "up" ? -1 : 1)];
  if (!other) return text;
  const [a,b] = node.offset < other.offset ? [node,other] : [other,node];
  const aStart = a.offset+bom, bStart = b.offset+bom;
  return text.slice(0,aStart) + text.slice(bStart,bStart+b.length) + text.slice(aStart+a.length,bStart) + text.slice(aStart,aStart+a.length) + text.slice(bStart+b.length);
}
