#!/usr/bin/env bash
# Makes Episode 2's recorded sound (The Whispering Pagoda) from the CC0 Freesound
# recordings listed in tools/audio/ep2-freesound.json, kept in
# art-source/audio/library/freesound. Needs ffmpeg (with libopus) and bc.
#
#   beds    stereo, seamless loops (the tail crossfaded into the head with an
#           equal-power curve), -20 LUFS: the game streams them and crossfades
#           between takes, so no loop point is ever heard twice in a row
#   loops   the same, mono, for beds placed in the world (the pond, frog patches)
#   shots   mono one-shots, trimmed, faded, peak -3 dBFS; bells and gongs keep
#           their whole decay
#
# All Ogg Opus with an AAC fallback (Audio Design Document 10), 48 kHz.
#
#   tools/audio/make-ep2-audio.sh           encode
#   tools/audio/make-ep2-audio.sh --fetch   download missing sources first (asks nothing:
#                                           the list was approved when it was made)
set -euo pipefail
cd "$(dirname "$0")/../.."
SRC=art-source/audio/library/freesound
OUT=public/assets/ep2/audio
MANIFEST=tools/audio/ep2-freesound.json
mkdir -p "$SRC" "$OUT"
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

if [[ "${1:-}" == "--fetch" ]]; then
  node -e '
    const m = require(process.argv[1]);
    for (const s of m.sources)
      console.log(`https://cdn.freesound.org/previews/${Math.floor(s.id / 1000)}/${s.id}_${s.uid}-hq.ogg ${m.folder}/${s.file}`);
  ' "$PWD/$MANIFEST" | while read -r url file; do
    [[ -s "$file" ]] || curl -sfL -o "$file" "$url"
  done
fi

calc() { # arithmetic with a leading zero (bc prints .5)
  printf '%.4f' "$(echo "$1" | bc -l)"
}

src() { # a path as given, or the source file whose name starts with this Freesound id
  if [[ "$1" == */* ]]; then echo "$1"; return; fi
  local f
  f=$(ls "$SRC/$1"_*.ogg 2>/dev/null | head -1)
  [[ -n "$f" ]] || { echo "missing source $1 (run with --fetch)" >&2; exit 1; }
  echo "$f"
}

lufs() { # integrated loudness of a wav
  ffmpeg -hide_banner -nostats -i "$1" -af ebur128 -f null - 2>&1 |
    sed -n 's/^ *I: *\(-*[0-9.]*\) LUFS.*/\1/p' | tail -1
}

peak() { # sample peak of a wav, dBFS
  ffmpeg -hide_banner -nostats -i "$1" -af volumedetect -f null - 2>&1 |
    sed -n 's/.*max_volume: \(-*[0-9.]*\) dB.*/\1/p'
}

encode() { # wav, gain dB, name, channels, opus kbps
  # The limiter only touches the odd gust or splash that the loudness gain pushes
  # past -3 dBFS (quiet field recordings are raised by up to 40 dB).
  local wav=$1 gain=$2 name=$3 bitrate=$5
  local chain="volume=${gain}dB,alimiter=limit=0.708:attack=4:release=60:level=0"
  ffmpeg -hide_banner -loglevel error -y -i "$wav" -af "$chain" \
    -c:a libopus -b:a "${bitrate}k" -application audio "$OUT/$name.ogg"
  ffmpeg -hide_banner -loglevel error -y -i "$wav" -af "$chain" \
    -c:a aac -b:a "$((bitrate + 16))k" "$OUT/$name.m4a"
}

# loop NAME ID START SECONDS CHANNELS FILTERS
# A seamless loop of SECONDS from START: the XF seconds after it are faded out over
# the first XF seconds, which fade in, so the end runs straight into the start.
loop() {
  local name=$1 id=$2 start=$3 dur=$4 layout=$5 filters=$6 xf=3
  local end
  end=$(calc "$start + $dur + $xf")
  ffmpeg -hide_banner -loglevel error -y -i "$(src "$id")" -filter_complex "
    [0:a]atrim=start=$start:end=$end,asetpts=PTS-STARTPTS,$filters,aresample=48000,aformat=channel_layouts=$layout,asplit=3[a][b][c];
    [a]atrim=0:$xf,asetpts=PTS-STARTPTS,afade=t=in:d=$xf:curve=qsin[head];
    [b]atrim=$dur:$(calc "$dur + $xf"),asetpts=PTS-STARTPTS,afade=t=out:d=$xf:curve=qsin[tail];
    [head][tail]amix=inputs=2:normalize=0[seam];
    [c]atrim=$xf:$dur,asetpts=PTS-STARTPTS[body];
    [seam][body]concat=n=2:v=0:a=1" -f wav "$TMP/loop.wav"
  local level gain
  level=$(lufs "$TMP/loop.wav")
  gain=$(calc "-20 - ($level)")
  local bitrate=56
  [[ "$layout" == stereo ]] && bitrate=80
  encode "$TMP/loop.wav" "$gain" "$name" "$layout" "$bitrate"
  printf '%-28s %6.1f s %-6s %6.1f LUFS -> -20\n' "$name" "$dur" "$layout" "$level"
}

# shot NAME ID START SECONDS FADE-OUT FILTERS
shot() {
  local name=$1 id=$2 start=$3 dur=$4 fade=$5 filters=$6
  local end out
  end=$(calc "$start + $dur")
  out=$(calc "$dur - $fade")
  ffmpeg -hide_banner -loglevel error -y -i "$(src "$id")" -af "atrim=start=$start:end=$end,asetpts=PTS-STARTPTS,$filters,aresample=48000,aformat=channel_layouts=mono,afade=t=in:d=0.004,afade=t=out:st=$out:d=$fade" \
    -f wav "$TMP/shot.wav"
  local level gain
  level=$(peak "$TMP/shot.wav")
  gain=$(calc "-3 - ($level)")
  encode "$TMP/shot.wav" "$gain" "$name" mono 64
  printf '%-28s %6.2f s peak %6.1f dB -> -3\n' "$name" "$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$OUT/$name.ogg")" "$level"
}

# The night: three takes of insects (Thailand, Ko Jum, Cát Tiên), heard everywhere.
loop amb_ep2_insects_a 177687 20 90 stereo "highpass=f=150,lowpass=f=14000"
# Ko Jum was recorded very quietly behind a gated hiss above 11 kHz: cut steeply.
loop amb_ep2_insects_b 386474 30 90 stereo "highpass=f=150,lowpass=f=8500,lowpass=f=8500,lowpass=f=8500,lowpass=f=8500"
loop amb_ep2_insects_c 806575 8 90 stereo "highpass=f=180,lowpass=f=12000"
# The wind: distant crowns roaring in gusts, and big leaves close by. The game sets
# their levels from the shared wind.
loop amb_ep2_wind_canopy 523389 2 120 stereo "highpass=f=50,lowpass=f=12000"
loop amb_ep2_wind_leaves 575645 1 54 stereo "highpass=f=120"
# The monks' recitation of the Dharma in Pali, from the hall (recorded for the project
# at a pagoda). The master is limited to -3 LUFS and clips: mono,
# the harsh top softened, levelled to -20 LUFS like Episode 1's smot.
loop amb_ep2_chant art-source/audio/ep2/khmer_monks_dharma_pali_source.mp3 1 230 mono "volume=-10dB,highpass=f=90,lowpass=f=7000"
# Placed in the world: frogs by the lotus pond and in the wet ground west, the pond's edge.
loop amb_ep2_frogs_a 109439 0 29 mono "highpass=f=250"
loop amb_ep2_frogs_b 109441 0 41 mono "highpass=f=200"
loop amb_ep2_pond 318064 0.5 55 mono "highpass=f=120,lowpass=f=6000"

# Bells, deepest to smallest, each with its whole ring. The middle one is the 1532
# bronze bell raised a fifth so the three voices stand apart.
shot sfx_ep2_bell_large 232333 66.8 21.5 4 "highpass=f=50"
shot sfx_ep2_bell_middle 668647 0 13 2.5 "highpass=f=60,asetrate=44100*1.4,aresample=44100"
shot sfx_ep2_bell_small 131348 0 4.8 1.2 "highpass=f=200"
# The gong struck by monks in Thailand, and the big drum: far off in the trees.
shot sfx_ep2_gong_1 803159 31.4 7 2.5 "highpass=f=50"
shot sfx_ep2_gong_2 803159 6.95 4.5 1 "highpass=f=50"
shot sfx_ep2_drum_1 858466 0.6 7.3 1.5 "highpass=f=35"
shot sfx_ep2_drum_2 858466 11.6 6.7 1.5 "highpass=f=35"
shot sfx_ep2_drum_3 858466 24.8 3.1 1 "highpass=f=35"
# Knocks in the walls of the kuti and the hall.
shot sfx_ep2_knock_1 448359 12.3 1.3 0.3 "highpass=f=70"
shot sfx_ep2_knock_2 448359 15.6 1.3 0.3 "highpass=f=70"
shot sfx_ep2_knock_3 448359 18.5 1.3 0.3 "highpass=f=70"
shot sfx_ep2_knock_4 728716 0.05 1.9 0.3 "highpass=f=70"
# The library and its bridge coming apart in the escape: old timber splitting.
shot sfx_ep2_splinter_1 873248 7 1.6 0.4 "highpass=f=60,asetrate=44100*0.8,aresample=44100"
shot sfx_ep2_splinter_2 873248 10 1.8 0.4 "highpass=f=60,asetrate=44100*0.8,aresample=44100"
shot sfx_ep2_splinter_3 873248 14.3 2.9 0.6 "highpass=f=60,asetrate=44100*0.8,aresample=44100"
shot sfx_ep2_splinter_4 483354 24 2 0.5 "highpass=f=60"
shot sfx_ep2_splinter_5 483354 47.1 2.9 0.6 "highpass=f=60"
# Trees and bamboo answering the wind.
shot sfx_ep2_creak_tree_1 726217 16.1 3.7 0.6 "highpass=f=120"
shot sfx_ep2_creak_tree_2 726217 33 2.6 0.5 "highpass=f=120"
shot sfx_ep2_creak_tree_3 726217 40.3 1.7 0.4 "highpass=f=120"
shot sfx_ep2_creak_tree_4 95263 0 13 1.5 "highpass=f=120,afade=t=in:d=1"
shot sfx_ep2_creak_bamboo_1 335891 40.5 4.5 1 "highpass=f=200,afade=t=in:d=0.5"
shot sfx_ep2_creak_bamboo_2 335891 88.5 6.5 1 "highpass=f=200,afade=t=in:d=0.5"
shot sfx_ep2_creak_bamboo_3 335891 121 4 1 "highpass=f=200,afade=t=in:d=0.5"
shot sfx_ep2_creak_bamboo_4 335891 149 2.8 0.8 "highpass=f=200,afade=t=in:d=0.5"
# Gusts swelling through one tree: the game sweeps them along the wind.
shot sfx_ep2_gust_1 714265 5 11 3 "highpass=f=120,afade=t=in:d=2:curve=qsin"
shot sfx_ep2_gust_2 714265 50 16 3 "highpass=f=120,afade=t=in:d=2:curve=qsin"
shot sfx_ep2_gust_3 714265 83 10 3 "highpass=f=120,afade=t=in:d=2:curve=qsin"
shot sfx_ep2_gust_4 714265 171 14 3 "highpass=f=120,afade=t=in:d=2:curve=qsin"
shot sfx_ep2_gust_5 714265 218 12 3 "highpass=f=120,afade=t=in:d=2:curve=qsin"
# Night calls: a village dog far off (recorded in Cambodia), scops owls, a tokay gecko.
shot sfx_ep2_dog_1 393829 24.7 7.3 1 "highpass=f=300,lowpass=f=3500"
shot sfx_ep2_dog_2 393829 33.5 4.5 0.8 "highpass=f=300,lowpass=f=3500"
shot sfx_ep2_dog_3 393829 39.4 6.8 1 "highpass=f=300,lowpass=f=3500"
shot sfx_ep2_dog_4 393829 61.9 3.9 0.8 "highpass=f=300,lowpass=f=3500"
shot sfx_ep2_owl_1 266898 2.4 10.6 1 "highpass=f=300"
shot sfx_ep2_owl_2 266898 50.3 7.7 1 "highpass=f=300"
shot sfx_ep2_owl_3 429185 0.6 9.4 1 "highpass=f=300"
shot sfx_ep2_gecko_1 686626 3.5 19.7 1 "highpass=f=150"
shot sfx_ep2_gecko_2 232287 0.3 7.4 1 "highpass=f=200"
# Something in the pond.
shot sfx_ep2_water_1 501323 0.2 3.4 0.8 "highpass=f=120"
shot sfx_ep2_water_2 501323 21.1 2 0.6 "highpass=f=120"
# The empty clay bowl shattering on the ground.
shot sfx_ep2_clay_1 399080 0.15 1.6 0.3 "highpass=f=80"
shot sfx_ep2_clay_2 399080 2.55 2.3 0.4 "highpass=f=80"
shot sfx_ep2_clay_3 399080 8.35 1.95 0.4 "highpass=f=80"
shot sfx_ep2_clay_4 583310 0 0.74 0.15 "highpass=f=80"
du -sh "$OUT"
