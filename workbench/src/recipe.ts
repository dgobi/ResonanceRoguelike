import { itemModel } from "./item";
import { recordRow } from "./orderedRecords";
export { itemValue as recipeValue } from "./item";

export function recipeModel(text: string) {
  const result = itemModel(text);
  return {...result, reason: result.reason ? "Correct JSON in Source to resume recipe controls. Your draft is retained." : ""};
}
export function recipeRow(text: string, field: string, action: "add" | "remove" | "up" | "down", index: number, tag?: string, row: Record<string,unknown> = {tag, min_tier: 1, ...(field === "requires_ambient" ? {} : {quantity: 1})}) {
  return recordRow(text,field,action,index,row);
}
