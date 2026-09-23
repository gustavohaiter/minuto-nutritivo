"""Aviso na tela: queima uma barra de alerta (fundo sólido + texto) numa
imagem de cena específica — usado pra avisos de saúde/segurança que o
roteiro marca com o campo opcional 'aviso_tela'. Fica na parte de CIMA da
imagem pra não brigar com a legenda (que já ocupa a parte de baixo)."""
from __future__ import annotations

import textwrap
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

COR_FUNDO = (176, 42, 42)
COR_TEXTO = (255, 255, 255)


def _carregar_fonte(cfg: dict[str, Any], tamanho: int) -> ImageFont.FreeTypeFont:
    caminho = cfg["_raiz"] / "assets" / "fonts" / "DejaVuSans-Bold.ttf"
    return ImageFont.truetype(str(caminho), tamanho)


def aplicar_aviso_tela(imagem_path: Path, texto: str, cfg: dict[str, Any], destino: Path) -> None:
    largura, altura = cfg["video"]["largura"], cfg["video"]["altura"]

    base = Image.open(imagem_path).convert("RGB")
    # a imagem original pode ter proporção diferente da vertical do vídeo —
    # cobre e centraliza igual o resto do pipeline faz no Ken Burns
    escala = max(largura / base.width, altura / base.height)
    novo_w, novo_h = int(base.width * escala), int(base.height * escala)
    base = base.resize((novo_w, novo_h), Image.LANCZOS)
    esquerda = (novo_w - largura) / 2
    topo = (novo_h - altura) / 2
    base = base.crop((esquerda, topo, esquerda + largura, topo + altura))

    draw = ImageDraw.Draw(base)
    tamanho_fonte = max(int(largura / 26), 24)
    fonte = _carregar_fonte(cfg, tamanho_fonte)

    largura_chars = max(int(largura / (tamanho_fonte * 0.58)), 10)
    linhas = textwrap.wrap(texto, width=largura_chars)

    alturas = [draw.textbbox((0, 0), linha, font=fonte)[3] for linha in linhas]
    altura_linha = max(alturas, default=tamanho_fonte) + int(tamanho_fonte * 0.35)
    margem_v = int(tamanho_fonte * 0.6)
    faixa_h = margem_v * 2 + altura_linha * len(linhas)

    draw.rectangle([0, 0, largura, faixa_h], fill=COR_FUNDO)

    y = margem_v
    for linha in linhas:
        bbox = draw.textbbox((0, 0), linha, font=fonte)
        largura_texto = bbox[2] - bbox[0]
        draw.text(((largura - largura_texto) / 2, y), linha, font=fonte, fill=COR_TEXTO)
        y += altura_linha

    destino.parent.mkdir(parents=True, exist_ok=True)
    base.save(destino)
