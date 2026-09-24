#!/usr/bin/env python3
"""Orquestrador do pipeline roteiro -> vídeo (Minuto Nutritivo).

`python main.py tudo` gera automaticamente:
  - saida/video_final.mp4          (vídeo normal, todas as cenas)
  - saida/curto/video_final.mp4    (Short, só as cenas marcadas "curto: sim")
  - saida/descricao_youtube.txt
  - saida/thumbnail.png            (só se o roteiro.md tiver o cabeçalho "Miniatura: N | texto")

Exemplos:
    python main.py parse
    python main.py verificar
    python main.py estimar
    python main.py tudo
    python main.py miniatura --cena 2 --texto "..."
    python main.py descricao
"""
from __future__ import annotations

import argparse
import copy
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

import assembly as assemblymod  # noqa: E402
import avisos as avisosmod  # noqa: E402
import config as configmod  # noqa: E402
import cta as ctamod  # noqa: E402
import images as imagesmod  # noqa: E402
import narration as narrationmod  # noqa: E402
import parser as parsermod  # noqa: E402
import subtitles as subtitlesmod  # noqa: E402
import thumbnail as thumbnailmod  # noqa: E402


def _carregar_dados_roteiro(cfg):
    caminho_roteiro = configmod.caminho(cfg, "roteiro")
    if not caminho_roteiro.exists():
        print(f"{caminho_roteiro} não encontrado. Confira o caminho em config.yaml -> caminhos.roteiro.")
        sys.exit(1)
    dados = parsermod.parse_roteiro(caminho_roteiro)
    if not dados["cenas"]:
        print(f"{caminho_roteiro} não tem nenhuma cena (## Cena NN) — confira a formatação do arquivo.")
        sys.exit(1)
    if dados.get("cta_automatico"):
        n = dados["cenas"][-1]["numero"]
        print(
            f"Cena {n} (CTA \"se inscreva\") adicionada automaticamente — não havia nenhuma cena com "
            "tipo: cta no roteiro.md. Edite a narração dela em cenas.json ou adicione a cena manualmente "
            "no roteiro.md se quiser personalizar o texto."
        )
    parsermod.salvar_cenas_json(dados, configmod.caminho(cfg, "cenas_json"))
    return dados


def _carregar_cenas_selecionadas(cfg, selecao):
    dados = _carregar_dados_roteiro(cfg)
    return parsermod.filtrar_cenas(dados["cenas"], selecao)


def _cfg_para_curto(cfg):
    """Cópia do cfg com video/legendas substituídos pelas chaves de shorts.* —
    o Short é vertical e tem legenda mais compacta; o resto (voz, imagens,
    trilha etc.) continua igual ao vídeo normal."""
    cfg_curto = copy.deepcopy(cfg)
    overrides = cfg.get("shorts", {})
    for secao in ("video", "legendas"):
        if secao in overrides:
            cfg_curto[secao].update(overrides[secao])
    return cfg_curto


def cmd_parse(args, cfg):
    dados = parsermod.parse_roteiro(configmod.caminho(cfg, "roteiro"))
    destino = configmod.caminho(cfg, "cenas_json")
    parsermod.salvar_cenas_json(dados, destino)
    print(f"{len(dados['cenas'])} cenas -> {destino}")
    if dados.get("cta_automatico"):
        print(f"Cena {dados['cenas'][-1]['numero']} (CTA \"se inscreva\") adicionada automaticamente.")


def cmd_verificar(args, cfg):
    cenas = _carregar_cenas_selecionadas(cfg, args.cenas)
    problemas: list[str] = []
    avisos: list[str] = []

    motor = cfg["voz"]["motor"]
    if motor == "elevenlabs":
        if not cfg["_env"]["ELEVENLABS_API_KEY"]:
            problemas.append("ELEVENLABS_API_KEY não configurada no .env (motor atual: elevenlabs).")
        if not cfg["voz"]["elevenlabs"].get("voice_id"):
            problemas.append("voz.elevenlabs.voice_id vazio no config.yaml — rode `python main.py vozes`.")

    trilha_path = configmod.caminho(cfg, "trilha")
    if not trilha_path.exists():
        avisos.append(f"{trilha_path} não existe — o vídeo final vai sair só com narração, sem música de fundo.")

    manual_dir = configmod.caminho(cfg, "imagens_manuais")
    tem_pexels = bool(cfg["_env"]["PEXELS_API_KEY"])
    tem_pixabay = bool(cfg["_env"]["PIXABAY_API_KEY"])
    n_manual = n_stock = n_sem_fonte = 0
    for c in cenas:
        tem_manual = any((manual_dir / f"{c['id']}{ext}").exists() for ext in imagesmod.EXTENSOES_MANUAIS)
        if tem_manual:
            n_manual += 1
            continue
        if c["imagem_busca"]:
            if tem_pexels or tem_pixabay:
                n_stock += 1
            else:
                problemas.append(
                    f"Cena {c['numero']}: sem imagem manual e sem PEXELS_API_KEY/PIXABAY_API_KEY configurada."
                )
        elif c.get("tipo") == "cta":
            continue
        else:
            n_sem_fonte += 1
            problemas.append(f"Cena {c['numero']}: sem imagem manual e sem imagem_busca preenchida no roteiro.md.")

    n_curto = sum(1 for c in cenas if c.get("curto"))
    info_custo = narrationmod.estimar_caracteres(cenas)
    print(f"Cenas: {len(cenas)} | caracteres: {info_custo['total_caracteres']} | marcadas p/ Short: {n_curto}")
    print(f"Imagens: {n_manual} manual(is), {n_stock} via banco de imagens, {n_sem_fonte} sem fonte nenhuma")
    if n_curto == 0:
        avisos.append("Nenhuma cena marcada com 'curto: sim' — só o vídeo normal vai ser gerado, sem Short.")

    if avisos:
        print("\nAVISOS (não bloqueiam, mas confira):")
        for a in avisos:
            print(" -", a)

    if problemas:
        print("\nPROBLEMAS (corrija antes de rodar `tudo`):")
        for p in problemas:
            print(" -", p)
        sys.exit(1)

    print("\nTudo certo — pode rodar `python main.py tudo`.")


def cmd_estimar(args, cfg):
    cenas = _carregar_cenas_selecionadas(cfg, args.cenas)
    info = narrationmod.estimar_caracteres(cenas)
    motor = cfg["voz"]["motor"]
    print(f"Cenas consideradas: {len(cenas)}")
    print(f"Total de caracteres de narração: {info['total_caracteres']}")
    if motor == "edge-tts":
        print("Motor atual: edge-tts — 100% grátis, esse número é só informativo (não há custo).")
    else:
        print("Motor atual: elevenlabs — confira o custo por caractere do seu plano antes de rodar tudo.")


def cmd_vozes(args, cfg):
    motor = cfg["voz"]["motor"]
    vozes = narrationmod.listar_vozes(cfg)
    if not vozes:
        print("Nenhuma voz encontrada.")
        return
    for v in vozes:
        print(f"{v['id']:<28} |  {v['nome']:<24} |  {v['extra']}")
    if motor == "edge-tts":
        print("\nCopie o id (ex.: pt-BR-FranciscaNeural) para voz.edge_tts.voice em config.yaml.")
    else:
        print("\nCopie o id desejado para voz.elevenlabs.voice_id em config.yaml.")


def _rodar_narracao(cenas, cfg, forcar, saida_dir):
    cache_dir = configmod.caminho(cfg, "cache") / "audio"
    resultado = narrationmod.montar_narracao_completa(cenas, cfg, cache_dir, saida_dir, forcar=forcar)
    (saida_dir / "narracao_meta.json").write_text(
        json.dumps({"duracao_total_segundos": resultado["duracao_total_segundos"]}), encoding="utf-8"
    )
    print(f"Narração pronta: {resultado['narracao_path']} ({resultado['duracao_total_segundos']:.1f}s)")
    for aviso in resultado["avisos"]:
        print("AVISO:", aviso)
    return resultado


def _rodar_imagens(cenas, cfg, forcar, saida_dir):
    manual_dir = configmod.caminho(cfg, "imagens_manuais")
    cache_dir = configmod.caminho(cfg, "cache") / "images"
    resultados = {}
    avisos = []
    for cena in cenas:
        if cena.get("tipo") == "cta":
            largura, altura = cfg["video"]["largura"], cfg["video"]["altura"]
            destino_cta = cache_dir / f"_cta_{largura}x{altura}.png"
            if forcar or not destino_cta.exists():
                ctamod.gerar_tela_cta(cfg, destino_cta)
            resultados[cena["numero"]] = {
                "numero": cena["numero"],
                "caminho": destino_cta,
                "fonte": "Identidade",
                "autor": "Minuto Nutritivo",
                "link": "",
            }
            continue
        r = imagesmod.obter_imagem_para_cena(cena, cfg, manual_dir, cache_dir, forcar=forcar)
        if r.get("caminho") and cena.get("aviso_tela"):
            largura, altura = cfg["video"]["largura"], cfg["video"]["altura"]
            # inclui as dimensões no nome — normal (horizontal) e Short (vertical)
            # cortam a imagem em proporções diferentes e não podem reaproveitar o
            # mesmo arquivo em cache
            destino_aviso = cache_dir / f"{cena['id']}_aviso_{largura}x{altura}.png"
            if forcar or not destino_aviso.exists():
                avisosmod.aplicar_aviso_tela(Path(r["caminho"]), cena["aviso_tela"], cfg, destino_aviso)
            r = {**r, "caminho": destino_aviso}
        resultados[cena["numero"]] = r
        if r.get("aviso"):
            avisos.append(r["aviso"])
    imagesmod.gerar_creditos_txt(resultados, saida_dir / "creditos.txt")

    persistido = {
        str(numero): {k: (str(v) if isinstance(v, Path) else v) for k, v in info.items()}
        for numero, info in resultados.items()
    }
    (saida_dir / "imagens_resultado.json").write_text(json.dumps(persistido, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Imagens processadas: {len(resultados)} cena(s) — créditos em {saida_dir / 'creditos.txt'}")
    for aviso in avisos:
        print("AVISO:", aviso)
    return {"resultados": resultados, "avisos": avisos}


def _rodar_legendas(timeline, cfg, saida_dir):
    srt_path = subtitlesmod.gerar_srt(timeline, cfg, saida_dir / "legendas.srt")
    ass_path = subtitlesmod.gerar_ass(timeline, cfg, saida_dir / "legendas_burn.ass")
    print(f"Legendas geradas: {srt_path}")
    return ass_path


def _rodar_montagem(cenas, cfg, timeline, resultados_imagens, duracao_total, ass_path, saida_dir, tmp_dir):
    res_video = assemblymod.montar_video(cenas, timeline, resultados_imagens, cfg, saida_dir, tmp_dir, duracao_total)
    for aviso in res_video["avisos"]:
        print("AVISO:", aviso)

    trilha_path = configmod.caminho(cfg, "trilha")
    if not trilha_path.exists():
        trilha_path = None
        print("AVISO: trilha.mp3 não encontrada — vídeo vai sair só com narração.")

    audio_final = saida_dir / "audio_final.mp3"
    assemblymod.mixar_audio(saida_dir / "narracao_completa.mp3", trilha_path, res_video["duracao_segundos"], cfg, audio_final)

    video_legenda = tmp_dir / "video_com_legenda.mp4"
    assemblymod.queimar_legenda(res_video["video_sem_audio"], ass_path, cfg, video_legenda)

    video_final = saida_dir / "video_final.mp4"
    assemblymod.juntar_video_audio(video_legenda, audio_final, video_final)
    print(f"Vídeo: {video_final}")
    return video_final


def _gerar_saida_completa(cenas, cfg, forcar, saida_dir, tmp_dir, rotulo):
    print(f"\n=== {rotulo} ({len(cenas)} cena(s)) ===")
    saida_dir.mkdir(parents=True, exist_ok=True)
    resultado_narr = _rodar_narracao(cenas, cfg, forcar, saida_dir)
    resultado_img = _rodar_imagens(cenas, cfg, forcar, saida_dir)
    ass_path = _rodar_legendas(resultado_narr["timeline"], cfg, saida_dir)
    video_final = _rodar_montagem(
        cenas, cfg, resultado_narr["timeline"], resultado_img["resultados"],
        resultado_narr["duracao_total_segundos"], ass_path, saida_dir, tmp_dir,
    )
    return video_final, resultado_narr["duracao_total_segundos"]


def cmd_narracao(args, cfg):
    cenas = _carregar_cenas_selecionadas(cfg, args.cenas)
    _rodar_narracao(cenas, cfg, args.forcar, configmod.caminho(cfg, "saida"))


def cmd_imagens(args, cfg):
    cenas = _carregar_cenas_selecionadas(cfg, args.cenas)
    _rodar_imagens(cenas, cfg, args.forcar, configmod.caminho(cfg, "saida"))


def cmd_legendas(args, cfg):
    saida_dir = configmod.caminho(cfg, "saida")
    timeline_path = saida_dir / "timeline.json"
    if not timeline_path.exists():
        print("timeline.json não existe — rode `python main.py narracao` primeiro.")
        sys.exit(1)
    timeline = json.loads(timeline_path.read_text(encoding="utf-8"))
    _rodar_legendas(timeline, cfg, saida_dir)


def _remontar(cenas, cfg, saida_dir, tmp_dir, rotulo):
    timeline_path = saida_dir / "timeline.json"
    meta_path = saida_dir / "narracao_meta.json"
    imagens_path = saida_dir / "imagens_resultado.json"
    ass_path = saida_dir / "legendas_burn.ass"
    for p, dica in ((timeline_path, "narracao"), (meta_path, "narracao"), (imagens_path, "imagens"), (ass_path, "legendas")):
        if not p.exists():
            print(f"{p.name} não existe — rode `python main.py {dica}` primeiro (ou use `python main.py tudo`).")
            sys.exit(1)

    timeline = json.loads(timeline_path.read_text(encoding="utf-8"))
    duracao_total = json.loads(meta_path.read_text(encoding="utf-8"))["duracao_total_segundos"]
    resultados_imagens = {int(k): v for k, v in json.loads(imagens_path.read_text(encoding="utf-8")).items()}

    numeros_pedidos = {c["numero"] for c in cenas}
    numeros_timeline = {e["numero"] for e in timeline}
    if numeros_pedidos != numeros_timeline:
        print(
            f"ERRO ({rotulo}): --cenas não bate com o que está em {timeline_path} — rode `narracao`/`imagens` de "
            "novo com a mesma seleção, ou use `python main.py tudo`."
        )
        sys.exit(1)

    print(f"\n=== {rotulo} ===")
    _rodar_montagem(cenas, cfg, timeline, resultados_imagens, duracao_total, ass_path, saida_dir, tmp_dir)


def cmd_montagem(args, cfg):
    cenas = _carregar_cenas_selecionadas(cfg, args.cenas)
    saida_dir = configmod.caminho(cfg, "saida")
    tmp_dir = configmod.caminho(cfg, "cache") / "tmp_montagem"
    _remontar(cenas, cfg, saida_dir, tmp_dir, "Vídeo normal")

    # remonta o Short também, se ele já tiver sido gerado antes (senão essa
    # pasta nem existe ainda) — sem isso, um `montagem` avulso (ex.: só pra
    # trocar a trilha) deixava o Short desatualizado, com a versão antiga.
    saida_curto = saida_dir / "curto"
    if (saida_curto / "timeline.json").exists():
        cenas_curto = [c for c in cenas if c.get("curto")]
        tmp_curto = configmod.caminho(cfg, "cache") / "tmp_montagem_curto"
        _remontar(cenas_curto, _cfg_para_curto(cfg), saida_curto, tmp_curto, "Short")


def cmd_tudo(args, cfg):
    dados = _carregar_dados_roteiro(cfg)
    cenas = parsermod.filtrar_cenas(dados["cenas"], args.cenas)
    saida_dir = configmod.caminho(cfg, "saida")
    tmp_dir = configmod.caminho(cfg, "cache") / "tmp_montagem"

    _gerar_saida_completa(cenas, cfg, args.forcar, saida_dir, tmp_dir, "Vídeo normal")

    cenas_curto = [c for c in cenas if c.get("curto")]
    if cenas_curto:
        saida_curto = saida_dir / "curto"
        tmp_curto = configmod.caminho(cfg, "cache") / "tmp_montagem_curto"
        _, duracao_curto = _gerar_saida_completa(
            cenas_curto, _cfg_para_curto(cfg), args.forcar, saida_curto, tmp_curto, "Short"
        )

        limite = cfg["shorts"]["duracao_maxima_segundos"]
        if duracao_curto > limite:
            print(
                f"\nAVISO: o Short saiu com {duracao_curto:.1f}s, acima do limite de {limite}s do YouTube Shorts. "
                "Marque menos cenas com 'curto: sim' no roteiro."
            )
        else:
            print(f"\nShort dentro do limite: {duracao_curto:.1f}s / {limite}s.")
    else:
        print("\nNenhuma cena marcada com 'curto: sim' no roteiro — Short não foi gerado.")

    print()
    _gerar_descricao(dados, cfg)

    if dados.get("miniatura_cena"):
        _gerar_miniatura(dados, dados["miniatura_cena"], dados["miniatura_texto"], cfg)
    else:
        print(
            "Miniatura não gerada automaticamente — roteiro.md não tem um cabeçalho \"Miniatura: N | texto\". "
            'Gere na mão: python main.py miniatura --cena N --texto "SEU TEXTO"'
        )


def _gerar_miniatura(dados, cena_numero, texto, cfg):
    cena = next((c for c in dados["cenas"] if c["numero"] == cena_numero), None)
    if not cena:
        print(f"Cena {cena_numero} não encontrada no roteiro — miniatura não gerada.")
        return None

    manual_dir = configmod.caminho(cfg, "imagens_manuais")
    cache_dir = configmod.caminho(cfg, "cache") / "images"
    resultado = imagesmod.obter_imagem_para_cena(cena, cfg, manual_dir, cache_dir)
    if not resultado.get("caminho"):
        print(f"Cena {cena_numero} sem imagem disponível ({resultado.get('aviso', 'sem detalhes')}) — miniatura não gerada.")
        return None

    saida_dir = configmod.caminho(cfg, "saida")
    saida_dir.mkdir(parents=True, exist_ok=True)
    destino = saida_dir / "thumbnail.png"
    thumbnailmod.gerar_thumbnail(Path(resultado["caminho"]), texto, cfg, destino)
    print(f"Miniatura gerada: {destino}")
    return destino


def cmd_miniatura(args, cfg):
    dados = _carregar_dados_roteiro(cfg)
    if not _gerar_miniatura(dados, args.cena, args.texto, cfg):
        sys.exit(1)


TAGS_FIXAS = ["minuto nutritivo", "nutrição", "alimentação saudável", "vida saudável", "dicas de saúde"]


def _gerar_tags(titulo: str) -> list[str]:
    # o padrão de título do canal é "[N] BENEFÍCIOS D[O/A/OS/AS] <alimento>" —
    # extrai o nome do alimento pra gerar tags específicas do vídeo, além
    # das fixas do canal
    m = re.search(r"(?i)benefícios\s+(d[oa]s?)\s+(.+)$", titulo.strip())
    if not m:
        return [titulo.lower(), *TAGS_FIXAS]
    prep, alimento = m.group(1).lower(), m.group(2).strip().lower()
    return [alimento, f"benefícios {prep} {alimento}", f"{alimento} benefícios", *TAGS_FIXAS]


def _gerar_descricao(dados, cfg):
    titulo = dados["titulo"]
    resumo = " ".join(c["narracao"].strip() for c in dados["cenas"][:3])
    tags = _gerar_tags(titulo)

    texto = f"""TÍTULO SUGERIDO:
{titulo} | Minuto Nutritivo

DESCRIÇÃO:
{resumo}

Este conteúdo é educativo e não substitui orientação de nutricionista ou médico.

Minuto Nutritivo — benefícios de alimentos em vídeos rápidos, toda semana.
Se inscreva e ative o sininho.

#nutricao #alimentacaosaudavel #minutonutritivo

TAGS SUGERIDAS (cole na caixa "Tags" do YouTube Studio, em Opções avançadas):
{", ".join(tags)}
""".strip() + "\n"

    saida_dir = configmod.caminho(cfg, "saida")
    saida_dir.mkdir(parents=True, exist_ok=True)
    destino = saida_dir / "descricao_youtube.txt"
    destino.write_text(texto, encoding="utf-8")
    print(f"Rascunho de título/descrição gerado: {destino}")
    return destino


def cmd_descricao(args, cfg):
    dados = _carregar_dados_roteiro(cfg)
    _gerar_descricao(dados, cfg)


def main():
    parser_cli = argparse.ArgumentParser(description="Pipeline roteiro -> vídeo (Minuto Nutritivo)")
    parser_cli.add_argument("--config", default="config.yaml", help="Caminho do config.yaml")
    sub = parser_cli.add_subparsers(dest="comando", required=True)

    def add_cenas_forcar(p):
        p.add_argument("--cenas", default=None, help='Ex.: "1-4" ou "1,3,5". Padrão: todas.')
        p.add_argument("--forcar", action="store_true", help="Ignora o cache e regenera tudo.")

    sub.add_parser("parse", help="roteiro.md -> cenas.json")

    p = sub.add_parser("verificar", help="Checagem rápida antes de rodar `tudo`")
    p.add_argument("--cenas", default=None)

    p = sub.add_parser("estimar", help="Estima caracteres de narração (custo ElevenLabs)")
    p.add_argument("--cenas", default=None)

    sub.add_parser("vozes", help="Lista vozes disponíveis")

    p = sub.add_parser("narracao", help="Gera só a narração")
    add_cenas_forcar(p)

    p = sub.add_parser("imagens", help="Busca só as imagens")
    add_cenas_forcar(p)

    sub.add_parser("legendas", help="Gera .srt/.ass a partir do timeline.json já existente")

    p = sub.add_parser("montagem", help="Monta o vídeo a partir do que já foi gerado")
    p.add_argument("--cenas", default=None)

    p = sub.add_parser("tudo", help="Roda o pipeline completo — gera vídeo normal E, se houver cenas 'curto: sim', o Short")
    add_cenas_forcar(p)

    p = sub.add_parser("miniatura", help="Gera saida/thumbnail.png a partir da imagem de uma cena + texto")
    p.add_argument("--cena", type=int, required=True)
    p.add_argument("--texto", required=True)

    sub.add_parser("descricao", help="Gera saida/descricao_youtube.txt")

    args = parser_cli.parse_args()
    cfg = configmod.carregar_config(args.config)

    comandos = {
        "parse": cmd_parse,
        "verificar": cmd_verificar,
        "estimar": cmd_estimar,
        "vozes": cmd_vozes,
        "narracao": cmd_narracao,
        "imagens": cmd_imagens,
        "legendas": cmd_legendas,
        "montagem": cmd_montagem,
        "tudo": cmd_tudo,
        "miniatura": cmd_miniatura,
        "descricao": cmd_descricao,
    }
    comandos[args.comando](args, cfg)


if __name__ == "__main__":
    main()
