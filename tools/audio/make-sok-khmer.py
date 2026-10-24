"""Generate Sok's four Piseth takes; optionally import the gramophone mix.

Install tools/audio/requirements-voice.txt into an isolated Python environment.
Run from any directory: python tools/audio/make-sok-khmer.py --import
"""

import argparse
import asyncio
import hashlib
import importlib.metadata
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

import edge_tts

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "art-source/audio/ep1/sok-km-KH.json"
OUTPUT = SOURCE.parent / "sok-piseth"


async def generate():
    script_bytes = SOURCE.read_bytes()
    script = json.loads(script_bytes)
    if script["voice"] != "km-KH-PisethNeural" or len(script["paragraphs"]) != 4:
        raise ValueError("Expected Piseth and all four paragraphs; English subtitles stay in investigation.ts")
    voices = await edge_tts.list_voices()
    voice = next((v for v in voices if v["ShortName"] == script["voice"]), None)
    if not voice or voice["Locale"] != script["language"]:
        raise RuntimeError("Piseth is unavailable; no substitute voice was generated")

    OUTPUT.mkdir(parents=True, exist_ok=True)
    files = []
    # Finish all requests before replacing the source take or changing the game manifest.
    with TemporaryDirectory(prefix=".staging-", dir=OUTPUT) as temporary:
        stage = Path(temporary)
        for i, text in enumerate(script["paragraphs"], 1):
            if not text.strip():
                raise ValueError(f"Paragraph {i} is empty")
            name = f"sok_piseth_{i}.mp3"
            print(f"Generating {script['voice']} paragraph {i}/4", flush=True)
            await edge_tts.Communicate(
                text, voice=script["voice"], rate=script["rate"], pitch=script["pitch"]
            ).save(str(stage / name))
            # Reject empty or undecodable responses before publishing any files.
            duration = float(subprocess.check_output([
                "ffprobe", "-v", "error", "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1", str(stage / name),
            ], text=True))
            if not 0.5 <= duration <= 120:
                raise ValueError(f"Invalid paragraph {i} duration: {duration}")
            files.append({"file": name, "seconds": duration,
                          "sha256": hashlib.sha256((stage / name).read_bytes()).hexdigest()})
        metadata = {
            "voice": script["voice"], "language": script["language"],
            "service": "Microsoft Edge online text-to-speech",
            "client": f"edge-tts {importlib.metadata.version('edge-tts')}",
            "rate": script["rate"], "pitch": script["pitch"],
            "generatedAt": datetime.now(timezone.utc).isoformat(),
            "scriptSha256": hashlib.sha256(script_bytes).hexdigest(), "files": files,
        }
        for take in files:
            (stage / take["file"]).replace(OUTPUT / take["file"])
        (OUTPUT / "provenance.json").write_text(json.dumps(metadata, indent=2) + "\n")
    return [str(OUTPUT / take["file"]) for take in files]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--import", dest="import_mix", action="store_true",
                        help="apply the gramophone filter and select Khmer voice in the game")
    args = parser.parse_args()
    recordings = asyncio.run(generate())
    if args.import_mix:
        subprocess.run(["node", "tools/audio/import-sok-voice.mjs", "km-KH", *recordings],
                       cwd=ROOT, check=True)
