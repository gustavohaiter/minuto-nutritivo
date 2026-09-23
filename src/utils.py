"""Utilitários compartilhados: chamadas a ffmpeg/ffprobe e checagem de dependências."""
from __future__ import annotations

import shutil
import subprocess
import time
from pathlib import Path
from typing import Callable, TypeVar

T = TypeVar("T")


class ErroFFmpeg(Exception):
    pass


def com_retentativas(
    func: Callable[[], T],
    excecoes: tuple[type[Exception], ...],
    tentativas: int = 3,
    espera_inicial: float = 3.0,
    descricao: str = "",
) -> T:
    """Chama func() de novo (com espera crescente) se ela lançar uma das
    `excecoes` — pensado pra falha de rede passageira (timeout, conexão caiu),
    não pra erro determinístico de API (esses `excecoes` não deve cobrir)."""
    ultimo_erro: Exception | None = None
    espera = espera_inicial
    for tentativa in range(1, tentativas + 1):
        try:
            return func()
        except excecoes as e:
            ultimo_erro = e
            if tentativa == tentativas:
                break
            print(f"AVISO: falha de rede{' em ' + descricao if descricao else ''} (tentativa {tentativa}/{tentativas}): {e}. Tentando de novo em {espera:.0f}s...")
            time.sleep(espera)
            espera *= 2
    raise ultimo_erro


def checar_ffmpeg() -> None:
    faltando = [b for b in ("ffmpeg", "ffprobe") if shutil.which(b) is None]
    if faltando:
        raise ErroFFmpeg(
            f"Não encontrei {', '.join(faltando)} no PATH. Instale o FFmpeg "
            "(https://ffmpeg.org/download.html) e garanta que esteja acessível no terminal."
        )


def probe_duration(caminho: Path) -> float:
    """Duração em segundos de um arquivo de mídia (0.0 se não existir ou falhar)."""
    if not Path(caminho).exists():
        return 0.0
    resultado = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "csv=p=0",
            str(caminho),
        ],
        capture_output=True,
        text=True,
    )
    saida = resultado.stdout.strip()
    try:
        return float(saida)
    except ValueError:
        return 0.0


def rodar_ffmpeg(args: list[str], descricao: str = "") -> None:
    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", *args]
    resultado = subprocess.run(cmd, capture_output=True, text=True)
    if resultado.returncode != 0:
        raise ErroFFmpeg(f"Falha no ffmpeg {descricao}:\n{' '.join(cmd)}\n{resultado.stderr[-3000:]}")
