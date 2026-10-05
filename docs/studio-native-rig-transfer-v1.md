# Native rig transfer in Studio

The Characters panel can transfer an embedded GLB clip between two explicitly mapped humanoid characters. It uses the [native rig transfer](native-rig-transfer-v1.md) and saved Godot resource audit, without a motion checkpoint or action whitelist. Original characters and mappings remain unchanged. A separate candidate becomes a library asset only after an explicit import.

## Workflow

1. Import source and target GLB characters in Characters and save both mappings. The source mapping must have zero placement offset and no custom axis overrides; target corrections are supported.
2. Open **Transfer an existing clip to another character**, refresh characters, select two different assets and bind their saved mappings.
3. Choose an embedded LINEAR source clip and 60, 120 or 240 Hz, then select **Transfer & verify playback**. Unsupported source motion fails under the documented transfer limits. The rate adds interpolation samples while retaining every original key and the exact duration.
4. Refresh transfers and review the completed candidate. The comparison selects the source clip and the newly appended target animation explicitly, retaining the target's older clips. Both versions use elapsed seconds and the existing grey native character renderer.
5. Download the candidate or explicitly add it and its mapping to the library. A saved-resource/root playback failure cannot be imported through this route. Import opens the separate candidate; build/review does not change character selection.

The candidate edit mapping is rebound to the new GLB checksum. Its placement offset and custom axis corrections are zeroed because these have already been baked into the transferred clip. The original target mapping remains in the immutable provenance. Later editing through legacy workflows may resample; the downloaded native GLB retains its original transfer clock.

## Binding and outputs

Jobs bind exact source/target asset and saved-profile checksums, clip index, sampling rate, original snapshots and implementation hashes. A changed active mapping requires a new bind before preparation. Completed jobs still refer to their original saved profile versions. Rehashed recipe, clock, raw observation, resource, mapping, scope and ZIP changes are checked against source and complete decoded observations.

Eight fixed downloads are exposed after completion: candidate ZIP, transferred GLB, edit mapping, root-motion JSON, transfer report, editable Godot `animation.res`, engine audit and job result. The ZIP includes contact data and asset-license lineage. Private input snapshots, implementation copies and raw observations are not download routes. Failed jobs retain local evidence and expose no completed downloads. Existing third-party asset and motion terms continue to apply to derived files.

The worker uses the existing separately provisioned, checksum-pinned Godot executable and offline environment. The public source repository does not bundle that executable, third-party models, character assets or an offline installer.

## Validation and limits

The offline backend tests use self-generated rigs and explicit engine doubles. They cover stale/invalid mappings, source mutation, immutable preparation, rehashed output corruption, failed-download isolation, explicit import/profile rebinding and request gates. Node tests exercise selection races, exact download populations, typed scope flags, import behavior and appended clip selection without a browser. Generated Studio must match its editable sources.

The frozen CPU-only source check passes **111 Python tests with zero skips**, including 36 new Studio transfer contracts, plus three offline Node suites and four module syntax checks. All checked source/test hashes remain unchanged afterward. Frozen result SHA256: `cb2c5c8e81ca4660b0dd2f89e3a024b5d4a4d78e5cfb2ceaf48b7bbdcc0effdb`. A separate parsed CI proof adds only the new Python suite and two Node suites; dependencies, action pins, permissions, matrices, environment and time budgets stay unchanged. Workflow proof SHA256: `a64dfc8c52fe371d11877fc1e488bc054ac9194871649d1c8c073e479216509e`. CI configuration was updated after the frozen source run and is recorded by this separate proof. These are local checks, not a claim that the subsequent hosted run has completed.

An actual serial CPU/headless study registers independently generated 19-joint source and 17-joint target fixtures, transfers their non-grid clip, reloads a saved native resource and checks **969 query times**. It verifies all eight download paths and both preview-source checksums, explicitly imports the candidate and confirms every original registry file remains unchanged. Both owned engine processes terminate with zero exits. Receipt SHA256: `b38b18eec0878f4c6c47b408bf35929d45f46c015200cd33243ff0829d237815`. Evidence stays locally under ignored `reports/studio-native-transfer-engine-v1`.

The fixtures contain trivial weighted triangles; they establish software/file/playback behavior, not production rig coverage or realistic motion. No live Studio HTTP/browser, rendered/GPU validation, production anatomical queries, model sampling/training or human cleanup review was performed. Contacts, gameplay markers, object/partner interactions, anatomy, foot sliding and animation quality remain separate checks. The transfer path rejects unsupported animated accessories, stretch, STEP/cubic channels, non-unit scale and unsupported geometry rather than silently discarding them. All project release gates remain open.
