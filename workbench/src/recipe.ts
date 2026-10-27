import { findNodeAtLocation } from "jsonc-parser";
import { syntax } from "./draft";
import { valueEdit } from "./layout";
import { itemModel } from "./item";
export { itemValue as recipeValue } from "./item";

export function recipeModel(text: string) {
  const result = itemModel(text);
  return {...result, reason: result.reason ? "Correct JSON in Source to resume recipe controls. Your draft is retained." : ""};
}
export function recipeRow(text: string, field: string, action: "add" | "remove" | "up" | "down", index: number, tag?: string, row: Record<string,unknown> = {tag, min_tier: 1, ...(field === "requires_ambient" ? {} : {quantity: 1})}) {
  const {tree, bom, diagnostics} = syntax(text);
  if (diagnostics.length || tree?.type !== "object") throw new Error("Repair recipe JSON first.");
  const array = findNodeAtLocation(tree, [field]);
  if (!array && action === "add") return valueEdit(text, [field], [row]);
  if (array?.type !== "array") throw new Error("Repair the requirement array in Source first.");
  const children = array.children || [];
  if (action === "add") {
    const offset = array.offset + array.length - 1 + bom;
    return text.slice(0, offset) + (children.length ? "," : "") + JSON.stringify(row) + text.slice(offset);
  }
  const node = children[index];
  if (!node) throw new Error("Requirement no longer exists.");
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
