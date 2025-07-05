#!/bin/bash

# DockPorts 启动脚本
# 用于快速启动容器端口监控应用

set -e

echo "🚀 启动 DockPorts 容器端口监控工具"
echo "======================================"

# 检查虚拟环境是否存在
if [ ! -d "venv" ]; then
    echo "📦 创建Python虚拟环境..."
    python3 -m venv venv
fi

# 激活虚拟环境
echo "🔧 激活虚拟环境..."
source venv/bin/activate

# 检查依赖是否已安装
if ! python -c "import flask, docker" 2>/dev/null; then
    echo "📥 安装Python依赖包..."
    pip install -r requirements.txt
fi

# 检查Docker是否可用
if ! docker info >/dev/null 2>&1; then
    echo "⚠️  警告: Docker服务不可用，某些功能可能受限"
fi

# 检查netstat命令是否可用
if ! command -v netstat >/dev/null 2>&1; then
    echo "⚠️  警告: netstat命令不可用，请安装net-tools包"
    echo "   运行: sudo apt install net-tools"
fi

echo "🌐 启动Web服务器..."
echo "   访问地址: http://localhost:7577"
echo "   按 Ctrl+C 停止服务"
echo "======================================"

# 启动应用
python app.py