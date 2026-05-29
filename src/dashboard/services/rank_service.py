"""
排名查询服务 - 使用 Playwright 渲染搜索引擎页面获取真实排名
（已移除Google，仅支持国内搜索引擎）
"""

import asyncio
import re
from urllib.parse import quote
from typing import Dict
from loguru import logger


class RankService:
    """排名查询服务类 - 使用 Playwright 渲染真实搜索结果"""

    # 搜索引擎URL模板（已移除Google）
    ENGINE_URLS = {
        'baidu': 'https://www.baidu.com/s?wd={keyword}&rn=50',
        'bing': 'https://www.bing.com/search?q={keyword}&count=50',
        '360': 'https://www.so.com/s?q={keyword}',
        'sogou': 'https://www.sogou.com/web?query={keyword}',
        'yisou': 'https://www.yisou.com/s?q={keyword}',
    }

    # PC端User-Agent
    PC_UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'

    # 移动端User-Agent
    MOBILE_UA = 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1'

    async def check_rank_async(self, keyword: str, domain: str, engine: str, device: str = "pc") -> Dict:
        """
        使用 Playwright 异步查询排名
        """
        url_template = self.ENGINE_URLS.get(engine)
        if not url_template:
            return {"engine": engine, "device": device, "rank": 0, "found": False}

        search_url = url_template.format(keyword=quote(keyword))
        ua = self.MOBILE_UA if device == "mobile" else self.PC_UA
        is_mobile = device == "mobile"

        try:
            from playwright.async_api import async_playwright

            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True,
                    args=[
                        '--disable-blink-features=AutomationControlled',
                        '--no-sandbox',
                        '--disable-dev-shm-usage',
                        '--disable-gpu',
                    ]
                )

                # 设置 User-Agent 和设备
                if is_mobile:
                    device_config = p.devices['iPhone 13']
                    context = await browser.new_context(
                        user_agent=ua,
                        **device_config
                    )
                else:
                    context = await browser.new_context(
                        user_agent=ua,
                        viewport={'width': 1920, 'height': 1080}
                    )

                page = await context.new_page()

                try:
                    await page.goto(search_url, wait_until="domcontentloaded", timeout=20000)

                    # 等待搜索结果加载（不同引擎等待不同元素）
                    if engine == 'baidu':
                        await page.wait_for_selector('#content_left', timeout=10000)
                    elif engine == 'bing':
                        await page.wait_for_selector('#b_results', timeout=10000)
                    elif engine == '360':
                        await page.wait_for_selector('.result', timeout=10000)
                    elif engine == 'sogou':
                        await page.wait_for_selector('.results', timeout=10000)
                    else:
                        await asyncio.sleep(3)

                    # 提取所有搜索结果链接
                    if engine == 'baidu':
                        # 百度：从 #content_left 中的结果链接提取
                        elements = await page.query_selector_all('#content_left .result a[href*="http"]')
                        links = []
                        seen = set()
                        for el in elements:
                            href = await el.get_attribute('href')
                            if href and href not in seen and href.startswith('http'):
                                links.append(href)
                                seen.add(href)
                    elif engine == 'bing':
                        elements = await page.query_selector_all('#b_results a[href^="http"]')
                        links = []
                        seen = set()
                        for el in elements:
                            href = await el.get_attribute('href')
                            if href and href not in seen:
                                links.append(href)
                                seen.add(href)
                    else:
                        # 通用方式：提取所有链接
                        all_links = await page.eval_on_selector_all('a[href^="http"]', 'els => els.map(e => e.href)')
                        links = list(dict.fromkeys(all_links))  # 去重保序

                    # 规范化 domain 用于匹配
                    domain_lower = domain.lower().replace('https://', '').replace('http://', '').rstrip('/')
                    if not domain_lower.startswith('www.'):
                        domain_variants = [domain_lower, 'www.' + domain_lower]
                    else:
                        domain_variants = [domain_lower, domain_lower[4:]]

                    position = 0
                    for i, link in enumerate(links):
                        link_lower = link.lower()
                        for variant in domain_variants:
                            if variant in link_lower:
                                position = i + 1
                                break
                        if position > 0:
                            break

                    if position > 0:
                        logger.info(f"🔍 [{engine}/{device}] '{keyword}' → {domain} 排名第 {position} 位")
                        return {"engine": engine, "device": device, "rank": position, "found": True}
                    else:
                        logger.info(f"🔍 [{engine}/{device}] '{keyword}' → {domain} 未找到 (前{len(links)}名)")
                        return {"engine": engine, "device": device, "rank": 0, "found": False}

                except Exception as e:
                    logger.error(f"排名查询页面加载失败 [{engine}/{device}]: {e}")
                    return {"engine": engine, "device": device, "rank": 0, "found": False, "error": str(e)}

                finally:
                    await context.close()
                    await browser.close()

        except Exception as e:
            logger.error(f"排名查询失败 [{engine}/{device}]: {e}")
            return {"engine": engine, "device": device, "rank": 0, "found": False, "error": str(e)}

    def check_rank(self, keyword: str, domain: str, engine: str, device: str = "pc") -> Dict:
        """
        同步接口：查询排名（在事件循环中运行异步方法）
        """
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # 如果已有事件循环在运行，创建新线程
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    future = pool.submit(asyncio.run, self.check_rank_async(keyword, domain, engine, device))
                    return future.result(timeout=30)
            else:
                return asyncio.run(self.check_rank_async(keyword, domain, engine, device))
        except RuntimeError:
            return asyncio.run(self.check_rank_async(keyword, domain, engine, device))

    def check_rank_multiple(self, keyword: str, domain: str, engines: list, device: str = "pc") -> list:
        """批量查询多个搜索引擎的排名"""
        results = []
        for engine in engines:
            result = self.check_rank(keyword, domain, engine, device)
            results.append(result)
        return results

    def get_supported_engines(self) -> list:
        """获取支持的搜索引擎列表"""
        return list(self.ENGINE_URLS.keys())


# 全局排名服务实例
rank_service = RankService()