#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="${ROOT_DIR}/.venv"

info() { printf '\033[1;34m[MoneyPrinterTurbo] %s\033[0m\n' "$*"; }
warn() { printf '\033[1;33m[MoneyPrinterTurbo] %s\033[0m\n' "$*"; }

install_debian_packages() {
  local sudo_cmd=""
  if [ "$(id -u)" -ne 0 ]; then
    command -v sudo >/dev/null 2>&1 || { warn "sudo is required to install system packages."; return 1; }
    sudo_cmd="sudo"
  fi
  "$sudo_cmd" apt-get update
  "$sudo_cmd" apt-get install -y python3 python3-venv python3-pip ffmpeg ca-certificates
}

info "Preparing system dependencies"
if command -v apt-get >/dev/null 2>&1; then
  install_debian_packages
elif command -v brew >/dev/null 2>&1; then
  brew install python ffmpeg
elif ! command -v python3 >/dev/null 2>&1 || ! command -v ffmpeg >/dev/null 2>&1; then
  warn "Unsupported package manager. Install Python 3.11+ and FFmpeg manually, then run this script again."
  exit 1
fi

command -v python3 >/dev/null 2>&1 || { warn "python3 was not found."; exit 1; }
command -v ffmpeg >/dev/null 2>&1 || { warn "ffmpeg was not found."; exit 1; }

info "Creating virtual environment at ${VENV_DIR}"
python3 -m venv "$VENV_DIR"
# shellcheck disable=SC1091
source "${VENV_DIR}/bin/activate"
python -m pip install --upgrade pip
python -m pip install -e "${ROOT_DIR}[dev]"

GPU_BACKEND="cpu"
if command -v nvidia-smi >/dev/null 2>&1 && nvidia-smi -L >/dev/null 2>&1; then
  GPU_BACKEND="auto (NVIDIA runtime detected)"
elif [ -e /dev/dri/renderD128 ]; then
  GPU_BACKEND="auto (VAAPI/QSV device detected)"
fi

info "Installation complete"
printf 'Run: source %s/bin/activate && python main.py\n' "$VENV_DIR"
printf 'Gradio: http://127.0.0.1:8501/studio\n'
printf 'Detected renderer mode: %s\n' "$GPU_BACKEND"
printf 'Benchmark: MPT_BENCH_URL=http://127.0.0.1:8501 ./scripts/benchmark.sh\n'
