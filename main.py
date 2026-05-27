#!/usr/bin/env python3
"""
SEO Traffic Bot - 自动化网站流量生成工具

使用方法:
    python main.py                    # 运行一次所有网站
    python main.py --continuous       # 持续运行模式
    python main.py --stats            # 查看今日统计
    python main.py --config           # 显示当前配置
"""

import argparse
import asyncio
import signal
import sys
from pathlib import Path

# 添加src到路径
sys.path.insert(0, str(Path(__file__).parent))

from src.config_manager import config
from src.visitor import visitor_manager
from src.monitor import monitor
from src.web_dashboard import dashboard
from loguru import logger


class TrafficBot:
    """SEO流量机器人主类"""
    
    def __init__(self):
        self.running = False
        self._setup_signal_handlers()
    
    def _setup_signal_handlers(self):
        """设置信号处理器"""
        def signal_handler(signum, frame):
            logger.info("\n👋 收到停止信号，正在优雅退出...")
            self.running = False
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    async def run_once(self):
        """运行一次所有网站"""
        logger.info(f"🚀 开始访问 {len(config.websites)} 个网站...")
        
        results = await visitor_manager.visit_all_websites()
        
        # 记录结果
        for result in results:
            monitor.record_visit(result)
        
        # 打印统计
        monitor.print_summary()
        
        return results
    
    async def run_continuous(self):
        """持续运行模式"""
        self.running = True
        
        logger.info("🔄 启动持续运行模式 (按 Ctrl+C 停止)")
        
        try:
            while self.running:
                await self.run_once()
                
                if not self.running:
                    break
                
                # 等待下一轮
                import random
                min_interval = config.behavior.min_visit_interval
                max_interval = config.behavior.max_visit_interval
                wait_time = random.randint(min_interval, max_interval)
                
                logger.info(f"⏳ 等待 {wait_time // 60} 分钟后开始下一轮...")
                
                # 分段等待，便于响应停止信号
                waited = 0
                while waited < wait_time and self.running:
                    await asyncio.sleep(1)
                    waited += 1
                    
        except asyncio.CancelledError:
            logger.info("👋 任务已取消")
        
        logger.info("✅ 已停止")
    
    def show_stats(self):
        """显示统计信息"""
        monitor.print_summary()
    
    def show_config(self):
        """显示当前配置"""
        print("\n" + "=" * 60)
        print("⚙️ 当前配置")
        print("=" * 60)
        
        print("\n📋 网站列表:")
        for i, site in enumerate(config.websites, 1):
            print(f"  {i}. {site.name or '未命名'}")
            print(f"     URL: {site.url}")
            print(f"     每日最大访问: {site.max_daily_visits}")
            if site.keywords:
                print(f"     关键词: {', '.join(site.keywords)}")
        
        print("\n🔧 浏览器设置:")
        print(f"  无头模式: {config.browser.headless}")
        print(f"  超时: {config.browser.timeout}ms")
        
        print("\n🎭 行为模拟:")
        print(f"  停留时间: {config.behavior.min_stay_duration}-{config.behavior.max_stay_duration} 秒")
        print(f"  访问间隔: {config.behavior.min_visit_interval}-{config.behavior.max_visit_interval} 秒")
        
        print("\n🌐 代理设置:")
        print(f"  启用代理: {config.proxy.enabled}")
        print(f"  代理API: {config.proxy.api_url}")
        
        print("\n📊 监控设置:")
        print(f"  日志级别: {config.monitoring.log_level}")
        print("=" * 60 + "\n")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="SEO Traffic Bot - 自动化网站流量生成工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python main.py                    # 运行一次
  python main.py -c                 # 持续运行
  python main.py -s                 # 查看统计
  python main.py --config           # 查看配置
        """
    )
    
    parser.add_argument(
        "-c", "--continuous",
        action="store_true",
        help="持续运行模式"
    )
    
    parser.add_argument(
        "-s", "--stats",
        action="store_true",
        help="显示今日统计"
    )
    
    parser.add_argument(
        "--config",
        action="store_true",
        help="显示当前配置"
    )
    
    parser.add_argument(
        "--dashboard",
        action="store_true",
        help="启动统计仪表盘"
    )
    
    parser.add_argument(
        "--dashboard-port",
        type=int,
        default=8080,
        help="仪表盘端口号 (默认: 8080)"
    )
    
    args = parser.parse_args()
    
    bot = TrafficBot()
    
    if args.stats:
        bot.show_stats()
    elif args.config:
        bot.show_config()
    elif args.dashboard:
        # 启动仪表盘
        dashboard.port = args.dashboard_port
        dashboard.start_server()
        print(f"\n📊 统计仪表盘已启动: http://0.0.0.0:{args.dashboard_port}")
        print("按 Ctrl+C 停止\n")
        try:
            while True:
                import time
                time.sleep(1)
        except KeyboardInterrupt:
            dashboard.stop_server()
    elif args.continuous:
        # 持续运行模式，同时启动仪表盘
        dashboard.port = args.dashboard_port
        dashboard.start_server()
        logger.info(f"📊 统计仪表盘已启动: http://0.0.0.0:{args.dashboard_port}")
        asyncio.run(bot.run_continuous())
        dashboard.stop_server()
    else:
        asyncio.run(bot.run_once())


if __name__ == "__main__":
    main()
