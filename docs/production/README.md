# Production tracking

Working files used day to day during production. Open the CSV in Excel, Numbers or Google Sheets (File → Import).

## asset-tracker.csv

Every asset needed for Episode 1: 50 visual assets, 38 sounds and 7 music cues, pre-filled from the Art Bible, the Beat Sheet and the Audio Design Document.

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
