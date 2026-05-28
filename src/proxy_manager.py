"""
代理管理模块 - 支持多种代理源
1. 免费代理池（默认启用）
2. 付费代理API（可选）
3. 直连备选
"""

import asyncio
import random
from typing import Optional, Dict
from loguru import logger

from .config_manager import config


class ProxyManager:
    """代理管理器 - 支持多种代理源"""

    def __init__(self):
        self.proxy_config = config.proxy
        self.enabled = self.proxy_config.enabled
        self.fallback_to_direct = self.proxy_config.fallback_to_direct
        self.test_url = self.proxy_config.test_url
        self.timeout = self.proxy_config.timeout

        # 免费代理池
        self._free_proxy_pool = None

    async def get_proxy(self) -> Optional[Dict]:
        """获取一个代理"""
        if not self.enabled:
            logger.debug("代理已禁用，使用直连")
            return None

        # 优先使用免费代理池
        proxy = await self._get_free_proxy()
        if proxy:
            return proxy

        # 免费代理不可用，尝试付费代理
        proxy = await self._get_paid_proxy()
        if proxy:
            return proxy

        # 都失败，使用直连
        if self.fallback_to_direct:
            logger.info("🔄 所有代理均不可用，使用直连")
            return None

        raise Exception("无法获取可用代理")

    async def _get_free_proxy(self) -> Optional[Dict]:
        """从免费代理池获取代理"""
        try:
            # 懒加载免费代理池
            if self._free_proxy_pool is None:
                from .free_proxy_pool import free_proxy_pool
                self._free_proxy_pool = free_proxy_pool

            proxy = await self._free_proxy_pool.get_proxy()
            if proxy:
                logger.info(f"✅ 使用免费代理: {proxy.get('ip', 'unknown')}:{proxy.get('port', 'unknown')}")
                return proxy
            else:
                logger.warning("⚠️ 免费代理池无可用代理")
                return None
        except Exception as e:
            logger.warning(f"⚠️ 获取免费代理失败: {e}")
            return None

    async def _get_paid_proxy(self) -> Optional[Dict]:
        """从付费代理API获取代理"""
        # 如果有付费代理配置，从这里获取
        # 目前未实现，可扩展
        return None

    async def get_proxy_with_retry(self, max_retries: int = 3) -> Optional[Dict]:
        """带重试的获取代理"""
        for attempt in range(max_retries):
            proxy = await self.get_proxy()
            if proxy is not None or not self.enabled:
                return proxy

            logger.warning(f"第 {attempt + 1} 次获取代理失败，{max_retries - attempt - 1} 次重试剩余")
            await asyncio.sleep(1)

        if self.fallback_to_direct:
            logger.info("所有重试失败，使用直连")
            return None

        raise Exception(f"经过 {max_retries} 次重试仍无法获取可用代理")

    def get_stats(self) -> Dict:
        """获取代理统计信息"""
        stats = {
            'enabled': self.enabled,
            'free_proxy_available': False,
            'paid_proxy_available': False,
            'fallback_to_direct': self.fallback_to_direct,
        }

        if self._free_proxy_pool:
            try:
                pool_stats = self._free_proxy_pool.get_stats()
                stats.update(pool_stats)
                stats['free_proxy_available'] = pool_stats.get('valid_count', 0) > 0
            except:
                pass

        return stats

    async def refresh_free_proxies(self):
        """刷新免费代理池"""
        if self._free_proxy_pool:
            await self._free_proxy_pool.fetch_and_validate()


# 全局代理管理器实例
proxy_manager = ProxyManager()
