# The Unbroken Debt — screen text

The screen interface extends the approved “Listen closely” entry screen. Its job is to stay quiet during play and remain readable over rain, darkness and lamplight. The title artwork and 1932 Cambodian setting remain the visual authority.

The implementation lives in `src/ui/html/design-system.css`, imported by `base.css`. Component styles consume its `--ui-*` variables. Use these tokens instead of introducing another palette, font, button treatment or spacing scale.

## Typography roles

| Role     | Token           | Use                                             |
| -------- | --------------- | ----------------------------------------------- |
| Display  | `--ui-display`  | Entry, episode titles, death/retry cards        |
| Heading  | `--ui-heading`  | Dialogs, satchel, document and notebook titles  |
| Section  | `--ui-section`  | Headings within notebook content                |
| Reading  | `--ui-reading`  | Documents and supporting story text             |
| Body     | `--ui-body`     | Gameplay instructions, settings, objectives     |
| Subtitle | `--ui-subtitle` | Spoken dialogue; speaker name uses caption size |
| Small    | `--ui-small`    | Buttons and secondary notes                     |
| Caption  | `--ui-caption`  | Page counts, save status, metadata              |

`--ui-font-display` uses the approved Georgia serif with a Preah Vihear fallback for Khmer. `--ui-font-body` uses locally bundled Ubuntu and Preah Vihear. Regular, medium and bold Ubuntu fonts use swap loading. No additional fonts or network requests are needed. Use balanced headings and roughly 60–65-character reading measures. Reading panels use 1.65 line height; dialogue uses 1.5. Keep Khmer title lines spacious.

Patrick Hand and Freehand are reserved for Sora’s physical, canvas-rendered sketchbook. The optional “Read clearly” panel uses the screen system.

## Color and surfaces

Bone `--ui-text` sits on warm near-black `--ui-bg` (`rgb(11 10 9)`) or warm charcoal `--ui-surface` (`#181613`). Hover states use `--ui-surface-hover` (`#28241f`); borders, secondary copy and focus rings use warm ash tones. Secondary copy uses `--ui-muted` or `--ui-subtle`; it should remain readable instead of being faded with opacity. Muted rust `--ui-accent` marks selection and small rules. Use `--ui-accent-bright` for readable text accents on dark surfaces.

Welcome, entry, dialogs, inventory and error panels share this palette. Welcome artwork, lamplight and entry decoration retain their atmosphere, while text, controls and focus states consume the shared tokens. Use `--ui-hud-bg` for hints and save status, `--ui-overlay-bg` for subtitles, stealth guidance and caught screens, and `--ui-backdrop` for modal dimming. These translucent surfaces derive from `--ui-bg-rgb`, so they remain in the same charcoal family. Avoid hardcoded green or cool-black panel backgrounds.

Transcripts, the notebook reader and ending documents use `--ui-paper` with `--ui-ink`, `--ui-paper-muted` and `--ui-paper-accent`. The shared rules remap control tokens locally so the same button pattern works on paper. Warm paper remains a meaningful document surface; it is not another UI theme.

## Controls and placement

All standard actions share a 44px minimum height, a fine border, a 3px radius, medium Ubuntu text, visible keyboard focus and restrained hover/pressed feedback. `setControlText()` renders control names as `<kbd>` elements while preserving the localized label and accessible text. Use it for hints and action labels, not prose quotations.

Dialogue is bottom centre with a separate speaker label and a dark backing. It never hides words with a line clamp. Existing timed subtitle chunking and cancellation remain unchanged. Control hints sit above dialogue. Stealth guidance sits near the top to avoid colliding with either. Save status sits at the top right. Layouts respect viewport gutters and safe-area insets, and panels scroll when content exceeds available height.

Use `--ui-space-*` for repeated spacing, `--ui-safe-*` for screen edges and named `--ui-z-*` layers. Do not place a permanent dashboard over gameplay. Developer performance and verification overlays are outside this system.

Document dialogs use a centred paper panel over `--ui-backdrop`. The reading area scrolls independently so the footer stays visible. Preserve paragraph breaks, use the paper accent for Next/Finish, and keep supporting actions quiet. Hide pagination for single-page notes; disable Previous on the first page of longer documents. Keyboard focus skips unavailable actions and includes the reading area when it overflows.

Settings, How to play, Credits and the new-game confirmation use the shared dark surface. The notebook and ending panels use the same paper treatment as document dialogs. All use `--ui-panel-padding`, the shared border/radius/shadow, and `--ui-backdrop` for modal dimming. Their content scrolls independently of the action row, including at short landscape heights. Use `ui-button ui-button-primary` for the main action; its colors automatically follow the enclosing dark or paper surface. Notebook section selection uses that same accent treatment. Supporting actions use standard buttons. Keep focus within dialogs and allow keyboard scrolling of overflowing content; Escape closes dismissible readers and menu dialogs, while ending choices retain their required story actions.

Requirements, loading errors and rendering warnings share the dark panel styling and readable overflow. The satchel and ordinary story cards use the shared primary action. The listening threshold and title menu retain their authored presentation; they are not standard dialog variants. Maps and physical sketchbook illustrations retain their own drawing colors.

## Motion and accessibility

Use `--ui-motion-fast` for controls and `--ui-motion-fade` for brief departures. Animate transforms and opacity, not layout dimensions. Reduced-motion preferences zero these shared durations; the entry gate also skips its departure delay. Black scene fades remain black for story transitions.

Focus, text selection and scrollbars belong to the palette. Use tabular numerals for page counts. Preserve existing keyboard bindings, localization, dialogue timing and save behavior.

## Review

Open `/tests/browser/text-system.html` during development. It uses production components without graphics initialization or writes to player saves. Views cover gameplay, stealth, story titles, the satchel, transcripts, notebook, ending, caught text, entry, main menu, requirements and load errors. Add `&clean` for captures without the fixture navigation. The background is title artwork used only to demonstrate contrast; it is not a gameplay screenshot.

Use `?view=document&note=arrival&clean` to review Mak Yey’s actual note, including the single-page controls and long-text layout. The default document sample has two pages for checking navigation and disabled states.

Use `?view=menu&saved&clean` for the new-game confirmation with a simulated saved game. The menu preview supplies an in-memory save reader, so it never reads or replaces player saves. Settings, How to play and Credits open from the menu. Ending variants use `view=ending`, `view=map`, `view=summary` and `view=choice`; `view=stall` previews the rendering warning. Review at desktop, 320 × 568, and 844 × 390, checking that actions stay visible, text remains scrollable, keyboard focus stays inside, and controls retain their 44px minimum height.
