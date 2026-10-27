import { syntax } from "./draft";
import { valueEdit } from "./layout";

export function creatureModel(text: string): {model: Record<string, unknown> | null; reason: string} {
  if (syntax(text).diagnostics.length) return {model: null, reason: "Correct JSON in Source to resume creature controls. Draft retained."};
  const model = JSON.parse(text.replace(/^\uFEFF/, ""));
  if (!model || typeof model !== "object" || Array.isArray(model)) return {model: null, reason: "One creature object is required. Source retained."};
  return {model, reason: ""};
}
export function creatureValue(text: string, field: "name" | "hp", value: string | number): string {
  const {model, reason} = creatureModel(text);
  if (!model) throw new Error(reason);
  if (field === "name") return model.name === value ? text : valueEdit(text, ["name"], value);
  if (!model.fighter || typeof model.fighter !== "object" || Array.isArray(model.fighter)) throw new Error("Restore the fighter object in Source.");
  // Two persisted authorities, one undoable operation. Never serialize siblings.
  const fighter = model.fighter as Record<string, unknown>;
  if (model.base_hp === value && fighter.max_hp === value) return text;
  return valueEdit(valueEdit(text, ["base_hp"], value), ["fighter", "max_hp"], value);
}
