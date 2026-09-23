"""Carrega config.yaml e variáveis de ambiente (.env)."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

RAIZ = Path(__file__).resolve().parent.parent


def carregar_config(caminho: str | Path = "config.yaml") -> dict[str, Any]:
    load_dotenv(RAIZ / ".env")
    caminho = RAIZ / caminho if not Path(caminho).is_absolute() else Path(caminho)
    with open(caminho, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    cfg["_env"] = {
        "ELEVENLABS_API_KEY": os.getenv("ELEVENLABS_API_KEY", ""),
        "PEXELS_API_KEY": os.getenv("PEXELS_API_KEY", ""),
        "PIXABAY_API_KEY": os.getenv("PIXABAY_API_KEY", ""),
    }
    cfg["_raiz"] = RAIZ
    return cfg


def caminho(cfg: dict[str, Any], chave: str) -> Path:
    """Resolve um caminho relativo definido em config['caminhos'][chave]."""
    return cfg["_raiz"] / cfg["caminhos"][chave]
