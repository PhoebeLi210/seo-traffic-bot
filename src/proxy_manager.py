"""
代理管理模块 - 负责获取和管理代理IP
支持多个免费代理源轮换
"""

import asyncio
import aiohttp
import random
from typing import Optional, Dict, Any, List
from loguru import logger

from .config_manager import config


class ProxyManager:
    """代理管理器 - 支持多代理源轮换"""
    
    # 免费代理API列表（已禁用，因为都返回404）
    # 如果需要启用代理，可以在这里添加其他有效的代理源
    FREE_PROXY_APIS = []
    
    # 付费代理API模板（需要用户提供）
    PAID_PROXY_APIS = []
    
    def __init__(self):
        self.proxy_config = config.proxy
        self.enabled = self.proxy_config.enabled
        self.fallback_to_direct = self.proxy_config.fallback_to_direct
        self.test_url = self.proxy_config.test_url
        self.timeout = self.proxy_config.timeout
        
        self._proxy_cache: Optional[str] = None
        self._cache_time: Optional[float] = None
        self._cache_duration = 60  # 缓存1分钟，避免重复使用同一代理
        self._used_proxies: set = set()  # 记录已使用的代理，避免重复
        self._proxy_index = 0  # 当前使用的代理源索引
    
    async def get_proxy(self) -> Optional[Dict[str, str]]:
        """
        从代理池获取一个可用代理
        
        Returns:
            代理字典，格式为 {"server": "http://ip:port", "type": "http"}
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
            # 尝试从多个代理源获取
            for attempts in range(3):
                proxy = await self._fetch_proxy_from_sources()
                if proxy:
                    # 验证代理是否可用
                    if await self._test_proxy(proxy):
                        self._proxy_cache = proxy
                        import time
                        self._cache_time = time.time()
                        self._used_proxies.add(proxy)
                        logger.info(f"✅ 获取到可用代理: {proxy}")
                        return {"server": f"http://{proxy}"}
                    else:
                        logger.warning(f"⚠️ 代理测试失败，跳过: {proxy}")
                        continue
            
            # 所有代理源都失败
            if self.fallback_to_direct:
                logger.info("🔄 所有代理源均无可用代理，使用直连")
                return None
            else:
                raise Exception("无法获取可用代理")
                
        except Exception as e:
            logger.error(f"❌ 获取代理失败: {e}")
            if self.fallback_to_direct:
                return None
            raise
    
    async def _fetch_proxy_from_sources(self) -> Optional[str]:
        """
        从多个代理源获取代理，轮换尝试
        
        Returns:
            代理地址，格式为 "ip:port"
        """
        # 随机打乱代理源顺序，避免总是用同一个
        sources = self.FREE_PROXY_APIS.copy()
        random.shuffle(sources)
        
        for source in sources:
            try:
                proxy = await self._fetch_from_source(source)
                if proxy and proxy not in self._used_proxies:
                    logger.debug(f"从 {source['name']} 获取到代理: {proxy}")
                    return proxy
            except Exception as e:
                logger.warning(f"从 {source['name']} 获取代理失败: {e}")
                continue
        
        # 如果免费代理都失败，尝试付费代理
        for source in self.PAID_PROXY_APIS:
            try:
                proxy = await self._fetch_from_source(source)
                if proxy and proxy not in self._used_proxies:
                    logger.info(f"从付费代理源 {source['name']} 获取到代理: {proxy}")
                    return proxy
            except Exception as e:
                logger.warning(f"从付费代理源 {source['name']} 获取代理失败: {e}")
                continue
        
        return None
    
    async def _fetch_from_source(self, source: Dict) -> Optional[str]:
        """
        从单个代理源获取代理
        
        Args:
            source: 代理源配置
            
        Returns:
            代理地址，格式为 "ip:port"
        """
        url = source.get('api', source.get('url'))
        
        try:
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url, ssl=False) as resp:
                    if resp.status == 200:
                        if source['parser'] == 'text':
                            # 纯文本格式：每行 ip:port
                            text = await resp.text()
                            proxies = [line.strip() for line in text.strip().split('\n') if ':' in line]
                            if proxies:
                                return random.choice(proxies)
                        elif source['parser'] == 'json':
                            # JSON格式
                            try:
                                data = await resp.json()
                                if isinstance(data, list) and len(data) > 0:
                                    item = random.choice(data)
                                    ip = item.get('ip', item.get('IP', ''))
                                    port = item.get('port', item.get('Port', ''))
                                    if ip and port:
                                        return f"{ip}:{port}"
                                elif isinstance(data, dict):
                                    # 可能包装在某个key里
                                    for key in ['data', 'list', 'result']:
                                        if key in data and isinstance(data[key], list) and data[key]:
                                            item = random.choice(data[key])
                                            ip = item.get('ip', item.get('IP', ''))
                                            port = item.get('port', item.get('Port', ''))
                                            if ip and port:
                                                return f"{ip}:{port}"
                            except:
                                pass
                    else:
                        logger.warning(f"代理源 {source['name']} 返回状态码: {resp.status}")
        except asyncio.TimeoutError:
            logger.debug(f"代理源 {source['name']} 请求超时")
        except Exception as e:
            logger.debug(f"代理源 {source['name']} 请求失败: {e}")
        
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
                        logger.debug(f"代理测试成功: {proxy}")
                        return True
                    return False
        except Exception as e:
            logger.debug(f"代理测试失败 {proxy}: {e}")
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
            await asyncio.sleep(2)
        
        if self.fallback_to_direct:
            logger.info("所有重试失败，使用直连")
            return None
        
        raise Exception(f"经过 {max_retries} 次重试仍无法获取可用代理")
    
    def invalidate_cache(self):
        """使代理缓存失效"""
        self._proxy_cache = None
        self._cache_time = None
        logger.debug("代理缓存已清除")
    
    def reset_used_proxies(self):
        """重置已使用代理记录，允许重复使用"""
        self._used_proxies.clear()
        logger.info("已重置代理使用记录")


# 全局代理管理器实例
proxy_manager = ProxyManager()
