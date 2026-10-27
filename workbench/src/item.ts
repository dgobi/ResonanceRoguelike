import { findNodeAtLocation } from "jsonc-parser";
import { syntax } from "./draft";
import { valueEdit } from "./layout";

export function itemModel(text: string): { model: Record<string, unknown> | null; reason: string } {
  if (syntax(text).diagnostics.length) return {model: null, reason: "Correct JSON in Source to resume item properties. Your draft is retained."};
  const model = JSON.parse(text.replace(/^\uFEFF/, ""));
  if (!model || typeof model !== "object" || Array.isArray(model)) return {model: null, reason: "Typed item editing requires one definition object. Source is preserved."};
  return {model, reason: ""};
}
export function itemValue(text: string, path: (string | number)[], value: unknown) {
  const parsed = itemModel(text);
  if (!parsed.model) throw new Error(parsed.reason);
  const {tree} = syntax(text), node = findNodeAtLocation(tree!, path);
  if (node && ["string", "number", "boolean", "null"].includes(node.type) && node.value === value) return text;
  return valueEdit(text, path, value);
}
export function keywordEntry(text: string, index: number, tag?: string, row: Record<string,unknown> = {tag, tier: 1}) {
  const parsed = itemModel(text);
  if (!parsed.model) throw new Error(parsed.reason);
  if (parsed.model.keywords === undefined) return valueEdit(text, ["keywords"], [row]);
  const {tree, bom} = syntax(text), array = findNodeAtLocation(tree!, ["keywords"]);
  if (array?.type !== "array") throw new Error("Repair keywords in Source first.");
  const children = array.children || [];
  if (tag !== undefined) {
    const offset = array.offset + array.length - 1 + bom;
    return text.slice(0, offset) + (children.length ? "," : "") + JSON.stringify(row) + text.slice(offset);
  }
  const node = children[index];
  if (!node) throw new Error("Keyword no longer exists in the current draft.");
  let start = node.offset + bom, end = start + node.length;
  if (index < children.length-1) end = children[index+1].offset + bom;
  else if (index > 0) start = children[index-1].offset + children[index-1].length + bom;
  return text.slice(0, start) + text.slice(end);
}
