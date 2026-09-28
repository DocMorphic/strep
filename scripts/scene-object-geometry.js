// Keep preview dimensions consistent with strep-object-geometry-v1.
export function scenePrimitive(obj) {
  if (!obj || typeof obj !== 'object') throw new Error('Scene object required');
  let geometry;
  if ('geometry' in obj) {
    if (['shape', 'size_m', 'radius_m'].some(key => key in obj)) throw new Error('Mixed geometry representations');
    geometry = obj.geometry;
  } else {
    if (obj.shape !== 'box' || 'radius_m' in obj) throw new Error('Versioned primitive geometry required');
    geometry = {schema: 'strep-object-geometry-v1', shape: 'box', size_m: obj.size_m};
  }
  if (!geometry || geometry.schema !== 'strep-object-geometry-v1') throw new Error('Unknown geometry schema');
  const field = {box: 'size_m', sphere: 'radius_m'}[geometry.shape];
  if (!field || Object.keys(geometry).sort().join(',') !== ['schema', 'shape', field].sort().join(',')) throw new Error('Invalid geometry fields');
  const dimensions = geometry.shape === 'box' ? geometry.size_m : [geometry.radius_m];
  if (!Array.isArray(dimensions) || dimensions.length !== (geometry.shape === 'box' ? 3 : 1) || dimensions.some(x => typeof x !== 'number' || !Number.isFinite(x) || x <= 0)) throw new Error('Positive finite primitive dimensions required');
  return {shape: geometry.shape, scale: geometry.shape === 'box' ? [...dimensions] : Array(3).fill(2 * dimensions[0])};
}
