// Keep preview dimensions consistent with strep-object-geometry-v1.
export function scenePrimitive(obj) {
  if (!obj || typeof obj !== 'object') throw new Error('Scene object required');
  let geometry;
  if ('geometry' in obj) {
    if (['shape', 'size_m', 'radius_m', 'height_m'].some(key => key in obj)) throw new Error('Mixed geometry representations');
    geometry = obj.geometry;
  } else {
    if (obj.shape !== 'box' || 'radius_m' in obj || 'height_m' in obj) throw new Error('Versioned primitive geometry required');
    geometry = {schema: 'strep-object-geometry-v1', shape: 'box', size_m: obj.size_m};
  }
  if (!geometry || geometry.schema !== 'strep-object-geometry-v1') throw new Error('Unknown geometry schema');
  if (geometry.shape === 'cylinder') {
    if (Object.keys(geometry).sort().join(',') !== 'height_m,radius_m,schema,shape' || [geometry.radius_m, geometry.height_m].some(x => typeof x !== 'number' || !Number.isFinite(x) || x <= 0)) throw new Error('Positive finite cylinder radius and full height required');
    return {shape: 'cylinder', scale: [2 * geometry.radius_m, geometry.height_m, 2 * geometry.radius_m]};
  }
  const field = {box: 'size_m', sphere: 'radius_m'}[geometry.shape];
  if (!field || Object.keys(geometry).sort().join(',') !== ['schema', 'shape', field].sort().join(',')) throw new Error('Invalid geometry fields');
  const dimensions = geometry.shape === 'box' ? geometry.size_m : [geometry.radius_m];
  if (!Array.isArray(dimensions) || dimensions.length !== (geometry.shape === 'box' ? 3 : 1) || dimensions.some(x => typeof x !== 'number' || !Number.isFinite(x) || x <= 0)) throw new Error('Positive finite primitive dimensions required');
  return {shape: geometry.shape, scale: geometry.shape === 'box' ? [...dimensions] : Array(3).fill(2 * dimensions[0])};
}


export function scenePrimitiveMesh(THREE, obj) {
  const primitive = scenePrimitive(obj);
  if (primitive.shape === 'sphere') return new THREE.SphereGeometry(.5, 64, 32);
  if (primitive.shape === 'cylinder') {
    const radius = primitive.scale[0] / 2;
    let segments = 4;
    while (radius * (1 - Math.cos(Math.PI / segments)) > .001) {
      segments *= 2;
      if (segments > 256) throw Error('Cylinder preview tolerance exceeds resource limit');
    }
    return new THREE.CylinderGeometry(.5, .5, 1, segments, 1, false);
  }
  return new THREE.BoxGeometry(1, 1, 1);
}
