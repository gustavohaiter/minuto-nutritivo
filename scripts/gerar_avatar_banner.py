"""Gera avatar (800x800) e banner de capa (2560x1440) do canal a partir do
logo escolhido em identidade/logo_escolhido.png. Rode a partir da raiz do
projeto: python3 scripts/gerar_avatar_banner.py"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

_RAIZ = Path(__file__).resolve().parent.parent
BASE = _RAIZ / "identidade"
VERDE = (58, 145, 87)
LARANJA = (230, 145, 56)
BG_CLARO = (250, 248, 240)
FONTE_TITULO = str(_RAIZ / "assets" / "fonts" / "DejaVuSans-Bold.ttf")
FONTE_SUB = str(_RAIZ / "assets" / "fonts" / "DejaVuSans.ttf")


def gerar_avatar(logo: Image.Image) -> None:
    avatar = logo.resize((800, 800), Image.LANCZOS)
    avatar.save(BASE / "avatar_800x800.png")

    mask = Image.new("L", (800, 800), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, 800, 800), fill=255)
    preview = Image.new("RGB", (800, 800), (40, 40, 40))
    preview.paste(avatar, (0, 0), mask)
    preview.save(BASE / "avatar_preview_circular.png")


def gerar_banner(logo: Image.Image) -> None:
    W, H = 2560, 1440
    banner = Image.new("RGB", (W, H), BG_CLARO)
    draw = ImageDraw.Draw(banner)

    logo_size = 200
    logo_small = logo.resize((logo_size, logo_size), Image.LANCZOS)
    lmask = Image.new("L", (logo_size, logo_size), 0)
    ImageDraw.Draw(lmask).ellipse((0, 0, logo_size, logo_size), fill=255)

    fonte_titulo = ImageFont.truetype(FONTE_TITULO, 84)
    fonte_sub = ImageFont.truetype(FONTE_SUB, 26)

    titulo = "MINUTO NUTRITIVO"
    subtitulo = "BENEFÍCIOS DE ALIMENTOS EM 60 SEGUNDOS"

    cx, cy = W / 2, H / 2
    bbox_t = draw.textbbox((0, 0), titulo, font=fonte_titulo)
    tw, th = bbox_t[2] - bbox_t[0], bbox_t[3] - bbox_t[1]
    bbox_s = draw.textbbox((0, 0), subtitulo, font=fonte_sub)
    sw, sh = bbox_s[2] - bbox_s[0], bbox_s[3] - bbox_s[1]

    gap1, gap2 = 22, 14
    bloco_h = logo_size + gap1 + th + gap2 + sh
    topo = cy - bloco_h / 2

    banner.paste(logo_small, (int(cx - logo_size / 2), int(topo)), lmask)
    ty = topo + logo_size + gap1
    draw.text((cx - tw / 2, ty), titulo, font=fonte_titulo, fill=VERDE)
    draw.text((cx - sw / 2, ty + th + gap2), subtitulo, font=fonte_sub, fill=LARANJA)

    banner.save(BASE / "banner_2560x1440.png")

    safe = banner.copy()
    sdraw = ImageDraw.Draw(safe)
    safe_w, safe_h = 1546, 423
    sdraw.rectangle([cx - safe_w / 2, cy - safe_h / 2, cx + safe_w / 2, cy + safe_h / 2], outline=(255, 0, 0), width=3)
    safe.save(BASE / "banner_preview_com_safe_area.png")

    if bloco_h >= safe_h:
        print(f"AVISO: bloco de texto ({bloco_h:.0f}px) maior que a safe area ({safe_h}px).")


def main() -> None:
    BASE.mkdir(parents=True, exist_ok=True)
    logo_path = BASE / "logo_escolhido.png"
    if not logo_path.exists():
        print(f"{logo_path} não encontrado — escolha o logo antes de rodar este script.")
        return
    logo = Image.open(logo_path).convert("RGB")
    gerar_avatar(logo)
    gerar_banner(logo)
    print("avatar_800x800.png e banner_2560x1440.png gerados em", BASE)


if __name__ == "__main__":
    main()
