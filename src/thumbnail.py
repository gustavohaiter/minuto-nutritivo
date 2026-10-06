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


def _quebrar_para_caber(
    draw: ImageDraw.ImageDraw, texto: str, fonte: ImageFont.FreeTypeFont, largura_max: float
) -> list[str]:
    """Reduz os caracteres por linha até a LARGURA RENDERIZADA (medida de
    verdade via textbbox, não estimada) caber dentro de largura_max."""
    largura_chars = 40
    linhas = textwrap.wrap(texto, width=largura_chars) or [texto]
    while largura_chars > 2:
        maior_linha = max(draw.textbbox((0, 0), l, font=fonte)[2] for l in linhas)
        if maior_linha <= largura_max:
            break
        largura_chars -= 1
        linhas = textwrap.wrap(texto, width=largura_chars) or [texto]
    return linhas


def gerar_thumbnail(imagem_path: Path, texto: str, cfg: dict[str, Any], destino: Path) -> None:
    base = Image.open(imagem_path).convert("RGB")
    base = ImageOps.fit(base, (W, H), Image.LANCZOS)
    base = _escurecer_base(base)
    draw = ImageDraw.Draw(base)

    # tenta do maior fonte pro menor até o texto caber em MAX_LINHAS sem
    # cortar nada — só corta (avisando) se nem no menor tamanho couber,
    # em vez de descartar palavras silenciosamente como antes. Cada linha
    # é medida de verdade (textbbox) contra a margem, não estimada por
    # contagem de caracteres — senão palavras longas/letras largas vazam
    # pra fora da miniatura.
    MAX_LINHAS = 4
    MARGEM = int(W * 0.08)
    largura_max = W - 2 * MARGEM
    texto_upper = texto.upper()
    linhas: list[str] = []
    tamanho_fonte = 64
    for tamanho_fonte in (108, 92, 76, 64, 54):
        fonte_teste = _carregar_fonte(cfg, tamanho_fonte)
        linhas = _quebrar_para_caber(draw, texto_upper, fonte_teste, largura_max)
        if len(linhas) <= MAX_LINHAS:
            break
    else:
        linhas_completas = linhas
        linhas = linhas[:MAX_LINHAS]
        print(
            f"AVISO: texto da miniatura não coube inteiro (\"{' '.join(linhas_completas)}\") — "
            f"ficou cortado em \"{' '.join(linhas)}\". Encurte o texto em roteiro.md (Miniatura: N | texto) "
            "pra caber."
        )
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
