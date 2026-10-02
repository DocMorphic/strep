# Contact sampling at game-frame clocks

The original imported-contact audit preserves exact stance boundaries, including
nearly coincident FP32 endpoints. This exposed a poorly conditioned speed pair
in the earlier CLI wave. A separate, predeclared frame-clock contract now checks
ordinary game-frame motion without replacing that failure. Denser sampling also
exposed a small speed overshoot in the previously passing Studio wave.

## Fixed measurement contract

Run the [imported-contact audit](native-engine-contacts-v1.md) with the additional
`--frame-sampling` option:

```powershell
.\.venv\Scripts\python.exe scripts/native_engine_contacts.py source.glb candidate.glb draft.json plant-policy.json reports/my-frame-contact-audit --base input.glb --frame-sampling
```

The versioned `strep-engine-frame-contact-sampling-v1` contract requires all
30, 60 and 120 Hz clocks at phase offsets 0, 0.25, 0.5 and 0.75 frames. A sample
time is `(integer_tick + phase) / rate` in absolute clip time. All twelve
populations are fixed before observing a result; none may be dropped or selected
afterward. A stance too short to provide two samples in any population is
unavailable and cannot pass this contract.

Source anchors, clearance and maximum gap apply to every requested stance point,
including exact boundaries, native keys and frame-clock samples. Velocity uses
adjacent ticks within one stance and one clock. It never differentiates the union
of events and frame clocks. Reports retain each clock, worst pair and displacement,
archive the contract/hash, and measure native and actual imported CPU skin
separately. The original 120 Hz and native-key results remain intact. The combined
flag requires the original stance contact gate and every frame population; a
passing frame result cannot override the old failure.

[Kimodo's official benchmark metrics](https://research.nvidia.com/labs/sil/projects/kimodo/docs/benchmark/metrics.html)
separately measure motion-frame foot skating, contact consistency, constraints
and text alignment. Our fixed mesh-patch clocks and author-supplied precision
limits are additional development checks, not NVIDIA thresholds or a realism
standard.

## Preserved clock stress study

The same four source/candidate exports from the original study are imported at
408 requested points per scene: 3,264 observations across eight scenes, with
77 bones and one imported skin surface each. Every original contact population's
numeric result reproduces exactly; no prior report is rewritten.

| Preserved candidate | Worst imported frame speed | All frame clocks | Original stance gate | Combined result |
| --- | ---: | --- | --- | --- |
| Studio wave | 5.000503 mm/s | Fail | Pass | Fail |
| Earlier CLI wave | 4.999197 mm/s | Pass | Fail | Fail |
| Rejected kick proposal | 164.383848 mm/s | Fail | Fail | Fail |
| Rejected crawl proposal | 1625.073108 mm/s | Fail | Fail | Fail |

Both wave requirements remain 1 mm anchor error and 5 mm/s patch speed. The
Studio wave exceeds speed at 120 Hz phases 0.25 and 0.5; native sampling passes
all phases. The CLI wave's old 95 ns endpoint failure remains independently
failed despite its ordinary frame pass. Kick/crawl exports are still rejected
raw proposals, not accepted editable-native candidates. These historical
development clips are not a new held-out benchmark population.

## Stricter proposal targets, unchanged public limits

The optional `native_plant_headroom.py` CLI derives a separate proposal policy
by subtracting an explicit speed reserve from the original limits. A positive
reserve must be smaller than every supplied speed limit; zero remains exact.
The public policy, source anchors and all original support/rate/edit limits stay
unchanged. The final raw candidate is independently measured against that public
policy. Actual native conversion and engine contact remain separate checks.

```powershell
.\.venv\Scripts\python.exe scripts/native_plant_headroom.py source.glb input.glb draft.json plant-policy.json reports/my-headroom-proposal --reserve 0.00001
```

A matched warm follow-up starts from the saved Studio raw proposal and targets
4.99 mm/s, reserving 0.01 mm/s below the public 5 mm/s. Three accepted bounded
coordinate steps satisfy the raw and shadow-native screens. Actual editable NPZ
and preview conversion independently pass all original support/contact/rate
gates. The converted preview then passes the original imported population and
all twelve frame clocks across 816 source/candidate observations. Worst imported
frame speed is 4.989232 mm/s; anchor error is 0.509842 mm. This result uses a warm
seed and does not establish default Studio behavior by itself.

New [Studio planting jobs](studio-native-plant-v1.md) use revision 2. They reserve
the smaller of 0.01 mm/s and 0.2% of the requested speed as an internal proposal
target, without adding a user tolerance control. Zero-speed requirements remain
zero. Budgets stay at eight joint and eight coordinate iterations. Public trial
audits, selected actual-native audits and asset-bound markers retain the original
requested limits. Completed revision-1 jobs remain readable with their saved
method archives; execution never silently rebinds an old request to new methods.

A separate actual revision-2 Studio job starts from the earlier accepted height
correction, with no warm planted proposal. Eight joint iterations and six
coordinate iterations satisfy raw and shadow screens. Actual native conversion
passes the original support/contact/rate gates, selects the new candidate and
binds its stance markers to that exact preview. Another 816 imported observations
pass the original contact population and all twelve frame clocks. Worst imported
frame speed is 4.990782 mm/s; native patch speed is 4.989844 mm/s. Imported anchor
error is 0.509842 mm, minimum height 0.253440 mm and maximum lowest-region height
1.936342 mm. The previous completed revision-1 job still serves unchanged.
This verifies this default backend path on one development clip and rig, not
general planting reliability.

Headroom is a search target, not a proven bound on arbitrary import error. A
passing native fit does not automatically acquire an engine pass. These studies
provide sampled imported joint/CPU skin evidence, without fresh GPU appearance,
continuous collision, force/balance, semantic quality or human cleanup approval.
No training admission, real model update or release approval follows. All 14
release capabilities remain unapproved and the formal 72-by-five population is
untouched; the full project goal remains active.

Local evidence is preserved under `reports/native-game-frame-contacts-v1/`,
`reports/native-engine-headroom-wave-v1/` and
`reports/studio-native-headroom-v1/`. Models, characters and generated exports
are excluded from the public source repository.

The final validation passes 1,802 model-free Python tests, all 16 JavaScript
suites and 215 CPU adapter/native-pipeline tests. Fixtures cover strict speeds,
phase failures, missing/short clocks, original anchors, exact endpoint geometry,
zero/proportional reserves, tamper rejection and legacy serving. All six new
engine studies rehash their inputs, current methods, archives and engine output.
The idle project-owned Studio listener is refreshed after terminal workers and
checks, using process/socket observation only. Live HTTP/browser and fresh GPU
rendering remain unverified. The local source/evidence receipt is
`reports/native-game-frame-validation-v1/verification.json`.
