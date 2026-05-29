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
        
        # API配置（根据青果网络文档）
        self.api_url = self.config.get('api_url', 'https://api.qg.net/proxy')  
        self.authkey = self.config.get('authkey', '')       # 注意参数名是 authkey
        self.authpwd = self.config.get('authpwd', '')       # 注意参数名是 authpwd
        self.protocol = self.config.get('protocol', 'http') # 支持 http 或 https
        self.num = self.config.get('num', 1)                # 每次提取IP数量（通道提取只能为1）
        
        # 限制配置（通道提取 API 限制：通道数*5+10，1通道 = 15次/分钟）
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
        根据青果网络文档：http://api.qg.net/proxy?authkey=xxx&authpwd=xxx&protocol=http&num=1
        """
        if not self.authkey or not self.authpwd:
            logger.error("❌ 未配置青果网络 AuthKey 或 AuthPwd")
            return None

        await self._wait_api_limit()

        params = {
            'authkey': self.authkey,
            'authpwd': self.authpwd,
            'protocol': self.protocol,
            'num': self.num
        }

        try:
            timeout = aiohttp.ClientTimeout(total=10)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(self.api_url, params=params) as resp:
                    self._last_api_call = time.time()
                    self.stats['api_calls'] += 1

                    if resp.status == 200:
                        data = await resp.json()
                        
                        # 检查返回格式
                        if data.get('code') == 200 and data.get('data'):
                            proxy_info = data['data'][0]
                            ip = proxy_info['ip']
                            port = proxy_info['port']
                            deadline = proxy_info.get('deadline')
                            
                            proxy_str = f"{ip}:{port}"
                            self.stats['total_fetched'] += 1
                            self.stats['total_used'] += 1
                            
                            logger.info(f"🍏 新代理: {proxy_str} (第{self.stats['total_fetched']}个) 存活至 {deadline}")
                            
                            return {
                                'server': f"{self.protocol}://{proxy_str}",
                                'ip': ip,
                                'port': port,
                                'deadline': deadline,
                                'source': 'qingguo'
                            }
                        else:
                            logger.error(f"❌ API返回错误码: {data.get('code')}, 信息: {data.get('msg', '未知错误')}")
                    else:
                        logger.error(f"❌ API HTTP错误: {resp.status}")
                        
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