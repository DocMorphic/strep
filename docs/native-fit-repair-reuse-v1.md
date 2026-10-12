# Fresh verification without repeating an identical repair search

The native fitter now reuses a successful repair when the exact same control
vector is evaluated again in the same fitting context. Final evaluation no
longer repeats every neighbor search just to export an identical clip. New
control vectors still start from the explicitly bound corrections and follow
the existing complete proposal checks.

A reuse entry binds the original report, intended-motion archive, search result,
every native probe receipt/array/asset (including failed candidates), selected
files and exact decoded residual. Modified evidence or in-memory corrections
reject reuse. Original authoring, source worlds, clocks, control boxes, policy
and source-cap population remain checked. Reuse exports fresh actor files,
performs strict payload/authoring audits and fresh complete native decoding,
and requires identical asset hashes and residuals. Authored serialized joint
speeds remain independently checked. A previously passing result that no
longer matches fresh checks is rejected rather than silently trusted.

Only fully passing native repairs enter this cache. Geometry/contact quality
approval is never cached: the outer fitter still measures complete declared
geometry and surface contacts on the returned export. Original selection and
quality/training/release flags remain unchanged.

## Measured development result

The retained humanoid kick's exact earlier accepted control vector is evaluated
twice in one context under the original 72-control authoring/cap epoch and
explicit 18-component start. The first evaluation performs the normal bounded
search; the second uses its checked repair and still freshly decodes every
native row. Both files are byte-identical to the earlier independently replayed
asset, with identical complete world poses/residuals and zero root error across
all 2,017 times. All 107,527 native conditions pass.

| Same curve evaluation | Native exports | Export/native time |
| --- | ---: | ---: |
| Initial bounded search | 30 | 176.131 s |
| Bound repair with fresh checks | 1 | 11.002 s |

This is about a 94% reduction in the repeated export/native step on one machine
and one curve. Geometry timings are excluded from that comparison. Both returned
files separately receive a complete fresh floor audit, reproducing all earlier
samples: **45.560871 mm peak and 231 failed times**. The clip remains unapproved;
reuse changes time, not motion quality. Raw evidence remains under
`reports/kenney-kick-repair-reuse-v1`. The job finishes at 223.641 s execution
within the unchanged resource policy; all 238 observations independently replay.

All **44 affected checks** pass, including eleven new cases for same-curve reuse
with/without authored speeds, fresh decoding, altered reports/unrounded arrays/
search/failure assets/selected files, changed memo state and different controls.
All 63 test resource observations replay. These checks do not certify broader
performance, engine playback, held-out actions or animator quality.

The earlier [focused workflow at `3fa7022`](https://github.com/DocMorphic/strep/actions/runs/38189436680)
passes all six Windows/Linux jobs: 745 Python checks per OS (678 contact/rig,
35 lineage, 32 game packages), 23 subtests and the offline editor. That revision
precedes this reuse change. Its full source workflow remains separate. The
declared inventory remains 469 Python modules / 42 Node suites. Studio's
original-bound storage-mode request/continuation path remains to be implemented;
legacy continuation must not drop the new repair contract.
