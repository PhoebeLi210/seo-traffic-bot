#!/bin/bash

# SEO Traffic Bot 启动脚本

set -e

# 激活虚拟环境
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# 检查参数
MODE=${1:-once}

if [ "$MODE" == "continuous" ] || [ "$MODE" == "-c" ]; then
    echo "🔄 启动持续运行模式..."
    python main.py --continuous
elif [ "$MODE" == "stats" ] || [ "$MODE" == "-s" ]; then
    echo "📊 显示统计信息..."
    python main.py --stats
elif [ "$MODE" == "config" ]; then
    echo "⚙️ 显示配置信息..."
    python main.py --config
else
    echo "🚀 运行一次..."
    python main.py
fi
