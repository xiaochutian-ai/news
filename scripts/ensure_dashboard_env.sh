#!/bin/bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VENV_PATH="$PROJECT_ROOT/.venv"
REQUIREMENTS_PATH="$PROJECT_ROOT/app/requirements.txt"

log() {
    echo "[env] $1"
}

fail() {
    echo "[env] $1" >&2
    exit 1
}

ensure_macos() {
    if [ "$(uname -s)" != "Darwin" ]; then
        fail "当前自动安装流程仅支持 macOS"
    fi
}

ensure_brew() {
    if command -v brew >/dev/null 2>&1; then
        log "Homebrew 已存在"
        return
    fi

    log "未检测到 Homebrew，开始安装"
    NONINTERACTIVE=1 /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

    if [ -x /opt/homebrew/bin/brew ]; then
        eval "$(/opt/homebrew/bin/brew shellenv)"
    elif [ -x /usr/local/bin/brew ]; then
        eval "$(/usr/local/bin/brew shellenv)"
    fi

    command -v brew >/dev/null 2>&1 || fail "Homebrew 安装后仍不可用"
}

ensure_python3() {
    if command -v python3 >/dev/null 2>&1; then
        log "python3 已存在"
        return
    fi

    log "未检测到 python3，开始通过 Homebrew 安装"
    brew install python
    command -v python3 >/dev/null 2>&1 || fail "python3 安装后仍不可用"
}

ensure_venv() {
    if [ ! -d "$VENV_PATH" ]; then
        log "创建项目虚拟环境"
        python3 -m venv "$VENV_PATH"
    fi

    if [ ! -x "$VENV_PATH/bin/python" ]; then
        log "检测到损坏的虚拟环境，重建 .venv"
        rm -rf "$VENV_PATH"
        python3 -m venv "$VENV_PATH"
    fi

    if ! "$VENV_PATH/bin/python" -m pip --version >/dev/null 2>&1; then
        log "虚拟环境缺少 pip，开始修复"
        "$VENV_PATH/bin/python" -m ensurepip --upgrade
    fi
}

install_python_dependencies() {
    if [ ! -f "$REQUIREMENTS_PATH" ]; then
        fail "缺少 requirements 文件: $REQUIREMENTS_PATH"
    fi

    log "升级 pip"
    "$VENV_PATH/bin/python" -m pip install --upgrade pip

    log "安装 Python 依赖"
    "$VENV_PATH/bin/python" -m pip install -r "$REQUIREMENTS_PATH"
}

main() {
    cd "$PROJECT_ROOT"
    ensure_macos
    ensure_brew
    ensure_python3
    ensure_venv
    install_python_dependencies
    log "Dashboard 环境准备完成"
}

main "$@"
