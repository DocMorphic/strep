// Khronos' validator runs locally; no upload or external-resource fetch.
import fs from 'node:fs';
import path from 'node:path';
import validator from '../assets/viewer/node_modules/gltf-validator/index.js';
const target=path.resolve(process.argv[2]);
const report=await validator.validateBytes(new Uint8Array(fs.readFileSync(target)),{uri:path.basename(target),maxIssues:1000});
fs.writeFileSync(process.argv[3]||path.join(path.dirname(target),'gltf-validation.json'),JSON.stringify(report,null,2));
console.log(JSON.stringify({errors:report.issues.numErrors,warnings:report.issues.numWarnings,infos:report.issues.numInfos,hints:report.issues.numHints}));
if(report.issues.numErrors)process.exitCode=1;
