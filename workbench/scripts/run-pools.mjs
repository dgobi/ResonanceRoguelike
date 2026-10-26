import { spawnSync } from "node:child_process";
import { mkdir } from "node:fs/promises";
import { resolve } from "node:path";
const root=resolve(".artifacts/w3a",`data-fixture-${Date.now()}`);
await mkdir(root,{recursive:true});
const r=spawnSync(process.env.RESONANCE_PYTHON || resolve("worker/runtime/python.exe"),["-X","utf8","-B","-c","import sys;sys.path.insert(0,'worker');from test_authoring import data_fixture;data_fixture(sys.argv[1])",root],{stdio:"inherit",windowsHide:true});
if(r.status!==0) process.exit(r.status||1);
const test=spawnSync(process.execPath,["scripts/desktop-test.mjs"],{stdio:"inherit",windowsHide:true,env:{...process.env,WORKBENCH_TEST_MODE:"pools",WORKBENCH_TEST_ROOT:root}});
process.exitCode=test.status||0;
