"""Gera trilha.mp3: melodia curta estilo marimba/xilofone (escala pentatônica
maior, staccato), 100% sintetizada, sem direitos autorais. O app já repete
o arquivo em loop na mixagem (não precisa gerar um arquivo longo).
Rode a partir da raiz do projeto: python3 scripts/gerar_trilha.py"""
from pathlib import Path

from pydub import AudioSegment
from pydub.generators import Sine

RAIZ = Path(__file__).resolve().parent.parent

# escala pentatônica maior (C D E G A) — soa alegre sem soar dissonante
NOTAS = [261.63, 329.63, 392.00, 523.25, 440.00, 392.00, 329.63, 293.66]
DUR_NOTA_MS = 260
GAP_MS = 40
GANHO_DB = -8   # ajuste aqui se quiser mais alta (menos negativo) ou mais baixa
REPETICOES = 8


def gerar_nota(freq: float) -> AudioSegment:
    fundamental = Sine(freq).to_audio_segment(duration=DUR_NOTA_MS).apply_gain(-6)
    # leve harmônico uma oitava acima, mais baixo — dá "brilho" de madeira/marimba
    brilho = Sine(freq * 2).to_audio_segment(duration=DUR_NOTA_MS).apply_gain(-16)
    nota = fundamental.overlay(brilho)
    return nota.fade_in(8).fade_out(180)


def main() -> None:
    barra = AudioSegment.silent(duration=0)
    for f in NOTAS:
        barra += gerar_nota(f) + AudioSegment.silent(duration=GAP_MS)

    trilha = barra * REPETICOES
    trilha = trilha.apply_gain(GANHO_DB).fade_in(300).fade_out(300)

    destino = RAIZ / "trilha.mp3"
    trilha.export(destino, format="mp3")
    print(f"{destino} gerada ({len(trilha) / 1000:.1f}s, o app repete em loop na mixagem).")


if __name__ == "__main__":
    main()
