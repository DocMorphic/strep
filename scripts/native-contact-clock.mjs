export function clampTime(value, duration) {
  if (!Number.isFinite(value) || !Number.isFinite(duration) || duration <= 0) throw Error('Finite time and positive duration required');
  return Math.max(0, Math.min(duration, value));
}

export function advanceTime(value, delta, duration) {
  if (!Number.isFinite(delta) || delta < 0) throw Error('Finite nonnegative elapsed time required');
  const time = clampTime(value + delta, duration);
  return {time, finished: time === duration};
}
