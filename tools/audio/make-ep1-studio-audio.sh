#!/usr/bin/env bash
# Encodes Episode 1 studio's real CC0 Freesound recordings (listed in
# tools/audio/ep1-studio-freesound.json) into public/assets/ep1/audio/
# as Ogg Opus + AAC (.m4a), 48 kHz, matching Episode 2's mastering standards:
#   - Seamless looping beds: -20 to -24 LUFS, equal-power crossfade seam
#   - One-shot scares & foley: mono, trimmed, faded, peak -3 dBFS
set -euo pipefail
cd "$(dirname "$0")/../.."
SRC=art-source/audio/library/freesound-ep1
OUT=public/assets/ep1/audio
mkdir -p "$SRC" "$OUT"
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

calc() { printf '%.4f' "$(echo "$1" | bc -l)"; }

src() {
  local f
  f=$(ls "$SRC/$1"_*.ogg 2>/dev/null | head -1)
  [[ -n "$f" ]] || { echo "missing source $1 in $SRC" >&2; exit 1; }
  echo "$f"
}

lufs() {
  ffmpeg -hide_banner -nostats -i "$1" -af ebur128 -f null - 2>&1 |
    sed -n 's/^ *I: *\(-*[0-9.]*\) LUFS.*/\1/p' | tail -1
}

peak() {
  ffmpeg -hide_banner -nostats -i "$1" -af volumedetect -f null - 2>&1 |
    sed -n 's/.*max_volume: \(-*[0-9.]*\) dB.*/\1/p'
}

encode() { # wav, gain dB, name, bitrate
  local wav=$1 gain=$2 name=$3 bitrate=$4
  local chain="volume=${gain}dB,alimiter=limit=0.708:attack=4:release=60:level=0"
  ffmpeg -hide_banner -loglevel error -y -i "$wav" -af "$chain" \
    -c:a libopus -b:a "${bitrate}k" -application audio "$OUT/$name.ogg"
  ffmpeg -hide_banner -loglevel error -y -i "$wav" -af "$chain" \
    -c:a aac -b:a "$((bitrate + 16))k" "$OUT/$name.m4a"
}

loop() { # NAME ID START DUR LAYOUT TARGET_LUFS XF FILTERS
  local name=$1 id=$2 start=$3 dur=$4 layout=$5 target=$6 xf=$7 filters=$8
  local end
  end=$(calc "$start + $dur + $xf")
  ffmpeg -hide_banner -loglevel error -y -i "$(src "$id")" -filter_complex "
    [0:a]atrim=start=$start:end=$end,asetpts=PTS-STARTPTS,$filters,aresample=48000,aformat=channel_layouts=$layout,asplit=3[a][b][c];
    [a]atrim=0:$xf,asetpts=PTS-STARTPTS,afade=t=in:d=$xf:curve=qsin[head];
    [b]atrim=$dur:$(calc "$dur + $xf"),asetpts=PTS-STARTPTS,afade=t=out:d=$xf:curve=qsin[tail];
    [head][tail]amix=inputs=2:normalize=0[seam];
    [c]atrim=$xf:$dur,asetpts=PTS-STARTPTS[body];
    [seam][body]concat=n=2:v=0:a=1" -f wav "$TMP/loop.wav"
  local level gain bitrate=56
  level=$(lufs "$TMP/loop.wav")
  gain=$(calc "$target - ($level)")
  [[ "$layout" == stereo ]] && bitrate=80
  encode "$TMP/loop.wav" "$gain" "$name" "$bitrate"
  printf '%-30s %5.1fs %-6s %5.1f -> %s LUFS\n' "$name" "$dur" "$layout" "$level" "$target"
}

shot() { # NAME ID START DUR FADE FILTERS
  local name=$1 id=$2 start=$3 dur=$4 fade=$5 filters=$6
  local end out
  end=$(calc "$start + $dur")
  out=$(calc "$dur - $fade")
  ffmpeg -hide_banner -loglevel error -y -i "$(src "$id")" \
    -af "atrim=start=$start:end=$end,asetpts=PTS-STARTPTS,$filters,aresample=48000,aformat=channel_layouts=mono,afade=t=in:d=0.005,afade=t=out:st=$out:d=$fade" \
    -f wav "$TMP/shot.wav"
  local level gain
  level=$(peak "$TMP/shot.wav")
  gain=$(calc "-3 - ($level)")
  encode "$TMP/shot.wav" "$gain" "$name" 64
  printf '%-30s %5.2fs mono   peak %5.1f -> -3 dB\n' "$name" "$dur" "$level"
}

# ---- Seamless environmental & dread beds
loop amb_ep1_studio_rain      812182 8   55 stereo -20 3   "highpass=f=65,lowpass=f=4800"
loop amb_ep1_studio_dread_bed 609149 6   52 stereo -22 3   "highpass=f=32,lowpass=f=480"
loop amb_ep1_bath_drip        794907 0.5 26 mono   -24 2   "highpass=f=220,lowpass=f=5600"
loop amb_ep1_bath_faucet      558859 0.6 6.2 mono  -20 1.2 "highpass=f=180,lowpass=f=6000"

# ---- Thunder variations (warm deep rolling monsoon thunder, never harsh static)
shot sfx_ep1_studio_thunder   709887 0.0  9.5  2.2 "highpass=f=32,lowpass=f=2400"
shot sfx_ep1_studio_thunder_2 709887 10.5 9.5  2.2 "highpass=f=32,lowpass=f=2100"
shot sfx_ep1_studio_thunder_3 431301 1.0  8.5  2.2 "highpass=f=32,lowpass=f=1500"

# ---- Physical impacts & altar/picture scares (StudioScares.ts loads these automatically!)
shot sfx_ep1_studio_picture   156578 0.0  1.50 0.25 "highpass=f=80,lowpass=f=8500"
shot sfx_ep1_studio_glass     221528 0.0  1.65 0.30 "highpass=f=120,lowpass=f=9000"
shot sfx_ep1_studio_vase      399080 0.1  1.80 0.35 "highpass=f=80,lowpass=f=8500"
shot sfx_ep1_studio_tear      873248 6.8  1.75 0.35 "highpass=f=60,asetrate=44100*0.86,aresample=48000"
shot sfx_ep1_studio_brass     181115 0.0  2.00 0.45 "highpass=f=120,lowpass=f=7500"
shot sfx_ep1_studio_brass_2   165310 0.0  1.60 0.35 "highpass=f=120,lowpass=f=7500"
shot sfx_ep1_studio_bowl      245944 1.2  2.60 0.50 "highpass=f=100,lowpass=f=6800"

# ---- House atmosphere & stalking footsteps (non-repeating pools!)
shot sfx_ep1_studio_creak_1   822745 1.0  1.00 0.20 "highpass=f=90,lowpass=f=4500"
shot sfx_ep1_studio_creak_2   822745 2.1  1.10 0.22 "highpass=f=90,lowpass=f=4200"
shot sfx_ep1_studio_creak_3   822745 4.5  1.75 0.35 "highpass=f=80,lowpass=f=4000"
shot sfx_ep1_studio_knock_1   448359 12.2 1.45 0.28 "highpass=f=70,lowpass=f=4000"
shot sfx_ep1_studio_knock_2   448359 15.4 1.45 0.28 "highpass=f=70,lowpass=f=4000"
shot sfx_ep1_studio_knock_3   728716 0.0  1.85 0.30 "highpass=f=70,lowpass=f=3800"
shot sfx_ep1_studio_steps_slow 874897 0.0 4.20 0.70 "highpass=f=60,lowpass=f=3400"
shot sfx_ep1_studio_steps_fast 523273 3.5 3.60 0.55 "highpass=f=65,lowpass=f=4000"

# ---- Bathroom & room doors (open, close, latch, slow eerie creak, heavy slam), cistern water, bulb & phone
shot sfx_ep1_studio_door_creak_1 275471 0.00 2.55 0.45 "highpass=f=90,lowpass=f=4800"
shot sfx_ep1_studio_door_creak_2 870437 7.65 1.15 0.25 "highpass=f=90,lowpass=f=4500"
shot sfx_ep1_studio_door_open    870437 0.52 0.72 0.16 "highpass=f=85,lowpass=f=5200"
shot sfx_ep1_studio_door_close   870437 2.24 0.62 0.14 "highpass=f=65,lowpass=f=5600"
shot sfx_ep1_studio_door_close_2 870437 4.10 0.64 0.14 "highpass=f=65,lowpass=f=5600"
shot sfx_ep1_studio_door_latch   870437 10.30 0.58 0.12 "highpass=f=120,lowpass=f=6200"
# Heavy teak door slam (pitched-down real wooden door close + solid panel thump)
ffmpeg -hide_banner -loglevel error -y \
  -i "$(src 870437)" -i "$(src 448359)" \
  -filter_complex "
    [0:a]atrim=2.24:2.88,asetpts=PTS-STARTPTS,asetrate=44100*0.82,aresample=48000,volume=1.35[shut];
    [1:a]atrim=12.18:12.68,asetpts=PTS-STARTPTS,lowpass=f=650,volume=1.15[thump];
    [shut][thump]amix=inputs=2:duration=longest:normalize=0,
    highpass=f=45,lowpass=f=4800,aresample=48000,aformat=channel_layouts=mono,
    atrim=0:0.85,afade=t=in:d=0.004,afade=t=out:st=0.65:d=0.20" \
  -f wav "$TMP/door_slam.wav"
level=$(peak "$TMP/door_slam.wav")
gain=$(calc "-3 - ($level)")
encode "$TMP/door_slam.wav" "$gain" "sfx_ep1_studio_door_slam" 64
printf '%-30s  0.85s mono   peak %5.1f -> -3 dB\n' "sfx_ep1_studio_door_slam" "$level"
shot sfx_ep1_studio_water_stir   634158 0.0 1.75 0.40 "highpass=f=80,lowpass=f=2200,asetrate=44100*0.78,aresample=48000"
shot sfx_ep1_studio_bulb_flicker 866662 0.5 2.55 0.40 "highpass=f=120,lowpass=f=5800"
shot sfx_ep1_studio_phone_ring   456433 7.2 4.00 0.55 "highpass=f=240,lowpass=f=4600"

# ---- Close-mic real breath & whispers (organic human air, zero noisy white static)
shot sfx_ep1_studio_breath    368615 0.0  1.45 0.30 "highpass=f=160,lowpass=f=4800"
shot sfx_ep1_studio_whisper_1 832742 0.0  0.74 0.16 "highpass=f=240,lowpass=f=4200"
shot sfx_ep1_studio_whisper_2 234044 0.55 2.80 0.45 "highpass=f=220,lowpass=f=4000"

# ---- Telephone call climax: real female gasp + breaking glass + heavy crash through 1930s phone EQ
ffmpeg -hide_banner -loglevel error -y \
  -i "$(src 318078)" -i "$(src 221528)" -i "$(src 483354)" \
  -filter_complex "
    [0:a]atrim=0.25:0.98,asetpts=PTS-STARTPTS,volume=1.5,adelay=60|60[gasp];
    [1:a]atrim=0:1.4,asetpts=PTS-STARTPTS,volume=0.85,adelay=620|620[glass];
    [2:a]atrim=0.5:2.2,asetpts=PTS-STARTPTS,volume=1.1,adelay=1100|1100[crash];
    [gasp][glass][crash]amix=inputs=3:duration=longest:normalize=0,
    highpass=f=380,highpass=f=380,lowpass=f=2850,lowpass=f=2850,
    aresample=48000,aformat=channel_layouts=mono,atrim=0:2.85,
    afade=t=in:d=0.01,afade=t=out:st=2.76:d=0.09" \
  -f wav "$TMP/call_terror.wav"
level=$(peak "$TMP/call_terror.wav")
gain=$(calc "-3 - ($level)")
encode "$TMP/call_terror.wav" "$gain" "sfx_ep1_studio_call_terror" 64
printf '%-30s  2.85s mono   peak %5.1f -> -3 dB\n' "sfx_ep1_studio_call_terror" "$level"

du -sh "$OUT"
