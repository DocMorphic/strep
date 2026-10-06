# Explicit contact reserve and saved-resource validation

The solver can use a tighter contact target to leave room for export/import precision, while acceptance continues to use the original authored limit. `scripts/native_contact_reserve.py` binds an explicit positive reserve to the contact-file SHA256 and existing contact IDs. It copies only the problem's contact rows for guidance; the original problem independently audits the resulting motion. Source-rate caps, edit permissions, boundary guards, query populations, scene intent and geometry policy remain unchanged. This helper is not yet connected to Studio or automatic Apply.

Twenty focused software tests pass with zero skips. They validate request binding, reserve bounds, actor/object/world target selection and copy/seed isolation; they do not demonstrate motion quality or engine precision.

## Generated-fixture study

Starting from the retained five-knot candidate, an explicit `0.5 Âµm` reserve changes the internal partner target from `20 Âµm` to `19.5 Âµm`. The original acceptance remains `20 Âµm`. One actual solver step reaches zero guidance merit. Original source/motion/contact and actor-transition conditions pass, all nine original cap arrays match byte-for-byte, and the complete 1,707-time / 665,730-query population remains. Whole-scene geometry still fails. Original source and prior failures are preserved.

One owned, serial CPU/headless Godot run saves and reloads the native resources and measures all 1,707 times. Pose, full CPU-skin, object-pose and root-reference fidelity pass. The engine exits zero with a clean log and stopped process tree; the driver is terminal and its worker lock is free. Candidate and current/archived method hashes remain unchanged.

| Partner contact | Maximum gap | Original acceptance | Result |
| --- | ---: | ---: | --- |
| Prior five-knot native | 19.995175 Âµm | 20 Âµm | Pass |
| Prior five-knot imported | 20.055678 Âµm | 20 Âµm | Fail |
| Reserved native | 19.494052 Âµm | 20 Âµm | Pass |
| Reserved imported | 19.589304 Âµm | 20 Âµm | Pass |

Ground contacts also pass; their maximum imported gap is `8.8182e-8 m`. Imported geometry remains failed, so the overall candidate is not approved. The reserve is an explicit empirical choice for this fixture, not a universal precision guarantee: every exported candidate still needs independent readback against its original limits.

This experiment uses generated closed-cube skins and arbitrary gesture clips, not a human high-five or held-out production action. No live HTTP/browser, rendering/GPU, physics, new model sampling/training or human review occurred. All fourteen release evidence arrays remain empty; production action/rig/object/partner validation and developer/animator cleanup remain open.

Local immutable numerical receipt: `reports/transition-contact-reserve-trial-v1/result.json`, SHA256 `525b53db32ddec1ba666e8df902d981e93a6534da8e71331be1b98e2b5ea5266`. Owned engine receipt: `reports/transition-contact-reserve-engine-v1/result.json`, SHA256 `04c55d8f30662ea8314067189ae2ba53d584c8904308968750f82e61d588857c`. Raw study outputs stay excluded from the public source repository.

Local software receipt: `reports/native-contact-reserve-source-v1/result.json`, SHA256 `c15b8e2c5717ea0170a7381cadf1a63577a0c326550f524bac7ed635a9a804ec`.
