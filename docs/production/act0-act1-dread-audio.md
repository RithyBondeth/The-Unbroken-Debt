# Act 0 and Act 1 dread audio

The title screen's horror carried into the studio, the taxi and the village, within the Audio Design Document's rules: silence still comes first, spirit sounds only play where a spirit is, and no chant, bell or Pinpeat is turned into a scare (section 6.3). Everything is synthesised; real recordings can replace any piece later.

## Shared pieces

- `src/audio/dread.ts`: the title screen's toolkit (moving band-pass, seamless loops, Schroeder hall, wordless whispers, creaks, knocks), now shared by `welcomeDread.ts` and the episode.
- `src/episodes/ep1/audio/dreadSounds.ts`: four stingers (`rise`, `shock`, `drop`, `swell`), a 32 s pressure bed, the ringing ears after a shock, and the studio's room tone with Phnom Penh beyond the rain.
- `src/episodes/ep1/audio/DreadScore.ts`: one per scene. The story sets a pressure level (the bed eases in over about 4 s and out over about 6 s, on the music bus) and fires stingers on the threat bus, which is never ducked. Hits are timed with the scene's own game-time waits.

## Where they play

| Moment | Sound |
|---|---|
| Studio, all through | Room tone, distant city, a horse cart passing, a far dog |
| Kit collected → clock stops | Pressure rises; `rise` lands on the candle and the clock dying |
| Phone ringing | Pressure 0.6 |
| Scream down the line | `shock` under the scream |
| Line dies | `drop`, ears ringing, pressure cut to nothing; 0.35 after the call |
| Taxi, 25–37.8 s | Pressure builds as the driver watches the forest |
| Taxi, 37.8 s (the figure) | `rise` lands on the flash; pressure 0.65 until "There's nobody behind us" |
| Shrine Neak Ta, seen close | `shock` with its vanish |
| Neak Ta vanishing further off | `drop` |
| Watcher by the gate | `swell` as it appears |
| Shadow behind the tent cloth | `shock` on the lightning |
| Phra Phum "ring" response | `drop` |
| Act 1 silences | Pressure follows the Neak Ta's presence and the night falling silent; the vigil passage keeps its own tension bed |

## Rebuilt and widened

- Taxi engine: a 1930s four-cylinder at about 1150 rpm, uneven cylinders, exhaust and body resonances, tappets, gear whine, wet tyres, puddle splashes, ruts and rattles. The old "presence" (the engine slowed down) is replaced by the score.
- Taxi wipers: slow, uneven vacuum wipers with rubber judder and a linkage knock.
- Village rain: a take per ear instead of a mono point pinned to the listener's head.
- Thunder: three rolls from random parts of the sky, the far ones lower.

## Listening

`/tests/browser/sound-audition.html` plays every new or rebuilt sound on its own. Synthesis adds about 1.1 s per scene while the Enter screen fades. These are tuned by measurement, not yet by ear: the levels and timbres still need a headphone pass (see the deferred S4 listening test).
