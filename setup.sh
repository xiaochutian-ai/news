#!/bin/bash
set -e

echo "=============================================="
echo "   民生新闻聚合系统 · Mac 一键启动"
echo "=============================================="

if ! command -v brew &> /dev/null; then
    echo "未安装 Homebrew，开始安装..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
fi

if [ ! -d "/Applications/Docker.app" ]; then
    echo "未安装 Docker Desktop，开始安装..."
    brew install --cask docker
fi

echo "启动 Docker Desktop..."
open -g /Applications/Docker.app
sleep 15

echo "启动 n8n 容器..."
docker compose up -d

echo "安装 Python 依赖..."
python3 -m pip install -r app/requirements.txt

echo "打开 n8n..."
open "http://localhost:5678"

echo "如需手动生成一版稿件，请执行: python3 -m app.main digest"
