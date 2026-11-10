# Taxi driver's Khmer lines

Seven lines for the driver in the Episode 1 taxi ride, one per driver subtitle in `src/episodes/ep1/travel/taxiConversation.ts`, in order: `taxi_driver_km_1.mp3` to `taxi_driver_km_7.mp3`. These are the chosen takes. They are source files only; the game does not play them yet.

Made with ElevenLabs text-to-speech on 2026-11-07: model `eleven_v4`, library voice **Duang - Deep, Engaging Storyteller**. Duang is a Thai voice reading Khmer, because ElevenLabs has no Khmer voices. The Khmer is everyday spoken style: the driver calls Sora ក្មួយ and himself ពូ. Text, delivery tags, lengths and checksums are in `provenance.json`. Line 5 is cut from `taxi_driver_km_refined_full.mp3`, at 4.45 to 8.0 s.

**Release blocker:** the chosen takes were made on the ElevenLabs Free plan, which does not allow commercial use. `creator-plan-alternates/` holds licensed takes of the same lines (same voice, model, text and tags) in case the chosen takes cannot ship.

- `khmer-source/`: native Khmer test takes of lines 1 and 5 from Microsoft's km-KH-PisethNeural (edge-tts). Not licensed to ship.

The Khmer text still needs native review (asset tracker S1-042).
