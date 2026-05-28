#!/usr/bin/env python3
"""
多用户服务器 - 整合流量机器人和Web仪表盘

使用方法:
    python multi_user_server.py          # 默认端口8081
    python multi_user_server.py --port 8082  # 指定端口
"""

import argparse
import asyncio
import sys
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.dashboard.server import start_dashboard, dashboard_server
from src.user_manager import user_manager
from src.config_manager import config
from src.visitor import visitor_manager
from src.monitor import monitor
from loguru import logger


class MultiUserServer:
    """多用户服务器"""

    def __init__(self, port: int = 8081):
        self.port = port
        self.running = False
        self.traffic_bot_task = None

    async def run_traffic_bot(self):
        """运行流量机器人（后台任务）"""
        logger.info("🤖 流量机器人后台服务已启动")

        while self.running:
            try:
                # 获取所有用户的网站列表
                all_websites = []
                for user in user_manager.list_all_users():
                    user_dir = user_manager.get_user_data_dir(user.user_id)
                    user_config_file = user_dir / "config" / "websites.json"

                    if user_config_file.exists():
                        import json
                        with open(user_config_file, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            websites = data.get('websites', [])
                            # 添加用户ID到网站配置
                            for site in websites:
                                site['_user_id'] = user.user_id
                            all_websites.extend(websites)

                if all_websites:
                    logger.info(f"🌐 本轮共 {len(all_websites)} 个网站需要访问")

                    # 先检查代理池是否有可用代理
                    proxy_stats = proxy_manager.get_stats()
                    if not proxy_stats.get('free_proxy_available', False):
                        logger.warning("⚠️ 代理池无可用代理，等待下一轮...")
                        # 等待后继续，不进行访问
                        await asyncio.sleep(60)
                        continue

                    # 访问所有网站
                    for site_config in all_websites:
                        user_id = site_config.get('_user_id')

                        # 创建网站配置对象（排除 _user_id 字段）
                        from src.config_manager import WebsiteConfig
                        config_copy = {k: v for k, v in site_config.items() if not k.startswith('_')}
                        website = WebsiteConfig(**config_copy)

                        if website.enabled:
                            # 访问网站
                            result = await visitor_manager.visit_website(website)

                            # 保存到用户专属统计目录
                            if user_id:
                                user_stats_dir = user_manager.get_user_data_dir(user_id) / "stats"
                                user_stats_dir.mkdir(parents=True, exist_ok=True)

                                # 使用用户专属目录保存统计
                                from datetime import date
                                today = date.today().isoformat()
                                stats_file = user_stats_dir / f"{today}.json"

                                # 加载或创建今日统计
                                import json
                                if stats_file.exists():
                                    try:
                                        with open(stats_file, 'r', encoding='utf-8') as f:
                                            today_stats = json.load(f)
                                    except:
                                        today_stats = {"date": today, "total_visits": 0, "successful_visits": 0, "failed_visits": 0, "websites": {}}
                                else:
                                    today_stats = {"date": today, "total_visits": 0, "successful_visits": 0, "failed_visits": 0, "websites": {}}

                                # 更新统计
                                today_stats["total_visits"] += 1
                                if result.get("success"):
                                    today_stats["successful_visits"] += 1
                                else:
                                    today_stats["failed_visits"] += 1

                                url = result.get("url", "unknown")
                                if url not in today_stats["websites"]:
                                    today_stats["websites"][url] = {"total_visits": 0, "successful_visits": 0, "failed_visits": 0}

                                today_stats["websites"][url]["total_visits"] += 1
                                if result.get("success"):
                                    today_stats["websites"][url]["successful_visits"] += 1
                                else:
                                    today_stats["websites"][url]["failed_visits"] += 1

                                # 保存统计
                                with open(stats_file, 'w', encoding='utf-8') as f:
                                    json.dump(today_stats, f, ensure_ascii=False, indent=2)

                                # 同时调用 monitor（可选）
                                monitor.record_visit(result)

                                # 打印结果
                                if result.get("success"):
                                    logger.info(f"✅ 访问成功: {url[:50]}...")
                                else:
                                    logger.error(f"❌ 访问失败: {url[:50]}... 错误: {result.get('error', '未知')[:50]}")
                else:
                    logger.info("⏳ 没有需要访问的网站")

                # 等待下一轮
                import random
                wait_time = random.randint(60, 180)  # 1-3分钟（缩短等待时间）
                logger.info(f"⏳ 等待 {wait_time} 秒后开始下一轮...")

                waited = 0
                while waited < wait_time and self.running:
                    await asyncio.sleep(1)
                    waited += 1

            except Exception as e:
                logger.error(f"❌ 流量机器人出错: {e}")
                await asyncio.sleep(60)

    def start(self):
        """启动服务器"""
        self.running = True

        # 配置日志
        logger.remove()
        logger.add(lambda msg: print(msg, end=""), level="INFO")
        logger.add("logs/server.log", rotation="1 day", retention="7 days")

        print(f"""
╔══════════════════════════════════════════════════════════╗
║           SEO Traffic Bot - 多用户服务器                 ║
╠══════════════════════════════════════════════════════════╣
║  仪表盘地址: http://0.0.0.0:{self.port:<5}                    ║
║  数据目录: data/                                         ║
╚══════════════════════════════════════════════════════════╝

📊 用户仪表盘功能:
   - 用户注册/登录
   - 网站管理
   - 统计数据查看
   - 排名查询
   - 任务列表
   - 趋势图表

🤖 流量机器人功能:
   - 自动访问所有用户网站
   - 数据隔离存储

按 Ctrl+C 停止服务
""")

        # 启动Web仪表盘（使用新的模块化Dashboard）
        dashboard_server.port = self.port
        dashboard_server.start_server()

        # 启动流量机器人（后台）
        loop = asyncio.get_event_loop()
        self.traffic_bot_task = loop.create_task(self.run_traffic_bot())

        try:
            # 保持运行
            loop.run_forever()
        except KeyboardInterrupt:
            print("\n👋 正在停止服务...")
            self.running = False
            if self.traffic_bot_task:
                self.traffic_bot_task.cancel()
            dashboard_server.stop_server()
            print("✅ 已停止")


def main():
    parser = argparse.ArgumentParser(description="SEO Traffic Bot - 多用户服务器")
    parser.add_argument("-p", "--port", type=int, default=8081, help="服务端口号 (默认: 8081)")

    args = parser.parse_args()

    server = MultiUserServer(port=args.port)
    server.start()


if __name__ == "__main__":
    main()
