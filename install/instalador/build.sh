#!/usr/bin/env bash
# Gera os instaladores de clique duplo em dist/ (rode no Mac, na raiz do repositório):
#   dist/CorteFacil-Instalador-Mac.zip      (app AppleScript; macOS)
#   dist/CorteFacil-Instalador-Windows.exe  (Go; Windows 10/11, 64 bits)
# Os dois baixam o install.sh / install.ps1 do main na hora: não precisam ser refeitos a cada versão,
# mas vão anexados em toda release (o site aponta para releases/latest/download/...).
set -euo pipefail
cd "$(dirname "$0")/../.."
ROOT="$PWD"; OUT="$ROOT/dist"; mkdir -p "$OUT"
VER="$(cat VERSION)"

# ---- Mac
TMP="$(mktemp -d)"; APP="$TMP/Instalar CorteFácil.app"
osacompile -o "$APP" install/instalador/mac.applescript
cp assets/icon.icns "$APP/Contents/Resources/applet.icns"
/usr/libexec/PlistBuddy -c "Set :CFBundleIdentifier dev.melhor.cortefacil.instalador" "$APP/Contents/Info.plist" 2>/dev/null \
  || /usr/libexec/PlistBuddy -c "Add :CFBundleIdentifier string dev.melhor.cortefacil.instalador" "$APP/Contents/Info.plist"
/usr/libexec/PlistBuddy -c "Add :CFBundleShortVersionString string $VER" "$APP/Contents/Info.plist" 2>/dev/null || true
codesign --force --deep -s - "$APP"   # assinatura ad hoc (sem conta Apple): o Mac pede "Abrir Mesmo Assim"
rm -f "$OUT/CorteFacil-Instalador-Mac.zip"
ditto -c -k --keepParent "$APP" "$OUT/CorteFacil-Instalador-Mac.zip"
rm -rf "$TMP"

# ---- Windows
cd install/instalador/windows
WINRES="github.com/tc-hib/go-winres@v0.3.3"
go run "$WINRES" simply --icon "$ROOT/assets/icon.png" --manifest cli \
  --product-name "CorteFácil" --file-description "Instalador do CorteFácil" \
  --product-version "$VER" --file-version "$VER" --copyright "Licença MIT" --original-filename "CorteFacil-Instalador-Windows.exe"
GOOS=windows GOARCH=amd64 CGO_ENABLED=0 go build -trimpath -ldflags "-s -w" -o "$OUT/CorteFacil-Instalador-Windows.exe" .
rm -f rsrc_windows_*.syso
cd "$ROOT"
ls -lh "$OUT"
