# Quantized-key support repair

An opt-in native support repair mode estimates steps from float32 quaternion
keys, promoted to float64 before interpolation. It can start from a completed
orientation study or a completed serialized repair, binding every ancestor
input, archived implementation, output and probe. Conflicting duplicate hashes
are rejected rather than overwritten. Each warm control vector must still
reproduce its prior GLB byte-for-byte.

This addresses numerical export behavior within the existing support editor.
It uses the unchanged Kimodo checkpoint and does not establish realistic motion
or general interaction support. **All four final proposals still fail the
unchanged rate screen; the input remains selected.**

## Method and reproduction

The [minimax/L1 repair](native-support-feasibility-v1.md) retains the same signed
constraint rows, original control boxes, authoring limits, 1-degree foot freedom,
5-degree swivel freedom, selected-input four-bin rate caps and 1e-5 tolerance.
The new difference model rounds native quaternion keys exactly as GLB export
does. Its absolute difference step is 1e-7 radians, shortened inside narrow
boxes. These are secant estimates of a discontinuous model, not derivatives or
feasibility certificates. The minimum trust radius before reporting a stall is
1e-9 radians. The ordinary smooth repair and Studio defaults remain unchanged.

The real study uses eight iterations per seed and a 2e-7-radian initial trust
radius. Every line-search proposal is exported, independently decoded and scored
at all 701 audit times. Numerical difference probes are not exported GLBs.
Rejected line-search exports remain saved. Final selection uses the existing
independent job audit, including preservation and all four rate groups.

```powershell
.venv/Scripts/python.exe scripts/native_support_job.py source.glb draft.json `
  reports/fresh-quantized-repair --joint-rates --joint-swivel `
  --joint-foot-orientation --repair-from reports/completed-repair-study `
  --repair-iterations 8 --repair-trust 0.0000002 --repair-quantized
```

The saved study must contain four ordered, completed, source/draft-matched
orientation or repair trials. Chaining retains ancestor hashes; a mutated
ancestor probe blocks a new study before its output folder is created.

## Four-seed development results

The study starts from the four saved proposals in
`reports/native-support-feasibility-v2`. It uses the same Studio v2 source
(`87c185ddf0dc50dec7e56bbc4c301f66896ed460a53c6c8eb6797ce5a89107c7`),
Y-up plane offset -0.056 m, two [1.6,2.4] s stances, edit keys [15,105],
30 mm displacement bound and 45-degree native local-angle bound.

| Trial | Starting worst excess | Final worst excess | Peak reduction | Rate failures | Iterations / stop |
| --- | --- | --- | --- | --- | --- |
| 1 | 0.0045174394 | 0.0036578101 | 19.03% | 67 / 13 / 25 / 14 | 8 / budget |
| 2 | 0.0000034781 | 0.0000030829 | 11.36% | 5 / 1 / 0 / 1 | 5 / stall |
| 3 | 0.0115194763 | 0.0109091337 | 5.30% | 76 / 9 / 19 / 14 | 8 / budget |
| 4 | 0.0018138644 | 0.0010863128 | 40.11% | 59 / 14 / 14 / 11 | 8 / budget |

Rate groups are position speed, position acceleration, angular speed and angular
acceleration. The failing row counts remain unchanged from the warm inputs.
Sampled support, native clocks and frozen/free/root/other-branch checks pass in
all four proposals. There are 142 stance samples per foot. The study preserves
124 decoded line-search GLBs, including four warm starts. No changed animation
is selected.

All four final GLBs replay byte-for-byte. Rounded-key proxy/decoder world
component error is at most 9.993e-16; normalized constraint component differences
are at most 1.226e-11 after rate differentiation. Actual decoded scores determine
acceptance. The first replay's exact squared-score assertion exposed a
1.735e-18 BLAS reduction difference. That failed replay is retained; repeating
with the worker's single-thread setting reproduces every saved score exactly.
No tolerance was changed.

## Bounded coordinate diagnostic

A separate four-round diagnostic tests the stalled second seed. In each round,
it finds columns structurally connected to positive constraint rows, then
screens individual bounded changes of both signs at 2e-7, 1e-7, 5e-8, 2e-8,
1e-8 and 5e-9 radians. Every score covers the full constraint vector. It exports
and independently decodes the best screened change before accepting it under
the same serialized merit rule. Numerical screens retain their starting vector,
column, displacement and score; they are distinct from exported proposals.

| Round | Screened columns | Numerical screens | Decoded rate failures |
| --- | --- | --- | --- |
| Start | — | — | 5 / 1 / 0 / 1 |
| 1 | 85 | 1,014 | 5 / 1 / 0 / 0 |
| 2 | 70 | 834 | 5 / 0 / 0 / 0 |
| 3 | 55 | 660 | 4 / 0 / 0 / 0 |
| 4 | 45 | 540 | 3 / 0 / 0 / 0 |

The worst normalized excess falls from 3.082896e-6 to 6.586748e-7. Five decoded
GLBs and 3,048 numerical screens are retained. Maximum coordinate change from
the starting vector is 2e-7 radians. **Three position-speed rows still fail.**
This is one saved development seed, not a selected job output or release proof.
A [bounded coordinate job mode](native-support-coordinates-v1.md) is now implemented;
its matched four-seed study is running. This diagnostic supports that test;
it does not justify weakening caps or claiming infeasibility for other seeds.

## Evidence and remaining work

- Four-seed result: `reports/native-support-quantized-repair-v1/result.json`,
  SHA256 `e7767e893b8fcfa6fa39ea663585534582fc98f82f23c5a5518940211280f1bb`.
- Successful exact replay:
  `reports/native-support-quantized-replay-v1-single-thread/result.json`,
  SHA256 `55e5a58c525227a1ab4a55df551ce95a81d759b10ff7df7e873820fb2154d2f3`.
- Coordinate diagnostic:
  `reports/native-support-coordinate-diagnostic-v1/result.json`,
  SHA256 `dd2923ddcbbd6eac8cb55ff1d084833a7aa3c030f8d59bb04b7d7b5844667230`.
- Rehash receipt: `reports/native-support-quantized-rehash-v1.json`;
  all 1,521 bound files match.

Nine added tests compare grouped quantized differences with separately exported
columns, including disjoint edit windows, and reject ambiguous modes. The real
four-trial job test now checks chained ancestry, unchanged caps, exact warm
replay, conflicting hashes and ancestor mutation. All 1,301 Python tests and
14 JavaScript suites pass. Commit `9aa83f9` passed hosted Windows/Linux checks.

Coordinate repair and the larger failures in the other seeds remain open.
After numerical acceptance, broader rigs/actions/scenes, engine imports,
continuous geometry, action correctness and human cleanup evidence are still
required. No training, held-out use, new engine/GPU/browser rendering, human
review, cleanup-time result or release approval is claimed. All 14 release
capabilities remain unapproved; the full-project goal remains active.
