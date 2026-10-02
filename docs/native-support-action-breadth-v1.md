# Native support diagnostics across development actions

The [multi-rig fitting work](native-support-rigs-v1.md) now has a broader
development diagnostic: jump/land, crawl, dance, kick, get-up and run/roll/stand
on CesiumMan and Quaternius female/male. These are 18 previously examined clips,
three character assets across two rig families. They reuse the existing seed-77
generation and retargets. There are no new model seeds, training runs or formal
release held-out evaluations. Action families remain evaluation categories,
not a supported-prompt whitelist.

The study binds the original rig manifest, generation request, exported clips,
rig profiles, transfer reports and coordinator method. Twelve Quaternius inputs
receive explicit static-roundoff preparation; raw inputs remain immutable.
All prepared drafts change only their input hash.

## Authored diagnostic conditions

Both foot regions use ground zero, 0.25 mm clearance reserve, 5 mm maximum gap,
30 mm ankle displacement and 45-degree local angle boxes. These are authored
clearance conditions, not independently annotated contact or semantic truth.

| Action | Stance interval, seconds | Editable native rotation keys |
| --- | --- | --- |
| Jump / land | 2.8–3.6 | 66–114 |
| Crawl | 1.6–2.4 | 15–105 |
| Dance | 1.8–2.2 | 42–78 |
| Kick | 3.1–3.7 | 84–117 |
| Get-up | 5.0–5.6 | 135–174 |
| Run / roll / stand | 6.0–6.6 | 165–204 |

Crawling also needs knee, hand and body supports. A two-foot dance constraint
can conflict with the intended steps. An unreachable authored condition is
not by itself evidence that the motion generator got the action wrong.

## Fitting outcomes

Four fixed smoothing variants per case produce 72 attempts. Fifty-two export
complete proposal GLBs; 20 reject unreachable authoring. The latter comprise
all four proposals on all three crawl assets and both Quaternius dance assets.
The failed attempts and exact retained inputs remain in the study population.

Of the 52 completed proposals, 42 pass sampled support/preservation checks and
10 fail. All 52 fail the unchanged source-relative rate selection. All 18 jobs
retain their exact fitting input; no proposal becomes a selected correction.

| Asset | Jump / land | Crawl | Dance | Kick | Get-up | Run / roll / stand |
| --- | --- | --- | --- | --- | --- | --- |
| CesiumMan | 4 support passes | 4 rejected | 4 support failures | 4 support passes | 4 support passes | 4 support passes |
| Quaternius female | 4 support passes | 4 rejected | 4 rejected | 4 support passes | 2 passes / 2 failures | 4 support passes |
| Quaternius male | 4 support passes | 4 rejected | 4 rejected | 4 support passes | 4 support failures | 4 support passes |

The completed dance failures include between-key penetration: left/right
minima reach approximately -0.341/-0.488 mm and the left maximum gap exceeds
5 mm. Female get-up trials 0/1 reach 30.008104 mm right-ankle displacement.
Male get-up trials reach 30.001016–30.008089 mm. These exceed the existing
30 mm bound and its 1e-7 m numerical allowance; no tolerance was widened.

The female roll proposals are the closest derivative result, with 12 failed
speed rows and zero acceleration/angular-speed/angular-acceleration failures
in each variant. They still fail selection. This is a diagnostic observation,
not proof of planted soles, naturalness or game readiness.

## Actual engine scope

Godot 4.7.2 imports the input and all four proposals for each of the 13 complete
populations, including failed support/rate proposals: 65 clips. The five wholly
rejected populations remain explicit and cannot supply nonexistent proposal
GLBs. The audit saves/reloads native LINEAR resources and reconstructs every
actual imported skin surface using its raw imported weights.

Bone/clock and surface correspondence are separate from foot-height checks.
The imported skin auditor measures height/penetration/gap; it does not validate
the fitter's ankle displacement or angle boxes. CPU reconstruction is not GPU
rendering, derivative preservation or ordinary gameplay playback.

All 65 clips pass the existing bone/clock and complete surface correspondence
checks across 59,645 sampled poses and 393,804,105 reconstructed vertex
observations. Maximum bone position error is 3.9609e-6 m, basis element error
1.5821e-6, and vertex distance 5.39542e-4 m (0.53955 mm). These maxima are
larger than the earlier wave-only study and remain visible in the evidence.

Forty-eight of 52 imported proposals pass the sampled height check; all four
Cesium dance proposals retain their height failures. All 13 imported inputs
fail their authored height conditions. Get-up proposals can pass imported
height checks while failing the fitter's separate displacement bounds. The
difference between 48 height passes and 42 full support passes is not an
engine repair or a changed acceptance condition.

Twelve input preparations stay below 1.29648e-7 m sampled mesh change
(0.130 micrometres), with the original 1e-5 m limit unchanged. All 2,456
bound evidence files rehash, including fitting/preparation failures, archived
methods, actual engine resources and the separate Studio verification.
Receipt: `77ec706c274896a29cf62d6440b31e9b0e1f8a93ed7fc5cfa575cf6f282b6a0c`.

Full raw requests, failures, proposals and engine resources remain under
ignored `reports/native-support-action-breadth-v1` and
`reports/native-support-breadth-imports-v1`; the receipt is
`reports/native-support-breadth-studio-evidence-v1/verification.json`.
The fitting coordinator result hash is
`d70fca3066dde12b172fd747efb12f32b63d27529f37f3ccc55d1d39d302b224`;
the actual import coordinator result hash is
`8f86db4df4c40a359fa7c94c1189d385313519502e50788870586a3a15f1e0c8`.

The [Studio preparation workflow](studio-support-preparation-v1.md) is tested
separately. No human cleanup evidence or release approval is inferred here.
All 14 release capabilities remain unapproved. Next work must address the
between-key bound failures and source-rate tradeoff, and extend support beyond
feet for ground, object and partner actions.
