import { LiveClient } from '../node_modules/@pebbly/aseprite-ai-artist/dist/bridge/client.js';
import { packageVersion } from '../node_modules/@pebbly/aseprite-ai-artist/dist/lib/version.js';
// This is only a launcher readiness probe. Authoring still uses MCP preflight.
const live = new LiveClient();
try {
  if (!await live.waitForBridge(5000)) throw new Error('Local bridge unavailable on port 9932. Check for a conflicting process.');
  if (!await live.waitForPlugin(8000)) throw new Error('Aseprite extension is not attached. Save/close/reopen Aseprite after setup; allow ai-artist.lua access if prompted, then rerun.');
  const [major, minor] = String(live.hello.asepriteVersion).split('.').map(Number);
  if (!(major > 1 || (major === 1 && minor >= 3))) throw new Error('Aseprite 1.3+ is required.');
  if (live.hello.extensionVersion !== packageVersion()) throw new Error('Extension version differs from the locked adapter. Save your work, rerun setup, then restart Aseprite normally.');
  await live.call('session.site');
  console.log(`Live Aseprite ${live.hello.asepriteVersion}; adapter/extension ${packageVersion()}; attached and answering.`);
} catch (error) {
  console.error(error.message);
  process.exitCode = 1;
} finally {
  live.close();
}
