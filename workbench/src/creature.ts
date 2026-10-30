import { syntax } from "./draft";
import { valueEdit } from "./layout";

export function creatureModel(text: string): {model: Record<string, unknown> | null; reason: string} {
  if (syntax(text).diagnostics.length) return {model: null, reason: "Correct JSON in Source to resume creature controls. Draft retained."};
  const model = JSON.parse(text.replace(/^\uFEFF/, ""));
  if (!model || typeof model !== "object" || Array.isArray(model)) return {model: null, reason: "One creature object is required. Source retained."};
  return {model, reason: ""};
}
export function creatureValue(text: string, field: string, value: string | number | boolean | string[]): string {
  const {model, reason} = creatureModel(text);
  if (!model) throw new Error(reason);
  const allowed = ["name","description","armour_value","damage_dice","damage_bonus","attack_verb","perception.sight_radius","perception.hearing_radius","perception.sees_in_dark","wander_radius","pursuit_timeout","speed","ai_type"];
  if (field !== "hp") {
    if (![...allowed,"perception.faction","perception.hostile_to"].includes(field)) throw new Error("Read-only creature field");
    const path=field.split(".");
    const current=path.reduce<unknown>((v,k)=>v && typeof v === "object" ? (v as Record<string,unknown>)[k] : undefined,model);
    return current===value ? text : valueEdit(text,path,value);
  }
  if (!model.fighter || typeof model.fighter !== "object" || Array.isArray(model.fighter)) throw new Error("Restore the fighter object in Source.");
  // Two persisted authorities, one undoable operation. Never serialize siblings.
  const fighter = model.fighter as Record<string, unknown>;
  if (model.base_hp === value && fighter.max_hp === value) return text;
  return valueEdit(valueEdit(text, ["base_hp"], value), ["fighter", "max_hp"], value);
}
