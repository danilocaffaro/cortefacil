<p align="center"><img src="assets/icon-180.png" width="96" alt="CorteFácil"></p>

<h1 align="center">CorteFácil</h1>
<p align="center"><b>Do vídeo bruto ao Reel pronto.</b><br>
Editor automático de vídeos para Instagram Reels, TikTok e YouTube Shorts.<br>
Grátis, roda no seu computador e não precisa de conta.<br><a href="https://cortefacil.melhor.dev">cortefacil.melhor.dev</a></p>

---

Você grava falando para a câmera, solta o arquivo no CorteFácil e ele faz o trabalho chato:

| | |
|---|---|
| 💬 **Legendas automáticas** | Palavra por palavra, animadas, em 6 estilos prontos (inclui o “Nativo”, discreto como o texto do Instagram) |
| ✂️ **Corta silêncios** | Remove pausas, respiros e vícios como “éé” e “ahn” |
| 🔥 **Destaca o que importa** | Números e palavras-chave em cor, com emojis |
| 🔍 **Zoom dinâmico** | Aproxima a cada corte para o vídeo não ficar parado |
| 📌 **Títulos de tópico** | Cabeçalhos no topo a cada assunto |
| 🔊 **Som de profissional** | Efeitos sonoros nos cortes e títulos (sutil ou marcante), volume no padrão das redes e música de fundo opcional |
| 🎨 **Personalize tudo** | Fonte, cores, contorno, animação, palavras por vez — e arraste legenda e título direto no vídeo. Salve como “meu estilo” |
| 💬 **Frases de destaque** | Uma frase forte em destaque enquanto você fala o trecho (a IA sugere) |
| 📱 **Todos os formatos** | 9:16, 4:5, 1:1 e 16:9, com guia das áreas que o Instagram cobre |
| ✨ **IA opcional** | Se você usa Claude Code ou Codex, ele edita como um profissional |

Para corrigir qualquer coisa, edite o texto: **cortar uma frase do texto corta o vídeo.**

---

## Instalar (2 minutos)

**Jeito mais fácil:** baixe o instalador e dê dois cliques.

| Mac | Windows 10 e 11 |
|---|---|
| [**Baixar para Mac**](https://github.com/danilocaffaro/cortefacil/releases/latest/download/CorteFacil-Instalador-Mac.zip) | [**Baixar para Windows**](https://github.com/danilocaffaro/cortefacil/releases/latest/download/CorteFacil-Instalador-Windows.exe) |
| Se o Mac avisar que não pode verificar o app: **Ajustes do Sistema › Privacidade e Segurança › Abrir Mesmo Assim**. | Se aparecer “O Windows protegeu o computador”: **Mais informações › Executar assim mesmo**. |

O aviso só aparece na primeira vez: o CorteFácil é gratuito e não tem a assinatura paga da Apple nem o certificado da Microsoft. O instalador só baixa e roda o mesmo script dos comandos abaixo.

Prefere o terminal? Use os comandos:

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

> **Na primeira vez que abrir**, você escolhe como transcrever a fala:
> - **No computador (recomendado):** sem conta e sem internet; o vídeo não sai da sua máquina. Baixa a IA uma única vez (1,6 GB no Mac com chip Apple, 0,5 GB nos outros).
> - **Na nuvem:** grátis pela [Groq](https://console.groq.com/keys), até ~8 h de áudio por dia, mais rápida em computadores antigos e sem download. Crie a conta, copie a chave e cole no app (leva 1 minuto). O áudio do vídeo é enviado à Groq.
>
> Dá para trocar depois na engrenagem ⚙︎. Se a nuvem falhar, o app usa a IA do computador automaticamente.

<details>
<summary><b>Prefere baixar o ZIP?</b></summary>

1. Nesta página, clique em **Code › Download ZIP** e descompacte o arquivo.
2. Mac: dê dois cliques em `Instalar no Mac.command`; se o Mac bloquear, vá em **Ajustes do Sistema › Privacidade e Segurança › Abrir Mesmo Assim**.
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
   - **Ajustes**: formato, ritmo dos cortes, zoom, efeitos sonoros, música de fundo.
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
Depende da sua escolha. Com a transcrição **no computador**, nada sai da sua máquina. Com a transcrição **na nuvem**, só o **áudio** vai para a Groq (o vídeo e a edição ficam no computador). O *Turbinar com IA* envia apenas o **texto** da transcrição para o Claude Code ou o Codex que você usa.

**O app acessa a internet sozinho?**
Só para duas consultas, no máximo 1 vez por dia cada, e nenhuma leva dados seus:
- **Atualizações:** pergunta ao GitHub qual é a versão mais recente.
- **Avisos do CorteFácil:** baixa o arquivo `promo.json` do site, com os avisos de apoio e parcerias. O pedido leva só a versão do app (`cortefacil/1.2.1`). Contar esses pedidos por dia é a única forma que temos de saber quantas pessoas usam o CorteFácil.

As duas podem ser desligadas na engrenagem ⚙︎.

**Onde ficam meus projetos?**
Na pasta `CorteFacil/projetos`, dentro da sua pasta de usuário.

**Como atualizo?**
O CorteFácil avisa sozinho na tela inicial quando sai uma versão nova: clique em **Ver novidades › Atualizar agora**. Ele baixa a versão, reinicia e mantém seus projetos e preferências; se algo der errado, volta para a versão anterior. Também dá para procurar na engrenagem ⚙︎ › *Procurar atualizações*.
> Instalou a versão 1.0.0? Ela ainda não tem o aviso: rode o comando de instalação mais uma vez e, daí em diante, as atualizações chegam pelo app.

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
