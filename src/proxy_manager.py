"""
代理管理模块 - 负责获取和管理代理IP
"""

import asyncio
import aiohttp
from typing import Optional, Dict, Any
from loguru import logger

from .config_manager import config


class ProxyManager:
    """代理管理器"""
    
    def __init__(self):
        self.proxy_config = config.proxy
        self.enabled = self.proxy_config.enabled
        self.api_url = self.proxy_config.api_url
        self.fallback_to_direct = self.proxy_config.fallback_to_direct
        self.test_url = self.proxy_config.test_url
        self.timeout = self.proxy_config.timeout
        
        self._proxy_cache: Optional[str] = None
        self._cache_time: Optional[float] = None
        self._cache_duration = 300  # 缓存5分钟
    
    async def get_proxy(self) -> Optional[Dict[str, str]]:
        """
        从代理池获取一个可用代理
        
        Returns:
            代理字典，格式为 {"server": "http://ip:port"}
            如果获取失败且允许直连，返回 None
        """
        if not self.enabled:
            logger.debug("代理已禁用，使用直连")
            return None
        
        # 检查缓存
        if self._proxy_cache and self._cache_time:
            import time
            if time.time() - self._cache_time < self._cache_duration:
                logger.debug(f"使用缓存代理: {self._proxy_cache}")
                return {"server": f"http://{self._proxy_cache}"}
        
        try:
            proxy = await self._fetch_from_pool()
            if proxy:
                # 验证代理是否可用
                if await self._test_proxy(proxy):
                    self._proxy_cache = proxy
                    self._cache_time = asyncio.get_event_loop().time()
                    logger.info(f"✅ 获取到可用代理: {proxy}")
                    return {"server": f"http://{proxy}"}
                else:
                    logger.warning(f"⚠️ 代理测试失败: {proxy}")
            
            # 获取失败或测试失败
            if self.fallback_to_direct:
                logger.info("🔄 使用本机IP直连")
                return None
            else:
                raise Exception("无法获取可用代理")
                
        except Exception as e:
            logger.error(f"❌ 获取代理失败: {e}")
            if self.fallback_to_direct:
                return None
            raise
    
    async def _fetch_from_pool(self) -> Optional[str]:
        """
        从代理池API获取代理
        
        Returns:
            代理地址，格式为 "ip:port"
        """
        try:
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(self.api_url) as resp:
                    if resp.status == 200:
                        proxy = await resp.text()
                        proxy = proxy.strip()
                        if proxy and ':' in proxy:
                            return proxy
                        else:
                            logger.warning(f"代理池返回格式异常: {proxy}")
                    else:
                        logger.warning(f"代理池API返回状态码: {resp.status}")
        except asyncio.TimeoutError:
            logger.error("获取代理超时")
        except Exception as e:
            logger.error(f"请求代理池失败: {e}")
        
        return None
    
    async def _test_proxy(self, proxy: str) -> bool:
        """
        测试代理是否可用
        
        Args:
            proxy: 代理地址，格式为 "ip:port"
            
        Returns:
            代理是否可用
        """
        try:
            proxy_url = f"http://{proxy}"
            timeout = aiohttp.ClientTimeout(total=10)
            
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(
                    self.test_url,
                    proxy=proxy_url,
                    ssl=False
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        logger.debug(f"代理测试成功，出口IP: {data.get('origin', 'unknown')}")
                        return True
                    return False
        except Exception as e:
            logger.debug(f"代理测试失败: {e}")
            return False
    
    async def get_proxy_with_retry(self, max_retries: int = 3) -> Optional[Dict[str, str]]:
        """
        带重试机制的获取代理
        
        Args:
            max_retries: 最大重试次数
            
        Returns:
            代理字典或 None
        """
        for attempt in range(max_retries):
            proxy = await self.get_proxy()
            if proxy is not None or not self.enabled:
                return proxy
            
            logger.warning(f"第 {attempt + 1} 次获取代理失败，{max_retries - attempt - 1} 次重试剩余")
            await asyncio.sleep(1)
        
        if self.fallback_to_direct:
            logger.info("所有重试失败，使用本机IP直连")
            return None
        
        raise Exception(f"经过 {max_retries} 次重试仍无法获取可用代理")
    
    def invalidate_cache(self):
        """使代理缓存失效"""
        self._proxy_cache = None
        self._cache_time = None
        logger.debug("代理缓存已清除")


# 全局代理管理器实例
proxy_manager = ProxyManager()
