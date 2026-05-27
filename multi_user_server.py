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

from src.multi_user_dashboard import multi_user_dashboard
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
                    
                    # 访问所有网站
                    for site_config in all_websites:
                        user_id = site_config.pop('_user_id', None)
                        
                        # 创建网站配置对象
                        from src.config_manager import WebsiteConfig
                        website = WebsiteConfig(**site_config)
                        
                        if website.enabled:
                            # 访问网站
                            result = await visitor_manager.visit_website(website)
                            
                            # 保存到用户专属统计目录
                            if user_id:
                                user_stats_dir = user_manager.get_user_data_dir(user_id) / "stats"
                                user_stats_dir.mkdir(parents=True, exist_ok=True)
                                
                                # 这里可以添加用户专属的统计记录逻辑
                                monitor.record_visit(result)
                else:
                    logger.info("⏳ 没有需要访问的网站")
                
                # 等待下一轮
                import random
                wait_time = random.randint(300, 600)  # 5-10分钟
                logger.info(f"⏳ 等待 {wait_time // 60} 分钟后开始下一轮...")
                
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

🤖 流量机器人功能:
   - 自动访问所有用户网站
   - 数据隔离存储

按 Ctrl+C 停止服务
""")
        
        # 启动Web仪表盘
        multi_user_dashboard.port = self.port
        multi_user_dashboard.start_server()
        
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
            multi_user_dashboard.stop_server()
            print("✅ 已停止")


def main():
    parser = argparse.ArgumentParser(description="SEO Traffic Bot - 多用户服务器")
    parser.add_argument("-p", "--port", type=int, default=8081, help="服务端口号 (默认: 8081)")
    
    args = parser.parse_args()
    
    server = MultiUserServer(port=args.port)
    server.start()


if __name__ == "__main__":
    main()
