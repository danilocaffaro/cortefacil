# Instalador do CorteFácil para Windows 10/11.
# Uso (cole no PowerShell):
#   irm https://raw.githubusercontent.com/danilocaffaro/cortefacil/main/install/install.ps1 | iex
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$Repo   = 'danilocaffaro/cortefacil'
$Branch = 'main'
$Dest   = if ($env:CORTEFACIL_HOME) { $env:CORTEFACIL_HOME } else { Join-Path $env:USERPROFILE 'CorteFacil' }
$AppName = 'CorteFácil'

function Step($t) { Write-Host "`n$t" -ForegroundColor White }
function Ok($t)   { Write-Host "  ✓ $t" -ForegroundColor Green }
function Fail($t) { Write-Host "`n✗ $t`n" -ForegroundColor Red; Read-Host 'Pressione Enter para sair'; exit 1 }

Write-Host "`n  ▶ CorteFácil — instalador" -ForegroundColor Yellow
Write-Host '  Editor automático de vídeos para Reels, TikTok e Shorts.'

# ---------------------------------------------------------------- 1. código
Step '1/4  Baixando o CorteFácil'
$local = $null
if ($PSScriptRoot -and (Test-Path (Join-Path $PSScriptRoot '..\pyproject.toml'))) { $local = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path }
if ($local) {
  $Dest = $local; Ok "Usando a pasta atual: $Dest"
} else {
  try {
    $tmp = Join-Path $env:TEMP ("cortefacil-" + [guid]::NewGuid())
    New-Item -ItemType Directory -Path $tmp | Out-Null
    $zip = Join-Path $tmp 'cf.zip'
    Invoke-WebRequest "https://codeload.github.com/$Repo/zip/refs/heads/$Branch" -OutFile $zip -UseBasicParsing
    Expand-Archive $zip -DestinationPath $tmp -Force
    $src = Get-ChildItem $tmp -Directory | Select-Object -First 1
    New-Item -ItemType Directory -Force -Path $Dest | Out-Null
    # atualiza sem apagar seus projetos, logs e ambiente
    robocopy $src.FullName $Dest /E /XD projetos logs .venv /NFL /NDL /NJH /NJS /NP | Out-Null
    Remove-Item $tmp -Recurse -Force
    Ok "Arquivos em $Dest"
  } catch { Fail "Não consegui baixar. Verifique sua internet e tente de novo. ($_)" }
}
Set-Location $Dest

# ---------------------------------------------------------------- 2. uv
Step '2/4  Preparando o Python'
$uv = (Get-Command uv -ErrorAction SilentlyContinue).Source
if (-not $uv) { $cand = Join-Path $env:USERPROFILE '.local\bin\uv.exe'; if (Test-Path $cand) { $uv = $cand } }
if (-not $uv) {
  Write-Host '  Instalando o uv (não precisa de administrador)…'
  $env:UV_NO_MODIFY_PATH = '1'
  powershell -ExecutionPolicy Bypass -NoProfile -Command "irm https://astral.sh/uv/install.ps1 | iex" | Out-Null
  $uv = Join-Path $env:USERPROFILE '.local\bin\uv.exe'
  if (-not (Test-Path $uv)) { Fail 'Não consegui instalar o uv.' }
}
Ok 'uv pronto'

# ---------------------------------------------------------------- 3. dependências
Step '3/4  Instalando componentes (pode levar alguns minutos na primeira vez)'
& $uv sync --frozen --quiet
if ($LASTEXITCODE -ne 0) { Fail 'Falha ao instalar os componentes. Rode de novo; se persistir, abra uma issue no GitHub.' }
Ok 'Componentes instalados'
Set-Content -Path (Join-Path $Dest '.path') -Value $env:PATH -NoNewline -Encoding UTF8
foreach ($c in 'claude','codex') { if (Get-Command $c -ErrorAction SilentlyContinue) { Ok "Assistente de IA encontrado: $c" } }

# ---------------------------------------------------------------- 4. atalho
Step '4/4  Criando o atalho'
$pyw  = Join-Path $Dest '.venv\Scripts\pythonw.exe'
$ws   = New-Object -ComObject WScript.Shell
$places = @([Environment]::GetFolderPath('Desktop'), (Join-Path ([Environment]::GetFolderPath('StartMenu')) 'Programs'))
foreach ($p in $places) {
  $lnk = $ws.CreateShortcut((Join-Path $p "$AppName.lnk"))
  $lnk.TargetPath = $pyw
  $lnk.Arguments = '"' + (Join-Path $Dest 'cortefacil\launcher.py') + '" --background'
  $lnk.WorkingDirectory = $Dest
  $lnk.IconLocation = (Join-Path $Dest 'assets\icon.ico')
  $lnk.Description = 'Editor automático de vídeos para Reels'
  $lnk.Save()
}
Ok "Atalho “$AppName” criado na Área de Trabalho e no Menu Iniciar"

Write-Host "`nPronto! 🎉  Abrindo o CorteFácil…" -ForegroundColor White
Start-Process -FilePath $pyw -ArgumentList ('"' + (Join-Path $Dest 'cortefacil\launcher.py') + '" --background') -WorkingDirectory $Dest
Write-Host "`n  Da próxima vez, é só abrir o ícone “$AppName” na Área de Trabalho."
Write-Host "  Se o navegador não abrir sozinho, acesse: http://localhost:8765`n"
