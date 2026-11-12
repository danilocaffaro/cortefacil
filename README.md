<p align="center"><img src="assets/icon-180.png" width="96" alt="CorteFácil"></p>

<h1 align="center">CorteFácil</h1>
<p align="center"><b>Do vídeo bruto ao Reel pronto.</b><br>
Editor automático de vídeos para Instagram Reels, TikTok e YouTube Shorts.<br>
Grátis, roda no seu computador e não precisa de conta.<br><a href="https://cortefacil.melhor.dev">cortefacil.melhor.dev</a></p>

---

Você grava falando para a câmera, solta o arquivo no CorteFácil e ele faz o trabalho chato:

| | |
|---|---|
| 💬 **Legendas automáticas** | Palavra por palavra, animadas, em 5 estilos prontos |
| ✂️ **Corta silêncios** | Remove pausas, respiros e vícios como “éé” e “ahn” |
| 🔥 **Destaca o que importa** | Números e palavras-chave em cor, com emojis |
| 🔍 **Zoom dinâmico** | Aproxima a cada corte para o vídeo não ficar parado |
| 📌 **Títulos de tópico** | Cabeçalhos no topo a cada assunto |
| 🔊 **Áudio nivelado** | Volume no padrão das redes, com música de fundo opcional |
| 📱 **Todos os formatos** | 9:16, 4:5, 1:1 e 16:9 |
| ✨ **IA opcional** | Se você usa Claude Code ou Codex, ele edita como um profissional |

Para corrigir qualquer coisa, edite o texto: **cortar uma frase do texto corta o vídeo.**

---

## Instalar (2 minutos)

### 🍎 Mac

1. Abra o **Terminal**: aperte `⌘ + Espaço`, digite `Terminal` e aperte Enter.
2. Copie a linha abaixo, cole no Terminal e aperte Enter:

```bash
curl -fsSL https://raw.githubusercontent.com/danilocaffaro/cortefacil/main/install/install.sh | bash
```

3. Pronto. O CorteFácil abre sozinho no navegador. Para abrir de novo depois, use o ícone **CorteFácil** na Mesa ou em Aplicativos.

### 🪟 Windows 10 e 11

1. Aperte a tecla **Windows**, digite `PowerShell` e aperte Enter.
2. Copie a linha abaixo, cole no PowerShell e aperte Enter:

```powershell
irm https://raw.githubusercontent.com/danilocaffaro/cortefacil/main/install/install.ps1 | iex
```

3. Pronto. Para abrir de novo depois, use o ícone **CorteFácil** na Área de Trabalho.

### 🐧 Linux

Use o mesmo comando do Mac no terminal.

> **Na primeira vez que abrir**, o CorteFácil baixa a IA de transcrição. Ela tem cerca de 1,6 GB no Mac com chip Apple e 0,5 GB nos outros computadores. Isso só acontece uma vez, e a tela mostra o progresso.

<details>
<summary><b>Prefere baixar o ZIP?</b></summary>

1. Nesta página, clique em **Code › Download ZIP** e descompacte o arquivo.
2. Mac: clique com o **botão direito** em `Instalar no Mac.command` e escolha **Abrir**.
   Windows: dê dois cliques em `Instalar no Windows.bat`.
</details>

<details>
<summary><b>Tem Claude Code ou Codex? Deixe ele instalar para você</b></summary>

Abra o Claude Code ou o Codex e cole:

> Instale o CorteFácil de https://github.com/danilocaffaro/cortefacil seguindo o AGENTS.md do repositório e abra o app para mim.
</details>

---

## Usar

1. **Arraste o vídeo** para a janela, ou clique em *Experimente com um exemplo*.
2. Espere alguns segundos enquanto ele **transcreve e corta**.
3. Ajuste o que quiser. Tudo aparece na hora, na pré-visualização:
   - **Estilo**: modelo da legenda, cor de destaque, tamanho, título de abertura.
   - **Texto**: clique numa palavra para ir até ela. Selecione um trecho para *Destacar*, *Cortar*, *Editar*, pôr *Emoji* ou marcar um *Tópico*.
   - **Ajustes**: formato, ritmo dos cortes, zoom, música de fundo.
4. Clique em **Exportar** e depois em **Baixar MP4**.

### Turbinar com IA (opcional)

Se você tem o **[Claude Code](https://claude.com/claude-code)** ou o **[Codex](https://developers.openai.com/codex/cli)** instalado e conectado à sua conta, o botão **Turbinar com IA** usa o seu assistente para:

- escolher os destaques e emojis certos;
- cortar frases repetidas, recomeços e gaguejadas;
- criar títulos de tópico no topo do vídeo;
- sugerir 3 ganchos de abertura;
- corrigir nomes e termos que a transcrição errou.

Você não precisa de chave de API: ele usa a conta que você já tem. Sem assistente, todo o resto funciona normalmente.

---

## Dúvidas

**Meus vídeos vão para a internet?**
Não. Tudo roda no seu computador. A única exceção é o *Turbinar com IA*: ele envia só o **texto** da transcrição para o Claude Code ou o Codex que você usa.

**Onde ficam meus projetos?**
Na pasta `CorteFacil/projetos`, dentro da sua pasta de usuário.

**Como atualizo?**
Rode de novo o comando de instalação. Seus projetos são mantidos.

**Como fecho o app?**
Clique no botão ⏻ no canto superior direito.

**O navegador não abriu.**
Acesse http://localhost:8765.

**Como desinstalo?**
Apague a pasta `CorteFacil` da sua pasta de usuário e o ícone CorteFácil (no Mac ele fica em `~/Applications`).

**Deu erro.**
Abra uma [issue](https://github.com/danilocaffaro/cortefacil/issues) e anexe o arquivo `CorteFacil/logs/servidor.log`.

---

## Para quem desenvolve

```bash
git clone https://github.com/danilocaffaro/cortefacil && cd cortefacil
uv sync
uv run cortefacil/launcher.py
```

O projeto é feito com Python, FastAPI, ffmpeg (via `imageio-ffmpeg`), Whisper (MLX no Mac com chip Apple, `faster-whisper` nos outros), Pillow e uma interface em HTML puro. A arquitetura está no [AGENTS.md](AGENTS.md).

Licença MIT. As fontes Montserrat e Anton seguem a licença SIL OFL (veja `cortefacil/fonts`).
