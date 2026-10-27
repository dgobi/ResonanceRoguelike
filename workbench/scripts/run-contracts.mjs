// Full existing recipe journey plus a compatible game-source extension in the
// same packaged app. Test inputs only; never a development checkout or campaign.
import assert from "node:assert/strict";
import {spawnSync} from "node:child_process";
import {mkdir,readFile,writeFile,readdir} from "node:fs/promises";
import {resolve,relative} from "node:path";
import {createHash} from "node:crypto";

const baseline="b85e12514dc2f173cac0fcd2e65de6b3b58fbafa";
const root=resolve(".artifacts/w3c",`data-fixture-${Date.now()}`);
const output=resolve(".artifacts/w5a");await mkdir(root,{recursive:true});await mkdir(output,{recursive:true});
const fixture=spawnSync(resolve("worker/runtime/python.exe"),["-X","utf8","-B","-c","import sys;sys.path.insert(0,'worker');from test_authoring import data_fixture;data_fixture(sys.argv[1])",root],{stdio:"inherit",windowsHide:true});
assert.equal(fixture.status,0);
const before=spawnSync("git",["show",`${baseline}:roguelike/engine/item_authoring.py`],{windowsHide:true});assert.equal(before.status,0);
await writeFile(resolve(root,"roguelike/engine/item_authoring.py"),before.stdout);
const sha=bytes=>createHash("sha256").update(bytes).digest("hex");
async function tree(path) {
  const entries=[];
  async function visit(p){for(const name of (await readdir(p,{withFileTypes:true})).sort((a,b)=>a.name.localeCompare(b.name))) {
    const file=resolve(p,name.name);if(name.isDirectory())await visit(file);else entries.push([relative(path,file).replaceAll("\\","/"),sha(await readFile(file))]);
  }}
  await visit(path);return {files:entries.length,sha256:sha(JSON.stringify(entries))};
}
async function fingerprint(){return {
  executable:sha(await readFile("src-tauri/target/release/resonance-workbench.exe")),
  bridge:sha(await readFile("src-tauri/target/release/bridge.py")),
  runtime:await tree(resolve("src-tauri/target/release/python")),frontend:await tree(resolve("dist")),
  installer:sha(await readFile("src-tauri/target/release/bundle/nsis/Resonance Workbench_0.9.0_x64-setup.exe")),
};}
const frozen=await fingerprint();
const test=spawnSync(process.execPath,["scripts/desktop-test.mjs"],{stdio:"inherit",windowsHide:true,env:{...process.env,
  WORKBENCH_TEST_MODE:"recipes",WORKBENCH_TEST_ROOT:root,WORKBENCH_CONTRACT_PROOF:"1",WORKBENCH_CONTRACT_AFTER:resolve("../roguelike/engine/item_authoring.py")}});
const after=await fingerprint();assert.deepEqual(after,frozen,"Compiled application, bridge, frontend, runtime or installer changed during compatible extension");
await writeFile(resolve(output,"extension-package.json"),JSON.stringify({baseline,root,passed:test.status===0,unchanged:true,before:frozen,after},null,2));
process.exitCode=test.status || 0;
