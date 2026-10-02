# Verified corpus reader v1

`scripts/kimodo_corpus_reader.py` verifies provenance and exact derivation of
reviewed development targets before a trainer consumes them. It provides a
typed example table with per-read checks and a full snapshot check for
checkpoint/resume. No real corpus has passed admission yet; the developer
packet still awaits actual corrections, review and rights evidence.

## Binding and validation

Corpus preparation now emits `strep-native-correction-corpus-v2`. V2 adds
explicit hash-bound `submission` and `release_reservations` references to the
target/evidence inventory. The reader rejects V1 manifests instead of guessing
which files supplied those decisions. Retain old outputs and prepare a fresh
directory with the current codec; this does not alter the original review draft
or confer new approval.

The caller supplies the expected manifest SHA-256 and exact codec binding.
The reader checks the pinned hash before parsing, uses the authoritative
release reservation catalog, and revalidates the original submission through
the source/review/rights and split checks used by preparation. Every accepted
item must appear exactly once, with matching prompt, original segment,
correction hash, split, cleanup time and notes. Reviewer and scope cannot be
substituted. Quality and release approvals must remain false.

All external file hashes and copied evidence are checked. Evidence must contain
the submission, reservation catalog, original review draft and every accepted
correction, rights attestation and attested evidence file. Missing/altered
copies, absolute/escaping artifact paths and reused target paths are rejected.
These checks retain a local snapshot; they are not a portable relocation scheme
or cryptographic proof of human identity.

Each target contains exactly finite FP32 `clean_features [1,T,369]`, finite FP32
`first_heading [1]` and Boolean `reviewed_foot_contacts [T,4]`. A separate CPU
representation re-encodes the bound native correction and its contact schedule.
Features, heading, labels and geometry/contact reports must agree exactly.
Changing a file and updating its checksum alone cannot substitute a target that
differs from its correction. Self-computed hashes from untrusted metadata are
not authentication; the caller must pin the trusted snapshot and codec.

This establishes compatibility with the declared local codec. Cross-runtime
or device reproducibility is not assumed; incompatible encodings need diagnosis
and regeneration under a versioned method. The reader cannot determine whether
a contact is physically correct, a human performed the review or a license
legally permits the declared use. Those remain human evidence requirements.

## Trainer-facing interface

```python
corpus = verify_corpus(
    corpus_directory,
    independent_cpu_motion_representation,
    expected_manifest_sha256=pinned_manifest_hash,
    expected_codec_binding=pinned_codec_binding,
)
train_examples = [item for item in corpus.examples if item.split == "train"]
values = corpus.read(train_examples[0].id)
corpus.assert_unchanged()  # before saving or resuming a training checkpoint
```

The example table contains ID, prompt, split, frame count and target path/hash.
`read` checks the manifest, checks the selected target before and after loading,
validates its typed layout and returns fresh tensor copies. Full source/evidence
checks run during verification and on demand via `assert_unchanged`; they are
not repeated for every example read. A trainer must call the full check at its
snapshot/checkpoint boundary, exclude validation examples from optimizer
updates and bind the manifest hash into its adapter checkpoint.

On the provisioned Windows workspace:

```powershell
.venv\Scripts\python.exe scripts/kimodo_corpus_reader.py reports/my-reviewed-corpus --manifest-sha256 <pinned-lowercase-sha256>
```

The CLI instantiates only the pinned CPU representation/statistics under the
worker lock, with current source/model/configuration bindings. It loads neither
a denoiser nor text encoder and does not train or promote an adapter. Component
tests need no vendor assets. Actual CLI verification still needs a genuinely
reviewed prepared corpus.

## Evidence and remaining work

118 focused CPU tests pass, including 26 reader tests. They cover a complete
numerical fixture producer/reader path, splits, pinned manifest/codec mismatches,
old schema and invented approvals, missing/modified evidence, path escape,
altered targets despite retagged hashes, report/review changes, population
completeness, shared target paths and post-verification changes. Changing
returned tensors does not alter the next read. Fixture reviews are numerical
test declarations, not real human evidence.

The local CPU canary `reports/kimodo-corpus-reader-canary-v1` encodes and reads
nine previously packed numerical corrections: 1,020 frames and 4,080 contact
channels. All typed tensors match and labels decode exactly. These are the
earlier synthetic 0.01 m translations/inverted suggestions, not approved
supervision. An unapproved pack result and the real unreviewed draft are both
rejected as corpus manifests. Admitted real targets, optimizer steps, newly
generated motions and formal release trials remain zero. Inputs and methods
are checked and archived; no human review or timed cleanup is claimed.

Hosted run 37012136900 passed all four Windows/Linux jobs for the preceding
packing commit. Reader tests join the separate CPU jobs; the existing 169-file
geometry job and 14 JS suites are unchanged and were not repeated locally.

Next work is a usable human review/submission path, actual reviewed licensed
corrections and a real trainer with learning curves, fresh-process resume and
unchanged-baseline improvement/forgetting comparisons. Scene/partner/finger
representations, broad controls, rig/native editing and animator cleanup remain
unfinished. The full goal stays active; all 14 capabilities remain unapproved.
