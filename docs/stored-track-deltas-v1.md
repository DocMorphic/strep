# Explicit native-key export without zero-edit drift

Development component, 2026-10-18. Exporting a selected rotation through a
normalization/conversion path can alter its stored components even when its
requested edit is zero. Shared animation samplers also need to be isolated
before changing a single channel.

`append_track_deltas` applies explicit per-key right-multiplied rotation
vectors or translation offsets on an unchanged native LINEAR clock. Each
track declares its protected keys and maximum edit norm. Incomplete clocks,
duplicate or missing channels, invalid values, protected-key edits and intended
edits exceeding the declared limit reject. Current bounded inputs support
2..300 keys and up to 256 track declarations; no key population is truncated.

The helper preserves source quaternion length before Float32 storage rather
than normalizing the original first. Zero-delta and protected key values stay
byte-exact. Only channels with actual edits receive appended outputs and new
samplers, so another channel sharing the old sampler stays unchanged. Original
samplers and the existing binary prefix remain intact. Static rig, mesh, skin
and material metadata are copied without modification.

After Float32 conversion, strict stored rotation/translation differences are
measured against the original channel. A rounding overshoot is reported as a
failure; values are not clipped and no physical epsilon is added. The returned
file data are diagnostic, not approved animation. Callers must bind the exact
source asset and permissions and independently verify raw and saved motion,
contacts, geometry, import and human quality.

All **264 focused source cases pass locally**: the previous 237, 25 new export
cases and two existing GLB checks. The new cases cover exact zero/protected
values, shared-sampler isolation, mixed rotation/root edits, source ownership,
strict stored rounding failure and invalid/incomplete declarations. The same
**264 cases pass on Windows and Ubuntu** at
`559d7da03abb1f19573880d03423780ad0e10380`
([hosted run](https://github.com/DocMorphic/strep/actions/runs/39144245348)).

The [retained diagnostic export](exploratory-export-replay-v1.md) independently
preserves 35,894 zero/unpermitted saved keys across both characters, all
protected/unselected local channels, original binary payloads and strict
rotation/root limits. Its numerical partial improvement survives raw and
saved replay, but 41 physical failures keep the animation unapproved.
Source evidence: `reports/stored-track-deltas-tests-v1` and
`reports/exploratory-export-progress-v1`.
