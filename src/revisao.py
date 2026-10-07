"""Folha de contato (contact sheet) com todas as imagens buscadas pro
roteiro, numeradas por cena — pra conferência visual rápida antes de rodar
a montagem (pessoas em destaque, ilustração em vez de foto, texto
sobreposto, logo de marca etc. precisam de olho humano, não dá pra
automatizar com segurança)."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont, ImageOps

COLUNAS = 3
CELULA_LARGURA = 480
CELULA_ALTURA = 360
FAIXA_LEGENDA = 36
FUNDO = (20, 20, 20)
FUNDO_FALHA = (70, 25, 25)


def _carregar_fonte(cfg: dict[str, Any], tamanho: int) -> ImageFont.FreeTypeFont:
    caminho = cfg["_raiz"] / "assets" / "fonts" / "DejaVuSans-Bold.ttf"
    return ImageFont.truetype(str(caminho), tamanho)


def gerar_folha_contato(resultados: dict[int, dict[str, Any]], cfg: dict[str, Any], destino: Path) -> Path | None:
    itens = sorted((numero, info) for numero, info in resultados.items() if info.get("caminho"))
    if not itens:
        return None

    n_linhas = -(-len(itens) // COLUNAS)  # ceil
    folha = Image.new(
        "RGB", (COLUNAS * CELULA_LARGURA, n_linhas * (CELULA_ALTURA + FAIXA_LEGENDA)), FUNDO
    )
    draw = ImageDraw.Draw(folha)
    fonte = _carregar_fonte(cfg, 22)

    for i, (numero, info) in enumerate(itens):
        col, lin = i % COLUNAS, i // COLUNAS
        x0 = col * CELULA_LARGURA
        y0 = lin * (CELULA_ALTURA + FAIXA_LEGENDA)

        try:
            img = Image.open(info["caminho"]).convert("RGB")
            img = ImageOps.fit(img, (CELULA_LARGURA, CELULA_ALTURA), Image.LANCZOS)
            folha.paste(img, (x0, y0))
        except Exception:
            draw.rectangle([x0, y0, x0 + CELULA_LARGURA, y0 + CELULA_ALTURA], fill=FUNDO_FALHA)
            draw.text((x0 + 10, y0 + 10), "não abriu", font=fonte, fill=(255, 255, 255))

        legenda = f"Cena {numero:02d} — {info.get('fonte', '?')}"
        draw.rectangle(
            [x0, y0 + CELULA_ALTURA, x0 + CELULA_LARGURA, y0 + CELULA_ALTURA + FAIXA_LEGENDA], fill=(0, 0, 0)
        )
        draw.text((x0 + 8, y0 + CELULA_ALTURA + 6), legenda, font=fonte, fill=(255, 255, 255))

    destino.parent.mkdir(parents=True, exist_ok=True)
    folha.save(destino, quality=88)
    return destino
