"""Narração: ElevenLabs (pago, endpoint com timestamps por caractere) ou
edge-tts (100% grátis, sem chave, timestamps por palavra). Motor escolhido
em config.yaml -> voz.motor. Cache por cena, independente do motor."""
from __future__ import annotations

import asyncio
import base64
import hashlib
import json
from pathlib import Path
from typing import Any

import requests
from pydub import AudioSegment
from tqdm import tqdm

from utils import com_retentativas

ELEVENLABS_URL = "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/with-timestamps"
ELEVENLABS_VOICES_URL = "https://api.elevenlabs.io/v1/voices"


class ErroNarracao(Exception):
    pass


def estimar_caracteres(cenas: list[dict[str, Any]]) -> dict[str, Any]:
    total = 0
    por_cena = {}
    for c in cenas:
        n = len(c["narracao"].strip())
        por_cena[c["numero"]] = n
        total += n
    return {"total_caracteres": total, "por_cena": por_cena}


def _hash_cena(texto: str, cfg: dict[str, Any]) -> str:
    motor = cfg["voz"]["motor"]
    if motor == "edge-tts":
        v = cfg["voz"]["edge_tts"]
        extra = {"voice": v["voice"], "rate": v.get("rate"), "volume": v.get("volume"), "pitch": v.get("pitch")}
    else:
        v = cfg["voz"]["elevenlabs"]
        extra = {
            "voice_id": v["voice_id"],
            "model_id": v["model_id"],
            "stability": v["stability"],
            "similarity_boost": v["similarity_boost"],
            "style": v.get("style", 0.0),
        }
    chave = json.dumps({"motor": motor, "texto": texto, **extra}, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(chave.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------- ElevenLabs

def _elevenlabs_chamar_api(texto: str, voz_cfg: dict[str, Any], api_key: str) -> dict[str, Any]:
    if not api_key:
        raise ErroNarracao(
            "ELEVENLABS_API_KEY não configurada no .env. Copie .env.example para .env e preencha."
        )
    if not voz_cfg.get("voice_id"):
        raise ErroNarracao(
            "voz.elevenlabs.voice_id não configurado no config.yaml. Rode `python main.py vozes`."
        )

    url = ELEVENLABS_URL.format(voice_id=voz_cfg["voice_id"])
    payload = {
        "text": texto,
        "model_id": voz_cfg["model_id"],
        "voice_settings": {
            "stability": voz_cfg["stability"],
            "similarity_boost": voz_cfg["similarity_boost"],
            "style": voz_cfg.get("style", 0.0),
            "use_speaker_boost": voz_cfg.get("use_speaker_boost", True),
        },
    }
    params = {"output_format": voz_cfg.get("output_format", "mp3_44100_128")}
    headers = {"xi-api-key": api_key, "Content-Type": "application/json"}

    resp = com_retentativas(
        lambda: requests.post(url, headers=headers, params=params, json=payload, timeout=120),
        excecoes=(requests.exceptions.RequestException,),
        descricao="ElevenLabs",
    )
    if resp.status_code != 200:
        raise ErroNarracao(f"ElevenLabs retornou {resp.status_code}: {resp.text[:500]}")
    return resp.json()


def _elevenlabs_alignment_para_palavras(alignment: dict[str, Any]) -> list[dict[str, Any]]:
    chars = alignment.get("characters") or []
    inicios = alignment.get("character_start_times_seconds") or []
    fins = alignment.get("character_end_times_seconds") or []

    palavras: list[dict[str, Any]] = []
    buffer = ""
    ini_buffer = None
    fim_buffer = None
    for ch, ini, fim in zip(chars, inicios, fins):
        if ch.isspace():
            if buffer:
                palavras.append({"texto": buffer, "inicio": ini_buffer, "fim": fim_buffer})
                buffer = ""
                ini_buffer = None
        else:
            if buffer == "":
                ini_buffer = ini
            buffer += ch
            fim_buffer = fim
    if buffer:
        palavras.append({"texto": buffer, "inicio": ini_buffer, "fim": fim_buffer})
    return palavras


def _sintetizar_cena_elevenlabs(texto: str, cfg: dict[str, Any], mp3_path: Path) -> tuple[list[dict[str, Any]], float]:
    api_key = cfg["_env"]["ELEVENLABS_API_KEY"]
    voz_cfg = cfg["voz"]["elevenlabs"]
    dados = _elevenlabs_chamar_api(texto, voz_cfg, api_key)

    audio_bytes = base64.b64decode(dados["audio_base64"])
    mp3_path.write_bytes(audio_bytes)

    palavras = _elevenlabs_alignment_para_palavras(dados.get("alignment") or {})
    duracao = AudioSegment.from_file(mp3_path).duration_seconds
    return palavras, duracao


def _elevenlabs_listar_vozes(api_key: str) -> list[dict[str, Any]]:
    if not api_key:
        raise ErroNarracao("ELEVENLABS_API_KEY não configurada no .env.")
    resp = requests.get(ELEVENLABS_VOICES_URL, headers={"xi-api-key": api_key}, timeout=30)
    if resp.status_code != 200:
        raise ErroNarracao(f"ElevenLabs retornou {resp.status_code}: {resp.text[:500]}")

    normalizadas = []
    for v in resp.json().get("voices", []):
        labels = v.get("labels", {})
        extra = f"{labels.get('language', '')} {labels.get('description', '') or labels.get('accent', '')}".strip()
        normalizadas.append({"id": v["voice_id"], "nome": v.get("name", ""), "extra": extra})
    return normalizadas


# ------------------------------------------------------------------ edge-tts

async def _edge_tts_gerar_async(texto: str, voz_cfg: dict[str, Any], mp3_path: Path) -> list[dict[str, Any]]:
    import edge_tts

    communicate = edge_tts.Communicate(
        texto,
        voz_cfg["voice"],
        rate=voz_cfg.get("rate", "+0%"),
        volume=voz_cfg.get("volume", "+0%"),
        pitch=voz_cfg.get("pitch", "+0Hz"),
        boundary="WordBoundary",
    )
    palavras: list[dict[str, Any]] = []
    with open(mp3_path, "wb") as f:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                inicio = chunk["offset"] / 10_000_000
                fim = (chunk["offset"] + chunk["duration"]) / 10_000_000
                palavras.append({"texto": chunk["text"], "inicio": inicio, "fim": fim})
    return palavras


def _sintetizar_cena_edge(texto: str, cfg: dict[str, Any], mp3_path: Path) -> tuple[list[dict[str, Any]], float]:
    try:
        import edge_tts  # noqa: F401
    except ImportError as e:
        raise ErroNarracao("Pacote edge-tts não instalado. Rode: pip install edge-tts") from e

    voz_cfg = cfg["voz"]["edge_tts"]
    palavras = com_retentativas(
        lambda: asyncio.run(_edge_tts_gerar_async(texto, voz_cfg, mp3_path)),
        excecoes=(Exception,),
        descricao="edge-tts",
    )
    duracao = AudioSegment.from_file(mp3_path).duration_seconds
    return palavras, duracao


async def _edge_tts_listar_vozes_async() -> list[dict[str, Any]]:
    import edge_tts

    vozes = await edge_tts.list_voices()
    pt_br = [v for v in vozes if v["Locale"].lower() == "pt-br"]
    return [
        {"id": v["ShortName"], "nome": v.get("FriendlyName", v["ShortName"]), "extra": f"{v['Locale']} {v['Gender']}"}
        for v in (pt_br or vozes)
    ]


def _edge_tts_listar_vozes() -> list[dict[str, Any]]:
    try:
        import edge_tts  # noqa: F401
    except ImportError as e:
        raise ErroNarracao("Pacote edge-tts não instalado. Rode: pip install edge-tts") from e
    return asyncio.run(_edge_tts_listar_vozes_async())


# ------------------------------------------------------------- API pública

def sintetizar_cena(
    cena: dict[str, Any],
    cfg: dict[str, Any],
    diretorio_cache: Path,
    forcar: bool = False,
) -> dict[str, Any]:
    """Gera (ou reaproveita do cache) o áudio + alinhamento por palavra de uma cena."""
    diretorio_cache.mkdir(parents=True, exist_ok=True)
    texto = cena["narracao"]
    hash_atual = _hash_cena(texto, cfg)

    mp3_path = diretorio_cache / f"{cena['id']}.mp3"
    align_path = diretorio_cache / f"{cena['id']}.alignment.json"
    meta_path = diretorio_cache / f"{cena['id']}.meta.json"

    if not forcar and mp3_path.exists() and align_path.exists() and meta_path.exists():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        if meta.get("hash") == hash_atual:
            palavras = json.loads(align_path.read_text(encoding="utf-8"))
            duracao = AudioSegment.from_file(mp3_path).duration_seconds
            return {
                "cena": cena["numero"],
                "mp3_path": mp3_path,
                "alignment": {"palavras": palavras},
                "duracao_segundos": duracao,
                "cache": True,
            }

    motor = cfg["voz"]["motor"]
    if motor == "edge-tts":
        palavras, duracao = _sintetizar_cena_edge(texto, cfg, mp3_path)
    elif motor == "elevenlabs":
        palavras, duracao = _sintetizar_cena_elevenlabs(texto, cfg, mp3_path)
    else:
        raise ErroNarracao(f"voz.motor desconhecido: {motor!r} (use 'elevenlabs' ou 'edge-tts')")

    align_path.write_text(json.dumps(palavras, ensure_ascii=False), encoding="utf-8")
    meta_path.write_text(json.dumps({"hash": hash_atual}), encoding="utf-8")

    return {
        "cena": cena["numero"],
        "mp3_path": mp3_path,
        "alignment": {"palavras": palavras},
        "duracao_segundos": duracao,
        "cache": False,
    }


def _distribuir_palavras_proporcional(
    originais: list[str], inicio: float, fim: float
) -> list[dict[str, Any]]:
    pesos = [len(w) for w in originais]
    soma_pesos = sum(pesos) or 1
    duracao_total = fim - inicio
    palavras: list[dict[str, Any]] = []
    t = inicio
    for texto, peso in zip(originais, pesos):
        duracao = duracao_total * peso / soma_pesos
        palavras.append({"texto": texto, "inicio": t, "fim": t + duracao})
        t += duracao
    return palavras


def _corrigir_texto_palavras(
    cena: dict[str, Any], palavras: list[dict[str, Any]], duracao_segundos: float, avisos: list[str]
) -> None:
    originais = cena["narracao"].split()
    if len(originais) == len(palavras):
        for original, palavra in zip(originais, palavras):
            palavra["texto"] = original
        return

    avisos.append(
        f"Cena {cena['numero']}: contagem de palavras do roteiro ({len(originais)}) "
        f"!= do motor de voz ({len(palavras)}) — timing da legenda dessa cena foi estimado."
    )
    palavras[:] = _distribuir_palavras_proporcional(originais, 0.0, duracao_segundos)


def montar_narracao_completa(
    cenas: list[dict[str, Any]],
    cfg: dict[str, Any],
    diretorio_cache: Path,
    saida_dir: Path,
    forcar: bool = False,
) -> dict[str, Any]:
    """Sintetiza todas as cenas selecionadas, concatena com as pausas e
    devolve um timeline.json com o tempo de cada cena e de cada palavra."""
    saida_dir.mkdir(parents=True, exist_ok=True)
    pausa_seg = cfg["pausas"]["duracao_segundos"]

    trilha_final = AudioSegment.silent(duration=0)
    timeline: list[dict[str, Any]] = []
    offset = 0.0
    avisos: list[str] = []

    for cena in tqdm(cenas, desc="Narração", unit="cena"):
        resultado = sintetizar_cena(cena, cfg, diretorio_cache, forcar=forcar)
        _corrigir_texto_palavras(cena, resultado["alignment"]["palavras"], resultado["duracao_segundos"], avisos)
        audio = AudioSegment.from_file(resultado["mp3_path"])

        if cena.get("tipo") == "cta":
            # a tela final ("se inscreva") fica exibida pelo menos duracao_cta_segundos,
            # mesmo que a narração em si seja mais curta que isso
            duracao_min_ms = int(cfg["placeholders"]["duracao_cta_segundos"] * 1000)
            if len(audio) < duracao_min_ms:
                audio += AudioSegment.silent(duration=duracao_min_ms - len(audio))

        trilha_final += audio
        inicio = offset
        fim = offset + audio.duration_seconds
        timeline.append(
            {
                "numero": cena["numero"],
                "id": cena["id"],
                "tipo": cena.get("tipo", "normal"),
                "curto": cena.get("curto", False),
                "inicio": inicio,
                "fim": fim,
                "alignment_offset": inicio,
                "alignment": resultado["alignment"],
                "cache": resultado["cache"],
            }
        )
        offset = fim

        if cena.get("pausa_apos"):
            trilha_final += AudioSegment.silent(duration=int(pausa_seg * 1000))
            offset += pausa_seg

    narracao_path = saida_dir / "narracao_completa.mp3"
    trilha_final.export(narracao_path, format="mp3")

    timeline_path = saida_dir / "timeline.json"
    timeline_path.write_text(json.dumps(timeline, ensure_ascii=False, indent=2), encoding="utf-8")

    return {
        "narracao_path": narracao_path,
        "timeline_path": timeline_path,
        "timeline": timeline,
        "duracao_total_segundos": offset,
        "avisos": avisos,
    }


def listar_vozes(cfg: dict[str, Any]) -> list[dict[str, Any]]:
    motor = cfg["voz"]["motor"]
    if motor == "edge-tts":
        return _edge_tts_listar_vozes()
    return _elevenlabs_listar_vozes(cfg["_env"]["ELEVENLABS_API_KEY"])
