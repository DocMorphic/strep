# Kenney development rig: converted, strict intake rejected

The separately authored CC0 Kenney Protagonists character was converted from
the retained FBX using the pinned Godot 4.7.2 FBXDocument/GLTFDocument path.
Actual script syntax and conversion completed. Only the model, four PNG skins
and included license were extracted; bundled animation FBXs were excluded.
The generated GLB has 61 nodes, one skin and zero animation clips. The engine
reports one skinned mesh with 1,029 vertices and 1,604 triangles.

Strep's current rigid-transform rig intake rejects this converted character:
`Rig import v1 requires unit scale and proper rigid node transforms`.
The converted Root node has scale `[100, 99.99999237060547,
99.99999237060547]`. LeftUpLeg, LeftFoot and RightUpLeg also have small non-unit
scale deviations. Removing these values without preserving mesh/bind behavior
would change the asset. The raw FBX scale metadata alone did not prove this;
the actual converted GLB does.

The seven-motion transfer worker preserves the rejection with zero attempted
cases. Its first independent replay fails before assessment because it imports
`array` from the wrong module. That failure and its resource trace remain saved.
A versioned replay imports the helper from `rig_asset` and successfully confirms
the rejected intake and zero transferred cases. It performs no numerical motion
replay and gives no rig, animation or quality approval.

Retained local evidence lives in `reports/kenney-protagonists-conversion-v1`,
`reports/kenney-development-transfer-v1` and
`reports/kenney-development-transfer-replay-v2`. Original assets and generated
payloads remain excluded from public Git. The public
[source ledger](source-ledger.md) records acquisition and license provenance.

An [explicit static-rig derivative](rig-scale-adaptation-v1.md) now passes strict
intake and independent default-shape replay while preserving the original asset.
All seven unchanged development clips transfer and independently replay. Large
floor penetrations remain in crawl, kick, get-up and run/roll/stand. This resolves
the intake limitation for this derivative, not animation quality or held-out
generalization. Animated, reflected and unsupported representations still need
their own measured support. The original rejection and failed replay remain saved.
