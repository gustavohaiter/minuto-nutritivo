# Minuto Nutritivo — pipeline roteiro → vídeo

Gera automaticamente, a partir de um `roteiro.md`, **dois vídeos**:
- `saida/video_final.mp4` — vídeo normal (vertical 9:16, 1-2 min)
- `saida/curto/video_final.mp4` — Short (≤60s, feito das cenas marcadas `curto: sim`)

Reaproveita a mesma arquitetura validada no canal Dossiê Obscuro: narração com
timestamp por palavra (ElevenLabs ou edge-tts grátis), busca de imagem
(Pexels/Pixabay, com fallback manual), Ken Burns + crossfade, legenda queimada,
trilha com ducking automático.

## 1. Setup

```bash
pip install -r requirements.txt
cp .env.example .env   # preencha as chaves que for usar
```

Chaves em `.env` (todas opcionais — sem elas o pipeline ainda funciona, só
avisa o que não vai dar pra fazer):
- `ELEVENLABS_API_KEY` — só se `voz.motor: elevenlabs` no config.yaml
- `PEXELS_API_KEY` / `PIXABAY_API_KEY` — pra buscar fotos automaticamente

FFmpeg precisa estar instalado e no PATH.

## 2. Formato do roteiro.md

```markdown
# 5 BENEFÍCIOS DO ABACATE
Tipo: educativo

## Cena 01
- narracao: Você sabia que o abacate pode fazer muito bem pro seu coração?
- imagem_busca: avocado closeup fresh
- curto: sim

## Cena 02
- narracao: Ele é rico em gorduras boas, que ajudam a controlar o colesterol.
- imagem_busca: avocado sliced healthy food
- curto: sim
```

- `narracao`: texto exato que vira fala.
- `imagem_busca`: termo em inglês pra achar foto (já busca vertical automaticamente).
- `imagem_manual: sim`: usa `imagens_manuais/cena_XX.png` em vez de buscar.
- `curto: sim`: essa cena entra no Short também. Marque as cenas mais fortes —
  juntas não podem passar de 60s (o pipeline avisa se passar).
- `[PAUSA]`: meio segundo de silêncio antes da próxima cena.

## 3. Rodando

```bash
python main.py parse        # roteiro.md -> cenas.json
python main.py verificar    # checagem rápida antes de gastar tempo/crédito
python main.py estimar      # custo em caracteres (só relevante pro ElevenLabs)
python main.py tudo         # gera video_final.mp4 E o Short (se tiver cena "curto")
python main.py miniatura --cena 1 --texto "SEU TEXTO AQUI"
python main.py descricao
```

Use `--forcar` em `narracao`/`imagens`/`tudo` pra ignorar cache e regerar do zero.
`--cenas "1-4"` roda só um recorte, útil pra testar antes do roteiro inteiro.

## 4. Saída

Tudo em `saida/` (vídeo normal) e `saida/curto/` (Short):
- `video_final.mp4` — 1080x1920, 30fps, narração + trilha + legenda queimada.
- `legendas.srt`, `creditos.txt`, `descricao_youtube.txt`, `thumbnail.png`.

## 5. Reaproveitando pra outro vídeo

Troque só o `roteiro.md` (e as imagens manuais, se usar) e rode de novo — nada
mais precisa mudar. `cache/` guarda áudio/imagem por cena (hash do texto), então
trocar só uma cena não regera as outras.
