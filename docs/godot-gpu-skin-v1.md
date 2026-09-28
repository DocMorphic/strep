# Actual GPU skin and world-placement verification

Development evidence, 2026-09-28. The full Strep goal remains active and no release gate is approved.

Earlier Godot audits compared imported bones and independently CPU-skinned vertices. They ran headlessly, which does not exercise the graphics backend. Godot's [RenderingServer documentation](https://docs.godotengine.org/en/stable/classes/class_renderingserver.html) explicitly distinguishes headless operation from rendering and exposes adapter/driver reporting and forced draws. The installed executable's help lists Windows/OpenGL and headless/dummy as separate driver combinations.

The local probe successfully renders through the NVIDIA GeForce RTX 3070 Ti Laptop GPU, OpenGL 3.3.0 / NVIDIA 610.74, in Godot 4.7.2. The engine executable matches its previously pinned acquisition hash. A minimized window and hidden process startup keep this a background audit; an independently owned SubViewport is rendered explicitly. The probe checks a nonblank image and reports its actual adapter, rather than treating process success as evidence of rendering. See `reports/godot-render-probe-v1`.

## Frozen comparison

`scripts/audit_godot_gpu_skin.py` copies all four existing cycle fixtures from the prior reverse-runtime request. These represent two rig families, not four independent action families. It checks the character, repeated reference and metadata hashes before use. Six fixed times include half-frames, a cycle boundary and a pose after two cycles. Both skeleton-space and extracted-root modes use a nonidentity initial world placement. Three fixed viewing directions give 144 paired comparisons.

The reference geometry is independently decoded and skinned in Python from the immutable repeated GLB, including all supported skin influences and original triangle indices. Godot renders that static triangle mesh with the same camera as the imported animated skin. Both use a solid, unshaded, double-sided white material on black. Camera bounds come only from the reference; an incorrect actor placement cannot be hidden by reframing the actual character.

Before rendering, the request fixes a minimum of 500 foreground pixels, silhouette intersection-over-union of at least 0.995, maximum silhouette discrepancy of 1.5 pixels, and no clipping at the image border. Empty images cannot pass. These are raster-agreement thresholds, not animation-quality thresholds.

All **144 comparisons pass**. The minimum intersection-over-union is **0.9997061786**, and the maximum silhouette distance is **1 pixel**. All 288 images, the engine output, request hashes and measured per-image values are retained in `reports/godot-gpu-skin-v1`. The first Python launch failed before creating an output because an array helper was imported from the wrong module; the corrected launch used `rig_asset.array` and completed normally. No image or threshold was adjusted after examining results.

## Negative control

`reports/godot-gpu-missing-root-v1` deliberately skips applying the extracted root transform to the actor for the existing turning fixture. It leaves the reference and skeleton-mode renders unchanged. All 18 skeleton-mode comparisons pass. All three views of the final extracted-mode pose detect the omitted-root defect: overlap is 0.556205, 0.425335 and 0.640807, with discrepancies of 41.76, 34.00 and 23.77 pixels. Fifteen of the eighteen deliberately broken extracted-mode samples fail overall; near the initial pose, the defect can be too small to cross the fixed threshold. The control's successful detection is not a pass for the broken clip.

The positive-run source version and the later optional-control version are preserved in `reports/godot-gpu-source-snapshots-v1`. The original Python source was reconstructed from the immediate control-only patch and verified byte-for-byte against its original pre-run hash; the actual positive-run GDScript was already copied into its project. No completed output or frozen request was rewritten.

## Scope and remaining work

This establishes rendered silhouette agreement and extracted-root placement at the declared sample times on one installed graphics backend. It does not validate imported materials, hidden interior geometry, lighting, performance, all intervening frames, other GPUs/engines, gameplay collision or attachment physics. Existing all-bone/CPU-skin audits supply separate transform evidence. Motion defects, action correctness, support quality and independent animator ratings remain separate gates.

The comparison page is `reports/godot-gpu-skin-v1/comparison.html`. Raw and deliberately faulty renders are labeled separately. The current Studio motion review and character exports are unchanged.
