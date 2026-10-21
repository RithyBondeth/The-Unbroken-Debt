#!/usr/bin/env bash
# Makes the game's footstep sets (Audio Design Document 4.1) from the Kenney
# Impact Sounds takes (CC0) in art-source/audio/library/kenney_impact_sounds:
# mono, trimmed, peak -3 dBFS, Ogg Opus 64 kbps with an AAC fallback
# (Audio Design Document 10). Needs ffmpeg.
#
#   teak   wood takes
#   stone  concrete takes
#   leaves grass takes as they are
#   dirt   grass takes, damped (rain-soaked earth)
#   mud    grass takes, damped harder and a little lower; the game layers a
#          suction on top (synth.ts mudSuction)
set -euo pipefail
cd "$(dirname "$0")/../.."
SRC=art-source/audio/library/kenney_impact_sounds
OUT=public/assets/shared/audio
mkdir -p "$OUT"
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

make() { # surface, source take, filters
  local surface=$1 take=$2 filters=$3
  local n=${take##*_}
  n=${n%.ogg}
  local name="$OUT/sfx_step_${surface}_${n}"
  local chain="pan=mono|c0=0.5*c0+0.5*c1,silenceremove=start_periods=1:start_threshold=-50dB,${filters},atrim=end=0.45,afade=t=out:st=0.33:d=0.12,aresample=48000"
  ffmpeg -hide_banner -loglevel error -y -i "$SRC/$take" -af "$chain" -f wav "$TMP/step.wav"
  local peak
  peak=$(ffmpeg -hide_banner -nostats -i "$TMP/step.wav" -af volumedetect -f null - 2>&1 |
    sed -n 's/.*max_volume: \(-*[0-9.]*\) dB.*/\1/p')
  local gain
  gain=$(echo "-3 - ($peak)" | bc -l)
  ffmpeg -hide_banner -loglevel error -y -i "$TMP/step.wav" -af "volume=${gain}dB" \
    -c:a libopus -b:a 64k -application audio "$name.ogg"
  ffmpeg -hide_banner -loglevel error -y -i "$TMP/step.wav" -af "volume=${gain}dB" \
    -c:a aac -b:a 64k "$name.m4a"
}

for i in 000 001 002 003 004; do
  make teak "footstep_wood_$i.ogg" "highpass=f=70"
  make stone "footstep_concrete_$i.ogg" "highpass=f=70"
  make leaves "footstep_grass_$i.ogg" "highpass=f=70"
  make dirt "footstep_grass_$i.ogg" "highpass=f=60,lowpass=f=3200"
  make mud "footstep_grass_$i.ogg" "highpass=f=50,lowpass=f=1600,asetrate=44100*0.9,aresample=44100"
done
ls -la "$OUT"
