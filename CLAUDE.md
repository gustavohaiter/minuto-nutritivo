# Instruções permanentes — Minuto Nutritivo

- **Sempre que eu montar/ajustar um roteiro novo, tenho que sugerir 2-3
  ideias de texto para a miniatura** (curto, impactante, maiúsculas — estilo
  "ISSO O ALHO FAZ PELO CORAÇÃO"), mesmo sem o usuário pedir. Ele decide entre
  as opções (ou pede outra) e eu só gero `saida/thumbnail.png` depois disso —
  nunca decido o texto sozinho sem apresentar opções primeiro.
- Se o usuário aprovar um texto, ofereço adicionar o cabeçalho `Miniatura: N | TEXTO`
  no `roteiro.md` pra isso sair automático no próximo `python main.py tudo`.
- **`imagem_busca` precisa ter o alimento principal como palavra dominante,
  sozinho — sem citar um segundo alimento junto** (ex.: "avocado ... lemon",
  "avocado ... olive oil"). O banco de imagens (Pexels/Pixabay) não garante
  que o alimento principal apareça em destaque quando o termo cita dois
  alimentos — às vezes traz o secundário sozinho (limão em vez de abacate,
  azeitona em vez de azeite sendo servido). Antes de fechar um roteiro,
  reviso cena por cena se o termo de busca tem essa ambiguidade e, se tiver,
  removo o alimento secundário do termo ou uso uma variedade/formato mais
  específico (mesma lógica do "navel orange" pra evitar tangerina).
