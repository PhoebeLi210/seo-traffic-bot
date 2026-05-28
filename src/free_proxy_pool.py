"""
免费代理池模块 - 从多个免费代理源抓取、验证、轮换IP
"""

import asyncio
import aiohttp
import re
import random
import time
from typing import Optional, Dict, List
from dataclasses import dataclass
from loguru import logger
import threading


@dataclass
class Proxy:
    """代理数据类"""
    ip: str
    port: int
    protocol: str = "http"
    anonymity: str = "高匿名"
    location: str = ""
    speed: float = 0.0
    last_check: float = 0
    fail_count: int = 0
    success_count: int = 0

    @property
    def address(self) -> str:
        return f"{self.ip}:{self.port}"

    @property
    def is_valid(self) -> bool:
        return self.fail_count < 3


class FreeProxyPool:
    """免费代理池 - 抓取、验证、轮换免费代理"""

    # 免费代理源列表
    PROXY_SOURCES = [
        {
            'name': 'xicidaili',
            'url': 'https://www.xicidaili.com/wn/',
            'parser': 'html',
            'check_interval': 300,  # 5分钟刷新一次
        },
        {
            'name': 'kxdaili',
            'url': 'https://www.kxdaili.com/dailiip/1/',
            'parser': 'html',
            'check_interval': 300,
        },
    ]

    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.test_url = self.config.get('test_url', 'http://httpbin.org/ip')
        self.test_timeout = self.config.get('test_timeout', 5)
        self.max_proxies = self.config.get('max_proxies', 100)
        self.validate_before_use = self.config.get('validate_before_use', True)

        self._proxies: List[Proxy] = []
        self._lock = threading.Lock()
        self._last_fetch = 0
        self._fetch_interval = 300  # 5分钟抓取一次
        self._current_index = 0

        # 统计
        self.stats = {
            'total_fetched': 0,
            'valid_count': 0,
            'used_count': 0,
            'fail_count': 0,
        }

    async def fetch_from_source(self, source: Dict) -> List[Proxy]:
        """从单个源抓取代理"""
        proxies = []
        try:
            timeout = aiohttp.ClientTimeout(total=30)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
                async with session.get(source['url'], headers=headers, ssl=False) as resp:
                    if resp.status == 200:
                        html = await resp.text()

                        if source['parser'] == 'html':
                            # 解析HTML表格
                            proxies = self._parse_html_proxies(html)
                        elif source['parser'] == 'text':
                            # 解析纯文本
                            proxies = self._parse_text_proxies(html)

                        logger.info(f"从 {source['name']} 获取到 {len(proxies)} 个代理")
                    else:
                        logger.warning(f"代理源 {source['name']} 返回状态码: {resp.status}")
        except Exception as e:
            logger.warning(f"从 {source['name']} 抓取失败: {e}")

        return proxies

    def _parse_html_proxies(self, html: str) -> List[Proxy]:
        """解析HTML表格格式的代理"""
        proxies = []
        # 匹配 IP 和端口
        ip_pattern = r'<td>(\d+\.\d+\.\d+\.\d+)</td>'
        port_pattern = r'<td>(\d+)</td>'

        ips = re.findall(ip_pattern, html)
        ports = re.findall(port_pattern, html)

        for i, ip in enumerate(ips[:50]):  # 限制数量
            if i < len(ports):
                try:
                    proxy = Proxy(
                        ip=ip,
                        port=int(ports[i]),
                        last_check=time.time()
                    )
                    proxies.append(proxy)
                except:
                    pass

        return proxies

    def _parse_text_proxies(self, text: str) -> List[Proxy]:
        """解析纯文本格式的代理 (ip:port)"""
        proxies = []
        lines = text.strip().split('\n')

        for line in lines[:50]:
            line = line.strip()
            if ':' in line:
                parts = line.split(':')
                if len(parts) >= 2:
                    try:
                        proxy = Proxy(
                            ip=parts[0].strip(),
                            port=int(parts[1].strip()),
                            last_check=time.time()
                        )
                        proxies.append(proxy)
                    except:
                        pass

        return proxies

    async def validate_proxy(self, proxy: Proxy) -> bool:
        """验证单个代理是否可用"""
        try:
            proxy_url = f"http://{proxy.ip}:{proxy.port}"
            timeout = aiohttp.ClientTimeout(total=self.test_timeout)

            async with aiohttp.ClientSession(timeout=timeout) as session:
                start = time.time()
                async with session.get(self.test_url, proxy=proxy_url, ssl=False) as resp:
                    elapsed = time.time() - start
                    if resp.status == 200:
                        proxy.speed = elapsed
                        proxy.last_check = time.time()
                        proxy.success_count += 1
                        return True
                    else:
                        proxy.fail_count += 1
                        return False
        except Exception as e:
            proxy.fail_count += 1
            return False

    async def fetch_and_validate(self) -> int:
        """抓取并验证所有代理源"""
        logger.info("🔄 开始抓取免费代理...")

        all_proxies = []

        # 从所有源抓取
        tasks = [self.fetch_from_source(source) for source in self.PROXY_SOURCES]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, list):
                all_proxies.extend(result)

        # 去重
        seen = set()
        unique_proxies = []
        for p in all_proxies:
            if p.address not in seen:
                seen.add(p.address)
                unique_proxies.append(p)

        logger.info(f"抓取到 {len(unique_proxies)} 个唯一代理，开始验证...")

        # 验证代理（并发但限制数量）
        validated = []
        semaphore = asyncio.Semaphore(20)  # 最多20个并发

        async def validate_with_limit(proxy):
            async with semaphore:
                if await self.validate_proxy(proxy):
                    return proxy
                return None

        tasks = [validate_with_limit(p) for p in unique_proxies[:50]]  # 最多验证50个
        results = await asyncio.gather(*tasks)

        for result in results:
            if result:
                validated.append(result)

        # 更新代理池
        with self._lock:
            self._proxies = validated
            self.stats['total_fetched'] = len(unique_proxies)
            self.stats['valid_count'] = len(validated)

        logger.info(f"✅ 验证完成，{len(validated)}/{len(unique_proxies)} 个代理可用")

        self._last_fetch = time.time()
        return len(validated)

    async def get_proxy(self) -> Optional[Dict]:
        """获取一个可用代理"""
        # 检查是否需要刷新
        if time.time() - self._last_fetch > self._fetch_interval:
            await self.fetch_and_validate()

        with self._lock:
            if not self._proxies:
                return None

            # 轮询获取
            self._current_index = (self._current_index + 1) % len(self._proxies)
            proxy = self._proxies[self._current_index]

            # 检查代理是否有效
            if not proxy.is_valid:
                # 移除无效代理
                self._proxies.remove(proxy)
                self.stats['fail_count'] += 1
                return self.get_proxy()  # 递归获取下一个

        # 验证代理（如果需要）
        if self.validate_before_use:
            if not await self.validate_proxy(proxy):
                with self._lock:
                    if proxy in self._proxies:
                        self._proxies.remove(proxy)
                return self.get_proxy()

        self.stats['used_count'] += 1
        return {
            'server': f"http://{proxy.address}",
            'ip': proxy.ip,
            'port': proxy.port
        }

    def get_stats(self) -> Dict:
        """获取代理池统计信息"""
        with self._lock:
            return {
                **self.stats,
                'pool_size': len(self._proxies),
                'last_fetch': self._last_fetch,
                'last_fetch_time': time.strftime('%H:%M:%S', time.localtime(self._last_fetch)) if self._last_fetch else '从未刷新'
            }

    async def start_background_refresh(self, interval: int = 300):
        """启动后台定时刷新"""
        while True:
            await asyncio.sleep(interval)
            try:
                await self.fetch_and_validate()
            except Exception as e:
                logger.error(f"后台刷新失败: {e}")


# 全局代理池实例
proxy_pool = FreeProxyPool()


# 便捷函数
async def get_free_proxy() -> Optional[Dict]:
    """获取一个免费代理"""
    return await proxy_pool.get_proxy()


async def refresh_proxy_pool():
    """刷新代理池"""
    return await proxy_pool.fetch_and_validate()


def get_proxy_pool_stats() -> Dict:
    """获取代理池状态"""
    return proxy_pool.get_stats()
