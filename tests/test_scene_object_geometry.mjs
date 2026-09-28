import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
// Load this standalone browser ES module without executing Studio or network IO.
const source = await readFile(new URL('../scripts/scene-object-geometry.js', import.meta.url), 'utf8');
const {scenePrimitive} = await import(`data:text/javascript;base64,${Buffer.from(source).toString('base64')}`);
assert.deepEqual(scenePrimitive({shape:'box',size_m:[1,2,3]}), {shape:'box',scale:[1,2,3]});
assert.deepEqual(scenePrimitive({geometry:{schema:'strep-object-geometry-v1',shape:'sphere',radius_m:.3}}), {shape:'sphere',scale:[.6,.6,.6]});
for (const obj of [
  {shape:'sphere',radius_m:.3},
  {geometry:{schema:'strep-object-geometry-v1',shape:'sphere',radius_m:-1}},
  {geometry:{schema:'strep-object-geometry-v1',shape:'sphere',radius_m:true}},
  {geometry:{schema:'strep-object-geometry-v1',shape:'sphere',radius_m:1},size_m:[2,2,2]},
  {geometry:{schema:'strep-object-geometry-v1',shape:'box',size_m:[1,2,Infinity]}},
]) assert.throws(() => scenePrimitive(obj));
console.log('Scene primitive preview dimensions: 7 checks passed.');
