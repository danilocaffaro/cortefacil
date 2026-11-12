# AGENTS.md — CorteFácil

Guia para agentes de código (Claude Code, Codex, Cursor…) que forem **instalar, rodar, diagnosticar ou modificar** o CorteFácil a pedido de um usuário. Fale com o usuário em português do Brasil, sem jargão.

## Instalar para o usuário

- **macOS / Linux**: `curl -fsSL https://raw.githubusercontent.com/danilocaffaro/cortefacil/main/install/install.sh | bash`
- **Windows** (PowerShell): `irm https://raw.githubusercontent.com/danilocaffaro/cortefacil/main/install/install.ps1 | iex`
- Se o repo já estiver clonado, rode `bash install/install.sh` (ou `install\install.ps1`) de dentro dele: instala no próprio diretório.

O instalador é idempotente e serve também para atualizar. Ele:
1. baixa o código para `~/CorteFacil` (pode mudar com `CORTEFACIL_HOME`) sem apagar `projetos/`, `logs/` e `.venv/`;
2. instala o `uv` em `~/.local/bin`, sem sudo nem admin;
3. roda `uv sync`, que baixa o Python 3.12 e as dependências;
4. grava o PATH do terminal em `.path`, para o app achar `claude`/`codex`/`node` quando aberto pelo ícone;
5. cria o atalho: no macOS, `~/Applications/CorteFácil.app` mais um link na Mesa; no Windows, `.lnk` na Área de Trabalho e no Menu Iniciar; no Linux, um `.desktop`;
6. abre o app.

`CORTEFACIL_NO_SHORTCUT=1` pula o passo 5 e não abre o app (útil em testes).

## Rodar

```bash
uv run cortefacil/launcher.py              # sobe em http://localhost:8765 e abre o navegador
uv run cortefacil/launcher.py --no-browser
```

O launcher reaproveita a instância que já estiver rodando. A porta muda com `CORTEFACIL_PORT`.

## Diagnóstico rápido

| Sintoma | O que verificar |
|---|---|
| App não abre | `logs/servidor.log`; porta 8765 ocupada (`lsof -i :8765`) |
| "Preparando…" parado | download do modelo do Hugging Face (internet ou proxy); cache em `~/.cache/huggingface/hub` |
| Transcrição na nuvem falha | chave em `config.json` (não imprima); teste com `cloud_stt.test_key`; o app cai para a IA local sozinho |
| IA "não encontrado" | `claude --version` / `codex --version` no terminal; reinstale para regravar o `.path` |
| IA "não conectado" | o usuário precisa rodar `claude` (ou `codex`) uma vez e fazer login |
| Erro no ffmpeg | `uv run python -c "import imageio_ffmpeg;print(imageio_ffmpeg.get_ffmpeg_exe())"` |

## Arquitetura

```
cortefacil/
  launcher.py     abre o servidor e o navegador (sem console quando --background)
  app.py          FastAPI: upload, projetos (em ../projetos/<id>/), render, IA, setup
  engine.py       análise (probe, proxy, Whisper, silêncios) → linha do tempo → render ffmpeg
  captions.py     desenho das legendas, títulos e frases de destaque com animações (quadros em paralelo)
  nlp.py          heurísticas PT-BR: palavras-chave, emojis, vícios
  cloud_stt.py    transcrição opcional na nuvem (Groq, Whisper turbo grátis); chave em config.json (600), com fallback local
  sfx.py          efeitos sonoros dos cortes (whoosh/pop sintetizados, sem arquivos de terceiros), mixados no render
  promo.py        apoio/patrocínio: lê promo.json do site (1x/dia), valida e mostra nos espaços home/export/engrenagem; sem rastreamento (ver docs/MONETIZACAO.md)
  updater.py      atualizações: confere a última release no GitHub (1x/dia), baixa, troca o código com backup em .update-backup/, roda uv sync --frozen e reinicia; desfaz se falhar
  validate.py     valida tudo o que a interface envia (cores, música, emoji, números) antes de chegar ao ffmpeg/HTML
  llm.py          "Turbinar com IA": chama `claude -p` ou `codex exec` (conta do usuário, sem API key)
  setup_check.py  onboarding: checa ffmpeg, baixa o modelo Whisper e mostra o progresso
  styles.py       estilos de legenda, formatos e ritmos (compartilhado com a UI via /api/config)
  static/index.html  UI inteira (HTML/CSS/JS puro, tokens no estilo Apple)
  fonts/          Montserrat e Anton (OFL), usadas no render e na prévia
```

Pontos centrais do motor:
- **Edição pelo texto**: cada palavra tem `s`/`e` (tempo) e as flags `kw`, `removed`, `filler` e `emoji`. Os trechos mantidos (`build_segments`) saem das palavras ativas, com a pausa máxima dada pelo ritmo. Depois os silêncios do `silencedetect` são subtraídos, porque o Whisper estica palavras.
- **Prévia = render**: a UI toca o proxy pulando os cortes e desenha a legenda em DOM. O render desenha os mesmos "estados" com o Pillow e os monta com o concat demuxer, como um overlay sobre os segmentos (`trim` + `crop/scale` com zoom) concatenados.
- **Faixa do topo e destaques**: gancho (`settings.title`), tópicos (`settings.topics = [{word_id, text}]`) e frases de destaque (`settings.callouts = [{start_id, end_id, text}]`) viram streams concat próprios. Durante uma frase de destaque a legenda some (como na referência).
- **Estilo efetivo** = preset (`styles.STYLES`) + `settings.custom` (fonte, cores, contorno, palavras por vez, animação…) via `styles.resolve_style`; a UI replica isso em `RS()`/`RT()` para a prévia ficar idêntica ao render.
- **Animações**: entrada da legenda (pop/subir/aparecer), soco da palavra falada, emoji elástico, título descendo; quadros só nas janelas de transição. Aproximação lenta via `zoompan` (`push_in`).
- **Encoder**: `h264_videotoolbox` no macOS; `libx264` nos outros sistemas.

## Convenções

- Interface e mensagens em PT-BR, para leigos: nada de termos técnicos na UI.
- Mantenha a UI num arquivo só, sem build. **Siga `docs/DESIGN.md`** (design system inspirado na Apple): tema claro por padrão e escuro opcional (`data-theme=dark`); uma única cor de ação (Action Blue `#0066cc`, ou `#2997ff` no escuro); SF Pro via `system-ui`; pesos 400/600; botões em pílula com `scale(.95)` ao pressionar; nada de gradientes decorativos; sombra só no "produto" (o vídeo).
- Toda mudança no motor deve ser testada renderizando `samples/exemplo.mp4` e inspecionando os quadros.

## Segurança (não quebre isto)

- O servidor escuta só em `127.0.0.1`. O middleware `only_local` (app.py) recusa `Host` que não seja localhost (DNS rebinding) e requisições de escrita vindas de outra origem (CSRF). Não adicione CORS.
- Todo ajuste e palavra que chega por `PUT /api/jobs/{id}` passa por `validate.py`. Ao criar um ajuste novo em `DEFAULT_SETTINGS`, adicione a regra dele lá, senão ele é descartado.
- Nunca interpole texto do usuário no grafo do ffmpeg sem validar o formato (cores só `#RRGGBB`, música só `music.<ext>`).
- A chave da Groq fica só em `config.json` (criado com permissão 600) e nunca volta para a interface.

## Publicar uma versão nova (o app dos usuários só vê *releases*)

1. Aumente `VERSION` (ex.: 1.1.0 → 1.2.0) e descreva as mudanças em `CHANGELOG.md`.
2. Commit + push no `main`.
3. `gh release create v1.2.0 --title "CorteFácil 1.2.0" --notes "<texto curto em português, em tópicos>"`. As notas aparecem na janela "Atualizar agora" do app.

A tag precisa ter o `VERSION` igual ao número dela. O instalador também instala a última release (sem release, usa o `main`). Para testar o atualizador sem publicar, use `CORTEFACIL_UPDATE_API` e `CORTEFACIL_UPDATE_DOWNLOAD` apontando para um servidor local.
