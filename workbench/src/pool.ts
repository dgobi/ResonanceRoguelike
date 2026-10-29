import { applyEdits, modify } from "jsonc-parser";
import { syntax } from "./draft";
import { valueEdit } from "./layout";
import {recordRow} from "./orderedRecords";
import {removeItemProperty} from "./item";

export type Pool = { id: string; description?:unknown; items?: Record<string, unknown>[]; roll_count?: number[] };
export function poolModel(text: string): { model: Pool | null; reason: string } {
  if (syntax(text).diagnostics.length)
    return { model: null, reason: "Correct JSON in Source to resume the table." };
  const r = JSON.parse(text.replace(/^\uFEFF/, ""));
  if (!r || typeof r !== "object" || Array.isArray(r) ||
      (r.items !== undefined && (!Array.isArray(r.items) || r.items.some((e: unknown) => !e || typeof e !== "object" || Array.isArray(e)))))
    return { model: null, reason: "Pool table requires one object with an items array of records. Source is preserved." };
  return { model: r, reason: "" };
}
export function poolValue(text: string, path: (string | number)[], value: unknown) {
  const p = poolModel(text);
  if (!p.model) throw new Error(p.reason);
  return valueEdit(text, path, value);
}
export function poolEntry(text: string, index: number, itemId?: string) {
  const p = poolModel(text);
  if (!p.model) throw new Error(p.reason);
  if (!p.model.items) return valueEdit(text, ["items"], [{ item_id: itemId, weight: 1 }]);
  const bom = text.startsWith("\uFEFF") ? "\uFEFF" : "", body = text.slice(bom.length);
  return bom + applyEdits(body, modify(body, ["items", index], itemId === undefined ? undefined : { item_id: itemId, weight: 1 },
    { formattingOptions: { insertSpaces: true, tabSize: 2, eol: text.includes("\r\n") ? "\r\n" : "\n" } }));
}

export const poolRow=(text:string,action:"up"|"down",index:number)=>recordRow(text,"items",action,index);
export const poolDefault=(text:string,path:(string|number)[])=>removeItemProperty(text,path);
