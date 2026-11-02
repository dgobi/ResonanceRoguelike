// Use the locked installer's targeted TOML writer, with a local runtime command.
import { install } from '../node_modules/@pebbly/aseprite-ai-artist/dist/install.js';
import { appendFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
const lab = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const result = install('codex', {
  scope: 'project', projectDir: lab, command: process.execPath,
  args: [path.join(lab, 'node_modules/@pebbly/aseprite-ai-artist/dist/cli.js'), 'serve'],
  env: { ASEPRITE_AI_ALLOW_LUA: '0', ASEPRITE_AI_HEADLESS: '0' },
  dryRun: process.argv.includes('--dry-run'),
});
console.log(result.note ?? `Configured ${result.file}`);
// Explicitly approved by the owner for ART-1 and future lab authoring.
// Other tools and the general sandbox/approval policies retain their defaults.
const approvals = ['sprite_manage', 'layer', 'draw', 'export'].map(tool =>
  `\n[mcp_servers.aseprite-ai-artist.tools.${tool}]\napproval_mode = "approve"\n`
).join('');
if (process.argv.includes('--dry-run')) console.log(approvals);
else appendFileSync(result.file, approvals);
