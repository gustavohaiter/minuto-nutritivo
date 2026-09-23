"""Parse de roteiro.md (formato simplificado, sem personagens/blocos) para
cenas.json — usado pelo Minuto Nutritivo."""
from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

CENA_RE = re.compile(r"^##\s*Cena\s*(\d+)\s*$", re.M)
CAMPO_RE = re.compile(r"^-\s*([a-zA-Z_]+)\s*:\s*(.*)$")
PAUSA_RE = re.compile(r"^-\s*\[PAUSA\]\s*$", re.I)


@dataclass
class Cena:
    numero: int
    id: str
    narracao: str = ""
    imagem_busca: str = ""
    imagem_manual: bool = False
    curto: bool = False
    pausa_apos: bool = False
    aviso_tela: str = ""
    tipo: str = "normal"


def parse_roteiro(caminho_md: str | Path) -> dict[str, Any]:
    caminho_md = Path(caminho_md)
    texto = caminho_md.read_text(encoding="utf-8")

    cabecalho, *resto = CENA_RE.split(texto)
    titulo_m = re.search(r"^#\s*(.+)$", cabecalho, re.M)
    tipo_m = re.search(r"^Tipo:\s*(.+)$", cabecalho, re.M | re.I)
    titulo = titulo_m.group(1).strip() if titulo_m else ""
    tipo_conteudo = tipo_m.group(1).strip() if tipo_m else ""

    cenas: list[Cena] = []
    for i in range(0, len(resto), 2):
        numero = int(resto[i])
        corpo = resto[i + 1]
        cena = Cena(numero=numero, id=f"cena_{numero:02d}")
        for linha in corpo.splitlines():
            linha = linha.strip()
            if not linha:
                continue
            if PAUSA_RE.match(linha):
                cena.pausa_apos = True
                continue
            m = CAMPO_RE.match(linha)
            if not m:
                continue
            campo, valor = m.group(1).lower(), m.group(2).strip()
            if campo == "narracao":
                cena.narracao = valor
            elif campo == "imagem_busca":
                cena.imagem_busca = "" if valor.strip() == "—" else valor
            elif campo == "imagem_manual":
                cena.imagem_manual = valor.lower().startswith("sim")
            elif campo == "curto":
                cena.curto = valor.lower().startswith("sim")
            elif campo == "aviso_tela":
                cena.aviso_tela = valor
        cenas.append(cena)

    return {
        "titulo": titulo,
        "tipo_conteudo": tipo_conteudo,
        "cenas": [asdict(c) for c in cenas],
    }


def salvar_cenas_json(dados: dict[str, Any], destino: str | Path) -> None:
    destino = Path(destino)
    destino.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")


def carregar_cenas_json(caminho_json: str | Path) -> dict[str, Any]:
    return json.loads(Path(caminho_json).read_text(encoding="utf-8"))


def filtrar_cenas(cenas: list[dict[str, Any]], selecao: str | None) -> list[dict[str, Any]]:
    """selecao: None (todas), "1-4", "1,3,5", ou "6"."""
    if not selecao:
        return cenas
    numeros: set[int] = set()
    for parte in selecao.split(","):
        parte = parte.strip()
        if "-" in parte:
            ini, fim = parte.split("-")
            numeros.update(range(int(ini), int(fim) + 1))
        elif parte:
            numeros.add(int(parte))
    return [c for c in cenas if c["numero"] in numeros]
