#!/bin/bash

# SEO Traffic Bot 安装脚本

set -e

echo "🚀 SEO Traffic Bot 安装脚本"
echo "=============================="

# 检查Python版本
echo "📋 检查Python版本..."
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "Python版本: $python_version"

# 检查是否为Python 3.8+
required_version="3.8"
if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then 
    echo "❌ 需要Python 3.8或更高版本"
    exit 1
fi

echo "✅ Python版本检查通过"

# 创建虚拟环境
echo "📦 创建虚拟环境..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "✅ 虚拟环境创建成功"
else
    echo "⚠️ 虚拟环境已存在"
fi

# 激活虚拟环境
echo "🔧 激活虚拟环境..."
source venv/bin/activate

# 升级pip
echo "⬆️ 升级pip..."
pip install --upgrade pip

# 安装依赖
echo "📥 安装依赖..."
pip install -r requirements.txt

# 安装Playwright浏览器
echo "🌐 安装Playwright浏览器..."
playwright install chromium

# 创建必要的目录
echo "📁 创建必要的目录..."
mkdir -p logs stats

# 复制环境变量文件
if [ ! -f ".env" ]; then
    echo "📝 创建环境变量文件..."
    cp .env.example .env
    echo "⚠️ 请编辑 .env 文件配置你的设置"
fi

# 检查配置文件
if [ ! -f "config/websites.json" ]; then
    echo "⚠️ 请编辑 config/websites.json 添加你的网站"
fi

echo ""
echo "✅ 安装完成！"
echo ""
echo "使用方法:"
echo "  1. 激活虚拟环境: source venv/bin/activate"
echo "  2. 编辑配置文件: config/websites.json"
echo "  3. 运行一次: python main.py"
echo "  4. 持续运行: python main.py --continuous"
echo "  5. 查看统计: python main.py --stats"
echo ""
echo "可选: 启动代理池 (需要Docker)"
echo "  docker-compose up -d proxypool redis"
echo ""
