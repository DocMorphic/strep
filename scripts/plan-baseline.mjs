// Dependency-free planning/fixture validation. Does not execute model commands.
import { readFileSync, writeFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { execFileSync } from 'node:child_process';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const readJson = p => JSON.parse(readFileSync(resolve(root, p), 'utf8').replace(/^\uFEFF/, ''));
const assert = (condition, message) => { if (!condition) throw new Error(message); };
const benchmark = readJson('benchmarks/v0.json');
const lock = readJson('benchmarks/sources.lock.json');
const asset = readJson('assets/characters/cesium-man/provenance.json');
const vendor = resolve(root, 'vendor/kimodo');
const commit = execFileSync('git', ['-c', `safe.directory=${vendor.replaceAll('\\', '/')}`, '-C', vendor, 'rev-parse', 'HEAD'], { encoding: 'utf8' }).trim();
assert(commit === lock.kimodo_git_commit, 'Kimodo source commit differs from lock');
const dirty = execFileSync('git', ['-c', `safe.directory=${vendor.replaceAll('\\', '/')}`, '-C', vendor, 'status', '--porcelain'], { encoding: 'utf8' }).trim();
assert(!dirty, 'Vendor source has changes; record a separate experiment condition');
assert(benchmark.model === 'Kimodo-SOMA-RP-v1.1', 'Unexpected baseline model');
assert(new Set(benchmark.seeds).size === benchmark.seeds.length && benchmark.seeds.length >= 3, 'Need distinct fixed seeds');
assert(benchmark.seeds.every(Number.isSafeInteger), 'Seeds must be integers');
assert(benchmark.cases.length === 4, 'Expected four cases');

const glb = readFileSync(resolve(root, benchmark.character));
assert(createHash('sha256').update(glb).digest('hex') === asset.sha256.toLowerCase(), 'Character checksum mismatch');
assert(glb.readUInt32LE(0) === 0x46546c67 && glb.readUInt32LE(4) === 2, 'Expected glTF 2 GLB');
assert(glb.readUInt32LE(8) === glb.length, 'GLB length mismatch');
assert(glb.readUInt32LE(16) === 0x4e4f534a, 'Expected GLB JSON first chunk');
const gltf = JSON.parse(glb.subarray(20, 20 + glb.readUInt32LE(12)).toString('utf8').trim());
assert(gltf.skins?.length > 0 && gltf.meshes?.length > 0, 'Fixture must be skinned');
assert(gltf.nodes.some(n => Number.isInteger(n.skin) && Number.isInteger(n.mesh)), 'No mesh bound to a skin');
for (const skin of gltf.skins) {
  assert(skin.joints.length > 0 && skin.joints.every(j => gltf.nodes[j]), 'Invalid skin joint references');
}

const jobs = [];
for (const test of benchmark.cases) {
  for (const track of test.tracks) {
    const prompts = track.prompt.split('.').map(s => s.trim()).filter(Boolean);
    assert(prompts.length === track.durations_s.length, `${test.id}: sentence/duration count mismatch`);
    assert(track.durations_s.every(s => s > 0 && s <= 10), 'Duration outside model segment limit');
    assert(track.constraints === null, 'Planner only implements the prompt-only condition');
    for (const seed of benchmark.seeds) {
      for (const condition of benchmark.conditions) {
        const id = `${test.id}/seed-${seed}/${condition.id}/actor-${track.actor}`;
        const args = [
          track.prompt, '--model', benchmark.model,
          '--duration', track.durations_s.join(' '),
          '--seed', String(seed), '--num_samples', String(benchmark.num_samples),
          '--diffusion_steps', String(benchmark.diffusion_steps),
          '--num_transition_frames', String(benchmark.num_transition_frames),
          '--output', `runs/${id}/attempt-001/source/motion`,
          '--bvh', '--bvh_standard_tpose'
        ];
        if (!condition.postprocess) args.push('--no-postprocess');
        jobs.push({
          id, status: 'not_run', cwd: root, executable: 'kimodo_gen', argv: args,
          seed, condition: condition.id, actor: track.actor, case_id: test.id,
          prompt: track.prompt, durations_s: track.durations_s, constraints: null,
          scene_targets: test.evaluation_targets, required_metrics: test.required_metrics,
          environment_after_pinned_downloads: {
            TEXT_ENCODER_MODE: 'local', TEXT_ENCODER_DEVICE: 'cpu',
            HF_HUB_OFFLINE: '1', TRANSFORMERS_OFFLINE: '1', LOCAL_CACHE: 'True',
            CHECKPOINT_DIR: resolve(root, 'models/checkpoints')
          },
          prerequisite: 'Select feasible hardware; install and freeze dependencies; stage exact model and encoder revisions; validate offline cache; calibrate scene; preserve run record and logs.',
          model_revision: lock.models.find(m => m.repo_id === `nvidia/${benchmark.model}`).revision,
          benchmark_sha256: createHash('sha256').update(readFileSync(resolve(root, 'benchmarks/v0.json'))).digest('hex'),
          kimodo_git_commit: commit, rig_sha256: asset.sha256,
          retarget_status: 'not_implemented', import_status: 'not_tested', metrics: null
        });
      }
    }
  }
}
assert(new Set(jobs.map(j => j.id)).size === jobs.length, 'Duplicate job IDs');
const report = {
  status: 'plan_only_no_inference', benchmark_id: benchmark.benchmark_id,
  counts: { generation_jobs: jobs.length, case_condition_trials: benchmark.cases.length * benchmark.seeds.length * benchmark.conditions.length },
  fixture: { bytes: glb.length, skins: gltf.skins.length, joint_counts: gltf.skins.map(s => s.joints.length), supplied_animation_count: gltf.animations?.length ?? 0 },
  jobs
};
const destination = resolve(root, 'benchmarks/generated-plan.json');
writeFileSync(destination, JSON.stringify(report, null, 2) + '\n');
console.log(JSON.stringify({ output: destination, status: report.status, counts: report.counts, fixture: report.fixture }, null, 2));
