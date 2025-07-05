#!/bin/bash

# DockPorts 部署脚本
# 用于快速部署到生产环境

set -e

echo "🐳 DockPorts 部署脚本"
echo "====================="

# 检查Docker和Docker Compose是否可用
if ! command -v docker >/dev/null 2>&1; then
    echo "❌ 错误: Docker未安装，请先安装Docker"
    exit 1
fi

if ! command -v docker-compose >/dev/null 2>&1 && ! docker compose version >/dev/null 2>&1; then
    echo "❌ 错误: Docker Compose未安装，请先安装Docker Compose"
    exit 1
fi

# 检查端口是否被占用
if netstat -tuln 2>/dev/null | grep -q ":7577 "; then
    echo "⚠️  警告: 端口7577已被占用，请修改docker-compose.yml中的端口配置"
    read -p "是否继续部署? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo "📦 构建Docker镜像..."
docker build -t dockports .

echo "🚀 启动服务..."
docker-compose up -d

echo "⏳ 等待服务启动..."
sleep 10

# 检查服务状态
if docker-compose ps | grep -q "Up"; then
    echo "✅ 部署成功!"
    echo "🌐 访问地址: http://localhost:7577"
    echo "📊 查看日志: docker-compose logs -f"
    echo "🛑 停止服务: docker-compose down"
else
    echo "❌ 部署失败，请查看日志:"
    docker-compose logs
    exit 1
fi

echo "====================="
echo "🎉 DockPorts 部署完成!"