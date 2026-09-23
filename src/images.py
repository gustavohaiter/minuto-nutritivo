"""Busca de imagens (Pexels com fallback Pixabay), imagens manuais e créditos."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import requests
from tqdm import tqdm

from utils import com_retentativas

PEXELS_SEARCH_URL = "https://api.pexels.com/v1/search"
PIXABAY_SEARCH_URL = "https://pixabay.com/api/"

EXTENSOES_MANUAIS = (".jpg", ".jpeg", ".png", ".webp")


class ErroImagem(Exception):
    pass


def _buscar_manual(cena_id: str, diretorio_manual: Path) -> Path | None:
    if not diretorio_manual.exists():
        return None
    for ext in EXTENSOES_MANUAIS:
        candidato = diretorio_manual / f"{cena_id}{ext}"
        if candidato.exists():
            return candidato
    return None


def _buscar_pexels(query: str, largura_minima: int, api_key: str, orientacao: str = "landscape") -> dict[str, Any] | None:
    if not api_key:
        return None
    resp = com_retentativas(
        lambda: requests.get(
            PEXELS_SEARCH_URL,
            headers={"Authorization": api_key},
            params={"query": query, "orientation": orientacao, "size": "large", "per_page": 10},
            timeout=30,
        ),
        excecoes=(requests.exceptions.RequestException,),
        descricao="Pexels",
    )
    if resp.status_code != 200:
        return None
    fotos = resp.json().get("photos", [])
    # em modo retrato o que importa é a altura, não a largura
    campo = "height" if orientacao == "portrait" else "width"
    candidatas = [f for f in fotos if f.get(campo, 0) >= largura_minima] or fotos
    if not candidatas:
        return None
    foto = candidatas[0]
    return {
        "url_download": foto["src"].get("large2x") or foto["src"]["original"],
        "fonte": "Pexels",
        "autor": foto.get("photographer", "desconhecido"),
        "link": foto.get("url", ""),
    }


def _buscar_pixabay(query: str, largura_minima: int, api_key: str, orientacao: str = "horizontal") -> dict[str, Any] | None:
    if not api_key:
        return None
    resp = com_retentativas(
        lambda: requests.get(
            PIXABAY_SEARCH_URL,
            params={
                "key": api_key,
                "q": query,
                "image_type": "photo",
                "orientation": orientacao,
                "min_width": largura_minima,
                "safesearch": "true",
                "per_page": 10,
            },
            timeout=30,
        ),
        excecoes=(requests.exceptions.RequestException,),
        descricao="Pixabay",
    )
    if resp.status_code != 200:
        return None
    hits = resp.json().get("hits", [])
    if not hits:
        return None
    hit = hits[0]
    return {
        "url_download": hit["largeImageURL"],
        "fonte": "Pixabay",
        "autor": hit.get("user", "desconhecido"),
        "link": hit.get("pageURL", ""),
    }


def _baixar(url: str, destino: Path) -> None:
    def tentar():
        resp = requests.get(url, timeout=60, stream=True)
        resp.raise_for_status()
        with open(destino, "wb") as f:
            for chunk in resp.iter_content(8192):
                f.write(chunk)

    com_retentativas(tentar, excecoes=(requests.exceptions.RequestException,), descricao="download de imagem")


def obter_imagem_para_cena(
    cena: dict[str, Any],
    cfg: dict[str, Any],
    diretorio_manual: Path,
    diretorio_cache: Path,
    forcar: bool = False,
) -> dict[str, Any]:
    diretorio_cache.mkdir(parents=True, exist_ok=True)
    cena_id = cena["id"]

    manual = _buscar_manual(cena_id, diretorio_manual)
    if manual:
        return {
            "numero": cena["numero"],
            "caminho": manual,
            "fonte": "Manual",
            "autor": "fornecida pelo usuário",
            "link": "",
        }

    query = cena["imagem_busca"]
    if not query:
        return {
            "numero": cena["numero"],
            "caminho": None,
            "fonte": None,
            "autor": None,
            "link": None,
            "aviso": f"Cena {cena['numero']} não tem imagem_busca nem imagem manual.",
        }

    meta_path = diretorio_cache / f"{cena_id}.meta.json"
    img_path_generico = diretorio_cache / cena_id  # extensão decidida na hora do download

    hash_query = hashlib.sha256(query.encode("utf-8")).hexdigest()
    if not forcar and meta_path.exists():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        if meta.get("hash") == hash_query:
            caminho_existente = Path(meta["caminho"])
            if caminho_existente.exists():
                return {
                    "numero": cena["numero"],
                    "caminho": caminho_existente,
                    "fonte": meta["fonte"],
                    "autor": meta["autor"],
                    "link": meta["link"],
                    "cache": True,
                }

    imagens_cfg = cfg["imagens"]
    orientacao = imagens_cfg.get("orientacao", "landscape")
    orientacao_pixabay = "vertical" if orientacao == "portrait" else orientacao
    resultado = _buscar_pexels(query, imagens_cfg["largura_minima"], cfg["_env"]["PEXELS_API_KEY"], orientacao)
    if resultado is None:
        resultado = _buscar_pixabay(query, imagens_cfg["largura_minima"], cfg["_env"]["PIXABAY_API_KEY"], orientacao_pixabay)

    if resultado is None:
        return {
            "numero": cena["numero"],
            "caminho": None,
            "fonte": None,
            "autor": None,
            "link": None,
            "aviso": f"Cena {cena['numero']}: nenhuma imagem encontrada para '{query}' (Pexels e Pixabay).",
        }

    ext = ".jpg"
    destino = img_path_generico.with_suffix(ext)
    _baixar(resultado["url_download"], destino)

    meta_path.write_text(
        json.dumps(
            {
                "hash": hash_query,
                "caminho": str(destino),
                "fonte": resultado["fonte"],
                "autor": resultado["autor"],
                "link": resultado["link"],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    return {
        "numero": cena["numero"],
        "caminho": destino,
        "fonte": resultado["fonte"],
        "autor": resultado["autor"],
        "link": resultado["link"],
        "cache": False,
    }


def processar_imagens(
    cenas: list[dict[str, Any]],
    cfg: dict[str, Any],
    diretorio_manual: Path,
    diretorio_cache: Path,
    forcar: bool = False,
) -> dict[str, Any]:
    resultados = {}
    avisos = []
    for cena in tqdm(cenas, desc="Imagens", unit="cena"):
        if cena["tipo"] != "normal":
            continue
        r = obter_imagem_para_cena(cena, cfg, diretorio_manual, diretorio_cache, forcar=forcar)
        resultados[cena["numero"]] = r
        if r.get("aviso"):
            avisos.append(r["aviso"])
    return {"resultados": resultados, "avisos": avisos}


def gerar_creditos_txt(resultados: dict[int, dict[str, Any]], destino: Path) -> None:
    linhas = ["Créditos de imagens", "=" * 40, ""]
    for numero in sorted(resultados):
        r = resultados[numero]
        if not r.get("caminho"):
            continue
        if r["fonte"] == "Manual":
            linhas.append(f"Cena {numero:02d}: imagem fornecida manualmente pelo usuário.")
        else:
            linhas.append(
                f"Cena {numero:02d}: {r['fonte']} — autor: {r['autor']} — link: {r['link']}"
            )
    destino.write_text("\n".join(linhas) + "\n", encoding="utf-8")
