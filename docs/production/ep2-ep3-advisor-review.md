# Episodes 2 and 3: cultural-advisor review

Everything in these two episodes that needs a cultural advisor or native Khmer speaker to approve. It was collected from the flags in the code and production documents. None of it has been reviewed yet.

For each item, mark **OK**, **Change** (say what) or **Remove**. Items marked **Decide first** could change what the game can show at all.

## Decide first

| # | Episode | Item | Question |
|---|---|---|---|
| 1 | 2 | Portraits on the stupas: real, unnamed people from Léon Busy's 1921 photographs (Albert Kahn Museum, CC0), including children. Some have their eyes or whole face scratched away. | Is it acceptable to use real people's portraits as funeral photographs, and to deface them for horror? |
| 2 | 2 | The Khmer goddess scan (Prajnaparamita) stands at the gate as a weathered guardian, and one of the pair has lost its head. | Is this acceptable treatment of the image? Is it appropriate at a wat gate? |
| 3 | 2 | Buddha images: beheaded, worn-faced and draped, on the image terrace and in the cloister. | Are headless and defaced Buddha images acceptable in a horror setting, and where is the line? |
| 4 | 2 | The skull altar and other sorcery dressing (`tools/areas/pagoda_rituals.py`). The code treats these as sorcery, not temple practice. | Will players read that distinction correctly? |
| 5 | 2 | Opened ash urns, with ash and bone spilt down the stupa plinth. | Is this acceptable? |

## Episode 2: The Whispering Pagoda

### Ghosts
- The starved corpse ghost (kmaoch): its white funeral cloth, and the white cotton thread at its wrists and ankles.
- The woman in red still looks like a kuntilanak, an Indonesian and Malay ghost, in a Khmer setting. Should a Khmer spirit replace her?

### Stupas and the compound
- The family ash stupas: their forms, and the cloth tied round them in white, saffron and red.
- Red cotton cord (sai sin) wound thickly round stupas, with paper tags knotted in. It is deliberately overdone, as if by someone afraid.
- Incense, candles and dead garlands left at stupas.
- Placement and dressing of the image terrace, cloister images, spirit houses, sema boundary stones and gate guardians.
- The naga balustrades at the gate.

### The hall
- The altar: a painted-plaster Buddha in saffron, calling the earth to witness, on a red lotus throne, with gilded bodhi trees, small images and old offerings.
- The doorway barrier: rusted chains, a white cotton cord and an inked yantra-style cloth (abstract geometry only).
- The elderly monk: how he looks, sits and is addressed.

### Practice and sound
- The questions already raised in `docs/pdf/14-Cultural-Guide-and-Glossary.pdf`: offerings, the dawn gesture, bell sequencing and how monks are addressed.
- The monks' chant is synthesized as a stand-in for a recorded smot, and it has a corrupted double. Is the stand-in acceptable, and what should the final recording be?
- The Pali formulas written in Khmer on props, listed in the `KHMER` inventory of the area tools.

### New lost-garden zones
The Sunken Tank's drowned images and the Bone Terrace's altar will be added here once built.

## Episode 3: The Drowned Village

- The water spirit's name and folklore.
- How Pich is portrayed.
- The ritual verse.
- The three candles and fourth light that free Kanha and Pich: does this read as a respectful ritual?
- Khmer numerals in the safe puzzle: the numerals themselves are standard, but check how they read in the scene. The damaged lunar annotation is deliberately not presented as a verified historical date conversion.

## Khmer text across the game

`docs/production/khmer-strings-review.csv` has 130 interface strings that are still drafts, with columns for the reviewer's corrections. It doesn't yet include the Episode 2 or Episode 3 strings.
