#!/usr/bin/env bash
# Masters Episode 1 Village's cinema-grade soundscape & Asian horror SFX into
# public/assets/ep1/audio/ as 48 kHz Ogg Opus + AAC (.m4a):
#   - Seamless outdoor/indoor monsoon beds: -17.5 to -20 LUFS, equal-power crossfade seams
#   - Organic spatialized horror & foley one-shots: zero robotic tremolo/sine buzz, clean -1.5 to -3 dBFS peaks
# Sources: CC0 1.0 Freesound field recordings in art-source/audio/library/freesound-ep1/
# and mastered CC0 SE Asian night recordings in public/assets/ep2/audio/.
# No sacred chants or Pinpeat are used as scares.
set -euo pipefail
cd "$(dirname "$0")/../.."
SRC=art-source/audio/library/freesound-ep1
EP2=public/assets/ep2/audio
OUT=public/assets/ep1/audio
mkdir -p "$OUT"
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

calc() { printf '%.4f' "$(echo "$1" | bc -l)"; }

src() {
  local f
  f=$(ls "$SRC/$1"_*.ogg 2>/dev/null | head -1)
  [[ -n "$f" ]] || { echo "missing source $1 in $SRC" >&2; exit 1; }
  echo "$f"
}

ep2() {
  local f="$EP2/$1.ogg"
  [[ -f "$f" ]] || { echo "missing ep2 source $f" >&2; exit 1; }
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
  local chain="volume=${gain}dB,alimiter=limit=0.84:attack=3:release=50:level=0"
  ffmpeg -hide_banner -loglevel error -y -i "$wav" -af "$chain" \
    -c:a libopus -b:a "${bitrate}k" -application audio "$OUT/$name.ogg"
  ffmpeg -hide_banner -loglevel error -y -i "$wav" -af "$chain" \
    -c:a aac -b:a "$((bitrate + 16))k" "$OUT/$name.m4a"
}

loop_from() { # NAME FILE START DUR LAYOUT TARGET_LUFS XF FILTERS
  local name=$1 file=$2 start=$3 dur=$4 layout=$5 target=$6 xf=$7 filters=$8
  local end
  end=$(calc "$start + $dur + $xf")
  ffmpeg -hide_banner -loglevel error -y -i "$file" -filter_complex "
    [0:a]atrim=start=$start:end=$end,asetpts=PTS-STARTPTS,$filters,aresample=48000,aformat=channel_layouts=$layout,asplit=3[a][b][c];
    [a]atrim=0:$xf,asetpts=PTS-STARTPTS,afade=t=in:d=$xf:curve=qsin[head];
    [b]atrim=$dur:$(calc "$dur + $xf"),asetpts=PTS-STARTPTS,afade=t=out:d=$xf:curve=qsin[tail];
    [head][tail]amix=inputs=2:normalize=0[seam];
    [c]atrim=$xf:$dur,asetpts=PTS-STARTPTS[body];
    [seam][body]concat=n=2:v=0:a=1" -f wav "$TMP/loop.wav"
  local level gain bitrate=64
  level=$(lufs "$TMP/loop.wav")
  gain=$(calc "$target - ($level)")
  [[ "$layout" == stereo ]] && bitrate=96
  encode "$TMP/loop.wav" "$gain" "$name" "$bitrate"
  printf '%-34s %5.1fs %-6s %5.1f -> %s LUFS\n' "$name" "$dur" "$layout" "$level" "$target"
}

shot_from() { # NAME FILE START DUR FADE FILTERS [TARGET_PEAK]
  local name=$1 file=$2 start=$3 dur=$4 fade=$5 filters=$6 target=${7:--2.0}
  local end out
  end=$(calc "$start + $dur")
  out=$(calc "$dur - $fade")
  ffmpeg -hide_banner -loglevel error -y -i "$file" \
    -af "atrim=start=$start:end=$end,asetpts=PTS-STARTPTS,$filters,aresample=48000,aformat=channel_layouts=mono,afade=t=in:d=0.005,afade=t=out:st=$out:d=$fade" \
    -f wav "$TMP/shot.wav"
  local level gain
  level=$(peak "$TMP/shot.wav")
  gain=$(calc "$target - ($level)")
  encode "$TMP/shot.wav" "$gain" "$name" 72
  printf '%-34s %5.2fs mono   peak %5.1f -> %s dB\n' "$name" "$dur" "$level" "$target"
}

echo "=== Remastering Episode 1 Village Cinema Horror Audio ==="

# ------------------------------------------------------------------ 1. Seamless Monsoon & Interior Beds
# Heavy outdoor tropical monsoon rain (real outdoor recording 431301, clean 45s rain curtain without thunder spikes)
loop_from amb_ep1_village_rain        "$(src 431301)" 66.0 44.0 stereo -18.0 3.0 \
  "highpass=f=55,lowpass=f=8600,equalizer=f=220:t=q:w=1.0:g=2.5,equalizer=f=3400:t=q:w=1.2:g=-1.5"

# Sheltered stilt-house / corrugated-tin & tile roof drumming rain (real indoor heavy rain 854720)
loop_from amb_ep1_village_roof_rain   "$(src 854720)" 24.0 29.0 stereo -18.5 2.5 \
  "highpass=f=48,lowpass=f=3600,equalizer=f=260:t=q:w=1.1:g=3.5"

# Under-house water drips through wet teak planks (24s organic drip recording 794907 — no short 2.5s cycling!)
loop_from amb_ep1_village_under_drips "$(src 794907)"  2.0 24.0 mono   -20.5 2.0 \
  "highpass=f=180,lowpass=f=6800,acompressor=threshold=-26dB:ratio=3:attack=5:release=120"

# Deep village psychological dread pressure drone (sub-warm, non-fatiguing, stereo)
loop_from amb_ep1_village_dread       "$(src 609149)"  3.0 50.0 stereo -18.5 3.0 \
  "highpass=f=28,lowpass=f=420,equalizer=f=68:t=q:w=1.1:g=3"

# Subtle real fluorescent/filament shop bulb crackle (NO raw 100Hz/200Hz sine buzz!)
loop_from amb_ep1_village_shop_buzz   "$(src 866662)"  1.1  2.0 mono   -26.0 0.25 \
  "highpass=f=140,lowpass=f=2600,acompressor=threshold=-22dB:ratio=2.5:attack=10:release=100"

# Vintage 1970s Khmer AM/SW valve radio: warm narrow-band tube static + eerie faint carrier whispers (NO robotic 4.5Hz tremolo!)
ffmpeg -hide_banner -loglevel error -y \
  -i "$(src 175944)" \
  -f lavfi -i "anoisesrc=c=brown:r=48000:d=10.5:seed=1972" \
  -i "$(src 866662)" \
  -filter_complex "
    [0:a]atrim=start=12.5:end=23.0,asetpts=PTS-STARTPTS,bandpass=f=1050:width_type=q:w=2.4,acompressor=threshold=-24dB:ratio=4:attack=8:release=140,volume=0.85[ghost];
    [1:a]bandpass=f=1450:width_type=q:w=1.3,tremolo=f=0.28:d=0.35,volume=0.22[hiss];
    [2:a]atrim=start=1.1:end=3.3,asetpts=PTS-STARTPTS,aloop=loop=4:size=105600,atrim=0:10.5,highpass=f=600,lowpass=f=2400,volume=0.20[crackle];
    [ghost][hiss][crackle]amix=inputs=3:duration=shortest:normalize=0,
    highpass=f=340,lowpass=f=2700,aresample=48000,aformat=channel_layouts=mono,asplit=3[a][b][c];
    [a]atrim=0:1.2,asetpts=PTS-STARTPTS,afade=t=in:d=1.2:curve=qsin[head];
    [b]atrim=9.0:10.2,asetpts=PTS-STARTPTS,afade=t=out:d=1.2:curve=qsin[tail];
    [head][tail]amix=inputs=2:normalize=0[seam];
    [c]atrim=1.2:9.0,asetpts=PTS-STARTPTS[body];
    [seam][body]concat=n=2:v=0:a=1" -f wav "$TMP/radio.wav"
level=$(lufs "$TMP/radio.wav"); gain=$(calc "-19.5 - ($level)")
encode "$TMP/radio.wav" "$gain" "amb_ep1_village_radio" 64
printf '%-34s %5.1fs mono   %5.1f -> -19.5 LUFS\n' "amb_ep1_village_radio" 9.0 "$level"

# ------------------------------------------------------------------ 2. Preay (ព្រាយ) Horror Bank
# Continuous 10s haunting muffled female weeping & broken-breath loop (stops dead on sight!)
ffmpeg -hide_banner -loglevel error -y \
  -i "$(src 318078)" -i "$(src 368615)" -i "$(src 234044)" \
  -filter_complex "
    [0:a]atrim=0:0.98,asetpts=PTS-STARTPTS,asetrate=44100*0.80,aresample=48000,highpass=f=150,lowpass=f=3200,aecho=0.8:0.7:55|115:0.30|0.16,volume=1.3[sobA];
    [0:a]atrim=0.18:0.98,asetpts=PTS-STARTPTS,asetrate=44100*0.72,aresample=48000,highpass=f=130,lowpass=f=2800,aecho=0.8:0.7:65|135:0.32|0.18,adelay=3600|3600,volume=1.15[sobB];
    [1:a]atrim=0:1.30,asetpts=PTS-STARTPTS,asetrate=44100*0.78,aresample=48000,highpass=f=140,lowpass=f=3400,adelay=1700|1700,volume=0.85[brA];
    [0:a]atrim=0:0.98,asetpts=PTS-STARTPTS,asetrate=44100*0.86,aresample=48000,highpass=f=160,lowpass=f=3100,aecho=0.8:0.7:50|105:0.28|0.14,adelay=6400|6400,volume=1.25[sobC];
    [2:a]atrim=0.60:3.40,asetpts=PTS-STARTPTS,asetrate=44100*0.84,aresample=48000,bandpass=f=780:width_type=q:w=1.4,adelay=7600|7600,volume=0.65[whisp];
    [sobA][sobB][brA][sobC][whisp]amix=inputs=5:duration=longest:normalize=0,
    apad=whole_dur=11.0,atrim=0:11.0,aresample=48000,aformat=channel_layouts=mono,asplit=3[a][b][c];
    [a]atrim=0:1.0,asetpts=PTS-STARTPTS,afade=t=in:d=1.0:curve=qsin[head];
    [b]atrim=9.8:10.8,asetpts=PTS-STARTPTS,afade=t=out:d=1.0:curve=qsin[tail];
    [head][tail]amix=inputs=2:normalize=0[seam];
    [c]atrim=1.0:9.8,asetpts=PTS-STARTPTS[body];
    [seam][body]concat=n=2:v=0:a=1" -f wav "$TMP/preay_weeping.wav"
level=$(lufs "$TMP/preay_weeping.wav"); gain=$(calc "-17.5 - ($level)")
encode "$TMP/preay_weeping.wav" "$gain" "amb_ep1_preay_weeping" 64
printf '%-34s %5.1fs mono   %5.1f -> -17.5 LUFS\n' "amb_ep1_preay_weeping" 9.8 "$level"

# One-shot muffled sobs (for corpse vanish & distant echoes)
shot_from sfx_ep1_preay_sob_1 "$(src 318078)" 0.00 0.96 0.20 "asetrate=44100*0.80,aresample=48000,highpass=f=140,lowpass=f=3400,aecho=0.8:0.75:65|140:0.35|0.18" -1.8
shot_from sfx_ep1_preay_sob_2 "$(src 318078)" 0.00 0.96 0.22 "asetrate=44100*0.72,aresample=48000,highpass=f=120,lowpass=f=2900,aecho=0.8:0.75:80|170:0.38|0.20" -1.8

# Organic Ju-On / Asian horror dry throat-creak & wet vocal rattle (REAL slow wood-creak grain + deep breath — NO robotic tremolo!)
ffmpeg -hide_banner -loglevel error -y \
  -i "$(src 368615)" -i "$(src 822745)" -i "$(src 873248)" \
  -filter_complex "
    [0:a]atrim=0:1.30,asetpts=PTS-STARTPTS,asetrate=44100*0.62,aresample=48000,bandpass=f=480:width_type=q:w=1.2,acompressor=threshold=-20dB:ratio=3.5:attack=4:release=80,volume=1.35[throat];
    [1:a]atrim=1.15:2.80,asetpts=PTS-STARTPTS,asetrate=44100*0.74,aresample=48000,bandpass=f=980:width_type=q:w=1.8,volume=0.85[creak];
    [2:a]atrim=2.08:3.75,asetpts=PTS-STARTPTS,asetrate=44100*0.66,aresample=48000,bandpass=f=1320:width_type=q:w=2.1,volume=0.45[grain];
    [throat][creak][grain]amix=inputs=3:duration=shortest:normalize=0,
    highpass=f=100,lowpass=f=3400,aecho=0.85:0.65:28|62:0.24|0.12,
    atrim=0:1.95,afade=t=in:d=0.05,afade=t=out:st=1.40:d=0.55,
    aresample=48000,aformat=channel_layouts=mono" -f wav "$TMP/preay_rattle.wav"
level=$(peak "$TMP/preay_rattle.wav"); gain=$(calc "-1.5 - ($level)")
encode "$TMP/preay_rattle.wav" "$gain" "sfx_ep1_preay_rattle" 72
printf '%-34s %5.2fs mono   peak %5.1f -> -1.5 dB\n' "sfx_ep1_preay_rattle" 1.95 "$level"

# Sharp cervical neck-snap / bone crack (crisp dry wood splinter + low pop, zero silence lead-in)
shot_from sfx_ep1_preay_neck_1 "$(src 873248)" 0.16 0.56 0.12 "asetrate=44100*1.08,aresample=48000,highpass=f=150,lowpass=f=6200,equalizer=f=950:t=q:w=1.5:g=6,acompressor=threshold=-18dB:ratio=3:attack=2:release=40" -1.5
shot_from sfx_ep1_preay_neck_2 "$(src 483354)" 0.44 0.44 0.10 "asetrate=44100*1.18,aresample=48000,highpass=f=140,lowpass=f=5800,equalizer=f=1120:t=q:w=1.5:g=5,acompressor=threshold=-18dB:ratio=3:attack=2:release=40" -1.5

# Intimate close-ear HRTF ghost breaths & creeping whispers (trimmed to active core + compressed for presence!)
shot_from sfx_ep1_preay_breath_1  "$(src 368615)" 0.00 1.32 0.28 "asetrate=44100*0.80,aresample=48000,highpass=f=120,lowpass=f=5200,acompressor=threshold=-22dB:ratio=3:attack=5:release=90" -1.8
shot_from sfx_ep1_preay_breath_2  "$(src 234044)" 0.58 2.85 0.42 "asetrate=44100*0.84,aresample=48000,highpass=f=160,lowpass=f=5400,acompressor=threshold=-24dB:ratio=3.5:attack=5:release=110" -1.8
shot_from sfx_ep1_preay_whisper_1 "$(src 234044)" 0.60 2.75 0.40 "highpass=f=220,lowpass=f=5800,acompressor=threshold=-24dB:ratio=4:attack=5:release=100,aecho=0.85:0.75:40|95:0.26|0.14" -1.8
shot_from sfx_ep1_preay_whisper_2 "$(src 175944)" 14.5 2.80 0.45 "asetrate=44100*0.92,aresample=48000,highpass=f=200,lowpass=f=5600,acompressor=threshold=-22dB:ratio=3.5:attack=5:release=110" -1.8

# Preay clawing wooden walls/shutters
shot_from sfx_ep1_preay_claw_1 "$(ep2 sfx_ep2_scratch_1)" 0.0 1.15 0.22 "highpass=f=160,lowpass=f=6000,acompressor=threshold=-22dB:ratio=3:attack=4:release=80" -2.0
shot_from sfx_ep1_preay_claw_2 "$(ep2 sfx_ep2_scratch_2)" 0.0 1.25 0.24 "highpass=f=160,lowpass=f=6000,acompressor=threshold=-22dB:ratio=3:attack=4:release=80" -2.0

# Barefoot wet stalk/rush steps (for dark blackout dart-past & extra footstep behind Sora)
shot_from sfx_ep1_preay_step_1 "$(src 874897)" 14.10 0.85 0.16 "highpass=f=90,lowpass=f=4800,acompressor=threshold=-24dB:ratio=3:attack=3:release=60" -2.0
shot_from sfx_ep1_preay_step_2 "$(src 766212)" 19.60 0.90 0.18 "highpass=f=90,lowpass=f=4600,acompressor=threshold=-24dB:ratio=3:attack=3:release=60" -2.0

# Cinema psychological horror impact / sub-hit (punchy thunder sub-drop + sharp wooden crack + dark drone tail)
ffmpeg -hide_banner -loglevel error -y \
  -i "$(src 709887)" -i "$(src 873248)" -i "$(src 609149)" \
  -filter_complex "
    [0:a]atrim=0.04:2.40,asetpts=PTS-STARTPTS,asetrate=44100*0.58,aresample=48000,lowpass=f=190,equalizer=f=55:t=q:w=1.0:g=5,volume=2.1[sub];
    [1:a]atrim=0.16:0.72,asetpts=PTS-STARTPTS,highpass=f=220,lowpass=f=4200,volume=1.15[snap];
    [2:a]atrim=4.0:6.35,asetpts=PTS-STARTPTS,highpass=f=110,lowpass=f=1400,volume=0.95[body];
    [sub][snap][body]amix=inputs=3:duration=longest:normalize=0,
    atrim=0:2.30,afade=t=in:d=0.006,afade=t=out:st=1.45:d=0.85,
    acompressor=threshold=-14dB:ratio=3:attack=2:release=80,
    aresample=48000,aformat=channel_layouts=mono" -f wav "$TMP/shock_hit.wav"
level=$(peak "$TMP/shock_hit.wav"); gain=$(calc "-1.2 - ($level)")
encode "$TMP/shock_hit.wav" "$gain" "sfx_ep1_village_shock" 72
printf '%-34s %5.2fs mono   peak %5.1f -> -1.2 dB\n' "sfx_ep1_village_shock" 2.30 "$level"

# Low rising cinema tension swell (dark sub-pressure swell for stalking reveals)
shot_from sfx_ep1_village_stinger_low "$(src 609149)" 18.0 3.60 1.20 \
  "highpass=f=36,lowpass=f=920,equalizer=f=72:t=q:w=1.2:g=4,afade=t=in:d=0.65:curve=exp" -2.0

# ------------------------------------------------------------------ 3. Krasue (អាប) Rice-Field Audio
# Eerie low breathy lament floating across flooded paddies (organic swell, NO robotic LFO tremolo)
ffmpeg -hide_banner -loglevel error -y \
  -i "$(src 609149)" -i "$(src 175944)" \
  -filter_complex "
    [0:a]atrim=10:22,asetpts=PTS-STARTPTS,bandpass=f=145:width_type=q:w=1.1,volume=1.15[pulse];
    [1:a]atrim=11:23,asetpts=PTS-STARTPTS,asetrate=44100*0.64,aresample=48000,bandpass=f=480:width_type=q:w=1.6,volume=0.95[air];
    [pulse][air]amix=inputs=2:duration=shortest:normalize=0,
    highpass=f=48,lowpass=f=2200,aresample=48000,aformat=channel_layouts=mono,asplit=3[a][b][c];
    [a]atrim=0:1.4,asetpts=PTS-STARTPTS,afade=t=in:d=1.4:curve=qsin[head];
    [b]atrim=9.5:10.9,asetpts=PTS-STARTPTS,afade=t=out:d=1.4:curve=qsin[tail];
    [head][tail]amix=inputs=2:normalize=0[seam];
    [c]atrim=1.4:9.5,asetpts=PTS-STARTPTS[body];
    [seam][body]concat=n=2:v=0:a=1" -f wav "$TMP/krasue_hum.wav"
level=$(lufs "$TMP/krasue_hum.wav"); gain=$(calc "-18.0 - ($level)")
encode "$TMP/krasue_hum.wav" "$gain" "amb_ep1_krasue_hum" 64
printf '%-34s %5.1fs mono   %5.1f -> -18.0 LUFS\n' "amb_ep1_krasue_hum" 9.5 "$level"

# Alerted red-state eerie guttural swoop & dark wind rush
ffmpeg -hide_banner -loglevel error -y \
  -i "$(src 318078)" -i "$(ep2 sfx_ep2_gust_1)" -i "$(src 709887)" \
  -filter_complex "
    [0:a]atrim=0:0.98,asetpts=PTS-STARTPTS,asetrate=44100*1.08,aresample=48000,highpass=f=280,lowpass=f=5200,volume=1.4[shriek];
    [1:a]atrim=0:1.80,asetpts=PTS-STARTPTS,highpass=f=110,lowpass=f=4200,volume=1.1[whoosh];
    [2:a]atrim=0.05:1.60,asetpts=PTS-STARTPTS,lowpass=f=200,volume=1.2[sub];
    [shriek][whoosh][sub]amix=inputs=3:duration=longest:normalize=0,
    aecho=0.8:0.75:55|110:0.28|0.14,atrim=0:1.85,afade=t=in:d=0.015,afade=t=out:st=1.25:d=0.60,
    aresample=48000,aformat=channel_layouts=mono" -f wav "$TMP/krasue_alert.wav"
level=$(peak "$TMP/krasue_alert.wav"); gain=$(calc "-1.5 - ($level)")
encode "$TMP/krasue_alert.wav" "$gain" "sfx_ep1_krasue_alert" 72
printf '%-34s %5.2fs mono   peak %5.1f -> -1.5 dB\n' "sfx_ep1_krasue_alert" 1.85 "$level"

# ------------------------------------------------------------------ 4. Village Puzzles, Gate, Well & Clock Foley
shot_from sfx_ep1_village_lock_click "$(src 181115)" 0.20 0.24 0.06 "asetrate=44100*1.45,aresample=48000,highpass=f=420,lowpass=f=7200" -3.0
shot_from sfx_ep1_village_lock_open  "$(src 165310)" 0.00 1.25 0.25 "highpass=f=140,lowpass=f=6800" -2.0
shot_from sfx_ep1_village_gate_open  "$(src 275471)" 0.00 2.35 0.45 "asetrate=44100*0.82,aresample=48000,highpass=f=70,lowpass=f=3800" -2.0
shot_from sfx_ep1_well_creak         "$(ep2 sfx_ep2_creak_bamboo_1)" 0.0 1.45 0.28 "highpass=f=90,lowpass=f=4800" -2.0
# Trimmed straight to the full splash core at t=2.00s (fixes -35 dB quietness!) + deep stone well echo
shot_from sfx_ep1_well_splash        "$(src 634158)" 2.00 0.85 0.22 "asetrate=44100*0.76,aresample=48000,highpass=f=90,lowpass=f=4400,aecho=0.82:0.78:70|155:0.44|0.24,acompressor=threshold=-20dB:ratio=3:attack=4:release=80" -1.8
shot_from sfx_ep1_well_tug           "$(src 483354)" 0.44 1.15 0.28 "asetrate=44100*0.72,aresample=48000,highpass=f=70,lowpass=f=2800,aecho=0.8:0.8:85|170:0.45|0.25" -1.5
shot_from sfx_ep1_clock_tick         "$(src 728716)" 0.04 0.16 0.05 "asetrate=44100*1.65,aresample=48000,bandpass=f=1600:width_type=q:w=2.4" -4.0
shot_from sfx_ep1_clock_chime        "$(ep2 sfx_ep2_bell_middle)" 0.0 3.60 0.85 "highpass=f=80,lowpass=f=5600" -2.5
shot_from sfx_ep1_clock_chime_low    "$(ep2 sfx_ep2_bell_large)"  0.0 4.20 1.00 "asetrate=48000*0.86,aresample=48000,highpass=f=60,lowpass=f=4200" -2.0
shot_from sfx_ep1_shrine_place       "$(src 245944)" 1.28 0.85 0.22 "highpass=f=140,lowpass=f=5400" -3.0

echo "=== Done! Remastered Episode 1 village audio in $OUT ==="
