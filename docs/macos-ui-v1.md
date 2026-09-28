# macOS-style desktop — 2026-09-25

The studio at http://127.0.0.1:8768/studio now targets the appearance of **macOS Tahoe 26**, replacing the earlier os-folio cream/orange theme. The portfolio sync remains completed; this change only affects strep.

## Reference and fidelity

Apple's [Tahoe announcement](https://www.apple.com/newsroom/2025/06/macos-tahoe-26-makes-the-mac-more-capable-productive-and-intelligent-than-ever/) describes the transparent menu bar and glass Dock/toolbars. Its [Apple Music screenshot](https://www.apple.com/newsroom/images/2025/06/macos-tahoe-26-makes-the-mac-more-capable-productive-and-intelligent-than-ever/article/Apple-WWDC25-macOS-Tahoe-26-Apple-Music-250609_big.jpg.large.jpg) was inspected visually for window hierarchy, traffic lights, rounded chrome, Dock spacing and opaque content surfaces.

Implemented: transparent top menu, small left-side traffic lights, soft window shadows, translucent toolbars, floating glass Dock with squircle icons, hover enlargement, open-window dots, right-aligned desktop icons, light/dark appearance, blue default accent, reduced transparency and reduced motion. Desktop icons select on click and open on double-click or keyboard activation. Dock clicks open or focus an app, without hiding an already focused preview.

This is a browser interpretation, **not native or pixel-identical macOS**. CSS blur/saturation/highlights approximate glass; native optical refraction, system fonts on Windows, OS menus and fullscreen/window tiling are not reproduced exactly. Measurements (28px menu, 12px traffic lights, 48px title bar, 51px Dock icons) are implementation choices inferred from the reference, not published Apple specifications. The wallpaper and app icons are original vectors; no Apple font or artwork is bundled. Green zoom fills the web desktop while keeping the Dock available.

## Implementation and preservation

Edit `scripts/desktop-shell.html`, `.css` and `.js`, then run `.venv/Scripts/python.exe scripts/build_desktop.py`. The animation engine and server are unchanged. Preference key `strep:desktop:macos-v1` avoids carrying the old orange theme forward; the existing motion draft key is retained. Pre-change UI files are in `reports/macos-ui-v1/`.

## Verification

Browser checks: light/dark rendering, persisted accessibility preferences, collection loading, library search and selection, final-frame SOMA visibility, minimize/reopen, repeated Dock focus, zoom/restore, titlebar drag, corner resize and preserved composer draft. Existing project suite: `python -m pytest tests -q`, **69 passed**, four upstream Torch deprecation warnings. Initial unscoped pytest discovery collected archived report snapshots and vendor tests and failed collection; using the project test directory avoids those unrelated collections.

No model generation or training was repeated for this visual change. No new claim about animation realism or contact quality.
