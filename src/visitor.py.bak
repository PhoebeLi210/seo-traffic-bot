"""
网站访问模块 - 负责访问单个网站并模拟用户行为
"""

import asyncio
import random
from datetime import datetime
from typing import Optional, Dict, Any
from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from loguru import logger

from .config_manager import config, WebsiteConfig
from .proxy_manager import proxy_manager
from .stealth_enhancer import stealth_enhancer
from .behavior_simulator import behavior_simulator


class WebsiteVisitor:
    """网站访问器"""
    
    def __init__(self):
        self.browser_config = config.browser
        self.timeout = self.browser_config.timeout
        self.headless = self.browser_config.headless
    
    async def visit(self, website: WebsiteConfig) -> Dict[str, Any]:
        """
        访问网站并模拟用户行为
        
        Args:
            website: 网站配置
            
        Returns:
            访问结果字典
        """
        result = {
            "url": website.url,
            "success": False,
            "start_time": datetime.now().isoformat(),
            "end_time": None,
            "duration": 0,
            "error": None,
            "pages_visited": 0,
        }
        
        browser: Optional[Browser] = None
        context: Optional[BrowserContext] = None
        page: Optional[Page] = None
        
        try:
            # 获取代理
            proxy = await proxy_manager.get_proxy_with_retry()
            
            # 启动浏览器 - 使用简化参数提高稳定性
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=self.headless,
                    args=[
                        '--no-sandbox',
                        '--disable-dev-shm-usage',
                        '--disable-gpu',
                    ]
                )
            
            # 创建反检测上下文
            context = await stealth_enhancer.create_stealth_context(browser, proxy)
            
            # 创建新页面
            page = await context.new_page()
            
            # 访问目标网站
            logger.info(f"🌐 正在访问: {website.url}")
            
            try:
                response = await page.goto(
                    website.url,
                    wait_until="domcontentloaded",
                    timeout=self.timeout
                )
                
                if response:
                    status = response.status
                    logger.info(f"✅ 页面加载成功，状态码: {status}")
                    result["pages_visited"] = 1
                else:
                    logger.warning("⚠️ 页面加载无响应")
                
                # 模拟用户行为
                await behavior_simulator.simulate_browsing(page)
                
                result["success"] = True
                
            except Exception as e:
                import traceback
                logger.error(f"❌ 页面访问失败: {e}")
                logger.error(f"详细错误: {traceback.format_exc()}")
                result["error"] = str(e)
            
            # 清理资源
            if context:
                await context.close()
            if browser:
                await browser.close()
        
        except Exception as e:
            import traceback
            logger.error(f"❌ 访问过程出错: {e}")
            logger.error(f"详细错误: {traceback.format_exc()}")
            result["error"] = str(e)
        
        finally:
            result["end_time"] = datetime.now().isoformat()
            if result["start_time"]:
                start = datetime.fromisoformat(result["start_time"])
                end = datetime.fromisoformat(result["end_time"])
                result["duration"] = (end - start).total_seconds()
        
        return result


class VisitorManager:
    """访问管理器"""
    
    def __init__(self):
        self.visitor = WebsiteVisitor()
        self.behavior_config = config.behavior
    
    async def visit_website(self, website: WebsiteConfig) -> Dict[str, Any]:
        """
        访问单个网站
        
        Args:
            website: 网站配置
            
        Returns:
            访问结果
        """
        return await self.visitor.visit(website)
    
    async def visit_all_websites(self) -> list:
        """
        访问所有启用的网站
        
        Returns:
            所有访问结果列表
        """
        websites = config.websites
        results = []
        
        for website in websites:
            result = await self.visit_website(website)
            results.append(result)
            
            # 访问间隔
            if website != websites[-1]:  # 不是最后一个
                min_interval = self.behavior_config.min_visit_interval
                max_interval = self.behavior_config.max_visit_interval
                wait_time = random.randint(min_interval, max_interval)
                
                minutes = wait_time // 60
                seconds = wait_time % 60
                logger.info(f"⏳ 等待 {minutes} 分 {seconds} 秒后继续...")
                await asyncio.sleep(wait_time)
        
        return results
    
    async def run_continuous(self):
        """持续运行模式"""
        logger.info(f"🚀 启动持续运行模式，监控 {len(config.websites)} 个网站")
        
        while True:
            try:
                results = await self.visit_all_websites()
                
                # 统计结果
                success_count = sum(1 for r in results if r["success"])
                logger.info(f"📊 本轮访问完成: {success_count}/{len(results)} 成功")
                
                # 等待下一轮
                min_interval = self.behavior_config.min_visit_interval
                max_interval = self.behavior_config.max_visit_interval
                wait_time = random.randint(min_interval, max_interval)
                
                minutes = wait_time // 60
                logger.info(f"⏳ 等待 {minutes} 分钟后开始下一轮...")
                await asyncio.sleep(wait_time)
                
            except asyncio.CancelledError:
                logger.info("👋 收到停止信号，正在退出...")
                break
            except Exception as e:
                logger.error(f"❌ 运行出错: {e}")
                await asyncio.sleep(60)  # 出错后等待1分钟再重试


# 全局访问管理器实例
visitor_manager = VisitorManager()
