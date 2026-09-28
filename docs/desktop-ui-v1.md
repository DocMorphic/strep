# Desktop OS interface — 2026-09-25

The user's `C:/me/code/os-folio` clone was clean on main. It was fast-forwarded from `9327c57` to `00b13d6f73b244963bf2798c14008bd75d6c7d91`; local HEAD equals origin/main and the checkout remains clean. No portfolio files were edited and no branch was pushed. This sync updates source files; it does not claim a fresh portfolio dependency install or build.

The strep studio at http://127.0.0.1:8768/studio now follows that repository's 2D desktop design: warm cream surfaces, orange wallpaper, brown borders, square window controls, desktop icons, a menu bar and dock. The 3D-world interface was not imported. The existing grey SOMA animation viewer lives inside Preview.

## Working apps

- New motion: arbitrary action descriptions and timed steps, persistent unfinished draft, seeds, real local generation.
- My animations: searchable clips from the current collection, with review flags and click-to-preview.
- Preview: collection/take selection, playback, scrub, camera views, request reuse and file downloads.
- Inspector: motion/contact/transition measurements and a full-body floor audit for the fourteen coverage takes.
- Activity: actual local pipeline status and available outputs.
- Settings: light/dark theme, four accent colors, window arrangement and saved browser preferences.
- readme.txt: use guide and current capability limits.

Windows support dragging, resizing, focus, minimize, maximize/restore, close and reopening from the dock. Window positions, visibility and theme persist. Narrow layouts constrain windows to the viewport. The generation worker, API and animation artifacts remain the existing implementation. No scripts or models from os-folio's 3D environment were imported.

## Source layout

`build_desktop.py` bundles `desktop-shell.html`, `desktop-shell.css`, `desktop-shell.js` and `action-studio-engine.js` into the served `action-studio.html`. Rebuild after editing those sources:

```powershell
.venv\Scripts\python.exe scripts/build_desktop.py
node --check scripts/desktop-shell.js
node --check scripts/action-studio-engine.js
```

The previous studio page and engine are preserved in `reports/desktop-ui-v1`. The local server requires no restart for rebuilt HTML. It still runs with `scripts/action_studio_server.py` on port 8768.

## Verification

69 project tests pass, with four existing upstream Torch deprecation warnings. Browser checks exercised the window controls, drag/resize, library search/selection, editing, theme persistence, draft recovery, playback and final-frame visibility. No console warnings/errors were observed. A fresh Balance study request was submitted through the desktop; it completed encoding, generation and export at `reports/action-jobs/20260925-184620-15dd1b9d`, and its GLB validates with zero errors/warnings. This proves execution and export, not semantic correctness or balance realism.

## Contact work continued

`audit_body_ground.py` measures every vertex of the actual SOMA body in every frame of all fourteen coverage takes, using all eight skin weights and the preview's Y=0 floor. It preserves source hashes and writes a separate `ground-audit.json`. It does not correct motion or update old scores silently.

Maximum surface penetration spans about 0.8–14.0 cm. The deepest locations in crawling, getting up and rolling are hand/finger regions (dominant skin weights provide approximate region labels). All fourteen worst-frame results were independently checked against decoded GLB world transforms and exported inverse bind matrices; maximum discrepancy is 2.71e-7 m. Inspector displays these results and can jump to the deepest frame. Other collections explicitly report that this surface audit is unavailable, rather than borrowing coverage measurements.

The next correction study should address hand/arm/finger contact, preserve limb lengths and timing, and check that penetration improvements do not worsen sliding, floating or motion. A universal upward shift is not established as a solution. No corrected or animator-approved motion is claimed in this milestone.
