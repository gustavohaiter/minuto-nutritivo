"""Tela final de call-to-action ("se inscreva no canal") — logo + texto sobre
fundo na cor da marca. Igual em espírito à cta.png do Dossiê Obscuro, mas já
usa a identidade visual do Minuto Nutritivo em vez de um placeholder de texto."""
from __future__ import annotations

import textwrap
from pathlib import Path
from typing import Any

from PIL import Image, ImageChops, ImageDraw, ImageFont

COR_FUNDO = (58, 145, 87)      # verde da marca (#3A9157)
COR_TEXTO = (255, 255, 255)
COR_ACENTO = (230, 145, 56)    # laranja da marca (#E69138)

TEXTO_PADRAO = "Gostou? Se inscreva no canal e ative o sininho!"


def _logo_recortada(cfg: dict[str, Any]) -> Image.Image:
    caminho = cfg["_raiz"] / "identidade" / "logo_escolhido.png"
    logo = Image.open(caminho).convert("RGB")
    # a logo é um PNG sem transparência, fundo branco sólido — sem chave de
    # cor o fundo branco vira uma caixa quadrada visível atrás do desenho
    # redondo. Usa "distância do branco" como canal alpha (pixel branco puro
    # = totalmente transparente, pixel colorido/preto = opaco) e recorta pela
    # bbox do alpha, não do retângulo bruto — senão os cantos da bbox (que a
    # arte redonda não preenche) continuam brancos.
    r, g, b = logo.split()
    minimo = ImageChops.darker(ImageChops.darker(r, g), b)
    alpha = ImageChops.invert(minimo)
    logo_rgba = Image.merge("RGBA", (r, g, b, alpha))
    caixa = alpha.point(lambda p: 255 if p > 12 else 0).getbbox()
    if caixa:
        logo_rgba = logo_rgba.crop(caixa)
    return logo_rgba


def _carregar_fonte(cfg: dict[str, Any], tamanho: int) -> ImageFont.FreeTypeFont:
    caminho = cfg["_raiz"] / "assets" / "fonts" / "DejaVuSans-Bold.ttf"
    return ImageFont.truetype(str(caminho), tamanho)


def gerar_tela_cta(cfg: dict[str, Any], destino: Path, texto: str = TEXTO_PADRAO) -> None:
    largura, altura = cfg["video"]["largura"], cfg["video"]["altura"]
    menor_lado = min(largura, altura)

    tela = Image.new("RGB", (largura, altura), COR_FUNDO)

    logo = _logo_recortada(cfg)
    logo_lado = int(menor_lado * 0.4)
    logo = logo.resize((logo_lado, int(logo_lado * logo.height / logo.width)), Image.LANCZOS)

    tamanho_fonte = max(int(largura / 22), 28)
    fonte = _carregar_fonte(cfg, tamanho_fonte)
    draw_medida = ImageDraw.Draw(tela)
    # quebra pela largura disponível (não por \n fixo) — o normal é 1920 de
    # largura e o Short só 1080, então a mesma frase precisa de números
    # de linha diferentes em cada formato
    largura_chars = max(int(largura * 0.85 / (tamanho_fonte * 0.56)), 10)
    linhas = textwrap.wrap(texto, width=largura_chars)
    alturas_linha = [draw_medida.textbbox((0, 0), l, font=fonte)[3] for l in linhas]
    altura_linha = max(alturas_linha, default=fonte.size) + int(fonte.size * 0.4)
    altura_texto_total = altura_linha * len(linhas)

    espaco = int(menor_lado * 0.06)
    bloco_altura = logo.height + espaco + altura_texto_total
    y0 = (altura - bloco_altura) / 2

    tela.paste(logo, (int((largura - logo.width) / 2), int(y0)), mask=logo)

    barra_y = int(y0 + logo.height + espaco / 2)
    barra_largura = int(logo.width * 0.5)
    draw_medida.rectangle(
        [(largura - barra_largura) / 2, barra_y, (largura + barra_largura) / 2, barra_y + 6],
        fill=COR_ACENTO,
    )

    y = y0 + logo.height + espaco
    for linha in linhas:
        bbox = draw_medida.textbbox((0, 0), linha, font=fonte)
        largura_texto = bbox[2] - bbox[0]
        draw_medida.text(((largura - largura_texto) / 2, y), linha, font=fonte, fill=COR_TEXTO)
        y += altura_linha

    destino.parent.mkdir(parents=True, exist_ok=True)
    tela.save(destino)
