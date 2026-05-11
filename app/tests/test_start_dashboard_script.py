import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import requests


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = PROJECT_ROOT / "start_dashboard.sh"


def _find_free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _wait_for_http(url: str, expected_text: str, timeout_seconds: float = 10.0) -> bool:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        try:
            response = requests.get(url, timeout=0.5)
            if response.ok and expected_text in response.text:
                return True
        except requests.RequestException:
            pass
        time.sleep(0.2)
    return False


def _wait_for_process_exit(process: subprocess.Popen[bytes], timeout_seconds: float = 5.0) -> bool:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        if process.poll() is not None:
            return True
        time.sleep(0.2)
    return False


def _kill_port_process(port: int) -> None:
    subprocess.run(
        ["bash", "-lc", f"lsof -ti tcp:{port} | xargs kill -9"],
        cwd=PROJECT_ROOT,
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def test_start_dashboard_script_replaces_existing_process_on_same_port() -> None:
    port = _find_free_port()
    url = f"http://127.0.0.1:{port}/"
    dummy_server = subprocess.Popen(
        [sys.executable, "-m", "http.server", str(port)],
        cwd=PROJECT_ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    try:
        assert _wait_for_http(url, "Directory listing for"), "dummy server should start first"

        result = subprocess.run(
            ["bash", str(SCRIPT_PATH)],
            cwd=PROJECT_ROOT,
            env={**os.environ, "PORT": str(port)},
            check=False,
            capture_output=True,
            text=True,
            timeout=20,
        )

        assert result.returncode == 0
        assert f"http://127.0.0.1:{port}/" in result.stdout
        assert _wait_for_process_exit(dummy_server), "script should stop the old port owner"
        assert _wait_for_http(url, "执行晨报生成"), "dashboard should start on the requested port"
    finally:
        _kill_port_process(port)
        if dummy_server.poll() is None:
            dummy_server.kill()
            dummy_server.wait(timeout=5)


def test_start_dashboard_script_bootstraps_env_before_start() -> None:
    script = SCRIPT_PATH.read_text(encoding="utf-8")

    assert 'scripts/ensure_dashboard_env.sh' in script
    assert '.venv/bin/python' in script
