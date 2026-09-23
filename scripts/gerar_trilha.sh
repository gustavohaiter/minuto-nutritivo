#!/bin/bash
# Gera trilha.mp3: fundo leve/animado (acorde maior + shaker sutil), 100%
# sintetizado, sem direitos autorais. Rode a partir da raiz do projeto:
# bash scripts/gerar_trilha.sh
set -e
cd "$(dirname "$0")/.."

ffmpeg -y \
  -f lavfi -i "sine=f=261.63:d=300" \
  -f lavfi -i "sine=f=329.63:d=300" \
  -f lavfi -i "sine=f=392.00:d=300" \
  -f lavfi -i "sine=f=523.25:d=300" \
  -f lavfi -i "anoisesrc=color=white:d=300:a=0.04" \
  -filter_complex "\
[0]volume=0.3,tremolo=f=2.0:d=0.5[a];\
[1]volume=0.22,tremolo=f=2.1:d=0.5[b];\
[2]volume=0.18,tremolo=f=1.9:d=0.5[c];\
[3]volume=0.12,tremolo=f=4.0:d=0.6[d];\
[4]bandpass=f=3000:width_type=h:w=4000,tremolo=f=4.0:d=0.85,volume=0.5[e];\
[a][b][c][d][e]amix=inputs=5:duration=longest:normalize=0[mixed];\
[mixed]lowpass=f=6000,volume=14dB,afade=t=in:d=2,afade=t=out:st=296:d=4,pan=stereo|c0=c0|c1=c0[out]" \
  -map "[out]" -t 300 -ar 44100 -c:a libmp3lame -q:a 4 trilha.mp3

echo "trilha.mp3 gerada (5 min, leve/animada)."
