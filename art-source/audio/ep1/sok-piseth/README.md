# Sok's Khmer gramophone recording

Voice: Microsoft **km-KH-PisethNeural**, generated through the Edge online text-to-speech service using [edge-tts](https://github.com/rany2/edge-tts). The original takes and generation metadata are kept here; the game uses the filtered Opus/AAC exports in `public/assets/ep1/audio/vo_sok_km_KH_*`.

The four paragraphs in `../sok-km-KH.json` align with the four existing English subtitles in `src/episodes/ep1/data/investigation.ts`. The translation preserves the 1910 pact, four lives/three payments, seventh-night deadline, five seals, chest/water-jar key and ancestral desk-key clue. Kanha is called Sok's elder sister, consistent with his being Sora's younger maternal uncle (ពូសុខ). This is an AI-drafted Khmer translation; native dialogue review is still pending.

Regenerate from the repository root:

```sh
python3 -m venv /tmp/sok-voice-env
/tmp/sok-voice-env/bin/pip install -r tools/audio/requirements-voice.txt
/tmp/sok-voice-env/bin/python tools/audio/make-sok-khmer.py --import
```

Requires network access for synthesis, Node.js, `ffmpeg`, and `ffprobe`. All speech is generated at build-authoring time: game playback uses local files. The importer applies a 280–3200 Hz gramophone filter and keeps English subtitles. To remix these existing source takes without synthesizing again:

```sh
node tools/audio/import-sok-voice.mjs km-KH art-source/audio/ep1/sok-piseth/sok_piseth_{1,2,3,4}.mp3
```
