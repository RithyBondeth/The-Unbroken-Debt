#!/usr/bin/env bash
# The kmaoch that comes down a tree head first (Episode 2): nails and knees on bark,
# the body hitting the ground, the scuttle after. CC0 Freesound recordings listed in
# tools/audio/ep2-freesound.json (fetch them with tools/audio/make-ep2-audio.sh --fetch).
# Mono one-shots, peak -3 dBFS, Ogg Opus with an AAC fallback, as make-ep2-audio.sh makes.
#
#   tools/audio/make-ep2-climb.sh
set -euo pipefail
cd "$(dirname "$0")/../.."
SRC=art-source/audio/library/freesound
OUT=public/assets/ep2/audio
mkdir -p "$OUT"
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

calc() { printf '%.4f' "$(echo "$1" | bc -l)"; }
src() {
  local f
  f=$(ls "$SRC/$1"_*.ogg 2>/dev/null | head -1)
  [[ -n "$f" ]] || { echo "missing source $1 (run make-ep2-audio.sh --fetch)" >&2; exit 1; }
  echo "$f"
}
peak() {
  ffmpeg -hide_banner -nostats -i "$1" -af volumedetect -f null - 2>&1 |
    sed -n 's/.*max_volume: \(-*[0-9.]*\) dB.*/\1/p'
}
encode() {
  local wav=$1 gain=$2 name=$3
  local chain="volume=${gain}dB,alimiter=limit=0.708:attack=4:release=60:level=0"
  ffmpeg -hide_banner -loglevel error -y -i "$wav" -af "$chain" -c:a libopus -b:a 64k -application audio "$OUT/$name.ogg"
  ffmpeg -hide_banner -loglevel error -y -i "$wav" -af "$chain" -c:a aac -b:a 80k "$OUT/$name.m4a"
}
# shot NAME ID START SECONDS FADE-OUT FILTERS
shot() {
  local name=$1 id=$2 start=$3 dur=$4 fade=$5 filters=$6
  local end out level
  end=$(calc "$start + $dur")
  out=$(calc "$dur - $fade")
  ffmpeg -hide_banner -loglevel error -y -i "$(src "$id")" -af "atrim=start=$start:end=$end,asetpts=PTS-STARTPTS,$filters,aresample=48000,aformat=channel_layouts=mono,afade=t=in:d=0.004,afade=t=out:st=$out:d=$fade" \
    -f wav "$TMP/shot.wav"
  level=$(peak "$TMP/shot.wav")
  encode "$TMP/shot.wav" "$(calc "-3 - ($level)")" "$name"
  printf '%-26s %5.2f s peak %6.1f dB -> -3\n' "$name" "$dur" "$level"
}

# Coming down the trunk: a scramble down a real tree, and fingers raking bark.
shot sfx_ep2_climb_1 491179 3.8 2.6 0.4 "highpass=f=90"
shot sfx_ep2_climb_2 811809 30.0 2.6 0.4 "highpass=f=120"
shot sfx_ep2_climb_3 811809 39.8 2.4 0.4 "highpass=f=120"
# Nails dug into the wood as it stops and turns its head.
shot sfx_ep2_scratch_1 830466 0.3 0.9 0.15 "highpass=f=150"
shot sfx_ep2_scratch_2 830466 1.35 0.8 0.15 "highpass=f=150"
shot sfx_ep2_scratch_3 830466 10.5 1.5 0.25 "highpass=f=150"
# The body hitting the leaf litter, slowed a little to weigh more.
shot sfx_ep2_drop_1 853591 0.85 0.9 0.3 "highpass=f=40,asetrate=44100*0.85,aresample=44100"
shot sfx_ep2_drop_2 853591 3.05 0.9 0.3 "highpass=f=40,asetrate=44100*0.85,aresample=44100"
shot sfx_ep2_drop_3 853591 10.65 0.9 0.3 "highpass=f=40,asetrate=44100*0.85,aresample=44100"
shot sfx_ep2_drop_4 504626 0 1.6 0.4 "highpass=f=35"
# Then it comes, fast, on hands and knees.
shot sfx_ep2_scuttle_1 669085 1.4 4.6 0.6 "highpass=f=120,lowpass=f=9000"
