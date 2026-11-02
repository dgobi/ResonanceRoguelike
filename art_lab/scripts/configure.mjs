// Use the locked installer's targeted TOML writer, with a local runtime command.
import { install } from '../node_modules/@pebbly/aseprite-ai-artist/dist/install.js';
import { readFileSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
const lab = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const result = install('codex', {
  scope: 'project', projectDir: lab, command: process.execPath,
  args: [path.join(lab, 'node_modules/@pebbly/aseprite-ai-artist/dist/cli.js'), 'serve'],
  env: { ASEPRITE_AI_ALLOW_LUA: '0', ASEPRITE_AI_HEADLESS: '0' },
  dryRun: process.argv.includes('--dry-run'),
});
// Owner requested routine approval-free access to the connected art tools.
// Keep this server policy in project config: this CLI's TUI fails to bootstrap
// when it is supplied as an inline -c override. Lua remains disabled above.
const approveArtTools = text => text.replace('[mcp_servers.aseprite-ai-artist]',
  '[mcp_servers.aseprite-ai-artist]\ndefault_tools_approval_mode = "approve"');
if (process.argv.includes('--dry-run')) console.log(approveArtTools(result.note));
else {
  writeFileSync(result.file, approveArtTools(readFileSync(result.file, 'utf8')));
  console.log(`Configured ${result.file}`);
}
