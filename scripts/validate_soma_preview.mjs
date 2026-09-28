import fs from 'node:fs';
import path from 'node:path';
import validator from '../assets/viewer/node_modules/gltf-validator/index.js';
const folder=path.resolve(process.argv[2] || 'reports/control-calibration-v1');
const manifest=JSON.parse(fs.readFileSync(path.join(folder,'soma-preview.json'),'utf8'));
const results=[];
for(const trial of manifest.trials){
 const file=path.join(folder,trial.method,'characters',trial.id,'soma.glb');
 const report=await validator.validateBytes(new Uint8Array(fs.readFileSync(file)),{uri:'soma.glb',maxIssues:1000});
 results.push({id:trial.id,method:trial.method,errors:report.issues.numErrors,warnings:report.issues.numWarnings,
  messages:report.issues.messages.filter(m=>m.severity<2)});
}
fs.writeFileSync(path.join(folder,'soma-preview-validation.json'),JSON.stringify(results,null,2));
console.log({exports:results.length,errors:results.reduce((n,r)=>n+r.errors,0),warnings:results.reduce((n,r)=>n+r.warnings,0)});
if(results.some(r=>r.errors))process.exitCode=1;
