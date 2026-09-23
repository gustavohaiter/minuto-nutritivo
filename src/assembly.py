"""Montagem final do vídeo: Ken Burns, crossfade, trilha com ducking e legenda queimada."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from utils import ErroFFmpeg, checar_ffmpeg, probe_duration, rodar_ffmpeg


def _expressao_ken_burns(indice: int, n_frames: int, zoom_max: float, passo: float) -> tuple[str, str, str]:
    """Devolve (z, x, y) do filtro zoompan, variando a direção do pan por índice de cena."""
    z = f"min(zoom+{passo},{zoom_max})"
    variante = indice % 3
    if variante == 0:
        x, y = "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"
    elif variante == 1:
        x = f"(iw-iw/zoom)*(on/{max(n_frames,1)})"
        y = f"(ih-ih/zoom)*(on/{max(n_frames,1)})"
    else:
        x = f"(iw-iw/zoom)*(1-on/{max(n_frames,1)})"
        y = f"(ih-ih/zoom)*(on/{max(n_frames,1)})"
    return z, x, y


def construir_clip_imagem(
    imagem_path: Path,
    duracao: float,
    indice: int,
    cfg: dict[str, Any],
    destino: Path,
) -> None:
    largura, altura, fps = cfg["video"]["largura"], cfg["video"]["altura"], cfg["video"]["fps"]
    zoom_max = cfg["video"]["ken_burns"]["zoom_maximo"]
    passo = cfg["video"]["ken_burns"]["velocidade"]
    n_frames = max(int(round(duracao * fps)), 1)

    z, x, y = _expressao_ken_burns(indice, n_frames, zoom_max, passo)
    super_w, super_h = largura * 2, altura * 2

    vf = (
        f"scale={super_w}:{super_h}:force_original_aspect_ratio=increase,"
        f"crop={super_w}:{super_h},"
        f"zoompan=z='{z}':x='{x}':y='{y}':d=1:s={largura}x{altura}:fps={fps},"
        f"format=yuv420p"
    )
    rodar_ffmpeg(
        [
            "-loop", "1", "-i", str(imagem_path),
            "-t", f"{duracao:.3f}",
            "-vf", vf,
            "-r", str(fps),
            "-an",
            "-c:v", "libx264", "-preset", "medium", "-crf", "18",
            str(destino),
        ],
        descricao=f"(clip imagem {imagem_path.name})",
    )


def encadear_xfade(clipes: list[Path], transicao: float, fps: int, destino: Path) -> None:
    """Concatena clipes com crossfade. Cada clipe (exceto o último) já deve vir
    com `transicao` segundos extras de duração (padding) — ver montar_video()."""
    if len(clipes) == 1:
        rodar_ffmpeg(["-i", str(clipes[0]), "-c", "copy", str(destino)], descricao="(copiar clipe único)")
        return

    inputs: list[str] = []
    for c in clipes:
        inputs += ["-i", str(c)]

    duracoes = [probe_duration(c) for c in clipes]
    filtros = []
    label_atual = "0:v"
    acumulado = duracoes[0]
    for i in range(1, len(clipes)):
        offset = acumulado - transicao
        saida_label = f"x{i}"
        filtros.append(
            f"[{label_atual}][{i}:v]xfade=transition=fade:duration={transicao:.3f}:offset={offset:.3f}[{saida_label}]"
        )
        acumulado = acumulado + duracoes[i] - transicao
        label_atual = saida_label

    filtro_complexo = ";".join(filtros)
    rodar_ffmpeg(
        [
            *inputs,
            "-filter_complex", filtro_complexo,
            "-map", f"[{label_atual}]",
            "-r", str(fps),
            "-c:v", "libx264", "-preset", "medium", "-crf", "18",
            str(destino),
        ],
        descricao="(encadeamento xfade)",
    )


def montar_video(
    cenas: list[dict[str, Any]],
    timeline: list[dict[str, Any]],
    resultados_imagens: dict[int, dict[str, Any]],
    cfg: dict[str, Any],
    saida_dir: Path,
    diretorio_tmp: Path,
    duracao_total: float,
) -> dict[str, Any]:
    checar_ffmpeg()
    saida_dir.mkdir(parents=True, exist_ok=True)
    diretorio_tmp.mkdir(parents=True, exist_ok=True)

    avisos: list[str] = []
    transicao = cfg["video"]["transicao_segundos"]
    fps = cfg["video"]["fps"]

    # 1) monta lista ordenada de (caminho_imagem, duracao) por cena presente no timeline
    unidades: list[dict[str, Any]] = []
    for i, entrada in enumerate(timeline):
        numero = entrada["numero"]
        if i + 1 < len(timeline):
            duracao = timeline[i + 1]["inicio"] - entrada["inicio"]
        else:
            duracao = duracao_total - entrada["inicio"]
        if duracao <= 0:
            continue

        imagem_info = resultados_imagens.get(numero)
        if not imagem_info or not imagem_info.get("caminho"):
            avisos.append(f"Cena {numero} sem imagem disponível — pulei essa cena na montagem.")
            continue
        unidades.append({"numero": numero, "caminho": Path(imagem_info["caminho"]), "duracao": duracao})

    if not unidades:
        raise ValueError("Nenhuma cena com mídia disponível para montar o vídeo.")

    # 2) todas as unidades formam um único bloco de crossfade contínuo
    clipes_individuais = []
    for j, u in enumerate(unidades):
        pad = transicao if j < len(unidades) - 1 else 0.0
        destino = diretorio_tmp / f"cena_{u['numero']:02d}.mp4"
        construir_clip_imagem(u["caminho"], u["duracao"] + pad, j, cfg, destino)
        clipes_individuais.append(destino)

    video_sem_audio = diretorio_tmp / "video_sem_audio.mp4"
    encadear_xfade(clipes_individuais, transicao, fps, video_sem_audio)

    duracao_video = probe_duration(video_sem_audio)

    return {
        "video_sem_audio": video_sem_audio,
        "duracao_segundos": duracao_video,
        "avisos": avisos,
    }


def mixar_audio(
    narracao_path: Path,
    trilha_path: Path | None,
    duracao_total: float,
    cfg: dict[str, Any],
    destino: Path,
) -> None:
    audio_cfg = cfg["audio"]
    if trilha_path is None or not trilha_path.exists():
        rodar_ffmpeg(
            [
                "-i", str(narracao_path),
                # apad garante silêncio extra se a narração for um pouquinho mais
                # curta que o vídeo (arredondamento de frames no ffmpeg); sem isso
                # o -t sozinho não preenche, só corta, e o áudio final podia sair
                # mais curto que o vídeo (perdendo o fim da última cena no mux).
                "-af", "apad",
                "-t", f"{duracao_total:.3f}",
                "-c:a", "libmp3lame", "-q:a", "2", str(destino),
            ],
            descricao="(áudio só narração, sem trilha)",
        )
        return

    limiar_linear = 10 ** (audio_cfg["ducking_threshold_db"] / 20)
    filtro = (
        f"[1:a]volume={audio_cfg['volume_trilha_db']}dB[bgvol];"
        f"[bgvol][0:a]sidechaincompress=threshold={limiar_linear:.4f}:ratio={audio_cfg['ducking_ratio']}:attack=200:release=800[bgducked];"
        f"[0:a][bgducked]amix=inputs=2:duration=first:normalize=0[mix];"
        f"[mix]apad[saida]"
    )
    rodar_ffmpeg(
        [
            "-i", str(narracao_path),
            "-stream_loop", "-1", "-i", str(trilha_path),
            "-filter_complex", filtro,
            "-map", "[saida]",
            "-t", f"{duracao_total:.3f}",
            "-c:a", "libmp3lame", "-q:a", "2",
            str(destino),
        ],
        descricao="(mixagem narração + trilha com ducking)",
    )


def queimar_legenda(video_sem_audio: Path, ass_path: Path, cfg: dict[str, Any], destino: Path) -> None:
    """Queima o .ass (gerado por subtitles.gerar_ass) no vídeo. Usamos .ass com
    PlayRes explícito em vez do filtro subtitles+force_style em cima do .srt
    porque o auto-wrap do ffmpeg pro .srt ignora a resolução real do vídeo e
    duplica as quebras de linha."""
    fps = cfg["video"]["fps"]
    ass_escapado = str(ass_path).replace("\\", "/").replace(":", "\\:")
    rodar_ffmpeg(
        [
            "-i", str(video_sem_audio),
            "-vf", f"ass='{ass_escapado}'",
            "-r", str(fps),
            "-c:v", "libx264", "-preset", "medium", "-crf", "18",
            # profile/level/pix_fmt "clássicos" — evita o erro "configurações de
            # codificação sem suporte" que o app Reprodutor Multimídia do Windows
            # dá com High Profile em níveis mais altos ou chroma fora de 4:2:0.
            "-pix_fmt", "yuv420p", "-profile:v", "high", "-level", "4.0",
            str(destino),
        ],
        descricao="(queima de legenda)",
    )


def juntar_video_audio(video_path: Path, audio_path: Path, destino: Path) -> None:
    dur_video = probe_duration(video_path)
    dur_audio = probe_duration(audio_path)
    if abs(dur_video - dur_audio) > 2.0:
        raise ErroFFmpeg(
            f"Vídeo ({dur_video:.1f}s) e áudio ({dur_audio:.1f}s) com duração muito diferente antes do "
            "mux final — provavelmente narração/imagens foram geradas pra uma seleção de cenas diferente "
            "da que está sendo montada agora. Rode `python main.py narracao` + `imagens` + `legendas` de "
            "novo com a MESMA seleção de --cenas antes da montagem (ou use `python main.py tudo`)."
        )
    rodar_ffmpeg(
        [
            "-i", str(video_path),
            "-i", str(audio_path),
            "-map", "0:v:0", "-map", "1:a:0",
            "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
            "-movflags", "+faststart",
            "-shortest",
            str(destino),
        ],
        descricao="(mux final vídeo + áudio)",
    )
