# Strep project instructions

Build toward the single project-wide goal in `docs/project-goal.md` and the release matrix in `benchmarks/project-release-v1.json`. Action families are evaluation categories, not a prompt whitelist. Keep measured failures visible and never infer release approval from successful export alone.

## GitHub workflow

The owner explicitly requested a public `DocMorphic/strep` repository and ongoing commits. After each coherent, validated change, commit the relevant source/documentation and push to `origin` on the current working branch. This authorization persists; do not ask again for routine commits and pushes. Avoid force pushes, history rewrites, or unrelated changes. Report a push failure honestly and retain the local commit.

Before staging, inspect the diff and excluded files. Never commit tokens, credentials, `.env` files, model weights, downloaded character payloads, dependency caches, personal machine reports, blind-review answer keys, or bulky generated study outputs. Keep generated outputs locally under ignored `reports/` and `runs/`; publish concise source-controlled methodology and result summaries with scope and limitations. Do not force-add ignored artifacts without an explicit reason and review.

Run checks appropriate to the changed behavior, document meaningful outcomes, and avoid rerunning completed expensive studies just to make a commit. Keep raw results immutable. Do not modify source imported by a running study worker; finish or otherwise account for that worker first.

The repository is a development source snapshot, not a fully bundled offline installer. Acquisition/setup limitations must stay explicit. Third-party models, code and assets retain their own terms; public visibility does not change those terms.
