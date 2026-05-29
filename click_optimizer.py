
#!/www/wwwroot/zhongshunbaode.com/stats/venv/bin/python

"""

独立 SEO 点击优化脚本 - 从用户数据目录读取网站配置

"""



import asyncio

import json

import random

import sys

import os

import time

from pathlib import Path

from loguru import logger

from playwright.async_api import async_playwright

import aiohttp

import yaml



# 添加项目根目录到路径

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))



# ========== 配置区域 ==========

# 用户ID（从您的 data/user_data 目录中找到的实际 ID）

USER_ID = "46cc8cdf3544ef89"



# 读取青果网络配置

with open('config/settings.yaml', 'r') as f:

    settings = yaml.safe_load(f)

    qg = settings.get('qingguo', {})

    AUTHKEY = qg.get('authkey', '')

    AUTHPWD = qg.get('authpwd', '')

    API_URL = qg.get('api_url', 'https://api.qg.net/proxy')

    PROTOCOL = qg.get('protocol', 'http')

    NUM = qg.get('num', 1)



# 用户网站配置文件路径

WEBSITES_JSON = Path(f"data/user_data/{USER_ID}/config/websites.json")



# 点击参数

KEYWORDS_PER_IP = random.randint(2, 3)   # 每个IP处理2-3个关键词

CLICKS_PER_KEYWORD = 5                  # 每个关键词点击次数

HEADLESS = True                         # 无头模式

TIMEOUT = 30000                         # 页面加载超时(ms)



# ========== 代理获取类 ==========

class QingguoProxy:

    def __init__(self):

        self.authkey = AUTHKEY

        self.authpwd = AUTHPWD

        self.api_url = API_URL

        self.protocol = PROTOCOL

        self.num = NUM

        self._last_call = 0

        self.min_interval = 4.0   # 15次/分钟



    async def _wait(self):

        elapsed = time.time() - self._last_call

        if elapsed < self.min_interval:

            await asyncio.sleep(self.min_interval - elapsed)



    async def get(self):

        if not self.authkey or not self.authpwd:

            logger.error("❌ 青果网络 AuthKey 或 AuthPwd 未配置")

            return None

        await self._wait()

        params = {

            'authkey': self.authkey,

            'authpwd': self.authpwd,

            'protocol': self.protocol,

            'num': self.num

        }

        try:

            async with aiohttp.ClientSession() as session:

                async with session.get(self.api_url, params=params, timeout=10) as resp:

                    self._last_call = time.time()

                    if resp.status == 200:

                        data = await resp.json()

                        if data.get('code') == 200 and data.get('data'):

                            info = data['data'][0]

                            ip = info['ip']

                            port = info['port']

                            proxy_str = f"{ip}:{port}"

                            logger.info(f"🍏 获取新代理: {proxy_str}")

                            return {'server': f"{self.protocol}://{proxy_str}", 'ip': ip, 'port': port}

                        else:

                            logger.error(f"API 返回错误: {data}")

                    else:

                        logger.error(f"HTTP {resp.status}")

        except Exception as e:

            logger.error(f"获取代理失败: {e}")

        return None



# ========== 点击执行类 ==========

class ClickOptimizer:

    def __init__(self):

        self.proxy_fetcher = QingguoProxy()

        self.keywords_per_ip = KEYWORDS_PER_IP

        self.clicks_per_keyword = CLICKS_PER_KEYWORD

        self.headless = HEADLESS

        self.timeout = TIMEOUT



    async def _click_batch(self, url: str, keywords: list, proxy: dict):

        """使用同一个代理访问一批关键词"""

        async with async_playwright() as p:

            browser = await p.chromium.launch(

                headless=self.headless,

                args=['--no-sandbox', '--disable-dev-shm-usage', '--disable-gpu']

            )

            proxy_config = {"server": proxy['server']} if proxy else None

            context = await browser.new_context(proxy=proxy_config)

            await context.set_extra_http_headers({

                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

            })

            for kw in keywords:

                for i in range(self.clicks_per_keyword):

                    page = await context.new_page()

                    # 构造带关键词参数的URL（可选）

                    sep = '&' if '?' in url else '?'

                    target_url = f"{url}{sep}keyword={kw}"

                    try:

                        await page.goto(target_url, wait_until="domcontentloaded", timeout=self.timeout)

                        logger.info(f"  ✅ {proxy['server']} -> {url} 关键词「{kw}」第{i+1}次")

                    except Exception as e:

                        logger.error(f"  ❌ 点击失败: {e}")

                    await page.close()

                    await asyncio.sleep(random.uniform(2, 5))

                await asyncio.sleep(1)

            await context.close()

            await browser.close()



    async def run(self):

        if not WEBSITES_JSON.exists():

            logger.error(f"配置文件不存在: {WEBSITES_JSON}")

            return

        with open(WEBSITES_JSON, 'r') as f:

            data = json.load(f)

        # 兼容两种可能的 JSON 结构

        if isinstance(data, list):

            websites = data

        elif isinstance(data, dict) and 'websites' in data:

            websites = data['websites']

        else:

            logger.error("无法解析 websites.json 格式")

            return



        logger.info(f"📋 加载了 {len(websites)} 个网站")

        for site in websites:

            url = site.get('url')

            keywords = site.get('keywords', [])

            if not keywords:

                logger.warning(f"⚠️ 网站 {url} 没有关键词，跳过")

                continue

            logger.info(f"\n🌐 处理网站: {url}，共 {len(keywords)} 个关键词")

            # 将关键词分组，每组使用一个新代理

            for i in range(0, len(keywords), self.keywords_per_ip):

                batch = keywords[i:i+self.keywords_per_ip]

                proxy = await self.proxy_fetcher.get()

                if not proxy:

                    logger.error(f"❌ 无法获取代理，跳过批次 {batch}")

                    break

                logger.info(f"🔄 新代理 {proxy['server']} 处理 {len(batch)} 个关键词: {batch}")

                await self._click_batch(url, batch, proxy)

                await asyncio.sleep(1)  # 避免 API 限流

        logger.success("✅ 所有任务完成")



if __name__ == "__main__":

    asyncio.run(ClickOptimizer().run())

