# macOS interaction study and desktop implementation

Reference target: **macOS Tahoe 26**, checked 2026-09-25. This replaces the earlier appearance-only shell. The user's correction about Control Center was valid: the initial enclosing settings card did not match Tahoe. It was discarded.

## Visual reference, actually inspected

Apple's [Mac Pro Essentials, Tahoe Control Center page](https://support.apple.com/en-ie/guide/mac-pro/apdc362a41b2/2025/mac/26) includes this [full-size Control Center reference](https://help.apple.com/assets/68AF4A4B86D71687240E66F4/68AF4A57E7E8EB927003A877/en_US/494205cbad6a30f1a69c2d66bbc9acfb.png). Viewed directly in the browser. The key geometry is a four-column arrangement of independently floating glass modules, without an enclosing card: a two-column Wi-Fi pill, two-row media tile, round connectivity buttons, Focus pill, two circular window controls, wide Display and Sound sliders, four utility circles and Edit Controls below. `control-center.html` and `.css` now implement that arrangement. Dimensions and timing are estimated web equivalents, not Apple specifications. Glass tint is adjusted for legibility when controls overlap white content.

## Behavior sources and implementation

| Primary source | Implemented behavior |
|---|---|
| [Desktop & Dock settings](https://support.apple.com/en-nz/guide/mac-help/mchlp1119/26/mac/26) | Pointer-distance Dock magnification, size preference, automatic hiding, running indicators, launch bounce, minimized thumbnails. Uses a scale-to-Dock animation, with reduced-motion support. |
| [Move and arrange windows](https://support.apple.com/lv-lv/guide/mac-help/mchlp2469/mac) | Separate close/minimize/quit UI states; close retains the running indicator. Dragging, eight resize edges, double-click title-bar fill, app switcher and restored geometry. Quitting a workspace panel does not kill a generation job. |
| [Fullscreen](https://support.apple.com/en-kg/guide/mac-help/mchl9c21d2be/26/mac/26) | Green control enters workspace fullscreen; menu and Dock recede and can be revealed at screen edges. Escape exits. Fill remains a separate operation. |
| [Tiling](https://support.apple.com/ur-in/guide/mac-help/mchlef287e5d/mac) | Hover/right-click/keyboard on green opens window options; halves, center, fill and restore; edge-drag highlights and tiles. |
| [Mission Control](https://support.apple.com/en-by/guide/mac-help/mchlb7beb9af/26/mac/26) | Animated live-window overview, selection, desktop spaces, creation/removal and dragging a window to another space. Wallpaper click reveals/restores windows. |
| [Spotlight](https://support.apple.com/en-ph/guide/mac-help/mchlp1008/mac) | Search applications, current-collection motions and desktop actions; filters and arrow/Enter selection. |

Additional workspace features: Stage Manager with window thumbnails; calendar and real job activity from the existing API; library collection sidebar and icon/list views. Control Center playback, next clip, restart, appearance, Stage Manager, workspace brightness, preview PNG capture, calculator and stopwatch are functional. Focus reduces workspace distractions.

## Scope and explicit differences

This is a browser desktop, **not macOS or a complete macOS emulator**. It does not provide Apple services, Finder access to the computer's filesystem, real OS processes, hardware controls, system trackpad gestures, native fullscreen Spaces, native app grouping, true Split View, native Genie distortion or Apple's Liquid Glass renderer. There are seven existing workspace apps; they are not replacements for Apple's bundled apps. Stage Manager supports individual windows, not arbitrary grouped sets. The library still opens clips on a single click.

Wi-Fi, Bluetooth, AirDrop and mirroring preserve the reference's visual placements but open explanatory system-control panels; no connection state is fabricated. Sound is disabled because motion assets have no audio. Display affects this workspace, not monitor hardware. Edit Controls edits working workspace preferences; arbitrary native Control Center module rearrangement is not implemented. Screenshot saves the animation canvas, not the whole operating-system screen.

Windows/browser-reserved shortcuts cannot be captured reliably. Visible menus always work. Local alternatives: Ctrl+Alt+Space for Spotlight, Ctrl+Alt+Tab for app switching, Ctrl+Up for overview, Ctrl+Alt+M minimize, Ctrl+Alt+F fullscreen, Ctrl+Alt+D desktop, Ctrl+Alt+Left/Right tiling, Escape back. Command shortcuts also work when delivered to the page.

## Source and build

`build_desktop.py` bundles `desktop-shell.html/css/js`, `desktop-window-manager.js`, `desktop-interactions.css`, `control-center.html/css/js` and the unchanged `action-studio-engine.js`. Rebuild with `.venv/Scripts/python.exe scripts/build_desktop.py`. The local server does not need restarting. Preference key: `strep:desktop:macos-v2`, migrated from v1. Motion drafts remain on their original key. Pre-change files are in `reports/macos-interactions-v2/`.

## Verification

Browser checks cover: Spotlight filtering/keyboard selection, actual clip selection, minimize thumbnail and restore, Mission Control, adding/removing spaces, fullscreen and Escape, Control Center media playback and calculator (7 × 8 = 56), Stage Manager, and preserved composer draft. Source syntax and template/ID checks pass. The animation engine hash is unchanged. Existing project tests: 69 passed, four upstream Torch deprecation warnings. No new generation or training was needed for this UI work. This is not a pixel-diff certification against native macOS; behavior and visual gaps are recorded above.
