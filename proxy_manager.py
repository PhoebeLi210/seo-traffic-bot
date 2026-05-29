"""
代理管理模块 - 支持多种代理源
优先级：青果网络 > 免费代理池
"""

import asyncio
from typing import Optional, Dict
from loguru import logger

from .config_manager import config


class ProxyManager:
    """代理管理器 - 支持多种代理源"""

    def __init__(self):
        self.proxy_config = config.proxy
        self.enabled = self.proxy_config.enabled
        self.allow_direct = False  # 默认不允许直连

        # 青果网络代理管理器
        self._qingguo_manager = None
        
        # 免费代理池
        self._free_proxy_pool = None

    async def get_proxy(self) -> Optional[Dict]:
        """获取一个代理（按优先级）"""
        if not self.enabled:
            logger.debug("代理已禁用")
            return None

        # 1. 优先使用青果网络代理
        proxy = await self._get_qingguo_proxy()
        if proxy:
            return proxy

        # 2. 青果网络不可用，尝试免费代理池
        proxy = await self._get_free_proxy()
        if proxy:
            return proxy

        # 3. 都失败，返回None（不使用直连）
        logger.warning("⚠️ 没有可用代理，暂停本次访问")
        return None

    async def _get_qingguo_proxy(self) -> Optional[Dict]:
        """从青果网络获取代理"""
        try:
            if self._qingguo_manager is None:
                from .qingguo_proxy_manager import qingguo_proxy_manager
                self._qingguo_manager = qingguo_proxy_manager

            proxy = await self._qingguo_manager.get_proxy()
            if proxy:
                logger.info(f"🍏 使用青果代理: {proxy['ip']}:{proxy['port']}")
                return proxy
            else:
                logger.debug("⚠️ 青果网络无可用代理")
                return None
        except Exception as e:
            logger.debug(f"⚠️ 获取青果代理失败: {e}")
            return None

    async def _get_free_proxy(self) -> Optional[Dict]:
        """从免费代理池获取代理"""
        try:
            if self._free_proxy_pool is None:
                from .free_proxy_pool import free_proxy_pool
                self._free_proxy_pool = free_proxy_pool

            proxy = await self._free_proxy_pool.get_proxy()
            if proxy:
                logger.info(f"🆓 使用免费代理: {proxy.get('ip', 'unknown')}")
                return proxy
            return None
        except Exception as e:
            logger.debug(f"⚠️ 获取免费代理失败: {e}")
            return None

    async def get_proxy_with_retry(self, max_retries: int = 3) -> Optional[Dict]:
        """带重试的获取代理"""
        for attempt in range(max_retries):
            proxy = await self.get_proxy()
            if proxy is not None:
                return proxy

            if attempt < max_retries - 1:
                logger.warning(f"第 {attempt + 1} 次获取代理失败，{max_retries - attempt - 1} 次重试剩余")
                await asyncio.sleep(2)

        logger.warning("⚠️ 所有重试失败，无可用代理")
        return None

    def get_stats(self) -> Dict:
        """获取代理统计信息"""
        stats = {
            'enabled': self.enabled,
            'allow_direct': self.allow_direct,
        }

        # 青果网络统计
        if self._qingguo_manager:
            try:
                stats['qingguo'] = self._qingguo_manager.get_stats()
            except:
                pass

        return stats


# 全局代理管理器实例
proxy_manager = ProxyManager()