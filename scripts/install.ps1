$ErrorActionPreference = "Stop"
$RootDir = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$VenvDir = Join-Path $RootDir ".venv"

function Info($Message) {
    Write-Host "[MoneyPrinterTurbo] $Message" -ForegroundColor Cyan
}

function Warn($Message) {
    Write-Host "[MoneyPrinterTurbo] $Message" -ForegroundColor Yellow
}

Set-Location $RootDir

if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
    if (Get-Command winget -ErrorAction SilentlyContinue) {
        Info "Installing Python with winget"
        winget install --id Python.Python.3.12 --exact --accept-source-agreements --accept-package-agreements
    } else {
        throw "Python launcher 'py' was not found and winget is unavailable. Install Python 3.11+ manually."
    }
}

if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) {
    if (Get-Command winget -ErrorAction SilentlyContinue) {
        Info "Installing FFmpeg with winget"
        winget install --id Gyan.FFmpeg.Shared --exact --accept-source-agreements --accept-package-agreements
    } else {
        Warn "FFmpeg was not found. Install FFmpeg and rerun this script."
    }
}

if (-not (Get-Command node -ErrorAction SilentlyContinue) -and (Get-Command winget -ErrorAction SilentlyContinue)) {
    Info "Installing Node.js LTS for optional provider CLIs"
    winget install --id OpenJS.NodeJS.LTS --exact --accept-source-agreements --accept-package-agreements
}

Info "Creating virtual environment at $VenvDir"
& py -3 -m venv $VenvDir
$Python = Join-Path $VenvDir "Scripts\python.exe"
& $Python -m pip install --upgrade pip
& $Python -m pip install -e "$RootDir[dev]"

$GpuMode = "cpu"
if (Get-Command nvidia-smi -ErrorAction SilentlyContinue) {
    try {
        & nvidia-smi -L | Out-Null
        if ($LASTEXITCODE -eq 0) { $GpuMode = "auto (NVIDIA runtime detected)" }
    } catch { }
}

Info "Installation complete"
Write-Host "Run: .\.venv\Scripts\Activate.ps1; python main.py"
Write-Host "Gradio: http://127.0.0.1:8501/studio"
Write-Host "Detected renderer mode: $GpuMode"
Write-Host "Benchmark: `$env:MPT_BENCH_URL='http://127.0.0.1:8501'; .\scripts\benchmark.sh"
