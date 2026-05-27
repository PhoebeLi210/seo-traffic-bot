"""
用户行为模拟模块 - 模拟真实用户的浏览行为
"""

import asyncio
import random
from typing import Optional
from playwright.async_api import Page
from loguru import logger

from .config_manager import config


class BehaviorSimulator:
    """用户行为模拟器"""
    
    def __init__(self):
        self.behavior_config = config.behavior
        self.scroll_config = self.behavior_config.scroll
        self.mouse_config = self.behavior_config.mouse_move
        self.click_config = self.behavior_config.click
    
    async def simulate_browsing(self, page: Page):
        """
        模拟完整的浏览行为
        
        Args:
            page: Playwright页面对象
        """
        # 随机停留时间
        await self._simulate_stay(page)
        
        # 模拟滚动
        if self.scroll_config.get('enabled', True):
            await self._simulate_scrolling(page)
        
        # 模拟鼠标移动
        if self.mouse_config.get('enabled', True):
            await self._simulate_mouse_movement(page)
        
        # 模拟点击
        if self.click_config.get('enabled', True):
            await self._simulate_clicks(page)
    
    async def _simulate_stay(self, page: Page):
        """
        模拟页面停留
        
        Args:
            page: Playwright页面对象
        """
        min_duration = self.behavior_config.min_stay_duration
        max_duration = self.behavior_config.max_stay_duration
        stay_duration = random.randint(min_duration, max_duration)
        
        logger.info(f"💤 页面停留 {stay_duration} 秒...")
        
        # 分段等待，模拟真实阅读行为
        remaining = stay_duration
        while remaining > 0:
            # 随机暂停1-3秒
            pause = min(random.uniform(1, 3), remaining)
            await asyncio.sleep(pause)
            remaining -= pause
            
            # 偶尔小幅度滚动
            if random.random() < 0.3 and remaining > 5:
                scroll_amount = random.randint(-100, 100)
                await page.evaluate(f"window.scrollBy(0, {scroll_amount})")
    
    async def _simulate_scrolling(self, page: Page):
        """
        模拟页面滚动
        
        Args:
            page: Playwright页面对象
        """
        min_scrolls = self.scroll_config.get('min_scrolls', 2)
        max_scrolls = self.scroll_config.get('max_scrolls', 5)
        num_scrolls = random.randint(min_scrolls, max_scrolls)
        
        min_distance = self.scroll_config.get('min_scroll_distance', 300)
        max_distance = self.scroll_config.get('max_scroll_distance', 1500)
        
        logger.debug(f"📜 模拟滚动 {num_scrolls} 次")
        
        for i in range(num_scrolls):
            # 随机滚动距离
            scroll_distance = random.randint(min_distance, max_distance)
            
            # 随机滚动方向（偶尔向上滚动）
            if random.random() < 0.2:
                scroll_distance = -random.randint(200, 500)
            
            # 平滑滚动
            await page.evaluate(f"""
                window.scrollBy({{
                    top: {scroll_distance},
                    behavior: 'smooth'
                }});
            """)
            
            # 滚动后等待
            await asyncio.sleep(random.uniform(1, 3))
    
    async def _simulate_mouse_movement(self, page: Page):
        """
        模拟鼠标移动
        
        Args:
            page: Playwright页面对象
        """
        min_moves = self.mouse_config.get('min_moves', 3)
        max_moves = self.mouse_config.get('max_moves', 8)
        num_moves = random.randint(min_moves, max_moves)
        
        logger.debug(f"🖱️ 模拟鼠标移动 {num_moves} 次")
        
        for i in range(num_moves):
            # 随机目标位置
            x = random.randint(100, 1500)
            y = random.randint(100, 800)
            
            # 移动鼠标
            await page.mouse.move(x, y)
            
            # 移动后短暂停留
            await asyncio.sleep(random.uniform(0.5, 1.5))
    
    async def _simulate_clicks(self, page: Page):
        """
        模拟页面点击
        
        Args:
            page: Playwright页面对象
        """
        click_probability = self.click_config.get('click_probability', 0.4)
        
        # 根据概率决定是否点击
        if random.random() > click_probability:
            return
        
        max_clicks = self.click_config.get('max_clicks_per_page', 2)
        num_clicks = random.randint(1, max_clicks)
        
        logger.debug(f"👆 尝试点击 {num_clicks} 个链接")
        
        for i in range(num_clicks):
            try:
                # 获取页面上的所有链接
                links = await page.query_selector_all('a[href]:not([href^="#"]):not([href^="javascript"])')
                
                if not links:
                    logger.debug("页面上没有可点击的链接")
                    return
                
                # 随机选择一个链接
                random_link = random.choice(links)
                
                # 获取链接信息
                href = await random_link.get_attribute('href')
                text = await random_link.text_content()
                
                # 检查链接是否可见
                is_visible = await random_link.is_visible()
                if not is_visible:
                    continue
                
                logger.info(f"🔗 点击链接: {text[:30] if text else '无文本'} -> {href[:50] if href else '无链接'}...")
                
                # 滚动到链接位置
                await random_link.scroll_into_view_if_needed()
                await asyncio.sleep(random.uniform(0.5, 1))
                
                # 点击链接
                await random_link.click()
                
                # 等待页面加载
                await page.wait_for_load_state('networkidle')
                
                # 在新页面停留
                await self._simulate_stay(page)
                
                # 返回原页面
                await page.go_back()
                await page.wait_for_load_state('networkidle')
                
            except Exception as e:
                logger.warning(f"点击操作失败: {e}")
                continue
    
    async def simulate_human_like_delay(self):
        """模拟人类反应延迟"""
        delay = random.uniform(0.5, 2)
        await asyncio.sleep(delay)


# 全局行为模拟器实例
behavior_simulator = BehaviorSimulator()
