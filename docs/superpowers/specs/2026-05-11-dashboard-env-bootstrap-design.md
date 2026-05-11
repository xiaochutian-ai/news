# Dashboard 环境自检与引导安装设计

## 目标

- 为 Dashboard 启动链路增加统一的环境自检脚本。
- 在 macOS 上自动检查并尽量安装系统依赖：`Homebrew`、`python3`。
- 在项目内使用独立 `.venv` 管理 Python 依赖，避免污染全局环境。
- 将环境检查脚本接入 `start_dashboard.sh`，让用户执行一次启动命令即可完成准备和启动。

## 背景

- 当前 `start_dashboard.sh` 只负责：
  - 切到项目根目录
  - 清理占用端口的旧进程
  - 用 `python3` 直接启动 Dashboard
- 当前项目的 Python 依赖集中在 `app/requirements.txt`。
- 仓库中已有 `setup.sh`，但它面向 `Docker/n8n` 场景，不适合继续承载 Dashboard 的独立环境准备职责。
- 用户已明确本次采用方案 B：
  - 系统层依赖自动检查与安装
  - Python 依赖放入项目内 `.venv`

## 方案对比

### 方案 A：在 `start_dashboard.sh` 内联全部检查逻辑

- 做法：
  - 直接在现有启动脚本中插入 `brew`、`python3`、`.venv`、`pip install` 全部逻辑
- 优点：
  - 文件数量最少
  - 调用路径最短
- 缺点：
  - `start_dashboard.sh` 职责混杂，既处理环境也处理服务生命周期
  - 后续排查安装失败和启动失败时边界不清晰

### 方案 B：拆分独立环境脚本，由 `start_dashboard.sh` 调用

- 做法：
  - 新增独立脚本负责环境自检和准备
  - `start_dashboard.sh` 只在开头调用该脚本，成功后继续原有启动流程
- 优点：
  - 责任清晰，高内聚低耦合
  - 便于重复执行和单独排查环境问题
  - 对现有启动逻辑改动最小
- 缺点：
  - 多一个脚本文件

### 方案 C：复用并改造 `setup.sh`

- 做法：
  - 将 Dashboard 环境检查逻辑继续叠加到现有 `setup.sh`
  - `start_dashboard.sh` 调用 `setup.sh`
- 优点：
  - 表面上脚本入口更集中
- 缺点：
  - `setup.sh` 已经偏向其他运行场景，继续叠加会让脚本职责继续发散
  - 容易把 Dashboard 启动和 Docker/n8n 启动意外耦合

## 推荐方案

- 采用方案 B：拆分独立环境脚本，由 `start_dashboard.sh` 调用。
- 原因：
  - 满足用户要求的系统层自动安装，同时保留 Python 环境隔离
  - 符合最小化改动原则，不需要改造现有 `setup.sh`
  - 环境准备失败和 Dashboard 启动失败可以被明确区分

## 设计

### 脚本边界

- 新增环境脚本，建议路径为 `scripts/ensure_dashboard_env.sh`。
- 该脚本只负责：
  - 检查是否为 macOS 运行环境
  - 检查并安装 `Homebrew`
  - 检查并安装 `python3`
  - 创建并修复项目内 `.venv`
  - 安装 `app/requirements.txt` 中声明的 Python 依赖
- 该脚本不负责：
  - 处理 Dashboard 端口冲突
  - 启动 Dashboard 服务
  - 启动 Docker、n8n 或其他附加组件

### `start_dashboard.sh` 的职责调整

- 保留现有职责：
  - 进入项目根目录
  - 处理端口占用
  - 启动 Dashboard
  - 等待健康检查通过并输出访问地址
- 在进入端口处理逻辑前新增一步：
  - 调用 `scripts/ensure_dashboard_env.sh`
- Dashboard 启动命令从全局 `python3` 切换为 `.venv/bin/python`

### 系统依赖检查

- `Homebrew`
  - 若 `brew` 已存在，直接复用
  - 若不存在，执行官方安装脚本
  - 安装后尝试兼容常见路径：
    - `/opt/homebrew/bin/brew`
    - `/usr/local/bin/brew`
- `python3`
  - 若已存在，直接使用
  - 若不存在，执行 `brew install python`
  - 安装完成后再次校验 `python3` 是否可执行

### 项目虚拟环境

- 虚拟环境固定放在项目根目录 `.venv`
- 若 `.venv` 不存在：
  - 执行 `python3 -m venv .venv`
- 若 `.venv/bin/python` 不存在：
  - 视为虚拟环境损坏，删除并重建 `.venv`
- 若 `.venv` 内缺少 `pip`：
  - 执行 `.venv/bin/python -m ensurepip --upgrade`

### Python 依赖安装

- 统一使用 `.venv/bin/python -m pip` 执行安装
- 安装流程建议为：
  1. 升级 `pip`
  2. 安装 `app/requirements.txt`
- 依赖安装每次启动前都允许执行一次，以保证缺失包可自动补齐
- 若后续需要优化启动耗时，可再增加轻量缓存判断，但本次不提前复杂化

### 输出与错误处理

- 环境脚本使用明确日志前缀输出关键阶段，例如：
  - `[env] 检查 Homebrew`
  - `[env] 安装 python3`
  - `[env] 创建虚拟环境`
  - `[env] 安装 Python 依赖`
- 任一步失败时立即退出，并把失败阶段暴露给调用方
- `start_dashboard.sh` 依赖 `set -euo pipefail`，环境脚本失败时直接中止启动

### 幂等性

- 已安装的 `brew`、`python3`、`.venv` 不重复创建
- 已存在的 `.venv` 可重复复用
- `pip install -r app/requirements.txt` 可重复执行，不应破坏已有环境
- 整体流程应允许用户多次执行 `./start_dashboard.sh`

## 数据流

1. 用户执行 `./start_dashboard.sh`
2. `start_dashboard.sh` 切换到项目根目录
3. `start_dashboard.sh` 调用 `scripts/ensure_dashboard_env.sh`
4. 环境脚本完成系统依赖检查、`.venv` 准备和 Python 依赖安装
5. `start_dashboard.sh` 清理端口占用
6. `start_dashboard.sh` 使用 `.venv/bin/python` 启动 `app.dashboard_server`
7. 健康检查通过后输出 Dashboard 地址、PID 和日志路径

## 文件影响

- 新增：
  - `scripts/ensure_dashboard_env.sh`
- 修改：
  - `start_dashboard.sh`
- 可选更新：
  - `README.md`
  - 将启动说明从“先手动安装依赖”更新为“可直接运行一键启动脚本”

## 失败兜底

- 非 macOS 环境：
  - 脚本直接报错并提示当前仅支持 macOS 自动安装路径
- `brew` 安装失败：
  - 脚本退出并提示用户检查网络或手动安装
- `python3` 安装失败：
  - 脚本退出并提示用户检查 Homebrew 状态
- `.venv` 创建失败：
  - 脚本退出，避免继续启动产生混乱状态
- `pip install` 失败：
  - 脚本退出，不继续启动 Dashboard
- 环境准备成功但 Dashboard 启动失败：
  - 保留现有日志输出逻辑，由 `start_dashboard.sh` 指向 `.tmp/dashboard.log`

## 测试与验证

- 静态验证：
  - 检查脚本语法是否正确
  - 检查修改后的 `start_dashboard.sh` 是否仍可正常解析
- 运行验证：
  - 在本机已有 `python3` 和 `.venv` 的情况下重复执行 `./start_dashboard.sh`
  - 确认会自动复用 `.venv` 并正常拉起 Dashboard
- 文档验证：
  - 若更新 `README.md`，确认命令与实际启动方式一致

## 范围边界

- 本次不修改 Dashboard 业务代码
- 本次不新增 Python 包管理工具，如 `poetry` 或 `uv`
- 本次不接入 Docker 或系统服务管理
- 本次不处理 Linux 或 Windows 的自动安装路径
- 本次不引入更复杂的依赖版本锁定机制
