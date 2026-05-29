"""
青果网络代理管理器 - 每次点击换新IP
"""

import asyncio
import aiohttp
import time
from typing import Optional, Dict
from loguru import logger


class QingguoProxyManager:
    """
    青果网络代理管理器
    
    策略：每次点击使用新IP（最安全的SEO做法）
    """

    def __init__(self, config: Dict = None):
        self.config = config or {}
        
        # API配置
        self.api_url = self.config.get('api_url', 'https://proxy.qg.net/get')
        self.auth_key = self.config.get('auth_key', '')
        self.auth_pwd = self.config.get('auth_pwd', '')
        
        # 限制配置
        self.max_calls_per_minute = 15
        self.min_interval = 4.0  # 4秒间隔 = 15次/分钟
        
        # 时间记录
        self._last_api_call = 0
        
        # 统计
        self.stats = {
            'total_fetched': 0,
            'total_used': 0,
            'api_calls': 0,
        }

    async def _wait_api_limit(self):
        """等待API速率限制"""
        elapsed = time.time() - self._last_api_call
        if elapsed < self.min_interval:
            wait = self.min_interval - elapsed
            await asyncio.sleep(wait)

    async def get_proxy(self) -> Optional[Dict]:
        """
        获取新代理（每次调用都获取新IP）
        """
        if not self.auth_key or not self.auth_pwd:
            logger.error("❌ 未配置青果网络API Key")
            return None

        await self._wait_api_limit()

        try:
            params = {
                'key': self.auth_key,
                'pwd': self.auth_pwd,
                'num': 1,
            }

            timeout = aiohttp.ClientTimeout(total=10)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(self.api_url, params=params) as resp:
                    self._last_api_call = time.time()
                    self.stats['api_calls'] += 1

                    if resp.status == 200:
                        data = await resp.text()
                        proxy_str = data.strip()
                        
                        if ':' in proxy_str:
                            parts = proxy_str.split(':')
                            if len(parts) == 2:
                                self.stats['total_fetched'] += 1
                                self.stats['total_used'] += 1
                                
                                logger.info(f"🍏 新代理: {proxy_str} (第{self.stats['total_fetched']}个)")
                                
                                return {
                                    'server': f"http://{proxy_str}",
                                    'ip': parts[0],
                                    'port': int(parts[1]),
                                    'source': 'qingguo'
                                }
                        else:
                            logger.warning(f"⚠️ 代理格式错误: {proxy_str}")
                    else:
                        logger.error(f"❌ API返回错误: {resp.status}")
                        
        except Exception as e:
            logger.error(f"❌ 获取代理失败: {e}")

        return None

    def get_stats(self) -> Dict:
        """获取统计信息"""
        return {
            **self.stats,
            'max_per_minute': self.max_calls_per_minute,
        }


# 全局实例
qingguo_proxy_manager = QingguoProxyManager()