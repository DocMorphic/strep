# Personal installations inside the project

The offline builder previously required every destination to be outside the
development project. That conflicted with the requested layout keeping Strep
work inside its project folder. Local personal installations can now be created
under `.local/installations/<name>`, which is ignored by Git and excluded from
the captured project source directories.

The builder and source copier share destination validation. They reject the
source root, its ancestors, other nested project locations, overlap with any
declared copied source directory, and a local path that resolves outside the
project. A custom snapshot cannot read files from its own installation output.
Existing installations are preserved. Explicit external destinations remain
supported for portability tests, but local development uses the project-owned
directory.

Missing parent directories are created only after the existing free-space
check passes. The check uses the nearest existing ancestor, so a new
`.local/installations` directory does not cause an unrelated missing-path error.
The 40 GiB requirement remains unchanged: relocating a copy within the project
does not reduce the amount of data copied.

All 22 focused source-snapshot and builder tests pass, including 12 new cases.
Tiny runtime/vendor fixtures exercise the complete builder under a destination
containing spaces and confirm all source/inventory hashes. Tests also cover
recursive-copy rejection, unchanged source inventories after nested copies,
preservation of local archive content and existing installs, and no directory
creation when space is insufficient. Both suites are now registered in the full
source CI inventory. The inventory check found they were previously absent; no
new hosted CI pass is claimed.

No real model weights, new full installation, server or inference job was
created by this verification. This validates layout and copy integrity, not
offline release readiness or redistribution rights. The existing source and
vendor checks, runtime isolation, licenses and model acquisition requirements
remain in force.
