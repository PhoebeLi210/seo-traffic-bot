#!/usr/bin/env python3
"""
统计仪表盘Web服务 - 独立运行，用于查看访问统计

使用方法:
    python dashboard_server.py          # 默认端口8080
    python dashboard_server.py --port 8888  # 指定端口
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.web_dashboard import dashboard
from loguru import logger


def main():
    parser = argparse.ArgumentParser(description="SEO Traffic Bot 统计仪表盘")
    parser.add_argument("-p", "--port", type=int, default=8080, help="服务端口号 (默认: 8080)")
    parser.add_argument("-d", "--stats-dir", default="stats", help="统计数据目录")
    
    args = parser.parse_args()
    
    # 配置日志
    logger.remove()
    logger.add(lambda msg: print(msg, end=""), level="INFO")
    
    # 设置仪表盘
    dashboard.stats_dir = Path(args.stats_dir)
    dashboard.port = args.port
    
    print(f"""
╔══════════════════════════════════════════════════════════╗
║           SEO Traffic Bot - 统计仪表盘                   ║
╠══════════════════════════════════════════════════════════╣
║  访问地址: http://服务器IP:{args.port:<5}                    ║
║  数据目录: {args.stats_dir:<20}                    ║
╚══════════════════════════════════════════════════════════╝

按 Ctrl+C 停止服务
""")
    
    try:
        dashboard.start_server()
        
        # 保持运行
        while True:
            import time
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n👋 正在停止服务...")
        dashboard.stop_server()
        print("✅ 已停止")


if __name__ == "__main__":
    main()
