# Verified-read cache groundwork

The Studio shared-transition correction workflow repeatedly rebuilds its complete numerical source chain during review and export. In the ongoing generated fixture study, this replay takes substantially longer than the owned headless engine processes. The new cache helpers prepare reuse of an unchanged, completed manifest without changing the original numerical verifier. They are not connected to the Studio server or scene/game exporters in this revision.

## Reuse contract

`scripts/verified_read_cache.py` keeps at most eight process-local results, keyed by job and full-reader identity. Callers must declare every input and implementation file, and every directory whose population matters. SHA256 signatures cover bytes and complete directory populations, including empty directories; timestamps are not evidence. Each cold read and cache hit checks the complete signature before and after returning a deep-copied value. Detected changes during a read raise an error and do not return a stale value. Failed full readers are not cached.

The cache serializes reads for the same job/reader while allowing different jobs to proceed independently. Its limits are 65,536 paths and 2 GiB of hashed bytes. Missing, external, linked, unsupported or oversized dependencies use the full reader without a partial cache signature. This fallback preserves the original verifier's behavior; it does not add semantic approval or relax any numerical threshold.

`scripts/studio_transition_fit_read_cache.py` discovers the graph for completed jobs: the Studio folder, original shared scene transition, all actor transition/root-support folders, original input files, candidate correction, fit trials, continuation ancestors and current implementation. Parsed metadata is itself hash-bound, preventing a changed discovery header from supplying an incomplete signature. Unknown schemas, cycles, excessive graphs and incomplete jobs fall back to the unchanged full manifest.

## Evidence and remaining integration

The two new suites pass 37 cases with zero failures or skips: 21 cache integrity/concurrency cases and 16 graph/public-adapter cases. Coverage includes same-size changes with restored timestamps, added/removed files and empty directories, changed methods and ancestors, discovery races, changes during cold/hit reads, reader exceptions, independent caller copies, bounded entries, and concurrent reads. Adapter tests use explicitly fake metadata payloads and full-reader stubs; they provide no motion-quality evidence.

Local source receipt: `reports/verified-read-cache-source-v4/result.json`, SHA256 `d1a9f0ac6d4a53148abf28f08e3072b6e1eff7ac2cb42395c57a4362f9eefb95`. The checked source and test bytes still match that receipt. The GitHub source workflow now includes both suites; local passage does not imply hosted CI passage.

A read-only graph inspection of the actual generated bridge job found 306 explicit files, eight complete trees, 13 discovery headers and 5,050 signature entries. Two signatures agreed, taking about 3.66 and 4.33 seconds. These are dependency-signature timings, not measured cache-hit or production UI timings.

A separate read-only numerical cold/warm driver has been prepared under ignored reports. It requires the current owned scene/game study to finish before running. It will execute the original full manifest, compare complete typed warm values, test caller-copy isolation, retain failed contact/quality decisions and unconfirmed timing, and prove the original graph bytes are unchanged. That comparison remains pending. No server hook, live HTTP/browser check, production speedup, new engine/model run, human review or release approval is claimed here.

The next integration must preserve the full verifier on graph changes or ineligible jobs and validate actual transport behavior before claiming responsive Studio review. All project release evidence gates remain open.
