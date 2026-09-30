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
assert.deepEqual(scenePrimitive({geometry:{schema:'strep-object-geometry-v1',shape:'cylinder',radius_m:.3,height_m:1.2}}), {shape:'cylinder',scale:[.6,1.2,.6]});
for(const geometry of [
  {schema:'strep-object-geometry-v1',shape:'cylinder',radius_m:.3},
  {schema:'strep-object-geometry-v1',shape:'cylinder',radius_m:true,height_m:1.2},
  {schema:'strep-object-geometry-v1',shape:'cylinder',radius_m:.3,height_m:-1},
  {schema:'strep-object-geometry-v1',shape:'cylinder',radius_m:.3,height_m:Infinity},
  {schema:'strep-object-geometry-v1',shape:'cylinder',radius_m:.3,height_m:1,size_m:[1,1,1]},
])assert.throws(()=>scenePrimitive({geometry}));
assert.throws(()=>scenePrimitive({shape:'box',size_m:[1,1,1],height_m:1}));
console.log('Scene primitive preview dimensions: box, sphere, cylinder and strict field rejection pass.');
