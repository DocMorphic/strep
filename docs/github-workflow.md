# Public source repository

Strep's public repository is intended to hold implementation, tests, benchmark specifications, rig profiles, provenance metadata, and research documentation. Local model weights, third-party asset payloads, environments, generated clips, detailed study outputs, credentials, machine reports, and blind-review keys remain outside Git.

Some historical documents reference ignored local files and localhost viewers. Those links describe the original development workspace; a fresh clone does not contain the corresponding artifacts. Source hashes in those documents are historical evidence bindings, not a promise that the referenced output is distributed here. `.gitattributes` preserves file bytes to avoid rewriting sources whose hashes were recorded during experiments.

## Ongoing changes

After a coherent change and its relevant checks, review `git diff` and `git status`, stage the intended files, make a descriptive commit, and push to the configured upstream. The owner has authorized routine commits and pushes during continued development. Do not use an unattended timer to snapshot unfinished files or force-push over remote changes. If a push fails, keep the local work and resolve the concrete problem before reporting publication as complete.

Record numerical and human-review results separately. A failing animation experiment can still produce a useful commit containing its implementation and an honest failure summary. Model quality is never implied by the existence of a public repository or a passing software test.
