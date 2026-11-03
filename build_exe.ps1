# Gera a distribuição Windows do INS Dashboard Studio (pasta + .exe).
#
# O ambiente virtual e os artefatos intermediários ficam em
# %LOCALAPPDATA%\insbuild para não esbarrar no limite de caminho do Windows
# (a pasta do projeto está dentro do OneDrive e tem caminho longo).
#
# Uso:
#   powershell -ExecutionPolicy Bypass -File .\build_exe.ps1

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

$ProjectRoot = $PSScriptRoot
$BuildRoot   = Join-Path $env:LOCALAPPDATA "insbuild"
$Venv        = Join-Path $BuildRoot "venv"
$Python      = Join-Path $Venv "Scripts\python.exe"
$DistRoot    = Join-Path $BuildRoot "dist"
$WorkRoot    = Join-Path $BuildRoot "work"
$AppName     = "INS Dashboard Studio"
$FinalDist   = Join-Path $ProjectRoot "dist"

Write-Host "== INS Dashboard Studio - build do executável ==" -ForegroundColor Cyan

if (-not (Test-Path $Python)) {
    Write-Host "Criando ambiente virtual em $Venv ..."
    py -3.13 -m venv $Venv
    if ($LASTEXITCODE -ne 0) {
        throw "Python 3.13 não encontrado. Instale-o e tente novamente."
    }
}

Write-Host "Instalando dependências de execução e de build ..."
& $Python -m pip install --upgrade pip setuptools wheel
& $Python -m pip install -r (Join-Path $ProjectRoot "requirements-build.txt")
if ($LASTEXITCODE -ne 0) { throw "Falha ao instalar as dependências." }

Write-Host "Empacotando (onedir, sem UPX) ..."
& $Python -m PyInstaller `
    --noconfirm `
    --clean `
    --workpath $WorkRoot `
    --distpath $DistRoot `
    (Join-Path $ProjectRoot "ins_dashboard.spec")
if ($LASTEXITCODE -ne 0) { throw "Falha no PyInstaller." }

Write-Host "Copiando a distribuição para $FinalDist ..."
New-Item -ItemType Directory -Force -Path $FinalDist | Out-Null
$FinalApp = Join-Path $FinalDist $AppName
if (Test-Path $FinalApp) {
    Remove-Item -Recurse -Force $FinalApp
}
Copy-Item -Recurse (Join-Path $DistRoot $AppName) $FinalApp

$Exe = Join-Path $FinalApp "$AppName.exe"
if (-not (Test-Path $Exe)) { throw "Executável não encontrado em $Exe" }

$SizeMb = [math]::Round(
    (Get-ChildItem $FinalApp -Recurse -File | Measure-Object Length -Sum).Sum / 1MB,
    1
)
Write-Host ""
Write-Host "Build concluído." -ForegroundColor Green
Write-Host "Executável: $Exe"
Write-Host "Tamanho da pasta: $SizeMb MB"
