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

Bone `--ui-text` sits on charcoal green `--ui-bg` or `--ui-surface`. Secondary copy uses `--ui-muted` or `--ui-subtle`; it should remain readable instead of being faded with opacity. Muted red `--ui-accent` marks selection and small rules. Use `--ui-accent-bright` for readable text accents on dark surfaces.

Transcripts, the notebook reader and ending documents use `--ui-paper` with `--ui-ink`, `--ui-paper-muted` and `--ui-paper-accent`. The shared rules remap control tokens locally so the same button pattern works on paper. Warm paper remains a meaningful document surface; it is not another UI theme.

## Controls and placement

All standard actions share a 44px minimum height, a fine border, a 3px radius, medium Ubuntu text, visible keyboard focus and restrained hover/pressed feedback. `setControlText()` renders control names as `<kbd>` elements while preserving the localized label and accessible text. Use it for hints and action labels, not prose quotations.

Dialogue is bottom centre with a separate speaker label and a dark backing. It never hides words with a line clamp. Existing timed subtitle chunking and cancellation remain unchanged. Control hints sit above dialogue. Stealth guidance sits near the top to avoid colliding with either. Save status sits at the top right. Layouts respect viewport gutters and safe-area insets, and panels scroll when content exceeds available height.

Use `--ui-space-*` for repeated spacing, `--ui-safe-*` for screen edges and named `--ui-z-*` layers. Do not place a permanent dashboard over gameplay. Developer performance and verification overlays are outside this system.

## Motion and accessibility

Use `--ui-motion-fast` for controls and `--ui-motion-fade` for brief departures. Animate transforms and opacity, not layout dimensions. Reduced-motion preferences zero these shared durations; the entry gate also skips its departure delay. Black scene fades remain black for story transitions.

Focus, text selection and scrollbars belong to the palette. Use tabular numerals for page counts. Preserve existing keyboard bindings, localization, dialogue timing and save behavior.

## Review

Open `/tests/browser/text-system.html` during development. It uses production components without graphics initialization or writes to player saves. Views cover gameplay, stealth, story titles, the satchel, transcripts, notebook, ending, caught text, entry, main menu, requirements and load errors. Add `&clean` for captures without the fixture navigation. The background is title artwork used only to demonstrate contrast; it is not a gameplay screenshot.
