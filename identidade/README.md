# Identidade do canal — Minuto Nutritivo

## Marca
- **Nome**: Minuto Nutritivo
- **Tom**: leve, energético, educativo — nada de linguagem clínica pesada.
- **Cores**: verde `#3A9157` (saúde/natural) + laranja `#E69138` (energia/apetite).
- **Tipografia**: DejaVu Sans Bold — moderna e arredondada, sem o peso "documental" do outro canal.

## Aviso obrigatório em toda descrição
Como é conteúdo de saúde/nutrição, toda descrição inclui: *"Este conteúdo é
educativo e não substitui orientação de nutricionista ou médico."* — já sai
assim automaticamente em `python main.py descricao`, não precisa lembrar.

## Logo/avatar
3 opções geradas via OpenArt, registradas em `registro.json`. Baixe pelo seu PC
(CDN da OpenArt não é acessível pelo sandbox):

```cmd
git pull
scripts\baixar_logos.bat
```

Escolha a que mais gostou, salve como `identidade/logo_escolhido.png` e rode:

```cmd
python scripts\gerar_avatar_banner.py
```

Isso gera `avatar_800x800.png` (upload no YouTube) e `banner_2560x1440.png`
(arte de capa, texto dentro da área segura).

## Vinheta — recomendo não usar
Diferente do Dossiê Obscuro, aqui eu não incluí vinheta de abertura. Com o
vídeo já tendo só 1-2 minutos (e o Short até 60s), 5 segundos de intro
consomem uma fatia grande demais do tempo total — o público de conteúdo
rápido costuma abandonar se não vir a informação logo de cara. Se quiser
mesmo assim, dá pra adicionar depois.
