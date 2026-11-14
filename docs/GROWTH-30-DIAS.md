# Plano de growth orgânico: 30 dias (16/11 a 15/12/2026)

Montado com o Growth Hacker (Grok Bot), que pesquisou o X e os concorrentes, e revisado pelo Claude Code. Sem verba de mídia.

## Diagnóstico

- **O gargalo é a instalação, não a divulgação.** Um comando no terminal perde quem não é dev. Divulgar antes de resolver isso desperdiça o primeiro clique de cada pessoa.
- **O que viraliza no X (BR):**
  - Reclamar do preço: "R$ 65,90 no CapCut é pachorra".
  - Vídeo de demonstração com antes e depois.
  - O que viraliza é o resultado da legenda, não o app.
- **"Alternativa open source ao CapCut" já tem dono (OpenCut).** O posicionamento é outro: *"o fluxo do Submagic (vídeo falado vira Reel), local, em português e grátis"*.
- **Concorrentes:**
  - CapCut Pro: R$ 65,90/mês ou R$ 469,90/ano;
  - Submagic: a partir de US$ 12/mês;
  - Opus Clip: a partir de US$ 15/mês.

## Os 3 canais, em ordem

1. **Vídeos curtos (Reels/TikTok/Shorts) e YouTube em PT**, sempre com antes e depois, editados no próprio CorteFácil.
2. **Micro-criadores de IA no Brasil** recebendo o app em primeira mão: 8 a 10 convites pessoais, sem pedir post em troca.
3. **X, depois TabNews e Show HN** (na semana 3, só com o instalador estável).

Ficam de fora:
- Product Hunt: nesta fase não move nada.
- r/opensource: desde 24/10 restringe projetos feitos com IA.
- Grupos de WhatsApp e Telegram: viram spam e não dá para medir. Só entram se for um grupo de que o Danilo já participa.

## Calendário

P1 = obrigatório, P2 = importante, P3 = só se houver gatilho.

### Semana 1 (16 a 22/11): instalação e medição

| Prioridade | Quem | Ação |
|---|---|---|
| P1 | Claude Code | Instalador `.exe` e `.app` pequenos, que baixam Python, ffmpeg e Whisper na primeira execução com barra de progresso (é o mesmo script de hoje, empacotado). Publicados na release. |
| P1 | Claude Code | Botão **Baixar para Mac/Windows** no topo do site. Transcrição local como padrão, sem cadastro; a Groq vira opção. |
| P1 | Claude Code | Versão no user-agent do `promo.json` (`cortefacil/1.2.x`). Explicar no README que o app faz essa consulta 1x/dia e dar opção de desligar. Sem isso, "sem tracking" vira acusação no HN. |
| P1 | Danilo | Vídeo de 15 s de como liberar o app: no macOS 15+ é Ajustes › Privacidade e Segurança › **Abrir Mesmo Assim** (o "botão direito › Abrir" não funciona mais); no Windows é **Mais informações › Executar assim mesmo**. |
| P1 | Danilo | 3 vídeos curtos de antes e depois. |
| P2 | Claude Code | Botão **Copiar legenda do post** no export, com "editado com CorteFácil" no texto, que a pessoa pode apagar. O cartão final de crédito é opcional e fica desligado por padrão. |

### Semana 2 (23 a 29/11): prova em público e semeadura

| Prioridade | Quem | Ação |
|---|---|---|
| P1 | Danilo | 3 vídeos curtos e 1 tutorial no YouTube, com título igual ao que as pessoas buscam ("legenda automática grátis", "tirar silêncio do vídeo"). Dá para gravar o tutorial na mesma sessão dos curtos. |
| P1 | Danilo | Lista de 8 a 10 micro-criadores de IA e convite pessoal a cada um. |
| P2 | Claude Code | Corrigir no mesmo dia os bloqueios de instalação que aparecerem. |
| P2 | Danilo | Post `Pitch:` no TabNews com a stack (Python, ffmpeg, Whisper) e o que ainda está tosco. Mais 2 posts por semana no X. |

### Semana 3 (30/11 a 06/12): lançamento técnico

| Prioridade | Quem | Ação |
|---|---|---|
| P1 | Danilo | Show HN escrito por ele (o HN barra texto gerado por IA), numa terça ou quarta de manhã no horário de San Francisco, acompanhando os comentários. |
| P2 | Danilo | Post em inglês no X com a demo. |
| P2 | Claude Code | GIF no README, `llms.txt` no site, issues respondidas em até 24 h. |

### Semana 4 (07 a 13/12): dobrar o que funcionou

| Prioridade | Quem | Ação |
|---|---|---|
| P1 | Danilo | Repostar vídeos de criadores e de usuários. Publicar o segundo tutorial. |
| P1 | Claude Code | Corrigir os principais bugs. Nenhum recurso novo. |
| P3 | Danilo | Product Hunt só se houver mais de 50 instalações ativas por dia. |

## Metas para o dia 30

- **30 a 80 instalações ativas por dia** (métrica principal; pedidos diários ao `promo.json` com user-agent `cortefacil`, contados no Cloudflare).
- 50 a 150 downloads da release.
- 25 a 60 estrelas no GitHub.
- 5 a 15 vídeos publicados por pessoas de fora (é a prova de que funciona).
- Pelo menos 2 criadores postando de forma espontânea.

Como medir:
- Cada app pede o `promo.json` 1x/dia, então pedidos por dia viram "instalações ativas por dia".
- O Cloudflare conta pedidos, não pessoas únicas.
- O plano gratuito guarda poucos dias, então é preciso anotar o número todo dia: `python3 -I .claude/site-visitas.py 1`.

**Regra de parada:** abaixo de 10 instalações ativas por dia na semana 3, o problema é o produto ou a instalação. Pare de divulgar e corrija.

## Ganchos prontos

1. "Gravei 4 minutos falando pra câmera. Numa passada no app: cortei os 'éé', pus legenda palavra por palavra e exportei em 9:16. Sem CapCut e sem assinatura."
2. "CapCut Pro no Brasil custa R$ 65,90 por mês. Eu só queria legenda animada e cortar silêncio. Isso aqui roda no Mac e no Windows, o vídeo não sai do seu computador e a licença é MIT."
3. "O que segura um Reel não é o corte, é a legenda batendo na palavra certa. Você apaga uma frase no texto e o vídeo corta junto. Sem marca d'água."
4. "Se você usa Claude Code, cola o repositório e pede pra ele instalar o CorteFácil. Ele escolhe os melhores trechos e sugere 3 ganchos."
5. "Não é um CapCut. É o fluxo que o Submagic cobra em dólar, vídeo falado virando Reel, só que local, em português e grátis."

## O que não fazer

- Não lançar em nenhum fórum antes do instalador e de uma demo de 30 a 45 s.
- Não comprar estrela nem pedir upvote.
- Não se vender como "alternativa ao CapCut".
- Não abrir post só reclamando de preço.
- Não responder desconhecidos com link.
- Não espalhar o projeto em diretórios e grupos.
- Não criar páginas de SEO em massa.
- Não mostrar Pix nem pedido de apoio antes de a pessoa conseguir exportar um vídeo.

## Decisões em aberto (do Danilo)

- **Assinatura Apple (US$ 99/ano):** Grok e Claude concordam em usar como gatilho a marca de 100 instalações ativas por dia. A decisão é do Danilo.
- **Crédito no export:** só o botão "copiar legenda do post" com o texto removível. O cartão final fica opcional e desligado.
