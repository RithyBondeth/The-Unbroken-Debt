#!/usr/bin/env bash
# Masters real CC0 Freesound recordings (from art-source/audio/library/freesound-ep1/)
# into public/assets/ep1/audio/ as Ogg Opus + AAC (.m4a) at 48 kHz for Episode 1's
# 1933 Citroën Rosalie storm drive:
#   - Seamless cabin rain & dread drone beds (-20 to -21 LUFS, equal-power crossfade)
#   - Non-repeating mono spatial horror & foley one-shots (peak -3 dBFS, clean fades)
# Cultural rule: zero sacred chants, temple bells, or Pinpeat used as scares.
set -euo pipefail
cd "$(dirname "$0")/../.."
SRC=art-source/audio/library/freesound-ep1
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

loop_single() { # NAME ID START DUR LAYOUT TARGET_LUFS XF FILTERS
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

# ---- 1. Seamless enclosed 1933 steel-cabin heavy monsoon rain bed (layered closed-window + storm body)
ffmpeg -hide_banner -loglevel error -y \
  -i "$(src 854720)" -i "$(src 812182)" \
  -filter_complex "
    [0:a]atrim=start=2:end=53,asetpts=PTS-STARTPTS,highpass=f=55,lowpass=f=3200,equalizer=f=340:t=q:w=1.2:g=3,volume=1.15[in_rain];
    [1:a]atrim=start=12:end=63,asetpts=PTS-STARTPTS,highpass=f=90,lowpass=f=2400,volume=0.42[out_rain];
    [in_rain][out_rain]amix=inputs=2:duration=shortest:normalize=0,aresample=48000,aformat=channel_layouts=stereo,asplit=3[a][b][c];
    [a]atrim=0:3,asetpts=PTS-STARTPTS,afade=t=in:d=3:curve=qsin[head];
    [b]atrim=48:51,asetpts=PTS-STARTPTS,afade=t=out:d=3:curve=qsin[tail];
    [head][tail]amix=inputs=2:normalize=0[seam];
    [c]atrim=3:48,asetpts=PTS-STARTPTS[body];
    [seam][body]concat=n=2:v=0:a=1" -f wav "$TMP/taxi_rain.wav"
level=$(lufs "$TMP/taxi_rain.wav")
gain=$(calc "-20 - ($level)")
encode "$TMP/taxi_rain.wav" "$gain" "amb_ep1_taxi_rain_cabin" 80
printf '%-30s %5.1fs %-6s %5.1f -> -20 LUFS\n' "amb_ep1_taxi_rain_cabin" 48.0 stereo "$level"

# ---- 2. Seamless cinematic low horror tension bed (feeds DreadScore in TaxiRide)
loop_single amb_ep1_taxi_dread_drone 609149 4 50 stereo -21 3 "highpass=f=30,lowpass=f=560"

# ---- 3. Real thunder claps & deep rolling monsoon storm (non-repeating 3-clip pool)
shot sfx_ep1_taxi_thunder_1   709887 0.0  8.8  2.0 "highpass=f=30,lowpass=f=2800"
shot sfx_ep1_taxi_thunder_2   709887 10.4 9.0  2.2 "highpass=f=30,lowpass=f=2400"
shot sfx_ep1_taxi_thunder_3   431301 0.8  8.4  2.0 "highpass=f=28,lowpass=f=1800"

# ---- 4. Beat 4a/4b visceral window slam (heavy steel-door thud + stressed laminated glass crack)
ffmpeg -hide_banner -loglevel error -y \
  -i "$(src 448359)" -i "$(src 728716)" -i "$(src 595487)" \
  -filter_complex "
    [0:a]atrim=12.18:12.82,asetpts=PTS-STARTPTS,asetrate=44100*0.76,aresample=48000,lowpass=f=480,volume=1.55[boom];
    [1:a]atrim=0.0:0.65,asetpts=PTS-STARTPTS,highpass=f=90,lowpass=f=3200,volume=1.10[slap];
    [2:a]atrim=1.0:1.75,asetpts=PTS-STARTPTS,highpass=f=850,lowpass=f=6800,volume=0.85,adelay=12|12[glass];
    [boom][slap][glass]amix=inputs=3:duration=longest:normalize=0,
    highpass=f=35,lowpass=f=6400,aresample=48000,aformat=channel_layouts=mono,
    atrim=0:1.05,afade=t=in:d=0.004,afade=t=out:st=0.72:d=0.33" \
  -f wav "$TMP/window_slam.wav"
level=$(peak "$TMP/window_slam.wav")
gain=$(calc "-2.5 - ($level)")
encode "$TMP/window_slam.wav" "$gain" "sfx_ep1_taxi_window_slam" 64
printf '%-30s  1.05s mono   peak %5.1f -> -2.5 dB\n' "sfx_ep1_taxi_window_slam" "$level"

# ---- 5. Eerie wet fingernail / glass tension scrape inside Beat 4a->4b blackout vacuum
ffmpeg -hide_banner -loglevel error -y \
  -i "$(src 595487)" -i "$(src 822745)" \
  -filter_complex "
    [0:a]atrim=14.2:15.7,asetpts=PTS-STARTPTS,highpass=f=1200,lowpass=f=5600,volume=1.25[glass];
    [1:a]atrim=4.5:6.0,asetpts=PTS-STARTPTS,asetrate=44100*1.45,aresample=48000,highpass=f=1400,lowpass=f=5200,volume=0.65[drag];
    [glass][drag]amix=inputs=2:duration=shortest:normalize=0,
    aresample=48000,aformat=channel_layouts=mono,atrim=0:1.35,
    afade=t=in:d=0.08,afade=t=out:st=0.95:d=0.40" \
  -f wav "$TMP/glass_scrape.wav"
level=$(peak "$TMP/glass_scrape.wav")
gain=$(calc "-3 - ($level)")
encode "$TMP/glass_scrape.wav" "$gain" "sfx_ep1_taxi_glass_scrape" 64
printf '%-30s  1.35s mono   peak %5.1f -> -3 dB\n' "sfx_ep1_taxi_glass_scrape" "$level"

# ---- 6. Close-mic behind-ear breath & wordless whispers (Beat 3 rear seat & Beat 4 blackout)
shot sfx_ep1_taxi_neck_breath 368615 0.0  1.42 0.28 "asetrate=44100*0.92,aresample=48000,highpass=f=140,lowpass=f=5200"
shot sfx_ep1_taxi_whisper_1   832742 0.0  0.72 0.16 "highpass=f=220,lowpass=f=4400"
shot sfx_ep1_taxi_whisper_2   234044 0.50 2.65 0.45 "highpass=f=210,lowpass=f=4200"
shot sfx_ep1_taxi_whisper_3   175944 1.20 2.40 0.48 "highpass=f=240,lowpass=f=4000"

# ---- 7. Subtle startled female breath/gasp (Sora's instinctive reaction after major shocks)
shot sfx_ep1_taxi_sora_gasp_1 318078 0.18 0.68 0.18 "highpass=f=180,lowpass=f=5600"
shot sfx_ep1_taxi_sora_gasp_2 318078 0.04 0.56 0.16 "asetrate=44100*1.05,aresample=48000,highpass=f=200,lowpass=f=5400"

# ---- 8. Beat 1 splintering jungle branch snap on right verge
ffmpeg -hide_banner -loglevel error -y \
  -i "$(src 873248)" -i "$(src 483354)" \
  -filter_complex "
    [0:a]atrim=6.75:7.95,asetpts=PTS-STARTPTS,volume=1.2[snap1];
    [1:a]atrim=0.45:1.55,asetpts=PTS-STARTPTS,volume=0.75,adelay=45|45[snap2];
    [snap1][snap2]amix=inputs=2:duration=longest:normalize=0,
    highpass=f=70,lowpass=f=6800,aresample=48000,aformat=channel_layouts=mono,
    atrim=0:1.25,afade=t=in:d=0.005,afade=t=out:st=0.88:d=0.37" \
  -f wav "$TMP/branch_snap.wav"
level=$(peak "$TMP/branch_snap.wav")
gain=$(calc "-3 - ($level)")
encode "$TMP/branch_snap.wav" "$gain" "sfx_ep1_taxi_branch_snap" 64
printf '%-30s  1.25s mono   peak %5.1f -> -3 dB\n' "sfx_ep1_taxi_branch_snap" "$level"

# ---- 9. Heavy back-seat leather/frame weight-shift creak right behind Sora (Beat 3 tension!)
ffmpeg -hide_banner -loglevel error -y \
  -i "$(src 275471)" -i "$(src 822745)" \
  -filter_complex "
    [0:a]atrim=0.0:1.65,asetpts=PTS-STARTPTS,asetrate=44100*0.74,aresample=48000,highpass=f=70,lowpass=f=2400,volume=1.15[c1];
    [1:a]atrim=1.0:2.2,asetpts=PTS-STARTPTS,asetrate=44100*0.80,aresample=48000,highpass=f=65,lowpass=f=2100,volume=0.85,adelay=120|120[c2];
    [c1][c2]amix=inputs=2:duration=longest:normalize=0,
    aresample=48000,aformat=channel_layouts=mono,atrim=0:1.75,
    afade=t=in:d=0.03,afade=t=out:st=1.30:d=0.45" \
  -f wav "$TMP/seat_creak.wav"
level=$(peak "$TMP/seat_creak.wav")
gain=$(calc "-3 - ($level)")
encode "$TMP/seat_creak.wav" "$gain" "sfx_ep1_taxi_seat_creak" 64
printf '%-30s  1.75s mono   peak %5.1f -> -3 dB\n' "sfx_ep1_taxi_seat_creak" "$level"

# ---- 10. Vintage 6V Edison filament / dash relay sputter & puddles splash pool
shot sfx_ep1_taxi_elec_flicker 866662 0.45 1.85 0.30 "highpass=f=130,lowpass=f=6200"
shot sfx_ep1_taxi_mud_splash_1 634158 0.0  1.45 0.32 "asetrate=44100*0.72,aresample=48000,highpass=f=65,lowpass=f=3200"
shot sfx_ep1_taxi_mud_splash_2 634158 1.6  1.35 0.30 "asetrate=44100*0.84,aresample=48000,highpass=f=70,lowpass=f=3400"

ls -lh "$OUT"/*taxi* | awk '{print $5, $9}'
