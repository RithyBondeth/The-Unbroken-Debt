# 5. Open Questions and Design Gaps

These came from reading the proposal and all five episode documents together. **When** says by which point each one must be decided.

## 5.1 Story and continuity

| # | Issue | When | Suggested resolution |
|---|---|---|---|
| Q1 | **The Silver Betel Box is never destroyed or cleansed.** Episodes 1, 3 and 4 end with a counter-ritual on the seal; Episode 2 only retrieves the box, yet Episode 5 calls all four "destroyed" and needs a "Silver Betel Box inlay" | Before Ep2 | Add a short ritual at the end of Ep2, for example offering the box back at the family stupa at dawn so the silver inlay comes loose |
| Q2 | **Two versions of the pact.** Ep2's flashback shows an offering to a woodland spirit at a stone altar; Ep4 says a blood contract was signed at the rubber estate | Before Ep1 (it's mentioned in Sok's journal) | One event: the great-grandfather made the offering at an ancient Neak Ta shrine *on estate land*, and the estate ledger recorded the "contract". Both scenes stay true |
| Q3 | **Historical date of the estate.** Large Cambodian rubber plantations mostly date from the 1920s; a functioning estate in Kampong Cham in 1910 is early | Before Ep1 | Either move the pact to the early 1920s (Sok could still be the one who tried to break it in 1928–31) or make the 1910 site the jungle shrine that *later* became the estate. Check with a historian |
| Q4 | **Sora's parents are missing.** "Four generations" makes Sora the last, but her parents are never mentioned. Yay Mey's place in the bloodline is unclear | Before Ep1 | Decide: are Sora's parents dead (taken by the curse?), and is Yay Mey the great-grandfather's daughter or a daughter-in-law? This can become a strong emotional thread |
| Q5 | **The clinic timeline.** Abandoned since 1920, the spirit drowned "decades ago", Sok photographed there in 1925 | Before Ep3 | Spirit drowned in 1920 (12 years earlier, so change "decades"); Sok used the abandoned clinic as a hiding place afterwards |
| Q6 | **The time between episodes.** Each episode ends around dawn and the next starts around midnight in a far-away province | Before Ep2 | State it: each episode is a following night, shown in a sketchbook entry ("Second night — Battambang pagoda") |
| Q7 | **Time mismatches in the docs.** Ep3: header 2:00–5:30 AM vs arrival 1:30 AM. Ep4: header ends 3:30 AM vs ending at 4:00 AM. Ep1: ritual deadline 3:00 AM, sunrise at 4:00 AM (sunrise in Cambodia is around 5:30–6:00 AM) | Before each episode | Fix the headers; change "sunlight" at 4 AM to "first grey light" or move it later |
| Q8 | **Ep1's map "shows four other locations"**, but later episodes depend on blood clues to reveal each place | Before Ep1 | The map shows four faint, unreadable marks; each blood line reveals one. Keeps the mystery |

## 5.2 Gameplay

| # | Issue | When | Suggested resolution |
|---|---|---|---|
| G1 | **No fail state defined.** What happens when an entity catches Sora? | Before Ep1 greybox | See [03-game-systems.md](03-game-systems.md) section 3.2: scare → checkpoint restart, no health bar |
| G2 | **Ending conditions are not tracked anywhere.** Taboos, hidden lore notes and "key lore choices" are never defined in Eps 1–4 | Before Ep1 | Define the counters now (section 3.3) and place 5–8 hidden lore notes per episode. Add 1–2 meaningful choices per episode |
| G3 | **Save model.** Checkpoints only, or also manual saves? | Before Ep1 | Checkpoints only (recommended for tension) |
| G4 | **Difficulty.** One difficulty, or a "story" mode with weaker entities? | Before Ep1 release | A story mode helps players who come for the culture and story |
| G5 | **Ep4 "hand-crank lantern"** that burns oil is unclear | Before Ep4 | Either an oil lantern (as in Eps 1–3) or a separate hand-crank light; pick one |
| G6 | **Fixed "kerosene spotlights" on walls (Ep3)** are unusual for 1932 | Before Ep3 | Large carbide or kerosene pressure lamps (period-appropriate) |
| G7 | **Ep5 Wind trial uses Pret**, who were tied to Pchum Ben in Ep2 | Before Ep5 | Fine as a callback; mention in the sketchbook why they are here |

## 5.3 Presentation and culture

| # | Issue | When | Suggested resolution |
|---|---|---|---|
| C1 | **Neak Ta as the antagonist.** Neak Ta are normally respected protectors | Before Ep1 | Frame it as a guardian enforcing a contract the family broke or abused, not as evil. The good ending (it bows and dissolves) already supports this |
| C2 | **Khmer terms need checking** (examples: "Mukhalingi" mask in Ep5, "Hup Mak" betel box in Ep2, "Mneang Sop" coffin in Ep1) | Before each episode | Native speaker review; keep a glossary file |
| C3 | **Sora's job title.** "Graphic designer" is a modern term | Before Ep1 | "Illustrator" or "commercial artist", which fits 1932 Phnom Penh |
| C4 | **Language of voices and text** | Before Ep1 | Recommended: Khmer voices, English and Khmer text |
| C5 | **The blood sacrifice in Ep5** (pricking her own finger) | Before Ep5 | Check with the advisor; keep it restrained |
| C6 | **Khmer text in the PDFs does not extract** (font embedding) | Now | Keep the Khmer titles and names in a plain-text glossary so they aren't lost |

## 5.4 Business and platform

| # | Question | When |
|---|---|---|
| B1 | Is Episode 1 free, pay-what-you-want, or paid? | Before Ep1 release |
| B2 | Where to publish: itch.io, your own site, both? (A browser game on itch.io is the easiest start.) | Before Ep1 release |
| B3 | Does the README's "Safari supported" claim hold on older macOS? (WebGL2 fallback, yes; WebGPU needs macOS 26+) | Spike S8 |
| B4 | Licence: the README says MIT. Do you want **code** open source but **art, story and audio** all rights reserved? MIT on everything lets anyone reuse your story and assets | Before the first public commit of assets |
