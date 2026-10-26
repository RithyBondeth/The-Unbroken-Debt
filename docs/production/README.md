# Production tracking

Working files used day to day during production. Open the CSV in Excel, Numbers or Google Sheets (File → Import).

## asset-tracker.csv

Every asset needed for Episode 1: 50 visual assets, 38 sounds and 7 music cues, pre-filled from the Art Bible, the Beat Sheet and the Audio Design Document. Two early Episode 3 rows (Pich) are included for planning.

| Column | How to use it |
|---|---|
| ID | `V1-###` visual, `S1-###` sound, `M1-##` music. Never reuse an ID. |
| Source | `C` custom (Blender), `L` library, `K` kitbash, `R` record yourself, `D` designed sound, `M` musicians |
| Priority | Critical / High / Medium / Low. Critical and High are needed for the greybox or core experience. |
| Status | `Not started` → `In progress` → `Review` → `Done`. Use `Blocked` with a note when waiting on someone. |
| Budget | Triangle or size budget from the Art Bible |
| Library / URL, Author, Licence, Credit required | **Fill these in for every third-party asset the moment you download it.** This column becomes the game's credits list. |

Rules:
- One row per asset; add rows as new assets appear.
- An asset is `Done` only when it passes the Art Bible approval checklist (section 12) and its licence is recorded.
- Before release, every row with a library source must have a licence and author.

## credits.md

Generated from the tracker by `npm run credits`: every third-party asset in use, grouped by author and licence, plus the software packages and a list of release blockers (assets in use whose licence is missing, unknown or unclear, or whose notes say `RELEASE BLOCKER`). Run it after editing the tracker; `npm run credits -- --strict` exits with an error while any blocker remains, for the release check.

## khmer-strings-review.csv

Every interface string with its Khmer draft (`src/data/strings/km.json`), for a native speaker to review. The draft was written by AI from the Cultural Guide's glossary; nothing in it is approved. Fill in the reviewer columns, then copy corrections into `km.json` and set Status to `Approved`. Until then the Khmer table only appears in development builds with `?lang=km`, falling back to English for anything missing. Dialogue, subtitles and sketchbook pages live in `src/episodes/ep1/data/` and are not yet in the string tables.
