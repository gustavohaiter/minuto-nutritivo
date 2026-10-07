"""Gera .srt/.ass a partir do timeline.json (timestamps por palavra, vindos do
motor de narração — ElevenLabs ou edge-tts, ver src/narration.py)."""
from __future__ import annotations

import textwrap
from pathlib import Path
from typing import Any


def _palavras_da_cena(entrada_timeline: dict[str, Any]) -> list[dict[str, Any]]:
    palavras = (entrada_timeline.get("alignment") or {}).get("palavras") or []
    offset = entrada_timeline.get("alignment_offset") or 0.0
    return [{"texto": p["texto"], "inicio": p["inicio"] + offset, "fim": p["fim"] + offset} for p in palavras]


def _contar_linhas(texto: str, largura: int) -> int:
    """Quantas linhas o textwrap realmente usaria pra esse texto — é essa
    contagem (não a soma de caracteres) que decide se um cue cabe, senão
    um texto que "parece" caber pode precisar de mais linhas na hora de
    desenhar e o textwrap.wrap(max_lines=...) corta palavra do fim sem avisar."""
    return max(len(textwrap.wrap(texto, width=largura)), 1)


def _agrupar_em_cues(
    palavras: list[dict[str, Any]],
    max_chars_linha: int,
    max_linhas: int,
    duracao_max: float,
    duracao_min: float,
) -> list[dict[str, Any]]:
    cues: list[dict[str, Any]] = []
    atual: list[dict[str, Any]] = []

    def fechar():
        if not atual:
            return
        texto = " ".join(p["texto"] for p in atual)
        cues.append({"texto": texto, "inicio": atual[0]["inicio"], "fim": atual[-1]["fim"]})

    for p in palavras:
        if not atual:
            atual = [p]
            continue
        texto_teste = " ".join(x["texto"] for x in atual) + " " + p["texto"]
        duracao_teste = p["fim"] - atual[0]["inicio"]
        if _contar_linhas(texto_teste, max_chars_linha) > max_linhas or duracao_teste > duracao_max:
            fechar()
            atual = [p]
        else:
            atual.append(p)
    fechar()

    # funde cues muito curtas com a seguinte, se couber (mesma checagem de
    # quebra de linha real, não soma de caracteres)
    fundidas: list[dict[str, Any]] = []
    for cue in cues:
        texto_combinado = f'{fundidas[-1]["texto"]} {cue["texto"]}' if fundidas else ""
        if (
            fundidas
            and (cue["fim"] - fundidas[-1]["inicio"]) <= duracao_max
            and (fundidas[-1]["fim"] - fundidas[-1]["inicio"]) < duracao_min
            and _contar_linhas(texto_combinado, max_chars_linha) <= max_linhas
        ):
            fundidas[-1]["texto"] = texto_combinado
            fundidas[-1]["fim"] = cue["fim"]
        else:
            fundidas.append(cue)
    return fundidas


def _formatar_srt_tempo(segundos: float) -> str:
    # arredonda o total em ms primeiro, depois decompõe com divmod — fazer
    # na ordem inversa (truncar segundos, arredondar só a parte fracionária)
    # podia gerar "29,1000" em vez de "30,000" quando a fração arredondava
    # pra cima do limite, um timestamp inválido que o ffmpeg/libass não
    # entende direito (e podia ser a causa de legenda "comendo" palavra)
    total_ms = int(round(segundos * 1000))
    horas, resto = divmod(total_ms, 3_600_000)
    minutos, resto = divmod(resto, 60_000)
    segs, milissegundos = divmod(resto, 1000)
    return f"{horas:02d}:{minutos:02d}:{segs:02d},{milissegundos:03d}"


def _montar_cues(timeline: list[dict[str, Any]], cfg: dict[str, Any]) -> list[dict[str, Any]]:
    leg_cfg = cfg["legendas"]
    max_chars_linha = leg_cfg["max_caracteres_por_linha"]
    max_linhas = leg_cfg["max_linhas"]
    duracao_max = leg_cfg["duracao_max_segundos"]
    duracao_min = leg_cfg["duracao_min_segundos"]

    # Agrupa cena por cena (não tudo junto) para uma legenda nunca misturar
    # palavras de duas cenas diferentes — o que podia acontecer quando uma
    # cena termina e a próxima começa sem pausa, ou juntar texto através de
    # um [PAUSA] silencioso entre elas.
    cues: list[dict[str, Any]] = []
    for entrada in timeline:
        # baseado em ter palavras alinhadas (não no tipo): cobre cenas normais
        # e também cta/despedida quando já têm narração real, sem precisar
        # listar tipos aqui de novo.
        palavras = _palavras_da_cena(entrada)
        if not palavras:
            continue
        cues.extend(_agrupar_em_cues(palavras, max_chars_linha, max_linhas, duracao_max, duracao_min))
    return cues


def _quebrar_para_exibir(texto: str, largura: int, max_linhas: int, contexto: str) -> list[str]:
    """Quebra o texto do cue pra exibição. _agrupar_em_cues já garante que
    cabe em max_linhas — isso aqui nunca deveria precisar cortar nada; se
    precisar (texto/config mudou de um jeito inesperado), avisa em vez de
    apagar palavra do fim silenciosamente como o textwrap.wrap(max_lines=...)
    fazia antes."""
    linhas = textwrap.wrap(texto, width=largura)
    if len(linhas) > max_linhas:
        print(
            f"AVISO: legenda \"{texto}\" precisou de {len(linhas)} linhas ({contexto}), mais que o "
            f"configurado ({max_linhas}) — exibindo tudo mesmo assim, só que mais alto que o padrão."
        )
    return linhas


def gerar_srt(timeline: list[dict[str, Any]], cfg: dict[str, Any], destino: Path) -> Path:
    """Gera o .srt (formato padrão, para upload de legendas no YouTube etc.)."""
    leg_cfg = cfg["legendas"]
    max_chars_linha = leg_cfg["max_caracteres_por_linha"]
    max_linhas = leg_cfg["max_linhas"]
    cues = _montar_cues(timeline, cfg)

    linhas_srt = []
    for i, cue in enumerate(cues, start=1):
        texto_quebrado = "\n".join(_quebrar_para_exibir(cue["texto"], max_chars_linha, max_linhas, "srt"))
        linhas_srt.append(str(i))
        linhas_srt.append(f"{_formatar_srt_tempo(cue['inicio'])} --> {_formatar_srt_tempo(cue['fim'])}")
        linhas_srt.append(texto_quebrado)
        linhas_srt.append("")

    destino.write_text("\n".join(linhas_srt), encoding="utf-8")
    return destino


def _formatar_ass_tempo(segundos: float) -> str:
    # mesmo cuidado do _formatar_srt_tempo: arredonda o total em centésimos
    # primeiro, depois decompõe com divmod — evita gerar "29.100" (inválido,
    # devia ser "30.00") quando a fração arredondava pra cima do limite
    total_cs = int(round(segundos * 100))
    horas, resto = divmod(total_cs, 360_000)
    minutos, resto = divmod(resto, 6_000)
    segs, centesimos = divmod(resto, 100)
    return f"{horas:d}:{minutos:02d}:{segs:02d}.{centesimos:02d}"


def gerar_ass(timeline: list[dict[str, Any]], cfg: dict[str, Any], destino: Path) -> Path:
    """Gera .ass com PlayRes explícito (evita o auto-wrap "gigante" que o ffmpeg
    faz ao converter .srt sem saber a resolução real do vídeo) — usado só para
    queimar a legenda no vídeo, o .srt continua sendo a entrega padrão."""
    leg_cfg = cfg["legendas"]
    video_cfg = cfg["video"]
    max_chars_linha = leg_cfg["max_caracteres_por_linha"]
    max_linhas = leg_cfg["max_linhas"]
    cues = _montar_cues(timeline, cfg)

    largura, altura = video_cfg["largura"], video_cfg["altura"]
    cabecalho = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {largura}
PlayResY: {altura}
WrapStyle: 1
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{leg_cfg['fonte']},{leg_cfg['tamanho_fonte']},{leg_cfg['cor_primaria']},&H000000FF,{leg_cfg['cor_borda']},&H64000000,-1,0,0,0,100,100,0,0,1,{leg_cfg['borda_espessura']},0,2,60,60,60,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    linhas_evento = []
    for cue in cues:
        texto_quebrado = "\\N".join(_quebrar_para_exibir(cue["texto"], max_chars_linha, max_linhas, "ass"))
        linhas_evento.append(
            f"Dialogue: 0,{_formatar_ass_tempo(cue['inicio'])},{_formatar_ass_tempo(cue['fim'])},Default,,0,0,0,,{texto_quebrado}"
        )

    destino.write_text(cabecalho + "\n".join(linhas_evento) + "\n", encoding="utf-8")
    return destino
