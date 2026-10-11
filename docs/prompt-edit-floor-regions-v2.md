# Localizing floor failures in section edits

The five retained [section-regeneration pilot takes](prompt-edit-v1.md) remain
failed quality screens. A new diagnostic separates floor violations present in
protected source frames from violations first observed inside the editable
section. It changes neither the animation nor the existing acceptance limit.
All 15 focused source checks pass. The guarded measurements of all five retained
takes completed after the contact and engine validation, with a completed
resource audit. Original inputs and outputs were retained; no clip was regenerated.

## Measurement

`scripts/edit_floor_regions.py` measures the complete loaded rig's skinned
vertices at each supplied pose against an explicitly declared horizontal floor.
For this development comparison, the floor is assumed to be Y=0 and the original
5 mm floor-screen limit is retained. The original source and serialized edited
GLB are sampled at the original integer-frame clock. Source and output hashes,
recipe parameters, sample times, depths and implementation hashes are retained
with the local results.

The actual smoothstep edit envelope determines the regions. A zero weight means
protected, including the two boundary samples at either edge and frames outside
the selected section. A nonzero weight means editable. The report records:

- Source violations in protected frames.
- Previously clean editable frames that violate the limit after editing.
- Previously invalid editable frames that become clean.
- Maximum source/output depth and failed frames in each region.
- Maximum depth change in protected frames.

Empty regions have null maxima. Older reports without these measurements expose
null diagnostic counts rather than implying no failures. The existing output
floor screen still fails if any sampled output exceeds the original limit.
Studio's character result note names the assumed flat Y=0 floor, shows both
counts when available and explicitly reports an unavailable breakdown for older
results. The desktop bundle was
regenerated from its sources and the character script passes syntax checking;
live browser rendering has not been verified for this addition. A browser check
on 2026-10-11 could not load Studio on port 8768 (`ERR_CONNECTION_REFUSED`);
no server was started or restarted for that check.

## Retained development results

These counts use the original assumed Y=0 plane and 5 mm limit. New failures are
editable frames whose source depth was within the limit and output depth exceeds it.

| Take | Protected / editable frames | Protected source failures | Newly failed editable frames | Recovered editable frames | Source / output maximum depth (mm) |
| --- | ---: | ---: | ---: | ---: | ---: |
| dance-203 | 24 / 96 | 0 | 67 | 0 | 3.013 / 14.379 |
| dance-204 | 24 / 96 | 0 | 19 | 0 | 3.013 / 20.750 |
| jump-land-203 | 14 / 47 | 13 | 30 | 0 | 26.010 / 79.083 |
| jump-land-204 | 14 / 47 | 13 | 27 | 0 | 26.010 / 62.567 |
| ui-jump-land-205 | 14 / 47 | 13 | 28 | 1 | 26.010 / 70.710 |

All five outputs still fail the floor screen. Maximum depth change in protected
frames is approximately 6.21e-16 m for the dance inputs and 4.44e-8 m for the jump
inputs, including serialization differences. The jump source already violates the
screen in 13 protected frames, so editing only the permitted section cannot make
the full output pass. The dance sources pass this screen, and their edited
sections introduce violations. Neither observation identifies which internal
generation, transfer or splice step caused the new failures.

Local `reports/prompt-edit-floor-regions-v2/result.json` binds all source/output,
recipe and implementation hashes. Per-take reports and measurement archives
retain the exact frame clock, envelope and depths; the guarded test log records
15 passing tests. The separate engine observation and geometry replays continue
under their own guards. These are development diagnostics, not release trials.

## Interpretation

A protected source violation cannot be corrected solely through this edit
envelope. A newly failed editable frame identifies where the edited output
worsened this screen; it does not establish which generation, retargeting or
splicing step caused it. Timing, support intent and action correctness require
separate evidence. This diagnostic neither repairs the motion nor approves it.

The plane is an assumption for these retained development takes, not a verified
scene surface. Integer-frame vertex depths do not establish continuous collision,
foot support, object or partner contact, force balance, self-collision, naturalness
or animator cleanup time. Held-out prompts and rigs remain untouched. The project
release gates remain open.
