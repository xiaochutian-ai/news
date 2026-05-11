# Dashboard Environment Bootstrap Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a reusable environment bootstrap script that auto-checks and installs Dashboard startup dependencies on macOS, prepares a project-local `.venv`, and invokes it from `start_dashboard.sh`.

**Architecture:** Keep startup responsibilities split into two layers. A new `scripts/ensure_dashboard_env.sh` handles macOS system dependency bootstrapping and project Python environment preparation, while `start_dashboard.sh` continues to own port cleanup, Dashboard process startup, and health checks. Use a repo-local `.venv` so runtime isolation stays local to the project and repeated starts are idempotent.

**Tech Stack:** Bash, Homebrew, Python 3, `venv`, `pip`, pytest-free shell verification

---

### Task 1: Add Environment Bootstrap Script

**Files:**
- Create: `scripts/ensure_dashboard_env.sh`

- [ ] **Step 1: Write the script first, then syntax-check it**

Create `scripts/ensure_dashboard_env.sh` with the following structure:

```bash
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
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

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
    [ -f "$REQUIREMENTS_PATH" ] || fail "缺少 requirements 文件: $REQUIREMENTS_PATH"

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
```

Run:

```bash
bash -n scripts/ensure_dashboard_env.sh
```

Expected: no output and exit code `0`.

- [ ] **Step 2: Make the new script executable**

Run:

```bash
chmod +x scripts/ensure_dashboard_env.sh
```

Expected: command succeeds with no output.

- [ ] **Step 3: Smoke-check the script without starting the server**

Run:

```bash
./scripts/ensure_dashboard_env.sh
```

Expected:
- Existing machines with `brew` and `python3` print reuse logs
- Missing `.venv` is created automatically
- Dependencies from `app/requirements.txt` are installed into `.venv`

- [ ] **Step 4: Commit the script-only change**

```bash
git add scripts/ensure_dashboard_env.sh
git commit -m "feat: add dashboard env bootstrap script"
```

### Task 2: Wire Bootstrap into Dashboard Startup

**Files:**
- Modify: `start_dashboard.sh`

- [ ] **Step 1: Edit the startup script to invoke environment setup before process work**

Update `start_dashboard.sh` so it calls the new script and uses `.venv/bin/python` for startup:

```bash
#!/bin/bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_ROOT"

"$PROJECT_ROOT/scripts/ensure_dashboard_env.sh"

HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-${1:-8000}}"
LOG_DIR="$PROJECT_ROOT/.tmp"
LOG_PATH="$LOG_DIR/dashboard.log"
DASHBOARD_URL="http://${HOST}:${PORT}/"
PYTHON_BIN="$PROJECT_ROOT/.venv/bin/python"

mkdir -p "$LOG_DIR"

existing_pids="$(lsof -ti "tcp:${PORT}" || true)"
if [ -n "$existing_pids" ]; then
    echo "端口 ${PORT} 已被占用，先停止旧进程: ${existing_pids}"
    kill $existing_pids || true
    sleep 1

    remaining_pids="$(lsof -ti "tcp:${PORT}" || true)"
    if [ -n "$remaining_pids" ]; then
        echo "旧进程未退出，强制停止: ${remaining_pids}"
        kill -9 $remaining_pids || true
        sleep 1
    fi
fi

echo "启动 Dashboard 服务..."
nohup "$PYTHON_BIN" -c "from app.dashboard_server import serve_dashboard; serve_dashboard(host='${HOST}', port=${PORT})" \
    >"$LOG_PATH" 2>&1 &
server_pid=$!

for _ in $(seq 1 50); do
    if curl -fsS "$DASHBOARD_URL" >/dev/null 2>&1; then
        echo "dashboard=${DASHBOARD_URL}"
        echo "pid=${server_pid}"
        echo "log=${LOG_PATH}"
        exit 0
    fi

    if ! kill -0 "$server_pid" >/dev/null 2>&1; then
        echo "Dashboard 启动失败，请检查日志: ${LOG_PATH}" >&2
        tail -n 50 "$LOG_PATH" >&2 || true
        exit 1
    fi

    sleep 0.2
done

echo "Dashboard 启动超时，请检查日志: ${LOG_PATH}" >&2
exit 1
```

- [ ] **Step 2: Syntax-check the startup script**

Run:

```bash
bash -n start_dashboard.sh
```

Expected: no output and exit code `0`.

- [ ] **Step 3: Run the updated startup flow end-to-end**

Run:

```bash
./start_dashboard.sh
```

Expected:
- Environment bootstrap runs first
- Dashboard starts with `.venv/bin/python`
- Output contains:

```text
dashboard=http://127.0.0.1:8000/
```

- [ ] **Step 4: Verify the service responds**

Run:

```bash
curl -fsS http://127.0.0.1:8000/ >/dev/null && echo ok
```

Expected:

```text
ok
```

- [ ] **Step 5: Commit the startup integration**

```bash
git add start_dashboard.sh
git commit -m "feat: bootstrap dashboard env on start"
```

### Task 3: Refresh Operator Docs

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Update the quick-start and service-start sections**

Adjust the Dashboard startup instructions in `README.md` to reflect the new flow:

```md
## 快速开始

```bash
./start_dashboard.sh
```

首次启动会自动检查并安装 Dashboard 依赖：

- `Homebrew`
- `python3`
- 项目内 `.venv`
- `app/requirements.txt` 中的 Python 包

## 运行本地服务

当前项目的本地服务入口是 Dashboard 服务，用于在浏览器中选择数据源、触发晨报生成并查看产物明细。

### 启动服务

```bash
./start_dashboard.sh
```
```

- [ ] **Step 2: Review the rest of `README.md` for stale manual-install wording**

Remove or rewrite lines that still claim users must run:

```bash
python3 -m pip install -r app/requirements.txt
python3 -m app.dashboard_server
```

Replace them with direct startup-script usage unless the text is explicitly documenting a manual fallback path.

- [ ] **Step 3: Sanity-check documentation consistency**

Run:

```bash
grep -n "python3 -m pip install -r app/requirements.txt\|python3 -m app.dashboard_server" README.md
```

Expected:
- No outdated mandatory startup instructions remain
- Any remaining matches are clearly labeled as manual fallback, not the default path

- [ ] **Step 4: Commit the docs update**

```bash
git add README.md
git commit -m "docs: refresh dashboard startup instructions"
```

### Task 4: Final Verification and Handoff

**Files:**
- Verify: `scripts/ensure_dashboard_env.sh`
- Verify: `start_dashboard.sh`
- Verify: `README.md`

- [ ] **Step 1: Run final shell syntax checks together**

Run:

```bash
bash -n scripts/ensure_dashboard_env.sh
bash -n start_dashboard.sh
```

Expected: both commands exit `0` with no output.

- [ ] **Step 2: Run the full startup flow once more after docs are updated**

Run:

```bash
./start_dashboard.sh
```

Expected:
- The script reuses existing `.venv`
- No dependency bootstrap step fails on repeat execution
- Dashboard remains reachable

- [ ] **Step 3: Record the changed files for review**

Expected changed set:

```text
scripts/ensure_dashboard_env.sh
start_dashboard.sh
README.md
docs/superpowers/specs/2026-05-11-dashboard-env-bootstrap-design.md
docs/superpowers/plans/2026-05-11-dashboard-env-bootstrap.md
```

- [ ] **Step 4: Prepare review summary**

Include:
- What the bootstrap script now installs automatically
- That runtime uses `.venv/bin/python`
- Whether repeated `./start_dashboard.sh` runs were verified
- Any environment limitations, especially macOS-only auto-install behavior
