# Verified continuation without a new motion reference

The [repeated restoration workflow](native-key-restoration-workflow-v1.md) previously stopped with 47 rate failures and 18 floor failures. `native_key_restoration_continuation.load` now reconstructs that exact saved state for further correction while retaining the original initializer, rig, clocks, contacts, physical edit limits and motion-rate arrays. It never substitutes the edited clip as a new rate reference or promotes a numerically improved candidate to a released asset.

```python
from native_key_restoration_continuation import load

problem, value, current, receipt = load(
    producer, trusted_result_digest, trusted_request_digest,
    replay_result_path, trusted_replay_digest, fresh_check_output)
# Continue with value/current; problem retains the original source and caps.
```

The API requires the completed restoration's original result/request digests and a matching trusted complete numerical replay receipt. It checks the complete returned-probe list, retention-history verification, immutable source bindings, archived methods, canonical final clip, original recipe and control population. All final clip bytes and complete contact/geometry/motion arrays are freshly reconstructed. Unverified, incomplete, mismatched or approval-bearing claims reject. Only the verified edited controls become the optimization starting point; source world transforms and all four original motion-cap arrays remain unchanged.

This is a Python continuation API. The actual research runner uses the existing public decoded evaluation and retention functions; a new Studio/CLI continuation selector is not claimed. Every old output, failed candidate and saved numerical replay remains intact.

## Actual continued development trial

The trial uses the same 372 active controls, native key interval, fixed root/endpoints/inactive keys, original 30-degree/22-cm bounds, raised-right-foot position target and 5-mm floor. The target is the earlier authored preservation example, not inferred ground support. Complete geometry still covers 2,017 times, 1,029 triangle-referenced vertices and 1,604 faces.

| Retained continuation step | Fraction | Rate failures | Floor failures |
| --- | ---: | ---: | ---: |
| Verified start | — | 47 | 18 |
| 1 | 1/8 | 41 | 17 |
| 2 | 1/8 | 40 | 15 |
| 3 | 1/8 | 35 | 12 |

The fourteen returned exports include larger rejected steps and a repeated final export. The final peak floor depth is 5.100925 mm, still above the unchanged 5-mm limit. Twelve rate rows and six floor samples are repaired relative to the verified start. Retention protects every previously passing condition and prevents increased individual violations. Thirty-five rate failures and twelve floor failures keep the candidate rejected and the original selected.

The continuation trial completes in 509.625 seconds/516 resource observations, including fresh validation of its saved starting state. Its resource trace replays with matching bindings. A separate fresh replay reconstructs all fourteen returned exports, exact complete observation arrays and every retention decision. It also compares all original rate-cap arrays with the previous restored state rather than deriving caps from the new clip. This replay passes in 320.234 seconds/331 resource observations, with its resource trace replayed. The final 35 rate failures, twelve floor failures and rejection remain exact. Shared curve/reader/skin methods remain explicit, and the optimizer is not rerun by that replay.

All five model-free continuation cases pass in 98.250 seconds/114 resource observations, with the recorded resource trace replayed. Tests verify exact saved-clip reconstruction, original initializer/cap identity and rejection of incomplete, mismatched, unverified or approval-bearing replay claims. No additional tests are inferred from the existing inventory count.

Local evidence remains under ignored `reports/native-key-continuation-validation-v1`, `reports/kenney-key-verified-continuation-v1` and `reports/kenney-key-verified-continuation-replay-v1`. Character payloads and bulky reports stay excluded from Git. The prior public workflow's hosted result and this new source's checks are separate from actual animation quality.

All fourteen release capabilities and calibration gates remain unchanged and unapproved. No generation, training, reserved held-out fixtures, engine execution, new human ratings or cleanup measurements occur here. Continuous collision, self-collision, balance, anatomy, semantic correctness, runtime/import fidelity and developer review remain separate work. The entire-project goal stays active while correction, general authoring integration and broader action/rig/style/object/partner/held-out evaluation continue.
