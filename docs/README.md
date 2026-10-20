# Documentation — Boon Sop: The Unbroken Debt

All design documents for the game. **Read the PDFs** in [`pdf/`](pdf/). Edit the HTML sources in [`src/`](src/) and rebuild.

## Document set

| No. | Document | What it covers |
|---|---|---|
| 00 | [Project Proposal](pdf/00-Project-Proposal.pdf) | Vision, pillars, story, episode roadmap, gameplay, culture, technology, production plan, risks |
| 01 | [Episode 1 · The House of Mourning](pdf/01-Episode-1-The-House-of-Mourning.pdf) | Battambang stilt house: funeral vigil, resource management, Seal #1 |
| 02 | [Episode 2 · The Whispering Pagoda](pdf/02-Episode-2-The-Whispering-Pagoda.pdf) | Pagoda on Pchum Ben: sound stealth, Pret, Seal #2 |
| 03 | [Episode 3 · The Drowned Village](pdf/03-Episode-3-The-Drowned-Village.pdf) | Flooded Tonle Sap clinic: water and warmth, Seal #3 |
| 04 | [Episode 4 · The Rubber Plantation](pdf/04-Episode-4-The-Rubber-Plantation.pdf) | Kampong Cham estate: fog navigation, voice-mimic taboo, Seal #4 |
| 05 | [Episode 5 · The Sunken Sanctuary](pdf/05-Episode-5-The-Sunken-Sanctuary.pdf) | Phnom Kulen: elemental trials, severance ritual, endings |
| 06 | [Development Plan](pdf/06-Development-Plan.pdf) | Roadmap, architecture, game systems, assets, resources, open questions |
| 07 | [Story Bible](pdf/07-Story-Bible.pdf) | Theme, rules of the debt, character arcs, structure, timeline |
| 08 | [Episode 1 Beat Sheet and Level Layout](pdf/08-Episode-1-Beat-Sheet-and-Level-Layout.pdf) | Every beat, trigger, item and patrol, with scaled maps |
| 09 | [Art Bible](pdf/09-Art-Bible.pdf) | Palettes, lighting, post-processing, scale, materials, costume, creatures, sensitivity rules |
| 10 | [Episode 1 Script and Text](pdf/10-Episode-1-Script.pdf) | All dialogue, Sok's recording, journal pages, lore notes, sketchbook text |
| 11 | [Technical Design Document](pdf/11-Technical-Design-Document.pdf) | Modules, events, data formats, Blender conventions, saves, AI, rendering, audio, deployment |
| 12 | [Controls and Interface](pdf/12-Controls-and-Interface.pdf) | Bindings, satchel and sketchbook UX, feedback without a HUD, menus, settings, accessibility |

Documents 08–12 are the **Phase 0 production documents** used to build Episode 1. Every episode document follows the same structure: overview, characters, locations, acts, mechanics, puzzles, entities, items, audio/visual, glossary, and revision notes with open issues.

## Folder layout

```
docs/
├── pdf/            Generated PDFs (read these)
├── src/            HTML sources + shared style.css (edit these)
│   └── fonts/      Ubuntu (English) and Preah Vihear (Khmer), with licences
└── archive/v1/     Original v1.0 documents, kept for reference
```

## Rebuilding the PDFs

Requires Google Chrome. From the repository root:

```bash
tools/build-docs.sh
```

To rebuild one document, pass its source name, for example `tools/build-docs.sh 01-episode-1`.

## Typography

- **English:** Ubuntu (Ubuntu Font Licence, `src/fonts/UFL.txt`)
- **Khmer:** Preah Vihear (SIL Open Font License, `src/fonts/OFL.txt`)
- **Diagrams and code:** Ubuntu Mono

Khmer text is wrapped in `<span class="km">` so it gets Khmer line spacing. All Khmer spellings should be checked by a native speaker; each episode's glossary lists terms to confirm.
