# 3. Game Systems Catalogue

Every mechanic from the five episode documents, grouped into systems. Build each system once and extend it. **Ep** = the episode that first needs it.

## 3.1 System matrix

| System | Ep | Used again in | Build notes |
|---|---|---|---|
| First-person controller (walk, crouch, head-bob) | 1 | All | Havok character controller; crouch lowers camera and noise |
| Interaction raycast (look + click/E) | 1 | All | Ray from screen centre; highlight via subtle glow or hand icon on the hands model, never a HUD crosshair |
| Inventory (satchel) | 1 | All | Data-driven items; physical satchel opens in front of the camera |
| Sketchbook (notes, maps, clues, runes) | 1 | All | 3D book; pages rendered to texture; entries unlocked by flags |
| Kerosene lamp (oil level, on/off) | 1 | All | Oil gauge is a mesh on the lamp; refills are pickups |
| Matches (limited count) | 1 | 5 (Fire trial) | Counter shown on the matchbox model |
| Timed upkeep loops (incense) | 1 | 5 | Generic "decaying resource" component: timer, warning stages, consequence |
| Hide spots (wardrobes, behind objects) | 1 | 2, 4 | Trigger volume + lamp off = hidden |
| Entity perception: sight cone | 1 | All | Cone + line-of-sight raycast; lamp light raises visibility |
| Entity perception: hearing | 1 | All | Noise events with loudness and radius (footsteps, objects, breath) |
| "Moves when unwatched" behaviour | 1 | 5 (Earth trial) | Checks whether the object is inside the camera frustum and not occluded |
| "Do not turn around" sequence | 1 | 4 (taboo), 5 | Tracks camera yaw relative to a reference direction |
| Scripted events and sequences | 1 | All | `async` sequence scripts reading/writing flags |
| Puzzle framework (slots, dials, combinations) | 1 | All | Gramophone dial, key fragments, chest → reused for offerings, safe dial, gears |
| Ritual sequence (ordered steps under pressure) | 1 | 3, 4, 5 | Step list with timer and failure handling |
| Checkpoints and save | 1 | All | See architecture doc, section 2.7 |
| Lamp shutter (hide light, flame stays lit) | 2 | 3, 4, 5 | Extends the lamp: states on / shuttered / out |
| Surface-based footstep noise (leaves vs dirt) | 2 | All | Material tag on ground meshes → noise multiplier and sound set |
| Hold breath | 2 | 5 | Short timed action; lowers noise; recovery cooldown |
| Throwable distractions | 2 | 3, 4 | Physics throw + noise event at impact |
| Mirror light-beam puzzle | 2 | 5 (Water trial) | Raycast reflections between rotatable mirrors |
| Timed escape / collapse sequence | 2 | 3, 4 | Scripted hazards + checkpoint at start |
| Rowboat navigation | 3 | — | Simplest viable version first (see cut list) |
| Wetness / body temperature | 3 | — | Resource that drains in water and recovers near heat; shown as screen-edge wetness and lamp flicker |
| Safe-zone lights | 3 | 4 | Area that repels a given entity type |
| Board-up / sealing (planks and tarps on windows) | 3 | — | Puzzle-framework slots that change a room's "flooding" state |
| Crawling through tight spaces | 4 | 5 | Extends crouch: lower camera height, forced slow speed, scripted collapse behind the player |
| Water-only entity movement | 3 | — | Separate navmesh made only of water surfaces |
| Compass (held item) | 4 | 5 | Needle follows world north; can be held while walking |
| Fog navigation loop | 4 | — | Wrong turns quietly loop the player; rows numbered on trees |
| Voice-mimic taboo | 4 | — | Entity plays a relative's voice behind the player; turning the camera or making noise counts as a broken taboo |
| Furnace / pressure-valve defence | 4 | — | Resource-juggling ritual variant |
| Hub with any-order trials | 5 | — | Flags per trial; rotunda reads them |
| Chant choice UI | 5 | — | Choice prompts drawn in the sketchbook; wrong answers cause damage |
| Boss ritual phases | 5 | — | Reuses ritual sequence + entity attacks |
| Ending resolver | 5 | — | Reads cross-episode counters (see 3.3) |

## 3.2 Fail state (missing from the design docs, decide in Phase 0)

The episode documents describe how Sora avoids entities but never what happens when she fails. Recommended default:

- Being caught → a short scare, fade to black, a page torn from the sketchbook, **restart at the last checkpoint**.
- No health bar. "Shadow damage" in Episode 5 can be shown through screen darkening and sound, with 2–3 hits allowed before failure.
- Running out of oil does not kill instantly; it makes the dark more dangerous (entities see further, whispers grow louder).

## 3.3 Cross-episode tracking (needed for the Episode 5 endings)

Episode 5's endings depend on behaviour across the whole game. Track these from Episode 1 onward, or the endings cannot work:

| Counter | Example sources |
|---|---|
| `taboosBroken` | Answering or turning to the mimic voice (Ep4); wasting rice offerings (Ep2); letting the Sai Sin thread break through negligence (Ep1) |
| `loreNotesFound / loreNotesTotal` | Hidden journal pages and notes in every episode |
| `ritualErrors` | Mistakes during counter-rituals in Eps 1–4 |
| `keyChoices` | Story choices; none are defined yet in Eps 1–4 (see open questions) |

## 3.4 Entity catalogue

| Entity | Ep | Senses | Behaviour | Counter-play |
|---|---|---|---|---|
| Neak Ta shadow | 1–5 | Sight + hearing; strengthens per episode | Mostly scripted appearances; roaming in set areas | Darkness, hiding, rituals |
| Shadow roamer (under-house) | 1 | Hearing mostly | Patrol + investigate noise | Quiet movement, lamp off |
| Pret | 2, 5 | **Hearing only** (blind) | Patrol stupa paths, drawn to offerings and noise | Crouch, soft ground, hold breath, distractions |
| Chhlong Tonle | 3 | Senses the player when they are in water | Moves only through water; surfaces from openings | Stay on dry surfaces, safe-zone lights |
| Khmaoch Prey | 4 | Reacts to the player looking back or replying | Mimics voices from behind | Keep walking, do not turn, stay silent |
| Neak Ta Guardian (boss) | 5 | Full awareness | Area attacks, tendrils, geometry bending | Complete ritual phases while evading |

One AI base (perception + state machine) with per-entity settings covers all of these.
