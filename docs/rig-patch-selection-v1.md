# Bone-region drafts for contact authoring

Studio's mesh-contact editor can draft vertices from a selected skin bone,
optionally including child bones and a box at the displayed pose. This makes
region authoring less dependent on picking individual proxy points for each
rig. Skin weights identify deformation ownership; they do not identify a palm,
sole, kneecap or a valid support schedule automatically.

## Authoring

Create or select a contact patch, then open **Draft a bone region**. Choose a
bone, minimum influence and whether to include child bones. Including children
can bring finger vertices into a hand region. **Preview bone region** leaves
the saved patch unchanged and shows an applicable draft with cyan markers.
Gold markers continue to show the existing patch.

Use **Limit to a box at the displayed pose** to refine a region. The first
unboxed preview fills the coordinate fields with the matched region's bounds.
Adjust those coordinates in world metres and preview again. Box limits are
inclusive and are evaluated on decoded skin positions at the requested frame,
including fractional frames. Membership is attached to the selected topology,
not recomputed as a moving contact surface during fitting.

**Apply to patch** explicitly replaces only that patch's vertex indices. Its
intervals, targets, editable joints, hard bounds and contact clocks stay
unchanged. Inspect the surface and refine its vertices before fitting. Changing
the displayed pose, source, patch or selector invalidates the old application;
draft changes invalidate pending results. The selected indices enter the normal
GLB-bound contact draft and saved fitting job. The selection recipe itself is a
read-only inspection result, not an anatomical annotation.

The editor retains its 256-vertex patch limit. Empty and oversized regions
cannot be applied; no silent subsampling is performed. Narrow the box, change
the influence or refine manually. A larger region is not evidence of better
contact coverage.

## Calculation and checks

`rig_patch_selection.py` sums normalized influence weights for the chosen skin
joint nodes across every stored channel, including eight-weight skins and
repeated joint slots. Skin slot indices are resolved through the skin's node
table; they are not assumed to equal node IDs. Static mesh primitives are
excluded from bone ownership, while their vertices still contribute to global
index offsets. The posed box uses the complete decoded skin.

The read-only `/api/rig-patch-selection` path verifies the completed published
clip, exact GLB hash, finite frame and explicit selector. It runs before the
generation-worker gate and does not launch a model or mutate a job. It retains
the Studio host/origin and JSON guards. Its result identifies the method hash,
requires review and explicitly declines anatomical and quality approval.

An independent observer inspected seven previously generated development
actions—jump/land, crawl, dance, wave, kick, get-up and run/roll/stand—on
CesiumMan and Quaternius female/male. Four mapped regions per clip were checked
at frame 54.5 with minimum influence 0.5: the two hands and two shins, once for
the bone alone and once with descendants and an 80 mm box around the posed
bone. These are arbitrary selection diagnostics, not proposed contact targets.
All 168 selections match independent scalar weight accumulation, node
traversal and separate bind-point skin reconstruction. Original GLBs, profiles,
reports and the bound manifest remain unchanged.

| Character | Bone-only applicable / 28 | Children + box applicable / 28 | Matched count ranges, bone / box |
| --- | ---: | ---: | --- |
| CesiumMan | 28 | 28 | 55–59 / 18–36 |
| Quaternius female | 14 | 14 | 114–290 / 55–410 |
| Quaternius male | 14 | 28 | 130–296 / 65–224 |

There were no empty regions in this observation. Every non-applicable region
exceeds 256 vertices and is retained as such. All three observed character
assets have four skin influences; eight-influence behavior is covered by the
portable fixture, not claimed as an eight-weight character experiment.

Evidence is local under `reports/rig-patch-selection-v2/`. The initial v1
coordinator failed on path/string concatenation before saving an observation;
its request, method archive and failure remain preserved. The corrected
observer reran independently without changing production methods or inputs.
Portable tests verify indexing, all eight slots, repeated influences, child
membership, boxes, oversized regions, actual source immutability, changed
bindings and the read-only handler's origin/busy behavior. DOM/source tests
verify explicit application, unchanged timing, nested-box/frame changes,
malformed results, missing approvals, late responses and duplicate clicks.
Forty focused Python checks pass; the complete model-free workflow passes
1,648 Python checks and fourteen explicit JavaScript suites. The marker fixture
also checks cyan preview indices through displayed world transforms, then gold
patch updates after Apply. This is CPU/DOM behavior, not rendered browser proof.

No new fitting, model inference/training/seed, formal held-out use, engine
import, browser/GPU rendering, submitted human review or cleanup timing is
supplied here. Existing crawl and broader motion-quality failures remain.
Anatomical surface selection and meaningful contact timing still need review;
scene/partner, style, rig, engine and full-release requirements remain open.
