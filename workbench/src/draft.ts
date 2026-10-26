import {
  findNodeAtLocation,
  parseTree,
  printParseErrorCode,
  type ParseError,
} from "jsonc-parser";
import { createTwoFilesPatch } from "diff";

export function syntax(source: string) {
  const bom = source.startsWith("\uFEFF") ? 1 : 0;
  const errors: ParseError[] = [];
  const tree = parseTree(source.slice(bom), errors, {
    disallowComments: true,
    allowTrailingComma: false,
    allowEmptyContent: false,
  });
  const diagnostics: { message: string; line: number; column: number }[] =
    errors.map((e) => {
      const before = source.slice(0, e.offset + bom).split(/\r\n|\r|\n/);
      return {
        message: printParseErrorCode(e.error),
        line: before.length,
        column: before.at(-1)!.length + 1,
      };
    });
  // Duplicate keys are forbidden by read_document too; don't let typed edits
  // choose a different occurrence than the production reader.
  function duplicates(node: typeof tree) {
    if (!node) return;
    if (node.type === "object") {
      const keys = new Set<string>();
      for (const prop of node.children || []) {
        const key = prop.children![0].value as string;
        if (keys.has(key))
          diagnostics.push({
            message: `Duplicate key: ${key}`,
            line: source.slice(0, prop.offset + bom).split("\n").length,
            column: 1,
          });
        keys.add(key);
      }
    }
    node.children?.forEach(duplicates);
  }
  duplicates(tree);
  return { tree, diagnostics, bom };
}

export function scalarEdit(
  source: string,
  key: "id" | "description" | "weight",
  value: string | number,
): string {
  const { tree, diagnostics, bom } = syntax(source);
  if (diagnostics.length || tree?.type !== "object")
    throw new Error("Correct JSON syntax before editing properties.");
  const node = findNodeAtLocation(tree, [key]);
  const text = JSON.stringify(value);
  if (node)
    return (
      source.slice(0, node.offset + bom) +
      text +
      source.slice(node.offset + bom + node.length)
    );
  // Insert a scalar immediately before the closing brace; all original spans
  // remain byte-identical, including nested arrays, indentation and line endings.
  const offset = tree.offset + tree.length - 1 + bom;
  const eol = source.includes("\r\n") ? "\r\n" : "\n";
  return (
    source.slice(0, offset) +
    `${tree.children?.length ? "," : ""}${eol}  ${JSON.stringify(key)}: ${text}${eol}` +
    source.slice(offset)
  );
}
export const sourceDiff = (
  before: string,
  after: string,
  path: string,
  target: string,
) =>
  createTwoFilesPatch(
    path,
    target,
    before,
    after,
    "opened bytes",
    "draft bytes",
    { context: 3 },
  );

export function currentVerdict(
  requestVersion: number,
  currentVersion: number,
  requestText: string,
  currentText: string,
) {
  return requestVersion === currentVersion && requestText === currentText;
}
