"""Gera miniatura (1280x720) do YouTube a partir da imagem de uma cena +
texto de destaque, no mesmo estilo visual do canal (vinheta escura, texto
mostarda com contorno pra legibilidade sobre foto)."""
from __future__ import annotations

import textwrap
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont, ImageOps

MUSTARD = (201, 156, 74)

W, H = 1280, 720


def _carregar_fonte(cfg: dict[str, Any], tamanho: int) -> ImageFont.FreeTypeFont:
    """Usa a fonte que vem junto do projeto (assets/fonts/) — não depende de
    fonte instalada no sistema, então funciona igual em Windows/Linux/Mac."""
    caminho = cfg["_raiz"] / "assets" / "fonts" / "DejaVuSerif-Bold.ttf"
    return ImageFont.truetype(str(caminho), tamanho)


def _escurecer_base(img: Image.Image) -> Image.Image:
    """Vinheta escura mais forte na parte de baixo (onde o texto fica)."""
    overlay = Image.new("L", (W, H), 0)
    draw = ImageDraw.Draw(overlay)
    for y in range(H):
        alpha = int(200 * (y / H) ** 1.6)
        draw.line([(0, y), (W, y)], fill=alpha)
    escuro = Image.new("RGB", (W, H), (8, 8, 10))
    return Image.composite(escuro, img, overlay)


def _desenhar_texto_com_contorno(
    draw: ImageDraw.ImageDraw, xy: tuple[float, float], texto: str, fonte: ImageFont.FreeTypeFont
) -> None:
    x, y = xy
    for dx in (-4, -2, 0, 2, 4):
        for dy in (-4, -2, 0, 2, 4):
            if dx or dy:
                draw.text((x + dx, y + dy), texto, font=fonte, fill=(0, 0, 0))
    draw.text((x, y), texto, font=fonte, fill=MUSTARD)


def gerar_thumbnail(imagem_path: Path, texto: str, cfg: dict[str, Any], destino: Path) -> None:
    base = Image.open(imagem_path).convert("RGB")
    base = ImageOps.fit(base, (W, H), Image.LANCZOS)
    base = _escurecer_base(base)
    draw = ImageDraw.Draw(base)

    linhas = textwrap.wrap(texto.upper(), width=14)[:3]
    tamanho_fonte = 108 if len(linhas) <= 2 else 84
    fonte = _carregar_fonte(cfg, tamanho_fonte)

    alturas = []
    for linha in linhas:
        bbox = draw.textbbox((0, 0), linha, font=fonte)
        alturas.append(bbox[3] - bbox[1])
    espaco_linha = int(tamanho_fonte * 0.25)
    bloco_h = sum(alturas) + espaco_linha * (len(linhas) - 1)

    y = H - 60 - bloco_h
    for linha, altura in zip(linhas, alturas):
        bbox = draw.textbbox((0, 0), linha, font=fonte)
        largura = bbox[2] - bbox[0]
        x = (W - largura) / 2
        _desenhar_texto_com_contorno(draw, (x, y), linha, fonte)
        y += altura + espaco_linha

    destino.parent.mkdir(parents=True, exist_ok=True)
    base.save(destino)
