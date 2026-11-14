#!/usr/bin/env bash
# Instalador do CorteFácil para macOS e Linux.
# Uso (cole no Terminal):
#   curl -fsSL https://raw.githubusercontent.com/danilocaffaro/cortefacil/main/install/install.sh | bash
set -euo pipefail

# tudo dentro de main(): se o download do script cair no meio, nada roda pela metade
main() {

REPO="danilocaffaro/cortefacil"
BRANCH="main"
DEST="${CORTEFACIL_HOME:-$HOME/CorteFacil}"
APP_NAME="CorteFácil"

b(){ printf "\n\033[1m%s\033[0m\n" "$*"; }
ok(){ printf "  \033[32m✓\033[0m %s\n" "$*"; }
info(){ printf "  %s\n" "$*"; }
fail(){ printf "\n\033[31m✗ %s\033[0m\n\n" "$*"; exit 1; }

printf "\n\033[1;33m  ▶ CorteFácil\033[0m — instalador\n"
printf "  Editor automático de vídeos para Reels, TikTok e Shorts.\n"

OS="$(uname -s)"
case "$OS" in Darwin|Linux) ;; *) fail "Sistema não suportado por este instalador ($OS). No Windows use o instalador do PowerShell.";; esac
command -v curl >/dev/null || fail "O comando 'curl' não foi encontrado."

# ---------------------------------------------------------------- 1. código
b "1/4  Baixando o CorteFácil"
SCRIPT_DIR=""
if [ -n "${BASH_SOURCE[0]:-}" ] && [ -f "${BASH_SOURCE[0]}" ]; then
  SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
fi
if [ -n "$SCRIPT_DIR" ] && [ -f "$SCRIPT_DIR/../pyproject.toml" ] && grep -q 'name = "cortefacil"' "$SCRIPT_DIR/../pyproject.toml"; then
  DEST="$(cd "$SCRIPT_DIR/.." && pwd)"
  ok "Usando a pasta atual: $DEST"
else
  # versão publicada mais recente (release); sem release, usa o main. CORTEFACIL_REF força uma tag.
  local TAG="${CORTEFACIL_REF:-}"
  if [ -z "$TAG" ]; then
    TAG="$(curl -fsSL "https://api.github.com/repos/$REPO/releases/latest" 2>/dev/null \
      | sed -n 's/.*"tag_name"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | head -1 || true)"
  fi
  local URL="https://codeload.github.com/$REPO/tar.gz/refs/heads/$BRANCH"
  if [ -n "$TAG" ]; then URL="https://codeload.github.com/$REPO/tar.gz/refs/tags/$TAG"; info "Versão $TAG"; fi
  TMP="$(mktemp -d)"
  curl -fsSL "$URL" | tar -xz -C "$TMP" \
    || fail "Não consegui baixar. Verifique sua internet e tente de novo."
  SRC="$(find "$TMP" -mindepth 1 -maxdepth 1 -type d | head -1)"
  mkdir -p "$DEST"
  # atualiza sem apagar seus projetos, logs e ambiente
  (cd "$SRC" && tar -cf - --exclude ./projetos --exclude ./logs --exclude ./.venv --exclude ./config.json --exclude ./.update-backup .) | (cd "$DEST" && tar -xf -)
  rm -rf "$TMP"
  ok "Arquivos em $DEST"
fi
cd "$DEST"

# ---------------------------------------------------------------- 2. uv (gerenciador de Python)
b "2/4  Preparando o Python"
UV="$(command -v uv || true)"
[ -z "$UV" ] && [ -x "$HOME/.local/bin/uv" ] && UV="$HOME/.local/bin/uv"
if [ -z "$UV" ]; then
  info "Instalando o uv (não precisa de senha)…"
  curl -LsSf https://astral.sh/uv/install.sh | env UV_NO_MODIFY_PATH=1 sh >/dev/null 2>&1 \
    || fail "Não consegui instalar o uv."
  UV="$HOME/.local/bin/uv"
fi
ok "uv pronto"

# ---------------------------------------------------------------- 3. dependências
b "3/4  Instalando componentes (pode levar alguns minutos na primeira vez)"
"$UV" sync --frozen --quiet || fail "Falha ao instalar os componentes. Rode de novo; se persistir, abra uma issue no GitHub."
ok "Componentes instalados"
# guarda o PATH do Terminal: assim o app encontra o Claude Code / Codex mesmo aberto pelo ícone.
# Soma ao que já estava salvo: o instalador de clique duplo roda com um PATH mais curto.
OLDPATH=""; [ -f "$DEST/.path" ] && OLDPATH="$(cat "$DEST/.path")"
printf "%s" "$(printf "%s:%s" "$PATH" "$OLDPATH" | tr ':' '\n' | awk 'NF && !seen[$0]++' | paste -sd: -)" > "$DEST/.path"
for c in claude codex; do
  if command -v "$c" >/dev/null 2>&1; then ok "Assistente de IA encontrado: $c"; fi
done

# ---------------------------------------------------------------- 4. atalho
b "4/4  Criando o atalho"
PY="$DEST/.venv/bin/python"
if [ -n "${CORTEFACIL_NO_SHORTCUT:-}" ]; then ok "Atalho pulado (modo teste)"; exit 0; fi
if [ "$OS" = "Darwin" ]; then
  APPDIR="$HOME/Applications"; mkdir -p "$APPDIR"
  APP="$APPDIR/$APP_NAME.app"
  rm -rf "$APP"
  # escapa \ e " para o texto do AppleScript (pastas com aspas não quebram o atalho)
  local AS_DEST="${DEST//\\/\\\\}"; AS_DEST="${AS_DEST//\"/\\\"}"
  local AS_PY="${PY//\\/\\\\}"; AS_PY="${AS_PY//\"/\\\"}"
  osacompile -o "$APP" -e "do shell script \"cd \" & quoted form of \"$AS_DEST\" & \" && nohup \" & quoted form of \"$AS_PY\" & \" cortefacil/launcher.py --background >/dev/null 2>&1 &\"" >/dev/null
  cp "$DEST/assets/icon.icns" "$APP/Contents/Resources/applet.icns" 2>/dev/null || true
  touch "$APP"
  ln -sfn "$APP" "$HOME/Desktop/$APP_NAME" 2>/dev/null || true
  ok "App criado: Aplicativos › $APP_NAME (e um atalho na Mesa)"
  b "Pronto! 🎉  Abrindo o CorteFácil…"
  info "Da próxima vez, é só abrir o ícone “$APP_NAME” na Mesa ou na pasta Aplicativos."
  open "$APP"
else
  DESK="$HOME/.local/share/applications"; mkdir -p "$DESK"
  cat > "$DESK/cortefacil.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=$APP_NAME
Comment=Editor automático de vídeos para Reels
Exec="$PY" "$DEST/cortefacil/launcher.py" --background
Icon=$DEST/assets/icon.png
Terminal=false
Categories=AudioVideo;Video;
EOF
  [ -d "$HOME/Desktop" ] && cp "$DESK/cortefacil.desktop" "$HOME/Desktop/" && chmod +x "$HOME/Desktop/cortefacil.desktop" || true
  ok "Atalho criado no menu de aplicativos"
  b "Pronto! 🎉  Abrindo o CorteFácil…"
  nohup "$PY" "$DEST/cortefacil/launcher.py" --background >/dev/null 2>&1 &
fi
printf "\n  Se o navegador não abrir sozinho, acesse: http://localhost:8765\n\n"
}

main "$@"
