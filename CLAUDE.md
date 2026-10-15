# Instruções permanentes — Minuto Nutritivo

- **Toda vez que eu montar um roteiro novo, já decido sozinho a miniatura**
  (atualizado — antes eu pedia aprovação primeiro, não pede mais): escolho o
  texto (curto, impactante, maiúsculas — estilo "ISSO O ALHO FAZ PELO
  CORAÇÃO") e a cena cuja imagem uso de fundo, e já deixo o cabeçalho
  `Miniatura: N | TEXTO` no `roteiro.md` desde a primeira versão, pra sair
  pronto no `python main.py tudo` sem passo extra. Se o usuário não gostar,
  ele troca manualmente (me pede ajuste ou edita o roteiro.md direto) — não
  preciso mais esperar aprovação antes de gerar.
- **`imagem_busca` precisa ter o alimento principal como palavra dominante,
  sozinho — sem citar um segundo alimento junto** (ex.: "avocado ... lemon",
  "avocado ... olive oil"). O banco de imagens (Pexels/Pixabay) não garante
  que o alimento principal apareça em destaque quando o termo cita dois
  alimentos — às vezes traz o secundário sozinho (limão em vez de abacate,
  azeitona em vez de azeite sendo servido). Antes de fechar um roteiro,
  reviso cena por cena se o termo de busca tem essa ambiguidade e, se tiver,
  removo o alimento secundário do termo ou uso uma variedade/formato mais
  específico (mesma lógica do "navel orange" pra evitar tangerina).
- **Regras de imagem (definidas pelo usuário, aplicar sempre, todo roteiro):**
  - Quando o usuário já manda o `imagem_busca` pronto na linha "Imagem:" do
    roteiro, uso exatamente como veio — não simplifico nem traduzo. Só ajusto
    se eu mesmo notar a ambiguidade do item acima (dois alimentos citados).
  - Nunca busco pelo nome em português puro de um alimento cujo nome em
    inglês pode ser confundido com outra coisa (ex.: "manga" sozinho traz
    quadrinho japonês e manga de roupa) — sempre uso o termo em inglês
    correto + "fruit"/"vegetable"/"food" quando fizer sentido.
  - Orientação paisagem, alta resolução, fundo limpo (já garantido pelo
    `config.yaml`: `imagens.orientacao: landscape`, `largura_minima`).
  - Pessoas em destaque, ilustração/desenho, infográfico com texto em outro
    idioma, logo de marca e texto sobreposto na foto não dá pra filtrar
    automaticamente (sem modelo de visão) — por isso a folha de contato
    (abaixo) existe: é o usuário que faz essa checagem final.
  - **Toda vez que `imagens`/`tudo` roda, gera automaticamente
    `saida/revisao_imagens.jpg`** (todas as imagens buscadas, numeradas por
    cena, pra conferência rápida antes da montagem — ver `src/revisao.py`).
    Isso já é automático, não precisa pedir de novo em cada roteiro.
  - **Nunca usar termo técnico/botânico fortemente associado a OUTRA fruta
    específica**, mesmo com o nome do alimento principal junto no termo (ex.:
    "pith" é quase só usado pra citros — "passion fruit ... pith" devolveu
    casca de laranja/limão em vez de maracujá, igual o problema do
    "lemon"/"olive oil" com abacate). Antes de fechar o termo de busca,
    pergunto: essa palavra, sozinha, me faria pensar em outra fruta? Se sim,
    troco por um termo mais genérico/descritivo (ex.: "rind", "inner layer",
    "skin cross section") que não carrega esse viés.
  - **Alimento regional/pouco conhecido fora do Brasil (ex.: jabuticaba,
    caju, açaí, cupuaçu)**: o banco de imagens tem pouco acervo e às vezes
    devolve fruta parecida errada (jabuticaba -> uva ou mirtilo). Sempre
    incluo "brazil"/"brazilian" no termo de busca dessas cenas — todas,
    não só a primeira — e aviso o usuário no fim pra conferir a folha de
    contato com atenção redobrada nelas, já indicando que pode precisar
    cair pra imagem manual (`imagens_manuais/<id_da_cena>.jpg`).
